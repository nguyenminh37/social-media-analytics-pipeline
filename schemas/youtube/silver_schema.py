from pyspark.sql.types import LongType, StringType, StructField, StructType, TimestampType


SILVER_YOUTUBE_CONTENT_EVENT_FIELDS = [
    "entity_id",
    "platform",
    "entity_type",
    "parent_entity_id",
    "title",
    "body_text",
    "author_id",
    "author_name",
    "source_url",
    "category",
    "tags",
    "published_at",
    "ingested_at",
    "event_time",
    "engagement_view_count",
    "engagement_like_count",
    "engagement_comment_count",
    "sentiment",
]

SILVER_YOUTUBE_CHANNEL_SNAPSHOT_FIELDS = [
    "channel_id",
    "channel_name",
    "description",
    "country",
    "published_at",
    "subscriber_count",
    "video_count",
    "view_count",
    "thumbnail_url",
    "source_url",
    "crawled_at",
    "ingested_at",
    "event_time",
]

SILVER_YOUTUBE_CONTENT_EVENT_SPARK_SCHEMA = StructType(
    [
        StructField("entity_id", StringType(), True),
        StructField("platform", StringType(), True),
        StructField("entity_type", StringType(), True),
        StructField("parent_entity_id", StringType(), True),
        StructField("title", StringType(), True),
        StructField("body_text", StringType(), True),
        StructField("author_id", StringType(), True),
        StructField("author_name", StringType(), True),
        StructField("source_url", StringType(), True),
        StructField("category", StringType(), True),
        StructField("tags", StringType(), True),
        StructField("published_at", StringType(), True),
        StructField("ingested_at", StringType(), True),
        StructField("event_time", TimestampType(), True),
        StructField("engagement_view_count", LongType(), True),
        StructField("engagement_like_count", LongType(), True),
        StructField("engagement_comment_count", LongType(), True),
        StructField("sentiment", StringType(), True),
    ]
)

SILVER_YOUTUBE_CHANNEL_SNAPSHOT_SPARK_SCHEMA = StructType(
    [
        StructField("channel_id", StringType(), True),
        StructField("channel_name", StringType(), True),
        StructField("description", StringType(), True),
        StructField("country", StringType(), True),
        StructField("published_at", StringType(), True),
        StructField("subscriber_count", LongType(), True),
        StructField("video_count", LongType(), True),
        StructField("view_count", LongType(), True),
        StructField("thumbnail_url", StringType(), True),
        StructField("source_url", StringType(), True),
        StructField("crawled_at", StringType(), True),
        StructField("ingested_at", StringType(), True),
        StructField("event_time", TimestampType(), True),
    ]
)
