from datetime import UTC, datetime, timedelta


class YouTubeAnalyticsService:
    def __init__(self, repository):
        self._repository = repository

    def health(self) -> dict:
        try:
            freshness = self._repository.fetch_freshness()
            status = "ok" if self._repository.ping() else "error"
        except Exception as exc:
            return {"status": "error", "error": str(exc)}
        return {"status": status, "freshness": self._serialize_datetimes(freshness)}

    def top_videos(self, window_minutes: int, limit: int) -> dict:
        since = self._window_start(window_minutes)
        videos = self._repository.fetch_top_videos(since, limit)
        return {
            "window_minutes": window_minutes,
            "limit": limit,
            "items": self._serialize_datetimes(videos),
        }

    def sentiment_metrics(self, window_minutes: int) -> dict:
        since = self._window_start(window_minutes)
        metrics = self._repository.fetch_sentiment_metrics(since)
        return {
            "window_minutes": window_minutes,
            "items": self._serialize_datetimes(metrics),
        }

    def trending_keywords(self, window_minutes: int, limit: int) -> dict:
        since = self._window_start(window_minutes)
        keywords = self._repository.fetch_trending_keywords(since, limit)
        return {
            "window_minutes": window_minutes,
            "limit": limit,
            "items": self._serialize_datetimes(keywords),
        }

    def _window_start(self, window_minutes: int) -> datetime:
        return datetime.now(UTC) - timedelta(minutes=window_minutes)

    def _serialize_datetimes(self, value):
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, list):
            return [self._serialize_datetimes(item) for item in value]
        if isinstance(value, dict):
            return {
                key: self._serialize_datetimes(item_value)
                for key, item_value in value.items()
            }
        return value
