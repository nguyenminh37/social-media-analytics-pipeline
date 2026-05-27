import json
import logging
import os
import shutil
from datetime import datetime

from elasticsearch import Elasticsearch, helpers
from pymongo import MongoClient, ReplaceOne
from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    array_join,
    coalesce,
    col,
    concat_ws,
    count,
    current_timestamp,
    explode,
    lit,
    min as spark_min,
    struct,
    to_json,
    to_timestamp,
    udf,
    when,
    window,
)
from pyspark.sql.types import ArrayType, StringType, StructField, StructType

from config.kafka_config import (
    KAFKA_BOOTSTRAP_SERVERS,
    PUBLIC_TREND_ALERTS_TOPIC,
    PUBLIC_TREND_METRICS_TOPIC,
    RAW_NEWS_ARTICLES_TOPIC,
    RAW_YOUTUBE_RSS_VIDEOS_TOPIC,
    SILVER_PUBLIC_CONTENT_EVENTS_TOPIC,
)
from config.mongo_config import MONGO_DATABASE, MONGO_URI
from config.minio_config import AGGREGATES_BUCKET, CLEAN_POSTS_BUCKET
from config.storage_config import (
    PUBLIC_CONTENT_EVENTS_COLLECTION,
    PUBLIC_CONTENT_EVENTS_INDEX,
    PUBLIC_CONTENT_EVENTS_PATH,
    PUBLIC_TREND_ALERTS_COLLECTION,
    PUBLIC_TREND_ALERTS_INDEX,
    PUBLIC_TREND_METRICS_COLLECTION,
    PUBLIC_TREND_METRICS_INDEX,
    PUBLIC_TREND_METRICS_PATH,
)
from spark_jobs.public_content.text_features import (
    extract_keywords,
)
from spark_jobs.shared.runtime import (
    create_spark_session,
    default_checkpoint_base,
    read_kafka_stream,
    reset_checkpoint_if_requested as reset_spark_checkpoint,
)


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
ENABLE_MINIO_SINK = os.getenv("ENABLE_MINIO_SINK", "true").lower() == "true"
ENABLE_MONGO_SINK = os.getenv("ENABLE_MONGO_SINK", "true").lower() == "true"
ENABLE_ES_SINK = os.getenv("ENABLE_ES_SINK", "true").lower() == "true"
STRICT_SINKS = os.getenv("STRICT_SINKS", "false").lower() == "true"
TREND_ALERT_MIN_CONTENT_COUNT = int(os.getenv("TREND_ALERT_MIN_CONTENT_COUNT", "4"))
CHECKPOINT_BASE = os.getenv(
    "PUBLIC_CONTENT_CHECKPOINT_BASE",
    default_checkpoint_base("public_content_stream_processor"),
)

extract_keywords_udf = udf(extract_keywords, ArrayType(StringType()))

NEWS_SCHEMA = StructType(
    [
        StructField("article_id", StringType(), True),
        StructField("platform", StringType(), True),
        StructField("source", StringType(), True),
        StructField("source_category", StringType(), True),
        StructField("title", StringType(), True),
        StructField("summary", StringType(), True),
        StructField("url", StringType(), True),
        StructField("published_at", StringType(), True),
        StructField("ingested_at", StringType(), True),
    ]
)

YOUTUBE_RSS_SCHEMA = StructType(
    [
        StructField("video_id", StringType(), True),
        StructField("platform", StringType(), True),
        StructField("source", StringType(), True),
        StructField("source_category", StringType(), True),
        StructField("channel_id", StringType(), True),
        StructField("channel_title", StringType(), True),
        StructField("title", StringType(), True),
        StructField("summary", StringType(), True),
        StructField("url", StringType(), True),
        StructField("published_at", StringType(), True),
        StructField("updated_at", StringType(), True),
        StructField("ingested_at", StringType(), True),
    ]
)


def reset_checkpoint_if_requested(spark) -> None:
    if os.getenv("RESET_CHECKPOINT_ON_START", "false").lower() != "true":
        return
    if CHECKPOINT_BASE.startswith("/"):
        shutil.rmtree(CHECKPOINT_BASE, ignore_errors=True)
        log.info("Removed checkpoint directory %s", CHECKPOINT_BASE)
        return
    reset_spark_checkpoint(spark, CHECKPOINT_BASE, True)


def parse_json_stream(stream: DataFrame, schema: StructType) -> DataFrame:
    from pyspark.sql.functions import from_json

    return stream.select(
        from_json(col("value").cast("string"), schema).alias("payload")
    ).select("payload.*")


def build_normalized_content_df(news_df: DataFrame, youtube_df: DataFrame) -> DataFrame:
    normalized_news = news_df.select(
        col("article_id").alias("content_id"),
        lit("article").alias("content_type"),
        col("platform"),
        col("source"),
        col("source_category"),
        col("title"),
        col("summary"),
        col("url").alias("source_url"),
        col("published_at"),
        col("ingested_at"),
        lit(None).cast("string").alias("channel_id"),
        lit(None).cast("string").alias("channel_title"),
    )
    normalized_youtube = youtube_df.select(
        col("video_id").alias("content_id"),
        lit("video").alias("content_type"),
        col("platform"),
        col("source"),
        col("source_category"),
        col("title"),
        col("summary"),
        col("url").alias("source_url"),
        col("published_at"),
        col("ingested_at"),
        col("channel_id"),
        col("channel_title"),
    )
    return (
        normalized_news.unionByName(normalized_youtube)
        .withColumn("body_text", concat_ws(" ", col("title"), col("summary")))
        .withColumn(
            "event_time",
            coalesce(to_timestamp("published_at"), to_timestamp("ingested_at"), current_timestamp()),
        )
        .withColumn("keywords", extract_keywords_udf(col("body_text")))
        .withColumn("keyword_text", array_join(col("keywords"), " "))
        .withColumn("sentiment", lit(None).cast("string"))
        .withColumn("sentiment_model", lit(None).cast("string"))
        .filter(col("content_id").isNotNull())
        .withWatermark("event_time", "2 hours")
        .dropDuplicates(["content_id"])
    )


def build_trend_metrics_df(content_df: DataFrame) -> DataFrame:
    keyword_events = content_df.select(
        col("event_time"),
        col("content_id"),
        col("platform"),
        col("source"),
        explode(col("keywords")).alias("keyword"),
    ).filter(col("keyword").isNotNull())

    return (
        keyword_events.groupBy(window(col("event_time"), "1 hour", "15 minutes"), col("keyword"))
        .agg(
            count("*").alias("content_count"),
            spark_min(when(col("platform") == "news", col("event_time"))).alias("first_news_time"),
            spark_min(when(col("platform") == "youtube", col("event_time"))).alias("first_youtube_time"),
        )
        .withColumn("window_start", col("window.start"))
        .withColumn("window_end", col("window.end"))
        .withColumn(
            "youtube_lag_minutes",
            when(
                col("first_news_time").isNotNull() & col("first_youtube_time").isNotNull(),
                (col("first_youtube_time").cast("long") - col("first_news_time").cast("long")) / 60,
            ),
        )
        .withColumn("trend_score", col("content_count").cast("double"))
        .drop("window")
    )


def build_alerts_df(trend_df: DataFrame) -> DataFrame:
    return (
        trend_df.filter(col("content_count") >= TREND_ALERT_MIN_CONTENT_COUNT)
        .withColumn("alert_type", lit("trend_spike"))
        .withColumn(
            "message",
            concat_ws(
                " ",
                lit("Topic"),
                col("keyword"),
                lit("reached"),
                col("content_count").cast("string"),
                lit("mentions in the latest trend window"),
            ),
        )
    )


def _json_ready(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    return value


def dataframe_records(df: DataFrame, json_safe: bool = False) -> list[dict]:
    records = [row.asDict(recursive=True) for row in df.collect()]
    if json_safe:
        return [_json_ready(record) for record in records]
    return records


def write_mongo(df: DataFrame, batch_id: int, collection_name: str, key_fields: list[str]) -> None:
    records = dataframe_records(df)
    if not records:
        return
    operations = [
        ReplaceOne({field: record.get(field) for field in key_fields}, record, upsert=True)
        for record in records
    ]
    with MongoClient(MONGO_URI) as client:
        client[MONGO_DATABASE][collection_name].bulk_write(operations, ordered=False)
    log.info("Wrote %s records to Mongo collection %s", len(records), collection_name)


def write_elasticsearch(df: DataFrame, batch_id: int, index_name: str, id_fields: list[str]) -> None:
    records = dataframe_records(df, json_safe=True)
    if not records:
        return
    client = Elasticsearch(ELASTICSEARCH_HOST)
    actions = []
    for record in records:
        document_id = ":".join(str(record.get(field, "")) for field in id_fields)
        actions.append({"_op_type": "index", "_index": index_name, "_id": document_id, "_source": record})
    helpers.bulk(client, actions)
    log.info("Indexed %s records to Elasticsearch index %s", len(records), index_name)


def run_optional_sink(name: str, df: DataFrame, batch_id: int, writer, strict: bool = STRICT_SINKS) -> None:
    try:
        writer(df, batch_id)
    except Exception as exc:
        log.exception("Sink %s failed for batch %s: %s", name, batch_id, exc)
        if strict:
            raise


def write_content_batch(df: DataFrame, batch_id: int) -> None:
    if ENABLE_MONGO_SINK:
        run_optional_sink(
            "mongo_public_content",
            df,
            batch_id,
            lambda batch_df, inner_id: write_mongo(
                batch_df, inner_id, PUBLIC_CONTENT_EVENTS_COLLECTION, ["content_id"]
            ),
        )
    if ENABLE_ES_SINK:
        run_optional_sink(
            "es_public_content",
            df,
            batch_id,
            lambda batch_df, inner_id: write_elasticsearch(
                batch_df, inner_id, PUBLIC_CONTENT_EVENTS_INDEX, ["content_id"]
            ),
        )


def write_trend_batch(df: DataFrame, batch_id: int) -> None:
    if ENABLE_MONGO_SINK:
        run_optional_sink(
            "mongo_public_trends",
            df,
            batch_id,
            lambda batch_df, inner_id: write_mongo(
                batch_df,
                inner_id,
                PUBLIC_TREND_METRICS_COLLECTION,
                ["keyword", "window_start", "window_end"],
            ),
        )
    if ENABLE_ES_SINK:
        run_optional_sink(
            "es_public_trends",
            df,
            batch_id,
            lambda batch_df, inner_id: write_elasticsearch(
                batch_df,
                inner_id,
                PUBLIC_TREND_METRICS_INDEX,
                ["keyword", "window_start", "window_end"],
            ),
        )


def write_alert_batch(df: DataFrame, batch_id: int) -> None:
    if ENABLE_MONGO_SINK:
        run_optional_sink(
            "mongo_public_alerts",
            df,
            batch_id,
            lambda batch_df, inner_id: write_mongo(
                batch_df,
                inner_id,
                PUBLIC_TREND_ALERTS_COLLECTION,
                ["keyword", "window_start", "window_end", "alert_type"],
            ),
        )
    if ENABLE_ES_SINK:
        run_optional_sink(
            "es_public_alerts",
            df,
            batch_id,
            lambda batch_df, inner_id: write_elasticsearch(
                batch_df,
                inner_id,
                PUBLIC_TREND_ALERTS_INDEX,
                ["keyword", "window_start", "window_end", "alert_type"],
            ),
        )


def write_kafka_stream(df: DataFrame, topic: str, checkpoint_name: str):
    return (
        df.select(to_json(struct("*")).alias("value"))
        .writeStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
        .option("topic", topic)
        .option("checkpointLocation", f"{CHECKPOINT_BASE}/{checkpoint_name}")
        .outputMode("append")
        .start()
    )


def main() -> None:
    spark = create_spark_session("public-content-stream-processor")
    reset_checkpoint_if_requested(spark)

    news_df = parse_json_stream(read_kafka_stream(spark, RAW_NEWS_ARTICLES_TOPIC), NEWS_SCHEMA)
    youtube_df = parse_json_stream(
        read_kafka_stream(spark, RAW_YOUTUBE_RSS_VIDEOS_TOPIC), YOUTUBE_RSS_SCHEMA
    )
    content_df = build_normalized_content_df(news_df, youtube_df)
    trend_df = build_trend_metrics_df(content_df)
    alerts_df = build_alerts_df(trend_df)

    queries = [
        write_kafka_stream(content_df, SILVER_PUBLIC_CONTENT_EVENTS_TOPIC, "kafka_content"),
        write_kafka_stream(trend_df, PUBLIC_TREND_METRICS_TOPIC, "kafka_trends"),
        write_kafka_stream(alerts_df, PUBLIC_TREND_ALERTS_TOPIC, "kafka_alerts"),
        content_df.writeStream.foreachBatch(write_content_batch)
        .option("checkpointLocation", f"{CHECKPOINT_BASE}/mongo_es_content")
        .outputMode("append")
        .start(),
        trend_df.writeStream.foreachBatch(write_trend_batch)
        .option("checkpointLocation", f"{CHECKPOINT_BASE}/mongo_es_trends")
        .outputMode("update")
        .start(),
        alerts_df.writeStream.foreachBatch(write_alert_batch)
        .option("checkpointLocation", f"{CHECKPOINT_BASE}/mongo_es_alerts")
        .outputMode("update")
        .start(),
    ]

    if ENABLE_MINIO_SINK:
        queries.extend(
            [
                content_df.writeStream.format("parquet")
                .option("checkpointLocation", f"{CHECKPOINT_BASE}/minio_content")
                .option("path", f"s3a://{CLEAN_POSTS_BUCKET}/{PUBLIC_CONTENT_EVENTS_PATH}")
                .outputMode("append")
                .start(),
                trend_df.writeStream.format("parquet")
                .option("checkpointLocation", f"{CHECKPOINT_BASE}/minio_trends")
                .option("path", f"s3a://{AGGREGATES_BUCKET}/{PUBLIC_TREND_METRICS_PATH}")
                .outputMode("append")
                .start(),
            ]
        )

    spark.streams.awaitAnyTermination()
    for query in queries:
        query.stop()


if __name__ == "__main__":
    main()
