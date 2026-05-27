import unittest
from datetime import UTC, datetime
from unittest.mock import patch

from serving_api.repository import (
    RECENCY_BOOST_FACTOR,
    YouTubeAnalyticsRepository,
    build_sentiment_summary_pipeline,
    build_top_videos_pipeline,
)


class FakeCursor:
    def __init__(self, documents):
        self._documents = list(documents)

    def sort(self, sort_spec):
        for field_name, direction in reversed(sort_spec):
            reverse = direction < 0
            self._documents.sort(
                key=lambda document: document.get(field_name),
                reverse=reverse,
            )
        return self

    def skip(self, amount):
        self._documents = self._documents[amount:]
        return self

    def limit(self, size):
        self._documents = self._documents[:size]
        return self

    def __iter__(self):
        return iter(self._documents)


class FakeTrendingCollection:
    def __init__(self, documents):
        self._documents = list(documents)

    def find_one(self, filter_query, projection, sort):
        matches = [
            document
            for document in self._documents
            if document["window_start"] >= filter_query["window_start"]["$gte"]
            and document["window_end"] <= filter_query["window_end"]["$lte"]
        ]
        if not matches:
            return None
        for field_name, direction in reversed(sort):
            reverse = direction < 0
            matches.sort(key=lambda document: document[field_name], reverse=reverse)
        selected = matches[0]
        return {key: selected.get(key) for key in projection if key != "_id"}

    def count_documents(self, filter_query):
        return sum(
            1
            for document in self._documents
            if document["window_start"] == filter_query["window_start"]
            and document["window_end"] == filter_query["window_end"]
        )

    def find(self, filter_query, projection):
        matches = [
            (
                {
                    key: value
                    for key, value in document.items()
                    if key in projection and key != "_id"
                }
                if any(value == 1 for key, value in projection.items() if key != "_id")
                else {key: value for key, value in document.items() if key != "_id"}
            )
            for document in self._documents
            if document["window_start"] == filter_query["window_start"]
            and document["window_end"] == filter_query["window_end"]
        ]
        return FakeCursor(matches)


class FakeMongoDatabase:
    def __init__(self, collection):
        self._collection = collection

    def __getitem__(self, _name):
        return self._collection


class FakeMongoClient:
    def __init__(self, _mongo_uri, collection):
        self._database = FakeMongoDatabase(collection)

    def __getitem__(self, _database_name):
        return self._database

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class YouTubeDashboardSemanticsTests(unittest.TestCase):
    def test_build_top_videos_pipeline_uses_explicit_time_range_and_pagination(self):
        from_time = datetime(2026, 5, 20, 0, 0, tzinfo=UTC)
        to_time = datetime(2026, 5, 27, 0, 0, tzinfo=UTC)

        pipeline = build_top_videos_pipeline(
            from_time=from_time,
            to_time=to_time,
            page_size=10,
            offset=10,
        )

        self.assertEqual(
            pipeline[0]["$match"],
            {
                "entity_type": "video",
                "event_time": {"$gte": from_time, "$lt": to_time},
            },
        )
        multiplier_expression = pipeline[3]["$addFields"]["recency_multiplier"]
        self.assertEqual(multiplier_expression["$add"][0], 1)
        self.assertEqual(
            multiplier_expression["$add"][1]["$multiply"][0],
            RECENCY_BOOST_FACTOR,
        )
        self.assertEqual(pipeline[5]["$facet"]["items"][0]["$sort"]["engagement_score"], -1)
        self.assertEqual(pipeline[5]["$facet"]["items"][1]["$skip"], 10)
        self.assertEqual(pipeline[5]["$facet"]["items"][2]["$limit"], 10)
        self.assertEqual(
            pipeline[5]["$facet"]["metadata"][0]["$group"]["total_items"],
            {"$sum": 1},
        )

    def test_build_sentiment_summary_pipeline_supports_group_pagination(self):
        from_time = datetime(2026, 5, 20, 0, 0, tzinfo=UTC)
        to_time = datetime(2026, 5, 27, 0, 0, tzinfo=UTC)

        pipeline = build_sentiment_summary_pipeline(
            from_time=from_time,
            to_time=to_time,
            page_size=10,
            offset=10,
        )

        self.assertEqual(
            pipeline[0],
            {
                "$match": {
                    "window_start": {"$gte": from_time},
                    "window_end": {"$lte": to_time},
                }
            },
        )
        self.assertEqual(pipeline[1]["$facet"]["items"][3]["$skip"], 10)
        self.assertEqual(pipeline[1]["$facet"]["items"][4]["$limit"], 10)
        self.assertEqual(
            pipeline[1]["$facet"]["totals"][3]["$group"]["total_items"],
            {"$sum": 1},
        )

    def test_fetch_trending_keywords_uses_latest_window_within_selected_range(self):
        latest_start = datetime(2026, 5, 27, 2, 0, tzinfo=UTC)
        latest_end = datetime(2026, 5, 27, 3, 0, tzinfo=UTC)
        documents = [
            {
                "keyword": "older",
                "frequency": 999,
                "window_start": datetime(2026, 5, 27, 1, 0, tzinfo=UTC),
                "window_end": datetime(2026, 5, 27, 2, 0, tzinfo=UTC),
            },
            {
                "keyword": "fresh-1",
                "frequency": 8,
                "window_start": latest_start,
                "window_end": latest_end,
            },
            {
                "keyword": "fresh-2",
                "frequency": 5,
                "window_start": latest_start,
                "window_end": latest_end,
            },
        ]
        repository = YouTubeAnalyticsRepository(mongo_uri="mongodb://unused", database="test-db")

        def fake_client_factory(*args, **kwargs):
            return FakeMongoClient(args[0], FakeTrendingCollection(documents))

        with patch("pymongo.MongoClient", side_effect=fake_client_factory):
            result = repository.fetch_trending_keywords(
                from_time=datetime(2026, 5, 27, 1, 30, tzinfo=UTC),
                to_time=datetime(2026, 5, 27, 4, 0, tzinfo=UTC),
                page=1,
                page_size=10,
            )

        self.assertEqual(result["window_start"], latest_start)
        self.assertEqual(result["window_end"], latest_end)
        self.assertEqual(result["total_items"], 2)
        self.assertEqual([item["keyword"] for item in result["items"]], ["fresh-1", "fresh-2"])


if __name__ == "__main__":
    unittest.main()
