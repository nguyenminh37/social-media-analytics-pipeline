import os

from config.env import PROJECT_ROOT  # noqa: F401


KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
PIPELINE_DLQ_TOPIC = os.getenv("KAFKA_PIPELINE_DLQ_TOPIC", "pipeline_dlq")

RAW_YOUTUBE_VIDEOS_TOPIC = os.getenv(
    "KAFKA_RAW_YOUTUBE_VIDEOS_TOPIC", "raw_youtube_videos"
)
RAW_YOUTUBE_COMMENTS_TOPIC = os.getenv(
    "KAFKA_RAW_YOUTUBE_COMMENTS_TOPIC", "raw_youtube_comments"
)
RAW_YOUTUBE_CHANNELS_TOPIC = os.getenv(
    "KAFKA_RAW_YOUTUBE_CHANNELS_TOPIC", "raw_youtube_channels"
)
RAW_NEWS_ARTICLES_TOPIC = os.getenv(
    "KAFKA_RAW_NEWS_ARTICLES_TOPIC", "raw_news_articles"
)
RAW_YOUTUBE_RSS_VIDEOS_TOPIC = os.getenv(
    "KAFKA_RAW_YOUTUBE_RSS_VIDEOS_TOPIC", "raw_youtube_rss_videos"
)
SILVER_YOUTUBE_CONTENT_EVENTS_TOPIC = os.getenv(
    "KAFKA_SILVER_YOUTUBE_CONTENT_EVENTS_TOPIC", "silver_youtube_content_events"
)
SILVER_YOUTUBE_CHANNEL_SNAPSHOTS_TOPIC = os.getenv(
    "KAFKA_SILVER_YOUTUBE_CHANNEL_SNAPSHOTS_TOPIC", "silver_youtube_channel_snapshots"
)
SILVER_PUBLIC_CONTENT_EVENTS_TOPIC = os.getenv(
    "KAFKA_SILVER_PUBLIC_CONTENT_EVENTS_TOPIC", "silver_public_content_events"
)
YOUTUBE_AGGREGATED_METRICS_TOPIC = os.getenv(
    "KAFKA_YOUTUBE_AGGREGATED_METRICS_TOPIC", "youtube_aggregated_metrics"
)
PUBLIC_TREND_METRICS_TOPIC = os.getenv(
    "KAFKA_PUBLIC_TREND_METRICS_TOPIC", "public_trend_metrics"
)
PUBLIC_TREND_ALERTS_TOPIC = os.getenv(
    "KAFKA_PUBLIC_TREND_ALERTS_TOPIC", "public_trend_alerts"
)
RAW_ARCHIVER_GROUP_ID = os.getenv("KAFKA_RAW_ARCHIVER_GROUP_ID", "raw-archiver")

TOPIC_SPECS = [
    {
        "name": PIPELINE_DLQ_TOPIC,
        "partitions": 3,
        "replication_factor": 1,
        "config": {"retention.ms": str(14 * 24 * 60 * 60 * 1000)},
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
        "name": RAW_NEWS_ARTICLES_TOPIC,
        "partitions": 3,
        "replication_factor": 1,
        "config": {"retention.ms": str(7 * 24 * 60 * 60 * 1000)},
    },
    {
        "name": RAW_YOUTUBE_RSS_VIDEOS_TOPIC,
        "partitions": 3,
        "replication_factor": 1,
        "config": {"retention.ms": str(7 * 24 * 60 * 60 * 1000)},
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
        "name": SILVER_PUBLIC_CONTENT_EVENTS_TOPIC,
        "partitions": 3,
        "replication_factor": 1,
        "config": {"retention.ms": str(14 * 24 * 60 * 60 * 1000)},
    },
    {
        "name": YOUTUBE_AGGREGATED_METRICS_TOPIC,
        "partitions": 1,
        "replication_factor": 1,
        "config": {"retention.ms": str(24 * 60 * 60 * 1000)},
    },
    {
        "name": PUBLIC_TREND_METRICS_TOPIC,
        "partitions": 1,
        "replication_factor": 1,
        "config": {"retention.ms": str(7 * 24 * 60 * 60 * 1000)},
    },
    {
        "name": PUBLIC_TREND_ALERTS_TOPIC,
        "partitions": 1,
        "replication_factor": 1,
        "config": {"retention.ms": str(7 * 24 * 60 * 60 * 1000)},
    },
]

RAW_ARCHIVER_TOPICS = [
    RAW_YOUTUBE_VIDEOS_TOPIC,
    RAW_YOUTUBE_COMMENTS_TOPIC,
    RAW_YOUTUBE_CHANNELS_TOPIC,
    RAW_NEWS_ARTICLES_TOPIC,
    RAW_YOUTUBE_RSS_VIDEOS_TOPIC,
]
