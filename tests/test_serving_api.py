import unittest
from datetime import datetime

from serving_api.app import ServingApiApp
from serving_api.service import YouTubeAnalyticsService


class FakeRepository:
    def ping(self) -> bool:
        return True

    def fetch_top_videos(self, from_time, to_time, page: int, page_size: int) -> dict:
        return {
            "latest_event_time": datetime(2026, 5, 27, 3, 0, 0),
            "total_items": 11,
            "items": [{"entity_id": "video-1", "engagement_score": 99}],
        }

    def fetch_sentiment_metrics(self, from_time, to_time, page: int, page_size: int) -> dict:
        return {
            "latest_window_end": datetime(2026, 5, 27, 3, 15, 0),
            "total_events": 30,
            "total_items": 6,
            "items": [{"sentiment": "positive", "event_count": 3}],
        }

    def fetch_trending_keywords(self, from_time, to_time, page: int, page_size: int) -> dict:
        return {
            "window_start": datetime(2026, 5, 27, 2, 0, 0),
            "window_end": datetime(2026, 5, 27, 3, 0, 0),
            "total_items": 21,
            "items": [{"keyword": "ai", "frequency": 7}],
        }

    def fetch_freshness(self) -> dict:
        return {"latest_content": None, "latest_sentiment_window": None}


class NonSerializableService:
    def health(self) -> dict:
        return {"status": "ok"}

    def top_videos(self, **kwargs) -> dict:
        return {
            "page": kwargs["page"],
            "page_size": kwargs["page_size"],
            "items": [{"created_at": datetime.now()}],
        }

    def sentiment_metrics(self, **kwargs) -> dict:
        return {"items": []}

    def trending_keywords(self, **kwargs) -> dict:
        return {"items": []}


class ServingApiTests(unittest.TestCase):
    def setUp(self) -> None:
        service = YouTubeAnalyticsService(FakeRepository())
        self.app = ServingApiApp(service)

    def test_top_videos_endpoint_returns_hours_filter_contract(self) -> None:
        status, payload = self.app.handle_request(
            "GET",
            "/api/youtube/top-videos?filter_mode=hours&window_hours=72&page=2&page_size=10",
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload["ranking_mode"], "recency_weighted_engagement")
        self.assertEqual(payload["filter_mode"], "hours")
        self.assertEqual(payload["window_hours"], 72)
        self.assertEqual(payload["page"], 2)
        self.assertEqual(payload["page_size"], 10)
        self.assertEqual(payload["total_items"], 11)
        self.assertEqual(payload["total_pages"], 2)
        self.assertTrue(payload["has_previous_page"])
        self.assertFalse(payload["has_next_page"])
        self.assertEqual(payload["latest_event_time"], "2026-05-27T03:00:00+00:00")
        self.assertEqual(payload["items"][0]["entity_id"], "video-1")

    def test_sentiment_endpoint_returns_date_range_contract(self) -> None:
        status, payload = self.app.handle_request(
            "GET",
            "/api/youtube/sentiment-metrics?filter_mode=date_range&date_from=2026-05-20&date_to=2026-05-27&page=1&page_size=10",
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload["filter_mode"], "date_range")
        self.assertEqual(payload["date_from"], "2026-05-20")
        self.assertEqual(payload["date_to"], "2026-05-27")
        self.assertEqual(payload["page"], 1)
        self.assertEqual(payload["page_size"], 10)
        self.assertEqual(payload["total_items"], 6)
        self.assertEqual(payload["total_events"], 30)
        self.assertEqual(payload["latest_window_end"], "2026-05-27T03:15:00+00:00")

    def test_trending_keywords_returns_pagination_metadata(self) -> None:
        status, payload = self.app.handle_request(
            "GET",
            "/api/youtube/trending-keywords?filter_mode=hours&window_hours=24&page=3&page_size=10",
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload["page"], 3)
        self.assertEqual(payload["total_items"], 21)
        self.assertEqual(payload["total_pages"], 3)
        self.assertTrue(payload["has_previous_page"])
        self.assertFalse(payload["has_next_page"])
        self.assertEqual(payload["window_start"], "2026-05-27T02:00:00+00:00")
        self.assertEqual(payload["items"][0]["keyword"], "ai")

    def test_date_range_rejects_invalid_order(self) -> None:
        status, payload = self.app.handle_request(
            "GET",
            "/api/youtube/top-videos?filter_mode=date_range&date_from=2026-05-27&date_to=2026-05-20&page=1&page_size=10",
        )

        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "invalid_query_params")

    def test_freshness_endpoint_returns_health_payload(self) -> None:
        status, payload = self.app.handle_request("GET", "/api/youtube/freshness")

        self.assertEqual(status, 200)
        self.assertIn("latest_content", payload)

    def test_render_json_returns_error_payload_on_serialization_failure(self) -> None:
        app = ServingApiApp(NonSerializableService())

        status, body = app.render_json(
            "GET",
            "/api/youtube/top-videos?filter_mode=hours&window_hours=72&page=1&page_size=10",
        )

        self.assertEqual(status, 503)
        self.assertIn("response_serialization_error", body.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
