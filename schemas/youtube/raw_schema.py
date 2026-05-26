from pyspark.sql.types import StringType, StructField, StructType


RAW_YOUTUBE_VIDEO_FIELDS = [
    "platform",
    "entity_type",
    "entity_id",
    "video_id",
    "title",
    "channel_id",
    "channel_title",
    "published_at",
    "description",
    "tags",
    "category_id",
    "duration",
    "view_count",
    "like_count",
    "comment_count",
    "thumbnail_url",
    "source_url",
    "crawled_at",
    "ingested_at",
]

RAW_YOUTUBE_CHANNEL_FIELDS = [
    "platform",
    "entity_type",
    "entity_id",
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
]

RAW_YOUTUBE_COMMENT_FIELDS = [
    "platform",
    "entity_type",
    "entity_id",
    "comment_id",
    "video_id",
    "author",
    "author_channel_id",
    "text",
    "like_count",
    "reply_count",
    "published_at",
    "updated_at",
    "source_url",
    "crawled_at",
    "ingested_at",
]

RAW_YOUTUBE_VIDEO_SPARK_SCHEMA = StructType(
    [StructField(field_name, StringType(), True) for field_name in RAW_YOUTUBE_VIDEO_FIELDS]
)

RAW_YOUTUBE_CHANNEL_SPARK_SCHEMA = StructType(
    [StructField(field_name, StringType(), True) for field_name in RAW_YOUTUBE_CHANNEL_FIELDS]
)

RAW_YOUTUBE_COMMENT_SPARK_SCHEMA = StructType(
    [StructField(field_name, StringType(), True) for field_name in RAW_YOUTUBE_COMMENT_FIELDS]
)

YOUTUBE_VIDEO_FIELDS = RAW_YOUTUBE_VIDEO_FIELDS
YOUTUBE_CHANNEL_FIELDS = RAW_YOUTUBE_CHANNEL_FIELDS
YOUTUBE_COMMENT_FIELDS = RAW_YOUTUBE_COMMENT_FIELDS
YOUTUBE_VIDEO_SPARK_SCHEMA = RAW_YOUTUBE_VIDEO_SPARK_SCHEMA
YOUTUBE_CHANNEL_SPARK_SCHEMA = RAW_YOUTUBE_CHANNEL_SPARK_SCHEMA
YOUTUBE_COMMENT_SPARK_SCHEMA = RAW_YOUTUBE_COMMENT_SPARK_SCHEMA
