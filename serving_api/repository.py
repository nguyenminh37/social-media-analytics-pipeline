from datetime import UTC, datetime

from config.mongo_config import MONGO_DATABASE, MONGO_URI
from config.storage_config import (
    YOUTUBE_CONTENT_EVENTS_COLLECTION,
    YOUTUBE_SENTIMENT_COLLECTION,
    YOUTUBE_TRENDING_COLLECTION,
)


class YouTubeAnalyticsRepository:
    def __init__(self, mongo_uri: str = MONGO_URI, database: str = MONGO_DATABASE):
        self._mongo_uri = mongo_uri
        self._database = database

    def ping(self) -> bool:
        from pymongo import MongoClient

        with MongoClient(self._mongo_uri, serverSelectionTimeoutMS=3000) as client:
            return bool(client.admin.command("ping"))

    def fetch_top_videos(self, since: datetime, limit: int) -> list[dict]:
        from pymongo import MongoClient

        pipeline = [
            {
                "$match": {
                    "entity_type": "video",
                    "event_time": {"$gte": since},
                }
            },
            {
                "$addFields": {
                    "engagement_score": {
                        "$add": [
                            {"$ifNull": ["$engagement_view_count", 0]},
                            {"$multiply": [{"$ifNull": ["$engagement_like_count", 0]}, 20]},
                            {"$multiply": [{"$ifNull": ["$engagement_comment_count", 0]}, 50]},
                        ]
                    }
                }
            },
            {"$sort": {"engagement_score": -1, "published_at": -1}},
            {"$limit": limit},
        ]
        with MongoClient(self._mongo_uri) as client:
            return list(
                client[self._database][YOUTUBE_CONTENT_EVENTS_COLLECTION].aggregate(pipeline)
            )

    def fetch_sentiment_metrics(self, since: datetime) -> list[dict]:
        from pymongo import MongoClient

        with MongoClient(self._mongo_uri) as client:
            cursor = (
                client[self._database][YOUTUBE_SENTIMENT_COLLECTION]
                .find({"window_end": {"$gte": since}}, {"_id": 0})
                .sort([("window_start", 1), ("entity_type", 1), ("sentiment", 1)])
            )
            return list(cursor)

    def fetch_trending_keywords(self, since: datetime, limit: int) -> list[dict]:
        from pymongo import DESCENDING, MongoClient

        with MongoClient(self._mongo_uri) as client:
            cursor = (
                client[self._database][YOUTUBE_TRENDING_COLLECTION]
                .find({"window_end": {"$gte": since}}, {"_id": 0})
                .sort([("frequency", DESCENDING), ("window_end", DESCENDING)])
                .limit(limit)
            )
            return list(cursor)

    def fetch_freshness(self) -> dict:
        from pymongo import DESCENDING, MongoClient

        with MongoClient(self._mongo_uri) as client:
            database = client[self._database]
            latest_content = database[YOUTUBE_CONTENT_EVENTS_COLLECTION].find_one(
                sort=[("event_time", DESCENDING)],
                projection={"_id": 0, "event_time": 1, "entity_id": 1},
            )
            latest_sentiment = database[YOUTUBE_SENTIMENT_COLLECTION].find_one(
                sort=[("window_end", DESCENDING)],
                projection={"_id": 0, "window_end": 1},
            )
            latest_trending = database[YOUTUBE_TRENDING_COLLECTION].find_one(
                sort=[("window_end", DESCENDING)],
                projection={"_id": 0, "window_end": 1},
            )
        return {
            "checked_at": datetime.now(UTC),
            "latest_content": latest_content,
            "latest_sentiment_window": latest_sentiment,
            "latest_trending_window": latest_trending,
        }
