import json
import os
import sys
from pathlib import Path

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
    from_json,
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
from spark_jobs.shared.runtime import (
    create_spark_session,
    default_checkpoint_base,
    normalize_mongo_records,
    reset_checkpoint_if_requested,
    write_dataframe_to_parquet,
)


CHECKPOINT_BASE = os.getenv(
    "YOUTUBE_CHECKPOINT_BASE", default_checkpoint_base("youtube_stream_processor")
)
ENABLE_MINIO_SINK = os.getenv("ENABLE_MINIO_SINK", "true").lower() == "true"
ENABLE_MONGO_SINK = os.getenv("ENABLE_MONGO_SINK", "true").lower() == "true"
ENABLE_ES_SINK = os.getenv("ENABLE_ES_SINK", "true").lower() == "true"
RESET_CHECKPOINT_ON_START = (
    os.getenv("RESET_CHECKPOINT_ON_START", "false").lower() == "true"
)


def read_kafka_json_stream(spark, topic: str, schema) -> DataFrame:
    raw_df = (
        spark.readStream.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
        .option("subscribe", topic)
        .option("startingOffsets", "latest")
        .load()
    )
    return raw_df.select(
        from_json(col("value").cast("string"), schema).alias("data")
    ).select("data.*")


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
    (
        batch_df.write.format("kafka")
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
        .option("topic", topic)
        .save()
    )


def write_content_to_mongo(batch_df: DataFrame, batch_id: int) -> None:
    records = [json.loads(row) for row in batch_df.toJSON().collect()]
    if not records:
        return
    records = normalize_mongo_records(records, ("published_at", "ingested_at", "event_time"))
    client = MongoClient(MONGO_URI)
    try:
        client[MONGO_DATABASE][YOUTUBE_CONTENT_EVENTS_COLLECTION].insert_many(
            records, ordered=False
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
    finally:
        client.close()


def write_metrics_to_mongo(batch_df: DataFrame, batch_id: int, collection: str) -> None:
    records = [json.loads(row) for row in batch_df.toJSON().collect()]
    if not records:
        return
    records = normalize_mongo_records(records, ("window_start", "window_end"))
    client = MongoClient(MONGO_URI)
    try:
        client[MONGO_DATABASE][collection].insert_many(records, ordered=False)
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
    finally:
        client.close()


def main() -> None:
    spark = create_spark_session("YouTubeAnalyticsPipeline")
    spark.sparkContext.setLogLevel("WARN")
    reset_checkpoint_if_requested(spark, CHECKPOINT_BASE, RESET_CHECKPOINT_ON_START)

    videos_df = read_kafka_json_stream(
        spark, RAW_YOUTUBE_VIDEOS_TOPIC, RAW_YOUTUBE_VIDEO_SPARK_SCHEMA
    )
    comments_df = read_kafka_json_stream(
        spark, RAW_YOUTUBE_COMMENTS_TOPIC, RAW_YOUTUBE_COMMENT_SPARK_SCHEMA
    )
    channels_df = read_kafka_json_stream(
        spark, RAW_YOUTUBE_CHANNELS_TOPIC, RAW_YOUTUBE_CHANNEL_SPARK_SCHEMA
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
        .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP_SERVERS)
        .option("topic", SILVER_YOUTUBE_CONTENT_EVENTS_TOPIC)
        .option("checkpointLocation", f"{CHECKPOINT_BASE}/raw_content_to_silver")
        .outputMode("append")
        .start(),
        build_channel_snapshot_sink_df(channel_snapshots_df)
        .writeStream.format("kafka")
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
        .option("checkpointLocation", f"{CHECKPOINT_BASE}/youtube_metrics_kafka")
        .outputMode("update")
        .start(),
    ]

    if ENABLE_MINIO_SINK:
        queries.extend(
            [
                content_df.writeStream.format("parquet")
                .option("path", f"s3a://{CLEAN_POSTS_BUCKET}/{YOUTUBE_CONTENT_EVENTS_PATH}")
                .option("checkpointLocation", f"{CHECKPOINT_BASE}/content_parquet")
                .outputMode("append")
                .start(),
                channel_snapshots_df.writeStream.format("parquet")
                .option(
                    "path",
                    f"s3a://{CLEAN_POSTS_BUCKET}/{YOUTUBE_CHANNEL_SNAPSHOTS_PATH}",
                )
                .option("checkpointLocation", f"{CHECKPOINT_BASE}/channels_parquet")
                .outputMode("append")
                .start(),
                sentiment_metrics_df.writeStream.foreachBatch(
                    lambda batch_df, batch_id: write_dataframe_to_parquet(
                        batch_df,
                        f"s3a://{AGGREGATES_BUCKET}/{YOUTUBE_AGGREGATES_PATH}/sentiment",
                    )
                )
                .option("checkpointLocation", f"{CHECKPOINT_BASE}/sentiment_parquet")
                .outputMode("update")
                .start(),
                trending_df.writeStream.foreachBatch(
                    lambda batch_df, batch_id: write_dataframe_to_parquet(
                        batch_df,
                        f"s3a://{AGGREGATES_BUCKET}/{YOUTUBE_AGGREGATES_PATH}/trending",
                    )
                )
                .option("checkpointLocation", f"{CHECKPOINT_BASE}/trending_parquet")
                .outputMode("update")
                .start(),
            ]
        )

    if ENABLE_MONGO_SINK:
        queries.extend(
            [
                content_df.writeStream.foreachBatch(write_content_to_mongo)
                .option("checkpointLocation", f"{CHECKPOINT_BASE}/mongo_content")
                .outputMode("append")
                .start(),
                channel_snapshots_df.writeStream.foreachBatch(write_channels_to_mongo)
                .option("checkpointLocation", f"{CHECKPOINT_BASE}/mongo_channels")
                .outputMode("append")
                .start(),
                sentiment_metrics_df.writeStream.foreachBatch(
                    lambda batch_df, batch_id: write_metrics_to_mongo(
                        batch_df, batch_id, YOUTUBE_SENTIMENT_COLLECTION
                    )
                )
                .option("checkpointLocation", f"{CHECKPOINT_BASE}/mongo_sentiment")
                .outputMode("update")
                .start(),
                trending_df.writeStream.foreachBatch(
                    lambda batch_df, batch_id: write_metrics_to_mongo(
                        batch_df, batch_id, YOUTUBE_TRENDING_COLLECTION
                    )
                )
                .option("checkpointLocation", f"{CHECKPOINT_BASE}/mongo_trending")
                .outputMode("update")
                .start(),
            ]
        )

    if ENABLE_ES_SINK:
        queries.extend(
            [
                content_df.writeStream.foreachBatch(write_content_to_es)
                .option("checkpointLocation", f"{CHECKPOINT_BASE}/es_content")
                .outputMode("append")
                .start(),
                channel_snapshots_df.writeStream.foreachBatch(write_channels_to_es)
                .option("checkpointLocation", f"{CHECKPOINT_BASE}/es_channels")
                .outputMode("append")
                .start(),
            ]
        )

    for query in queries:
        query.awaitTermination()


if __name__ == "__main__":
    main()
