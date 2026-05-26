import os

from config.env import PROJECT_ROOT  # noqa: F401


KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
RAW_POSTS_TOPIC = os.getenv("KAFKA_RAW_TOPIC", "raw_posts")
PROCESSED_POSTS_TOPIC = os.getenv("KAFKA_PROCESSED_TOPIC", "processed_posts")
AGGREGATED_METRICS_TOPIC = os.getenv("KAFKA_AGGREGATED_TOPIC", "aggregated_metrics")

RAW_YOUTUBE_VIDEOS_TOPIC = os.getenv(
    "KAFKA_RAW_YOUTUBE_VIDEOS_TOPIC", "raw_youtube_videos"
)
RAW_YOUTUBE_COMMENTS_TOPIC = os.getenv(
    "KAFKA_RAW_YOUTUBE_COMMENTS_TOPIC", "raw_youtube_comments"
)
RAW_YOUTUBE_CHANNELS_TOPIC = os.getenv(
    "KAFKA_RAW_YOUTUBE_CHANNELS_TOPIC", "raw_youtube_channels"
)
SILVER_YOUTUBE_CONTENT_EVENTS_TOPIC = os.getenv(
    "KAFKA_SILVER_YOUTUBE_CONTENT_EVENTS_TOPIC", "silver_youtube_content_events"
)
SILVER_YOUTUBE_CHANNEL_SNAPSHOTS_TOPIC = os.getenv(
    "KAFKA_SILVER_YOUTUBE_CHANNEL_SNAPSHOTS_TOPIC", "silver_youtube_channel_snapshots"
)
YOUTUBE_AGGREGATED_METRICS_TOPIC = os.getenv(
    "KAFKA_YOUTUBE_AGGREGATED_METRICS_TOPIC", "youtube_aggregated_metrics"
)

TOPIC_SPECS = [
    {
        "name": RAW_POSTS_TOPIC,
        "partitions": 3,
        "replication_factor": 1,
        "config": {"retention.ms": str(7 * 24 * 60 * 60 * 1000)},
    },
    {
        "name": PROCESSED_POSTS_TOPIC,
        "partitions": 3,
        "replication_factor": 1,
        "config": {"retention.ms": str(3 * 24 * 60 * 60 * 1000)},
    },
    {
        "name": AGGREGATED_METRICS_TOPIC,
        "partitions": 1,
        "replication_factor": 1,
        "config": {"retention.ms": str(24 * 60 * 60 * 1000)},
    },
    {
        "name": RAW_YOUTUBE_VIDEOS_TOPIC,
        "partitions": 3,
        "replication_factor": 1,
        "config": {"retention.ms": str(7 * 24 * 60 * 60 * 1000)},
    },
    {
        "name": RAW_YOUTUBE_COMMENTS_TOPIC,
        "partitions": 3,
        "replication_factor": 1,
        "config": {"retention.ms": str(7 * 24 * 60 * 60 * 1000)},
    },
    {
        "name": RAW_YOUTUBE_CHANNELS_TOPIC,
        "partitions": 1,
        "replication_factor": 1,
        "config": {"retention.ms": str(14 * 24 * 60 * 60 * 1000)},
    },
    {
        "name": SILVER_YOUTUBE_CONTENT_EVENTS_TOPIC,
        "partitions": 3,
        "replication_factor": 1,
        "config": {"retention.ms": str(7 * 24 * 60 * 60 * 1000)},
    },
    {
        "name": SILVER_YOUTUBE_CHANNEL_SNAPSHOTS_TOPIC,
        "partitions": 1,
        "replication_factor": 1,
        "config": {"retention.ms": str(14 * 24 * 60 * 60 * 1000)},
    },
    {
        "name": YOUTUBE_AGGREGATED_METRICS_TOPIC,
        "partitions": 1,
        "replication_factor": 1,
        "config": {"retention.ms": str(24 * 60 * 60 * 1000)},
    },
]
