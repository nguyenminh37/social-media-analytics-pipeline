import json
from http import HTTPStatus
from urllib.parse import parse_qs, urlparse


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
                    window_minutes=self._int_param(query, "window_minutes", 1440),
                    limit=self._int_param(query, "limit", 10),
                )
            if parsed.path == "/api/youtube/sentiment-metrics":
                return HTTPStatus.OK, self._service.sentiment_metrics(
                    window_minutes=self._int_param(query, "window_minutes", 180)
                )
            if parsed.path == "/api/youtube/trending-keywords":
                return HTTPStatus.OK, self._service.trending_keywords(
                    window_minutes=self._int_param(query, "window_minutes", 180),
                    limit=self._int_param(query, "limit", 20),
                )
            if parsed.path == "/api/youtube/freshness":
                health_payload = self._service.health()
                status = (
                    HTTPStatus.OK
                    if health_payload.get("status") == "ok"
                    else HTTPStatus.SERVICE_UNAVAILABLE
                )
                return status, health_payload.get("freshness", health_payload)
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
