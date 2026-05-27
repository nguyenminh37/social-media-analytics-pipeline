import json
from datetime import UTC, date, datetime, time, timedelta
from http import HTTPStatus
from urllib.parse import parse_qs, urlparse


DEFAULT_PAGE_SIZE = 10
DEFAULT_WINDOW_HOURS = 24


class ServingApiApp:
    def __init__(self, service=None):
        if service is None:
            from serving_api.repository import YouTubeAnalyticsRepository
            from serving_api.service import YouTubeAnalyticsService

            service = YouTubeAnalyticsService(YouTubeAnalyticsRepository())
        self._service = service

    def handle_request(self, method: str, path: str) -> tuple[int, dict]:
        if method != "GET":
            return HTTPStatus.METHOD_NOT_ALLOWED, {"error": "method_not_allowed"}

        parsed = urlparse(path)
        query = parse_qs(parsed.query)
        try:
            if parsed.path == "/health":
                payload = self._service.health()
                status = (
                    HTTPStatus.OK
                    if payload.get("status") == "ok"
                    else HTTPStatus.SERVICE_UNAVAILABLE
                )
                return status, payload
            if parsed.path == "/api/youtube/top-videos":
                return HTTPStatus.OK, self._service.top_videos(
                    **self._time_filter_params(query),
                    page=self._int_param(query, "page", 1),
                    page_size=self._int_param(query, "page_size", DEFAULT_PAGE_SIZE),
                )
            if parsed.path == "/api/youtube/sentiment-metrics":
                return HTTPStatus.OK, self._service.sentiment_metrics(
                    **self._time_filter_params(query),
                    page=self._int_param(query, "page", 1),
                    page_size=self._int_param(query, "page_size", DEFAULT_PAGE_SIZE),
                )
            if parsed.path == "/api/youtube/trending-keywords":
                return HTTPStatus.OK, self._service.trending_keywords(
                    **self._time_filter_params(query),
                    page=self._int_param(query, "page", 1),
                    page_size=self._int_param(query, "page_size", DEFAULT_PAGE_SIZE),
                )
            if parsed.path == "/api/youtube/freshness":
                health_payload = self._service.health()
                status = (
                    HTTPStatus.OK
                    if health_payload.get("status") == "ok"
                    else HTTPStatus.SERVICE_UNAVAILABLE
                )
                return status, health_payload.get("freshness", health_payload)
            if parsed.path == "/api/public/overview":
                return HTTPStatus.OK, self._service.public_overview(
                    **self._time_filter_params(query),
                )
            if parsed.path == "/api/public/trend-alerts":
                return HTTPStatus.OK, self._service.public_trend_alerts(
                    **self._time_filter_params(query),
                    page=self._int_param(query, "page", 1),
                    page_size=self._int_param(query, "page_size", DEFAULT_PAGE_SIZE),
                )
            if parsed.path == "/api/public/content-events":
                return HTTPStatus.OK, self._service.public_content_events(
                    **self._time_filter_params(query),
                    page=self._int_param(query, "page", 1),
                    page_size=self._int_param(query, "page_size", DEFAULT_PAGE_SIZE),
                )
            if parsed.path == "/api/public/ai-briefing":
                return HTTPStatus.OK, self._service.public_ai_briefing()
        except ValueError:
            return HTTPStatus.BAD_REQUEST, {"error": "invalid_query_params"}
        except Exception as exc:
            return HTTPStatus.SERVICE_UNAVAILABLE, {"error": str(exc)}
        return HTTPStatus.NOT_FOUND, {"error": "not_found"}

    def render_json(self, method: str, path: str) -> tuple[int, bytes]:
        status, payload = self.handle_request(method, path)
        try:
            body = json.dumps(payload).encode("utf-8")
        except TypeError as exc:
            status = HTTPStatus.SERVICE_UNAVAILABLE
            body = json.dumps(
                {"error": "response_serialization_error", "detail": str(exc)}
            ).encode("utf-8")
        return int(status), body

    def _int_param(self, query: dict[str, list[str]], name: str, default: int) -> int:
        raw_value = query.get(name, [str(default)])[0]
        value = int(raw_value)
        return max(value, 1)

    def _time_filter_params(self, query: dict[str, list[str]]) -> dict:
        filter_mode = query.get("filter_mode", ["hours"])[0]
        if filter_mode == "hours":
            window_hours = self._int_param(query, "window_hours", DEFAULT_WINDOW_HOURS)
            to_time = datetime.now(UTC)
            from_time = to_time - timedelta(hours=window_hours)
            return {
                "filter_mode": filter_mode,
                "window_hours": window_hours,
                "date_from": None,
                "date_to": None,
                "from_time": from_time,
                "to_time": to_time,
            }
        if filter_mode == "date_range":
            date_from = self._date_param(query, "date_from")
            date_to = self._date_param(query, "date_to")
            if date_from > date_to:
                raise ValueError("invalid_date_range")
            from_time = datetime.combine(date_from, time.min, tzinfo=UTC)
            to_time = datetime.combine(date_to + timedelta(days=1), time.min, tzinfo=UTC)
            return {
                "filter_mode": filter_mode,
                "window_hours": None,
                "date_from": date_from.isoformat(),
                "date_to": date_to.isoformat(),
                "from_time": from_time,
                "to_time": to_time,
            }
        raise ValueError("invalid_filter_mode")

    def _date_param(self, query: dict[str, list[str]], name: str) -> date:
        raw_value = query.get(name, [None])[0]
        if not raw_value:
            raise ValueError(f"missing_{name}")
        return date.fromisoformat(raw_value)
