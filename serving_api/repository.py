from datetime import UTC, datetime

from config.mongo_config import MONGO_DATABASE, MONGO_URI
from config.storage_config import (
    AI_TREND_BRIEFINGS_COLLECTION,
    PUBLIC_CONTENT_EVENTS_COLLECTION,
    PUBLIC_TREND_ALERTS_COLLECTION,
    YOUTUBE_CONTENT_EVENTS_COLLECTION,
    YOUTUBE_SENTIMENT_COLLECTION,
    YOUTUBE_TRENDING_COLLECTION,
)


RECENCY_BOOST_FACTOR = 0.35


def build_top_videos_pipeline(
    from_time: datetime,
    to_time: datetime,
    page_size: int,
    offset: int,
) -> list[dict]:
    return [
        {
            "$match": {
                "entity_type": "video",
                "event_time": {"$gte": from_time, "$lt": to_time},
            }
        },
        {
            "$addFields": {
                "ranking_timestamp": "$event_time",
                "base_engagement_score": {
                    "$add": [
                        {"$ifNull": ["$engagement_view_count", 0]},
                        {"$multiply": [{"$ifNull": ["$engagement_like_count", 0]}, 20]},
                        {
                            "$multiply": [
                                {"$ifNull": ["$engagement_comment_count", 0]},
                                50,
                            ]
                        },
                    ]
                },
            }
        },
        {
            "$addFields": {
                "age_minutes": {
                    "$max": [
                        0,
                        {
                            "$divide": [
                                {"$subtract": [to_time, "$ranking_timestamp"]},
                                60000,
                            ]
                        },
                    ]
                },
                "range_minutes": {
                    "$max": [
                        1,
                        {
                            "$divide": [
                                {"$subtract": [to_time, from_time]},
                                60000,
                            ]
                        },
                    ]
                },
            }
        },
        {
            "$addFields": {
                "recency_multiplier": {
                    "$add": [
                        1,
                        {
                            "$multiply": [
                                RECENCY_BOOST_FACTOR,
                                {
                                    "$max": [
                                        0,
                                        {
                                            "$subtract": [
                                                1,
                                                {
                                                    "$min": [
                                                        1,
                                                        {
                                                            "$divide": [
                                                                "$age_minutes",
                                                                "$range_minutes",
                                                            ]
                                                        },
                                                    ]
                                                },
                                            ]
                                        },
                                    ]
                                },
                            ]
                        },
                    ]
                }
            }
        },
        {
            "$addFields": {
                "engagement_score": {
                    "$multiply": [
                        "$base_engagement_score",
                        "$recency_multiplier",
                    ]
                }
            }
        },
        {
            "$facet": {
                "items": [
                    {"$sort": {"engagement_score": -1, "ranking_timestamp": -1}},
                    {"$skip": offset},
                    {"$limit": page_size},
                    {
                        "$project": {
                            "_id": 0,
                            "age_minutes": 0,
                            "range_minutes": 0,
                        }
                    },
                ],
                "metadata": [
                    {
                        "$group": {
                            "_id": None,
                            "latest_event_time": {"$max": "$ranking_timestamp"},
                            "total_items": {"$sum": 1},
                        }
                    },
                    {"$project": {"_id": 0}},
                ],
            }
        },
    ]


def build_sentiment_summary_pipeline(
    from_time: datetime,
    to_time: datetime,
    page_size: int,
    offset: int,
) -> list[dict]:
    grouped_pipeline = [
        {
            "$group": {
                "_id": {
                    "entity_type": "$entity_type",
                    "sentiment": "$sentiment",
                },
                "event_count": {"$sum": "$event_count"},
            }
        },
        {
            "$project": {
                "_id": 0,
                "entity_type": "$_id.entity_type",
                "sentiment": "$_id.sentiment",
                "event_count": 1,
            }
        },
        {"$sort": {"event_count": -1, "entity_type": 1, "sentiment": 1}},
    ]
    return [
        {
            "$match": {
                "window_start": {"$gte": from_time},
                "window_end": {"$lte": to_time},
            }
        },
        {
            "$facet": {
                "items": grouped_pipeline
                + [
                    {"$skip": offset},
                    {"$limit": page_size},
                ],
                "totals": grouped_pipeline
                + [
                    {
                        "$group": {
                            "_id": None,
                            "total_items": {"$sum": 1},
                            "total_events": {"$sum": "$event_count"},
                        }
                    },
                    {"$project": {"_id": 0}},
                ],
                "metadata": [
                    {
                        "$group": {
                            "_id": None,
                            "latest_window_end": {"$max": "$window_end"},
                        }
                    },
                    {"$project": {"_id": 0}},
                ],
            }
        },
    ]


class YouTubeAnalyticsRepository:
    def __init__(self, mongo_uri: str = MONGO_URI, database: str = MONGO_DATABASE):
        self._mongo_uri = mongo_uri
        self._database = database

    def ping(self) -> bool:
        from pymongo import MongoClient

        with MongoClient(self._mongo_uri, serverSelectionTimeoutMS=3000) as client:
            return bool(client.admin.command("ping"))

    def fetch_top_videos(
        self,
        from_time: datetime,
        to_time: datetime,
        page: int,
        page_size: int,
    ) -> dict:
        from pymongo import MongoClient

        offset = (page - 1) * page_size
        pipeline = build_top_videos_pipeline(from_time, to_time, page_size, offset)
        with MongoClient(self._mongo_uri) as client:
            result = list(
                client[self._database][YOUTUBE_CONTENT_EVENTS_COLLECTION].aggregate(pipeline)
            )
        facet = result[0] if result else {}
        metadata = (facet.get("metadata") or [{}])[0]
        return {
            "items": facet.get("items", []),
            "latest_event_time": metadata.get("latest_event_time"),
            "total_items": metadata.get("total_items", 0),
        }

    def fetch_sentiment_metrics(
        self,
        from_time: datetime,
        to_time: datetime,
        page: int,
        page_size: int,
    ) -> dict:
        from pymongo import MongoClient

        offset = (page - 1) * page_size
        pipeline = build_sentiment_summary_pipeline(from_time, to_time, page_size, offset)
        with MongoClient(self._mongo_uri) as client:
            result = list(
                client[self._database][YOUTUBE_SENTIMENT_COLLECTION].aggregate(pipeline)
            )
        facet = result[0] if result else {}
        metadata = (facet.get("metadata") or [{}])[0]
        totals = (facet.get("totals") or [{}])[0]
        return {
            "items": facet.get("items", []),
            "latest_window_end": metadata.get("latest_window_end"),
            "total_events": totals.get("total_events", 0),
            "total_items": totals.get("total_items", 0),
        }

    def fetch_trending_keywords(
        self,
        from_time: datetime,
        to_time: datetime,
        page: int,
        page_size: int,
    ) -> dict:
        from pymongo import DESCENDING, MongoClient

        offset = (page - 1) * page_size
        with MongoClient(self._mongo_uri) as client:
            collection = client[self._database][YOUTUBE_TRENDING_COLLECTION]
            latest_window = collection.find_one(
                {
                    "window_start": {"$gte": from_time},
                    "window_end": {"$lte": to_time},
                },
                {"_id": 0, "window_start": 1, "window_end": 1},
                sort=[("window_end", DESCENDING), ("window_start", DESCENDING)],
            )
            if latest_window is None:
                return {
                    "items": [],
                    "window_start": None,
                    "window_end": None,
                    "total_items": 0,
                }

            filter_query = {
                "window_start": latest_window["window_start"],
                "window_end": latest_window["window_end"],
            }
            total_items = collection.count_documents(filter_query)
            items = list(
                collection.find(filter_query, {"_id": 0})
                .sort([("frequency", DESCENDING), ("keyword", 1)])
                .skip(offset)
                .limit(page_size)
            )
        return {
            "items": items,
            "window_start": latest_window.get("window_start"),
            "window_end": latest_window.get("window_end"),
            "total_items": total_items,
        }

    def fetch_freshness(self) -> dict:
        from pymongo import MongoClient

        with MongoClient(self._mongo_uri) as client:
            database = client[self._database]
            latest_content = database[YOUTUBE_CONTENT_EVENTS_COLLECTION].find_one(
                sort=[("event_time", -1)],
                projection={"_id": 0, "event_time": 1, "entity_id": 1},
            )
            latest_sentiment = database[YOUTUBE_SENTIMENT_COLLECTION].find_one(
                sort=[("window_end", -1)],
                projection={"_id": 0, "window_end": 1},
            )
            latest_trending = database[YOUTUBE_TRENDING_COLLECTION].find_one(
                sort=[("window_end", -1)],
                projection={"_id": 0, "window_end": 1},
            )
        return {
            "checked_at": datetime.now(UTC),
            "latest_content": latest_content,
            "latest_sentiment_window": latest_sentiment,
            "latest_trending_window": latest_trending,
        }

    def fetch_public_overview(self, from_time: datetime, to_time: datetime) -> dict:
        from pymongo import MongoClient

        with MongoClient(self._mongo_uri) as client:
            database = client[self._database]
            content = database[PUBLIC_CONTENT_EVENTS_COLLECTION]
            alerts = database[PUBLIC_TREND_ALERTS_COLLECTION]
            briefings = database[AI_TREND_BRIEFINGS_COLLECTION]
            content_filter = {"event_time": {"$gte": from_time, "$lt": to_time}}
            alert_filter = {"window_end": {"$gte": from_time, "$lt": to_time}}
            latest_content = content.find_one(
                content_filter,
                {"_id": 0},
                sort=[("event_time", -1)],
            )
            latest_alert = alerts.find_one(
                alert_filter,
                {"_id": 0},
                sort=[("content_count", -1), ("trend_score", -1), ("window_end", -1)],
            )
            latest_briefing = briefings.find_one(
                {},
                {"_id": 0},
                sort=[("created_at", -1)],
            )
            platform_counts = list(
                content.aggregate(
                    [
                        {"$match": content_filter},
                        {"$group": {"_id": "$platform", "count": {"$sum": 1}}},
                        {"$project": {"_id": 0, "platform": "$_id", "count": 1}},
                        {"$sort": {"count": -1, "platform": 1}},
                    ]
                )
            )
            sentiment_counts = list(
                content.aggregate(
                    [
                        {"$match": {**content_filter, "sentiment": {"$ne": None}}},
                        {"$group": {"_id": "$sentiment", "count": {"$sum": 1}}},
                        {"$project": {"_id": 0, "sentiment": "$_id", "count": 1}},
                        {"$sort": {"count": -1, "sentiment": 1}},
                    ]
                )
            )
            return {
                "checked_at": datetime.now(UTC),
                "content_count": content.count_documents(content_filter),
                "scored_content_count": content.count_documents(
                    {**content_filter, "sentiment": {"$ne": None}}
                ),
                "trend_alert_count": alerts.count_documents(alert_filter),
                "latest_content": latest_content,
                "latest_alert": latest_alert,
                "latest_briefing": latest_briefing,
                "platform_counts": platform_counts,
                "sentiment_counts": sentiment_counts,
            }

    def fetch_public_trend_alerts(
        self,
        from_time: datetime,
        to_time: datetime,
        page: int,
        page_size: int,
    ) -> dict:
        from pymongo import MongoClient

        offset = (page - 1) * page_size
        filter_query = {"window_end": {"$gte": from_time, "$lt": to_time}}
        with MongoClient(self._mongo_uri) as client:
            collection = client[self._database][PUBLIC_TREND_ALERTS_COLLECTION]
            total_items = collection.count_documents(filter_query)
            items = list(
                collection.find(filter_query, {"_id": 0})
                .sort(
                    [
                        ("content_count", -1),
                        ("trend_score", -1),
                        ("window_end", -1),
                        ("keyword", 1),
                    ]
                )
                .skip(offset)
                .limit(page_size)
            )
        return {"items": items, "total_items": total_items}

    def fetch_public_content_events(
        self,
        from_time: datetime,
        to_time: datetime,
        page: int,
        page_size: int,
    ) -> dict:
        from pymongo import MongoClient

        offset = (page - 1) * page_size
        filter_query = {"event_time": {"$gte": from_time, "$lt": to_time}}
        with MongoClient(self._mongo_uri) as client:
            collection = client[self._database][PUBLIC_CONTENT_EVENTS_COLLECTION]
            total_items = collection.count_documents(filter_query)
            items = list(
                collection.find(filter_query, {"_id": 0})
                .sort([("event_time", -1), ("source", 1)])
                .skip(offset)
                .limit(page_size)
            )
        return {"items": items, "total_items": total_items}

    def fetch_latest_ai_briefing(self) -> dict:
        from pymongo import MongoClient

        with MongoClient(self._mongo_uri) as client:
            briefing = client[self._database][AI_TREND_BRIEFINGS_COLLECTION].find_one(
                {},
                {"_id": 0},
                sort=[("created_at", -1)],
            )
        return briefing or {}
