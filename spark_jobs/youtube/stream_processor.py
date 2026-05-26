import json
import os
import sys
from pathlib import Path
import logging

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from elasticsearch import Elasticsearch
from pymongo import MongoClient, UpdateOne
from pyspark.sql import DataFrame
from pyspark.sql.functions import (
    coalesce,
    col,
    count,
    current_timestamp,
    explode,
    length,
    lit,
    lower,
    regexp_replace,
    split,
    struct,
    to_json,
    to_timestamp,
    trim,
    window,
)

from config.elasticsearch_config import ELASTICSEARCH_HOST
from config.kafka_config import (
    KAFKA_BOOTSTRAP_SERVERS,
    PIPELINE_DLQ_TOPIC,
    RAW_YOUTUBE_CHANNELS_TOPIC,
    RAW_YOUTUBE_COMMENTS_TOPIC,
    RAW_YOUTUBE_VIDEOS_TOPIC,
    SILVER_YOUTUBE_CHANNEL_SNAPSHOTS_TOPIC,
    SILVER_YOUTUBE_CONTENT_EVENTS_TOPIC,
    YOUTUBE_AGGREGATED_METRICS_TOPIC,
)
from config.minio_config import AGGREGATES_BUCKET, CLEAN_POSTS_BUCKET
from config.mongo_config import MONGO_DATABASE, MONGO_URI
from config.storage_config import (
    YOUTUBE_AGGREGATES_PATH,
    YOUTUBE_CHANNEL_SNAPSHOTS_COLLECTION,
    YOUTUBE_CHANNEL_SNAPSHOTS_INDEX,
    YOUTUBE_CHANNEL_SNAPSHOTS_PATH,
    YOUTUBE_CONTENT_EVENTS_COLLECTION,
    YOUTUBE_CONTENT_EVENTS_INDEX,
    YOUTUBE_CONTENT_EVENTS_PATH,
    YOUTUBE_SENTIMENT_COLLECTION,
    YOUTUBE_TRENDING_COLLECTION,
)
from schemas.youtube.raw_schema import (
    RAW_YOUTUBE_CHANNEL_SPARK_SCHEMA,
    RAW_YOUTUBE_COMMENT_SPARK_SCHEMA,
    RAW_YOUTUBE_VIDEO_SPARK_SCHEMA,
)
from spark_jobs.sentiment_udf import sentiment_udf
from spark_jobs.shared.quality import build_dlq_sink_df, split_valid_and_dlq_rows
from spark_jobs.shared.runtime import (
    create_spark_session,
    default_checkpoint_base,
    normalize_mongo_records,
    read_kafka_stream,
    reset_checkpoint_if_requested,
    write_dataframe_to_parquet,
)


log = logging.getLogger(__name__)

CHECKPOINT_BASE = os.getenv(
    "YOUTUBE_CHECKPOINT_BASE", default_checkpoint_base("youtube_stream_processor")
)
ENABLE_MINIO_SINK = os.getenv("ENABLE_MINIO_SINK", "true").lower() == "true"
ENABLE_MONGO_SINK = os.getenv("ENABLE_MONGO_SINK", "true").lower() == "true"
ENABLE_ES_SINK = os.getenv("ENABLE_ES_SINK", "true").lower() == "true"
FAIL_ON_OPTIONAL_SINK_ERROR = (
    os.getenv("FAIL_ON_OPTIONAL_SINK_ERROR", "false").lower() == "true"
)
RESET_CHECKPOINT_ON_START = (
    os.getenv("RESET_CHECKPOINT_ON_START", "false").lower() == "true"
)


def build_video_content_events(videos_df: DataFrame) -> DataFrame:
    return (
        videos_df.withColumn("event_time", to_timestamp(col("published_at")))
        .withColumn("event_time", coalesce(col("event_time"), current_timestamp()))
        .select(
            col("video_id").alias("entity_id"),
            coalesce(col("platform"), lit("youtube")).alias("platform"),
            lit("video").alias("entity_type"),
            lit(None).cast("string").alias("parent_entity_id"),
            trim(col("title")).alias("title"),
            trim(col("description")).alias("body_text"),
            col("channel_id").alias("author_id"),
            col("channel_title").alias("author_name"),
            col("source_url"),
            col("category_id").alias("category"),
            col("tags"),
            col("published_at"),
            col("ingested_at"),
            col("event_time"),
            col("view_count").cast("long").alias("engagement_view_count"),
            col("like_count").cast("long").alias("engagement_like_count"),
            col("comment_count").cast("long").alias("engagement_comment_count"),
        )
        .filter(col("entity_id").isNotNull())
        .withColumn("sentiment", sentiment_udf(coalesce(col("title"), col("body_text"))))
        .withWatermark("event_time", "10 minutes")
        .dropDuplicates(["entity_id"])
    )


def build_comment_content_events(comments_df: DataFrame) -> DataFrame:
    return (
        comments_df.withColumn("event_time", to_timestamp(col("published_at")))
        .withColumn("event_time", coalesce(col("event_time"), current_timestamp()))
        .select(
            col("comment_id").alias("entity_id"),
            coalesce(col("platform"), lit("youtube")).alias("platform"),
            lit("comment").alias("entity_type"),
            col("video_id").alias("parent_entity_id"),
            lit(None).cast("string").alias("title"),
            trim(col("text")).alias("body_text"),
            col("author_channel_id").alias("author_id"),
            col("author").alias("author_name"),
            col("source_url"),
            lit(None).cast("string").alias("category"),
            lit(None).cast("string").alias("tags"),
            col("published_at"),
            col("ingested_at"),
            col("event_time"),
            lit(None).cast("long").alias("engagement_view_count"),
            col("like_count").cast("long").alias("engagement_like_count"),
            lit(None).cast("long").alias("engagement_comment_count"),
        )
        .filter(col("entity_id").isNotNull())
        .withColumn("sentiment", sentiment_udf(coalesce(col("body_text"), lit(""))))
        .withWatermark("event_time", "10 minutes")
        .dropDuplicates(["entity_id"])
    )


def build_channel_snapshots(channels_df: DataFrame) -> DataFrame:
    return (
        channels_df.withColumn("event_time", to_timestamp(col("crawled_at")))
        .withColumn("event_time", coalesce(col("event_time"), current_timestamp()))
        .select(
            "channel_id",
            "channel_name",
            "description",
            "country",
            "published_at",
            col("subscriber_count").cast("long").alias("subscriber_count"),
            col("video_count").cast("long").alias("video_count"),
            col("view_count").cast("long").alias("view_count"),
            "thumbnail_url",
            "source_url",
            "crawled_at",
            "ingested_at",
            "event_time",
        )
        .filter(col("channel_id").isNotNull())
        .withWatermark("event_time", "10 minutes")
        .dropDuplicates(["channel_id", "crawled_at"])
    )


def build_silver_content_sink_df(content_df: DataFrame) -> DataFrame:
    return content_df.select(
        col("entity_id").cast("string").alias("key"),
        to_json(struct(*content_df.columns)).alias("value"),
    )


def build_channel_snapshot_sink_df(channel_df: DataFrame) -> DataFrame:
    return channel_df.select(
        col("channel_id").cast("string").alias("key"),
        to_json(struct(*channel_df.columns)).alias("value"),
    )


def build_sentiment_metrics_df(content_df: DataFrame) -> DataFrame:
    return (
        content_df.groupBy(
            window(col("event_time"), "15 minutes"),
            col("entity_type"),
            col("sentiment"),
        )
        .agg(count("*").alias("event_count"))
        .select(
            lit("youtube_sentiment").alias("metric_type"),
            "entity_type",
            "sentiment",
            "event_count",
            col("window.start").alias("window_start"),
            col("window.end").alias("window_end"),
        )
    )


def build_trending_keywords_df(content_df: DataFrame) -> DataFrame:
    text_df = content_df.select(
        col("event_time"),
        explode(split(coalesce(col("title"), col("body_text")), r"\s+")).alias(
            "raw_keyword"
        ),
    )
    return (
        text_df.withColumn(
            "keyword",
            trim(regexp_replace(lower(col("raw_keyword")), r"^[^\w]+|[^\w]+$", "")),
        )
        .filter(length(col("keyword")) > 3)
        .groupBy(window(col("event_time"), "1 hour", "15 minutes"), col("keyword"))
        .agg(count("*").alias("frequency"))
    )


def build_aggregated_metrics_sink_df(
    sentiment_metrics_df: DataFrame, trending_df: DataFrame
) -> DataFrame:
    sentiment_json_df = sentiment_metrics_df.select(
        lit("youtube_sentiment").alias("key"),
        to_json(struct(*sentiment_metrics_df.columns)).alias("value"),
    )
    trending_json_df = trending_df.select(
        lit("youtube_trending").alias("key"),
        to_json(
            struct(
                lit("youtube_trending").alias("metric_type"),
                col("keyword"),
                col("frequency"),
                col("window.start").alias("window_start"),
                col("window.end").alias("window_end"),
            )
        ).alias("value"),
    )
    return sentiment_json_df.unionByName(trending_json_df)


def write_to_kafka(batch_df: DataFrame, batch_id: int, topic: str) -> None:
    if batch_df.rdd.isEmpty():
        return
    row_count = batch_df.count()
    (
        batch_df.write.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
        .option("topic", topic)
        .save()
    )
    log.info("Batch %s wrote %s rows to Kafka topic %s", batch_id, row_count, topic)


def run_optional_sink(
    sink_name: str,
    batch_df: DataFrame,
    batch_id: int,
    writer,
    *,
    strict: bool = FAIL_ON_OPTIONAL_SINK_ERROR,
) -> None:
    try:
        writer(batch_df, batch_id)
        log.info("Batch %s completed optional sink %s", batch_id, sink_name)
    except Exception:
        log.exception("Batch %s failed optional sink %s", batch_id, sink_name)
        if strict:
            raise


def write_content_to_mongo(batch_df: DataFrame, batch_id: int) -> None:
    records = [json.loads(row) for row in batch_df.toJSON().collect()]
    if not records:
        return
    records = normalize_mongo_records(records, ("published_at", "ingested_at", "event_time"))
    client = MongoClient(MONGO_URI)
    try:
        operations = [
            UpdateOne({"entity_id": record["entity_id"]}, {"$set": record}, upsert=True)
            for record in records
        ]
        if operations:
            client[MONGO_DATABASE][YOUTUBE_CONTENT_EVENTS_COLLECTION].bulk_write(
                operations, ordered=False
            )
            log.info(
                "Batch %s upserted %s YouTube content rows into MongoDB collection %s",
                batch_id,
                len(operations),
                YOUTUBE_CONTENT_EVENTS_COLLECTION,
            )
    finally:
        client.close()


def write_channels_to_mongo(batch_df: DataFrame, batch_id: int) -> None:
    records = [json.loads(row) for row in batch_df.toJSON().collect()]
    if not records:
        return
    records = normalize_mongo_records(
        records, ("published_at", "crawled_at", "ingested_at", "event_time")
    )
    client = MongoClient(MONGO_URI)
    try:
        operations = [
            UpdateOne(
                {"channel_id": record["channel_id"], "crawled_at": record["crawled_at"]},
                {"$set": record},
                upsert=True,
            )
            for record in records
        ]
        if operations:
            client[MONGO_DATABASE][YOUTUBE_CHANNEL_SNAPSHOTS_COLLECTION].bulk_write(
                operations, ordered=False
            )
            log.info(
                "Batch %s upserted %s YouTube channel rows into MongoDB collection %s",
                batch_id,
                len(operations),
                YOUTUBE_CHANNEL_SNAPSHOTS_COLLECTION,
            )
    finally:
        client.close()


def flatten_windowed_metric_record(record: dict) -> dict:
    normalized = record.copy()
    window = normalized.pop("window", None)
    if isinstance(window, dict):
        normalized.setdefault("window_start", window.get("start"))
        normalized.setdefault("window_end", window.get("end"))
    return normalized


def write_metrics_to_mongo(batch_df: DataFrame, batch_id: int, collection: str) -> None:
    records = [json.loads(row) for row in batch_df.toJSON().collect()]
    if not records:
        return
    if collection == YOUTUBE_TRENDING_COLLECTION:
        records = [flatten_windowed_metric_record(record) for record in records]
    records = normalize_mongo_records(records, ("window_start", "window_end"))
    client = MongoClient(MONGO_URI)
    try:
        if collection == YOUTUBE_SENTIMENT_COLLECTION:
            operations = [
                UpdateOne(
                    {
                        "window_start": record["window_start"],
                        "window_end": record["window_end"],
                        "entity_type": record["entity_type"],
                        "sentiment": record["sentiment"],
                    },
                    {"$set": record},
                    upsert=True,
                )
                for record in records
            ]
        else:
            operations = [
                UpdateOne(
                    {
                        "window_start": record["window_start"],
                        "window_end": record["window_end"],
                        "keyword": record["keyword"],
                    },
                    {"$set": record},
                    upsert=True,
                )
                for record in records
            ]
        if operations:
            client[MONGO_DATABASE][collection].bulk_write(operations, ordered=False)
            log.info(
                "Batch %s upserted %s YouTube metric rows into MongoDB collection %s",
                batch_id,
                len(operations),
                collection,
            )
    finally:
        client.close()


def write_content_to_es(batch_df: DataFrame, batch_id: int) -> None:
    records = [json.loads(row) for row in batch_df.toJSON().collect()]
    if not records:
        return
    client = Elasticsearch(ELASTICSEARCH_HOST)
    try:
        for record in records:
            client.index(
                index=YOUTUBE_CONTENT_EVENTS_INDEX,
                id=record["entity_id"],
                document=record,
            )
        log.info(
            "Batch %s indexed %s YouTube content rows into Elasticsearch index %s",
            batch_id,
            len(records),
            YOUTUBE_CONTENT_EVENTS_INDEX,
        )
    finally:
        client.close()


def write_channels_to_es(batch_df: DataFrame, batch_id: int) -> None:
    records = [json.loads(row) for row in batch_df.toJSON().collect()]
    if not records:
        return
    client = Elasticsearch(ELASTICSEARCH_HOST)
    try:
        for record in records:
            document_id = f"{record['channel_id']}:{record['crawled_at']}"
            client.index(
                index=YOUTUBE_CHANNEL_SNAPSHOTS_INDEX,
                id=document_id,
                document=record,
            )
        log.info(
            "Batch %s indexed %s YouTube channel rows into Elasticsearch index %s",
            batch_id,
            len(records),
            YOUTUBE_CHANNEL_SNAPSHOTS_INDEX,
        )
    finally:
        client.close()


def main() -> None:
    spark = create_spark_session("YouTubeAnalyticsPipeline")
    spark.sparkContext.setLogLevel("WARN")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    reset_checkpoint_if_requested(spark, CHECKPOINT_BASE, RESET_CHECKPOINT_ON_START)

    videos_df, videos_dlq_df = split_valid_and_dlq_rows(
        read_kafka_stream(spark, RAW_YOUTUBE_VIDEOS_TOPIC),
        RAW_YOUTUBE_VIDEO_SPARK_SCHEMA,
        required_fields=["video_id", "title", "channel_id"],
        source_pipeline="youtube_videos",
    )
    comments_df, comments_dlq_df = split_valid_and_dlq_rows(
        read_kafka_stream(spark, RAW_YOUTUBE_COMMENTS_TOPIC),
        RAW_YOUTUBE_COMMENT_SPARK_SCHEMA,
        required_fields=["comment_id", "video_id", "text"],
        source_pipeline="youtube_comments",
    )
    channels_df, channels_dlq_df = split_valid_and_dlq_rows(
        read_kafka_stream(spark, RAW_YOUTUBE_CHANNELS_TOPIC),
        RAW_YOUTUBE_CHANNEL_SPARK_SCHEMA,
        required_fields=["channel_id", "channel_name"],
        source_pipeline="youtube_channels",
    )
    youtube_dlq_df = (
        videos_dlq_df.unionByName(comments_dlq_df).unionByName(channels_dlq_df)
    )

    content_df = build_video_content_events(videos_df).unionByName(
        build_comment_content_events(comments_df)
    )
    channel_snapshots_df = build_channel_snapshots(channels_df)
    sentiment_metrics_df = build_sentiment_metrics_df(content_df)
    trending_df = build_trending_keywords_df(content_df)

    queries = [
        build_silver_content_sink_df(content_df)
        .writeStream.format("kafka")
        .queryName("youtube_silver_content_kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
        .option("topic", SILVER_YOUTUBE_CONTENT_EVENTS_TOPIC)
        .option("checkpointLocation", f"{CHECKPOINT_BASE}/raw_content_to_silver")
        .outputMode("append")
        .start(),
        build_channel_snapshot_sink_df(channel_snapshots_df)
        .writeStream.format("kafka")
        .queryName("youtube_silver_channels_kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
        .option("topic", SILVER_YOUTUBE_CHANNEL_SNAPSHOTS_TOPIC)
        .option("checkpointLocation", f"{CHECKPOINT_BASE}/raw_channels_to_silver")
        .outputMode("append")
        .start(),
        build_aggregated_metrics_sink_df(sentiment_metrics_df, trending_df)
        .writeStream.foreachBatch(
            lambda batch_df, batch_id: write_to_kafka(
                batch_df, batch_id, YOUTUBE_AGGREGATED_METRICS_TOPIC
            )
        )
        .queryName("youtube_gold_metrics_kafka")
        .option("checkpointLocation", f"{CHECKPOINT_BASE}/youtube_metrics_kafka")
        .outputMode("update")
        .start(),
        build_dlq_sink_df(youtube_dlq_df)
        .writeStream.format("kafka")
        .queryName("youtube_dlq_kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
        .option("topic", PIPELINE_DLQ_TOPIC)
        .option("checkpointLocation", f"{CHECKPOINT_BASE}/youtube_dlq")
        .outputMode("append")
        .start(),
    ]

    if ENABLE_MINIO_SINK:
        queries.extend(
            [
                content_df.writeStream.foreachBatch(
                    lambda batch_df, batch_id: run_optional_sink(
                        "minio_content_parquet",
                        batch_df,
                        batch_id,
                        lambda inner_df, inner_batch_id: write_dataframe_to_parquet(
                            inner_df,
                            f"s3a://{CLEAN_POSTS_BUCKET}/{YOUTUBE_CONTENT_EVENTS_PATH}",
                        ),
                    )
                )
                .queryName("youtube_minio_content")
                .option("checkpointLocation", f"{CHECKPOINT_BASE}/content_parquet")
                .outputMode("append")
                .start(),
                channel_snapshots_df.writeStream.foreachBatch(
                    lambda batch_df, batch_id: run_optional_sink(
                        "minio_channel_parquet",
                        batch_df,
                        batch_id,
                        lambda inner_df, inner_batch_id: write_dataframe_to_parquet(
                            inner_df,
                            f"s3a://{CLEAN_POSTS_BUCKET}/{YOUTUBE_CHANNEL_SNAPSHOTS_PATH}",
                        ),
                    )
                )
                .queryName("youtube_minio_channels")
                .option("checkpointLocation", f"{CHECKPOINT_BASE}/channels_parquet")
                .outputMode("append")
                .start(),
                sentiment_metrics_df.writeStream.foreachBatch(
                    lambda batch_df, batch_id: run_optional_sink(
                        "minio_sentiment_parquet",
                        batch_df,
                        batch_id,
                        lambda inner_df, inner_batch_id: write_dataframe_to_parquet(
                            inner_df,
                            f"s3a://{AGGREGATES_BUCKET}/{YOUTUBE_AGGREGATES_PATH}/sentiment",
                        ),
                    )
                )
                .queryName("youtube_minio_sentiment")
                .option("checkpointLocation", f"{CHECKPOINT_BASE}/sentiment_parquet")
                .outputMode("update")
                .start(),
                trending_df.writeStream.foreachBatch(
                    lambda batch_df, batch_id: run_optional_sink(
                        "minio_trending_parquet",
                        batch_df,
                        batch_id,
                        lambda inner_df, inner_batch_id: write_dataframe_to_parquet(
                            inner_df,
                            f"s3a://{AGGREGATES_BUCKET}/{YOUTUBE_AGGREGATES_PATH}/trending",
                        ),
                    )
                )
                .queryName("youtube_minio_trending")
                .option("checkpointLocation", f"{CHECKPOINT_BASE}/trending_parquet")
                .outputMode("update")
                .start(),
            ]
        )

    if ENABLE_MONGO_SINK:
        queries.extend(
            [
                content_df.writeStream.foreachBatch(
                    lambda batch_df, batch_id: run_optional_sink(
                        "mongo_content",
                        batch_df,
                        batch_id,
                        write_content_to_mongo,
                    )
                )
                .queryName("youtube_mongo_content")
                .option("checkpointLocation", f"{CHECKPOINT_BASE}/mongo_content")
                .outputMode("append")
                .start(),
                channel_snapshots_df.writeStream.foreachBatch(
                    lambda batch_df, batch_id: run_optional_sink(
                        "mongo_channels",
                        batch_df,
                        batch_id,
                        write_channels_to_mongo,
                    )
                )
                .queryName("youtube_mongo_channels")
                .option("checkpointLocation", f"{CHECKPOINT_BASE}/mongo_channels")
                .outputMode("append")
                .start(),
                sentiment_metrics_df.writeStream.foreachBatch(
                    lambda batch_df, batch_id: run_optional_sink(
                        "mongo_sentiment",
                        batch_df,
                        batch_id,
                        lambda inner_df, inner_batch_id: write_metrics_to_mongo(
                            inner_df, inner_batch_id, YOUTUBE_SENTIMENT_COLLECTION
                        ),
                    )
                )
                .queryName("youtube_mongo_sentiment")
                .option("checkpointLocation", f"{CHECKPOINT_BASE}/mongo_sentiment")
                .outputMode("update")
                .start(),
                trending_df.writeStream.foreachBatch(
                    lambda batch_df, batch_id: run_optional_sink(
                        "mongo_trending",
                        batch_df,
                        batch_id,
                        lambda inner_df, inner_batch_id: write_metrics_to_mongo(
                            inner_df, inner_batch_id, YOUTUBE_TRENDING_COLLECTION
                        ),
                    )
                )
                .queryName("youtube_mongo_trending")
                .option("checkpointLocation", f"{CHECKPOINT_BASE}/mongo_trending")
                .outputMode("update")
                .start(),
            ]
        )

    if ENABLE_ES_SINK:
        queries.extend(
            [
                content_df.writeStream.foreachBatch(
                    lambda batch_df, batch_id: run_optional_sink(
                        "elasticsearch_content",
                        batch_df,
                        batch_id,
                        write_content_to_es,
                    )
                )
                .queryName("youtube_es_content")
                .option("checkpointLocation", f"{CHECKPOINT_BASE}/es_content")
                .outputMode("append")
                .start(),
                channel_snapshots_df.writeStream.foreachBatch(
                    lambda batch_df, batch_id: run_optional_sink(
                        "elasticsearch_channels",
                        batch_df,
                        batch_id,
                        write_channels_to_es,
                    )
                )
                .queryName("youtube_es_channels")
                .option("checkpointLocation", f"{CHECKPOINT_BASE}/es_channels")
                .outputMode("append")
                .start(),
            ]
        )

    for query in queries:
        query.awaitTermination()


if __name__ == "__main__":
    main()
