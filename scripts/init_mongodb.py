import logging
import sys
from pathlib import Path
from datetime import timedelta
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from pymongo import MongoClient
import pymongo
from config.mongo_config import (
    MONGO_DATABASE,
    MONGO_METRICS_TTL_DAYS,
    MONGO_POSTS_TTL_DAYS,
    MONGO_URI,
)
from config.storage_config import (
    PUBLIC_CONTENT_EVENTS_COLLECTION,
    PUBLIC_TREND_ALERTS_COLLECTION,
    PUBLIC_TREND_METRICS_COLLECTION,
    YOUTUBE_CHANNEL_SNAPSHOTS_COLLECTION,
    YOUTUBE_CONTENT_EVENTS_COLLECTION,
    YOUTUBE_SENTIMENT_COLLECTION,
    YOUTUBE_TRENDING_COLLECTION,
)

logging.basicConfig(level=logging.INFO)

def create_index_safe(collection, keys, **kwargs):
    try:
        collection.create_index(keys, **kwargs)
    except pymongo.errors.DuplicateKeyError as exc:
        collection_name = getattr(collection, "name", "unknown")
        logging.warning(
            "Could not create index on '%s' with keys %s due to existing duplicates: %s",
            collection_name,
            keys,
            exc,
        )


def drop_legacy_trending_unique_index(collection) -> None:
    legacy_keys = [
        ("window_start", pymongo.ASCENDING),
        ("window_end", pymongo.ASCENDING),
        ("keyword", pymongo.ASCENDING),
    ]
    desired_keys = [
        ("window_start", pymongo.ASCENDING),
        ("window_end", pymongo.ASCENDING),
        ("entity_type", pymongo.ASCENDING),
        ("keyword", pymongo.ASCENDING),
    ]
    try:
        index_info = collection.index_information()
    except Exception as exc:  # pragma: no cover - defensive
        logging.warning("Could not inspect indexes for trending collection: %s", exc)
        return

    for index_name, info in index_info.items():
        if info.get("key") == desired_keys:
            return

    for index_name, info in index_info.items():
        if info.get("key") == legacy_keys and info.get("unique"):
            collection.drop_index(index_name)
            logging.info(
                "Dropped legacy trending unique index %s to include entity_type",
                index_name,
            )
            return

def init_mongodb(client: MongoClient, db_name: str):
    db = client[db_name]
    posts_ttl_seconds = int(timedelta(days=MONGO_POSTS_TTL_DAYS).total_seconds())
    metrics_ttl_seconds = int(
        timedelta(days=MONGO_METRICS_TTL_DAYS).total_seconds()
    )

    # 1. YouTube Silver Content Indexes
    youtube_content = db[YOUTUBE_CONTENT_EVENTS_COLLECTION]
    create_index_safe(
        youtube_content,
        [("entity_id", pymongo.ASCENDING)],
        unique=True,
    )
    youtube_content.create_index([("entity_type", pymongo.ASCENDING)])
    youtube_content.create_index([("parent_entity_id", pymongo.ASCENDING)])
    youtube_content.create_index([("event_time", pymongo.DESCENDING)])
    youtube_content.create_index([("published_at", pymongo.DESCENDING)])
    youtube_content.create_index([("sentiment", pymongo.ASCENDING)])
    youtube_content.create_index(
        [("ingested_at", pymongo.ASCENDING)],
        expireAfterSeconds=posts_ttl_seconds,
    )
    logging.info(f"Created indexes for {YOUTUBE_CONTENT_EVENTS_COLLECTION}")

    # 2. YouTube Channel Snapshot Indexes
    youtube_channels = db[YOUTUBE_CHANNEL_SNAPSHOTS_COLLECTION]
    create_index_safe(
        youtube_channels,
        [("channel_id", pymongo.ASCENDING), ("crawled_at", pymongo.ASCENDING)],
        unique=True,
    )
    youtube_channels.create_index([("channel_id", pymongo.ASCENDING)])
    youtube_channels.create_index([("event_time", pymongo.DESCENDING)])
    youtube_channels.create_index(
        [("ingested_at", pymongo.ASCENDING)],
        expireAfterSeconds=posts_ttl_seconds,
    )
    logging.info(f"Created indexes for {YOUTUBE_CHANNEL_SNAPSHOTS_COLLECTION}")

    # 3. YouTube Metric Indexes
    youtube_sentiment = db[YOUTUBE_SENTIMENT_COLLECTION]
    youtube_sentiment.create_index([("window_start", pymongo.DESCENDING)])
    create_index_safe(
        youtube_sentiment,
        [
            ("window_start", pymongo.ASCENDING),
            ("window_end", pymongo.ASCENDING),
            ("entity_type", pymongo.ASCENDING),
            ("sentiment", pymongo.ASCENDING),
        ],
        unique=True,
    )
    youtube_sentiment.create_index(
        [("window_end", pymongo.ASCENDING)],
        expireAfterSeconds=metrics_ttl_seconds,
    )
    logging.info(f"Created indexes for {YOUTUBE_SENTIMENT_COLLECTION}")

    youtube_trending = db[YOUTUBE_TRENDING_COLLECTION]
    youtube_trending.create_index([("window_start", pymongo.DESCENDING)])
    drop_legacy_trending_unique_index(youtube_trending)
    create_index_safe(
        youtube_trending,
        [
            ("window_start", pymongo.ASCENDING),
            ("window_end", pymongo.ASCENDING),
            ("entity_type", pymongo.ASCENDING),
            ("keyword", pymongo.ASCENDING),
        ],
        unique=True,
    )
    youtube_trending.create_index(
        [("window_end", pymongo.ASCENDING)],
        expireAfterSeconds=metrics_ttl_seconds,
    )
    logging.info(f"Created indexes for {YOUTUBE_TRENDING_COLLECTION}")

    # 4. Public Content Indexes
    public_content = db[PUBLIC_CONTENT_EVENTS_COLLECTION]
    create_index_safe(
        public_content,
        [("content_id", pymongo.ASCENDING)],
        unique=True,
    )
    public_content.create_index([("event_time", pymongo.DESCENDING)])
    public_content.create_index([("published_at", pymongo.DESCENDING)])
    public_content.create_index([("platform", pymongo.ASCENDING)])
    public_content.create_index([("source", pymongo.ASCENDING)])
    public_content.create_index(
        [("sentiment_model", pymongo.ASCENDING), ("event_time", pymongo.DESCENDING)]
    )
    public_content.create_index(
        [("ingested_at", pymongo.ASCENDING)],
        expireAfterSeconds=posts_ttl_seconds,
    )
    logging.info(f"Created indexes for {PUBLIC_CONTENT_EVENTS_COLLECTION}")

    # 5. Public Trend Metric Indexes
    public_trends = db[PUBLIC_TREND_METRICS_COLLECTION]
    public_trends.create_index([("window_end", pymongo.DESCENDING), ("keyword", pymongo.ASCENDING)])
    create_index_safe(
        public_trends,
        [
            ("keyword", pymongo.ASCENDING),
            ("window_start", pymongo.ASCENDING),
            ("window_end", pymongo.ASCENDING),
        ],
        unique=True,
    )
    public_trends.create_index(
        [("window_end", pymongo.ASCENDING)],
        expireAfterSeconds=metrics_ttl_seconds,
    )
    logging.info(f"Created indexes for {PUBLIC_TREND_METRICS_COLLECTION}")

    # 6. Public Trend Alert Indexes
    public_alerts = db[PUBLIC_TREND_ALERTS_COLLECTION]
    public_alerts.create_index(
        [("window_end", pymongo.DESCENDING), ("trend_score", pymongo.DESCENDING)]
    )
    create_index_safe(
        public_alerts,
        [
            ("keyword", pymongo.ASCENDING),
            ("window_start", pymongo.ASCENDING),
            ("window_end", pymongo.ASCENDING),
            ("alert_type", pymongo.ASCENDING),
        ],
        unique=True,
    )
    public_alerts.create_index(
        [("window_end", pymongo.ASCENDING)],
        expireAfterSeconds=metrics_ttl_seconds,
    )
    logging.info(f"Created indexes for {PUBLIC_TREND_ALERTS_COLLECTION}")

def main():
    client = MongoClient(MONGO_URI)
    try:
        init_mongodb(client, MONGO_DATABASE)
        logging.info("MongoDB initialization completed.")
    finally:
        client.close()

if __name__ == "__main__":
    main()
