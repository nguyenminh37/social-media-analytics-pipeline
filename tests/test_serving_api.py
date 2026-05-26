import unittest

from serving_api.app import ServingApiApp
from serving_api.service import YouTubeAnalyticsService


class FakeRepository:
    def ping(self) -> bool:
        return True

    def fetch_top_videos(self, since, limit: int) -> list[dict]:
        return [{"entity_id": "video-1", "engagement_score": 99}]

    def fetch_sentiment_metrics(self, since) -> list[dict]:
        return [{"sentiment": "positive", "event_count": 3}]

    def fetch_trending_keywords(self, since, limit: int) -> list[dict]:
        return [{"keyword": "ai", "frequency": 7}]

    def fetch_freshness(self) -> dict:
        return {"latest_content": None, "latest_sentiment_window": None}


class ServingApiTests(unittest.TestCase):
    def setUp(self) -> None:
        service = YouTubeAnalyticsService(FakeRepository())
        self.app = ServingApiApp(service)

    def test_top_videos_endpoint_returns_contract(self) -> None:
        status, payload = self.app.handle_request(
            "GET",
            "/api/youtube/top-videos?window_minutes=120&limit=5",
        )

        self.assertEqual(status, 200)
        self.assertEqual(payload["window_minutes"], 120)
        self.assertEqual(payload["limit"], 5)
        self.assertEqual(payload["items"][0]["entity_id"], "video-1")

    def test_freshness_endpoint_returns_health_payload(self) -> None:
        status, payload = self.app.handle_request("GET", "/api/youtube/freshness")

        self.assertEqual(status, 200)
        self.assertIn("latest_content", payload)


if __name__ == "__main__":
    unittest.main()
