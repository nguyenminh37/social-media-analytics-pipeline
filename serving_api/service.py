from datetime import UTC, datetime


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

    def top_videos(
        self,
        *,
        filter_mode: str,
        window_hours: int | None,
        date_from: str | None,
        date_to: str | None,
        from_time: datetime,
        to_time: datetime,
        page: int,
        page_size: int,
    ) -> dict:
        result = self._repository.fetch_top_videos(
            from_time=from_time,
            to_time=to_time,
            page=page,
            page_size=page_size,
        )
        return {
            "ranking_mode": "recency_weighted_engagement",
            **self._pagination_payload(
                filter_mode=filter_mode,
                window_hours=window_hours,
                date_from=date_from,
                date_to=date_to,
                from_time=from_time,
                to_time=to_time,
                page=page,
                page_size=page_size,
                total_items=result.get("total_items", 0),
            ),
            "latest_event_time": self._serialize_datetimes(
                result.get("latest_event_time")
            ),
            "items": self._serialize_datetimes(result.get("items", [])),
        }

    def sentiment_metrics(
        self,
        *,
        filter_mode: str,
        window_hours: int | None,
        date_from: str | None,
        date_to: str | None,
        from_time: datetime,
        to_time: datetime,
        page: int,
        page_size: int,
    ) -> dict:
        result = self._repository.fetch_sentiment_metrics(
            from_time=from_time,
            to_time=to_time,
            page=page,
            page_size=page_size,
        )
        return {
            **self._pagination_payload(
                filter_mode=filter_mode,
                window_hours=window_hours,
                date_from=date_from,
                date_to=date_to,
                from_time=from_time,
                to_time=to_time,
                page=page,
                page_size=page_size,
                total_items=result.get("total_items", 0),
            ),
            "latest_window_end": self._serialize_datetimes(
                result.get("latest_window_end")
            ),
            "total_events": result.get("total_events", 0),
            "items": self._serialize_datetimes(result.get("items", [])),
        }

    def trending_keywords(
        self,
        *,
        filter_mode: str,
        window_hours: int | None,
        date_from: str | None,
        date_to: str | None,
        from_time: datetime,
        to_time: datetime,
        page: int,
        page_size: int,
    ) -> dict:
        result = self._repository.fetch_trending_keywords(
            from_time=from_time,
            to_time=to_time,
            page=page,
            page_size=page_size,
        )
        return {
            **self._pagination_payload(
                filter_mode=filter_mode,
                window_hours=window_hours,
                date_from=date_from,
                date_to=date_to,
                from_time=from_time,
                to_time=to_time,
                page=page,
                page_size=page_size,
                total_items=result.get("total_items", 0),
            ),
            "window_start": self._serialize_datetimes(result.get("window_start")),
            "window_end": self._serialize_datetimes(result.get("window_end")),
            "items": self._serialize_datetimes(result.get("items", [])),
        }

    def _pagination_payload(
        self,
        *,
        filter_mode: str,
        window_hours: int | None,
        date_from: str | None,
        date_to: str | None,
        from_time: datetime,
        to_time: datetime,
        page: int,
        page_size: int,
        total_items: int,
    ) -> dict:
        total_pages = max((total_items + page_size - 1) // page_size, 1) if total_items else 0
        return {
            "filter_mode": filter_mode,
            "window_hours": window_hours,
            "date_from": date_from,
            "date_to": date_to,
            "from_time": self._serialize_datetimes(from_time),
            "to_time": self._serialize_datetimes(to_time),
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_previous_page": page > 1 and total_pages > 0,
            "has_next_page": page < total_pages,
        }

    def _serialize_datetimes(self, value):
        if isinstance(value, datetime):
            if value.tzinfo is None:
                value = value.replace(tzinfo=UTC)
            return value.astimezone(UTC).isoformat()
        if isinstance(value, list):
            return [self._serialize_datetimes(item) for item in value]
        if isinstance(value, dict):
            return {
                key: self._serialize_datetimes(item_value)
                for key, item_value in value.items()
            }
        return value
