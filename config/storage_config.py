import os

from config.env import PROJECT_ROOT  # noqa: F401


RAW_ARCHIVE_PREFIX = os.getenv("MINIO_RAW_ARCHIVE_PREFIX", "kafka_raw")

YOUTUBE_CONTENT_EVENTS_COLLECTION = os.getenv(
    "MONGO_YOUTUBE_CONTENT_EVENTS_COLLECTION", "youtube_content_events"
)
YOUTUBE_CHANNEL_SNAPSHOTS_COLLECTION = os.getenv(
    "MONGO_YOUTUBE_CHANNEL_SNAPSHOTS_COLLECTION", "youtube_channel_snapshots"
)
YOUTUBE_SENTIMENT_COLLECTION = os.getenv(
    "MONGO_YOUTUBE_SENTIMENT_COLLECTION", "youtube_sentiment_metrics"
)
YOUTUBE_TRENDING_COLLECTION = os.getenv(
    "MONGO_YOUTUBE_TRENDING_COLLECTION", "youtube_trending_topics"
)

YOUTUBE_CONTENT_EVENTS_INDEX = os.getenv(
    "ELASTICSEARCH_YOUTUBE_CONTENT_EVENTS_INDEX", "youtube_content_events"
)
YOUTUBE_CHANNEL_SNAPSHOTS_INDEX = os.getenv(
    "ELASTICSEARCH_YOUTUBE_CHANNEL_SNAPSHOTS_INDEX", "youtube_channel_snapshots"
)

YOUTUBE_CONTENT_EVENTS_PATH = os.getenv(
    "MINIO_YOUTUBE_CONTENT_EVENTS_PATH", "youtube/content_events"
)
YOUTUBE_CHANNEL_SNAPSHOTS_PATH = os.getenv(
    "MINIO_YOUTUBE_CHANNEL_SNAPSHOTS_PATH", "youtube/channel_snapshots"
)
YOUTUBE_AGGREGATES_PATH = os.getenv(
    "MINIO_YOUTUBE_AGGREGATES_PATH", "youtube/aggregates"
)
