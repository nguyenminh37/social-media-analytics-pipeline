#!/usr/bin/env python3
"""Seed Kibana data views, searches, Vega charts, and a demo dashboard."""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


DEFAULT_KIBANA_URL = "http://108.61.246.243:15601"
KIBANA_VERSION = "8.16.0"

DATA_VIEWS = {
    "sma-public-content-events": {
        "title": "public_content_events",
        "name": "Public content events",
        "timeFieldName": "event_time",
    },
    "sma-public-trend-metrics": {
        "title": "public_trend_metrics",
        "name": "Public trend metrics",
        "timeFieldName": "window_end",
    },
    "sma-public-trend-alerts": {
        "title": "public_trend_alerts",
        "name": "Public trend alerts",
        "timeFieldName": "window_end",
    },
}

LEGACY_OBJECTS = [
    ("search", "sma-latest-ai-briefings"),
    ("index-pattern", "sma-ai-trend-briefings"),
]

DASHBOARD_ID = "sma-vietnam-public-trend-intelligence"


def request_json(
    kibana_url: str,
    method: str,
    path: str,
    payload: dict[str, Any] | None = None,
    *,
    timeout: float = 30,
) -> dict[str, Any]:
    body = None if payload is None else json.dumps(payload).encode("utf-8")
    request = Request(
        f"{kibana_url.rstrip('/')}{path}",
        data=body,
        method=method,
        headers={
            "Content-Type": "application/json",
            "kbn-xsrf": "social-media-analytics-seed",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            response_body = response.read().decode("utf-8")
    except HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"{method} {path} failed: HTTP {exc.code}: {error_body}") from exc
    except URLError as exc:
        raise RuntimeError(f"{method} {path} failed: {exc}") from exc
    if not response_body:
        return {}
    return json.loads(response_body)


def wait_for_kibana(kibana_url: str, timeout_seconds: int) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        try:
            status = request_json(kibana_url, "GET", "/api/status", timeout=5)
            level = status.get("status", {}).get("overall", {}).get("level")
            if level == "available":
                return
        except Exception as exc:  # noqa: BLE001 - surfaced if the wait expires.
            last_error = exc
        time.sleep(3)
    detail = f" Last error: {last_error}" if last_error else ""
    raise TimeoutError(f"Kibana did not become available within {timeout_seconds}s.{detail}")


def saved_object(
    kibana_url: str,
    object_type: str,
    object_id: str,
    attributes: dict[str, Any],
    references: list[dict[str, str]] | None = None,
) -> None:
    encoded_type = quote(object_type, safe="")
    encoded_id = quote(object_id, safe="")
    request_json(
        kibana_url,
        "POST",
        f"/api/saved_objects/{encoded_type}/{encoded_id}?overwrite=true",
        {"attributes": attributes, "references": references or []},
    )


def delete_saved_object(kibana_url: str, object_type: str, object_id: str) -> None:
    encoded_type = quote(object_type, safe="")
    encoded_id = quote(object_id, safe="")
    try:
        request_json(kibana_url, "DELETE", f"/api/saved_objects/{encoded_type}/{encoded_id}")
    except RuntimeError as exc:
        if "HTTP 404" not in str(exc):
            raise


def cleanup_legacy_objects(kibana_url: str) -> None:
    for object_type, object_id in LEGACY_OBJECTS:
        delete_saved_object(kibana_url, object_type, object_id)


def search_source(index_ref_name: str | None = None) -> str:
    source: dict[str, Any] = {
        "query": {"query": "", "language": "kuery"},
        "filter": [],
    }
    if index_ref_name:
        source["indexRefName"] = index_ref_name
    return json.dumps(source, separators=(",", ":"))


def seed_data_views(kibana_url: str) -> None:
    for data_view_id, attributes in DATA_VIEWS.items():
        saved_object(
            kibana_url,
            "index-pattern",
            data_view_id,
            {
                "title": attributes["title"],
                "name": attributes["name"],
                "timeFieldName": attributes["timeFieldName"],
                "sourceFilters": "[]",
                "fields": "[]",
                "fieldAttrs": "{}",
                "fieldFormatMap": "{}",
                "runtimeFieldMap": "{}",
                "allowHidden": False,
            },
        )


def create_saved_search(
    kibana_url: str,
    object_id: str,
    title: str,
    data_view_id: str,
    columns: list[str],
    sort_field: str,
) -> None:
    index_ref = "kibanaSavedObjectMeta.searchSourceJSON.index"
    saved_object(
        kibana_url,
        "search",
        object_id,
        {
            "title": title,
            "description": "",
            "columns": columns,
            "sort": [[sort_field, "desc"]],
            "grid": {},
            "hideChart": False,
            "isTextBasedQuery": False,
            "usesAdHocDataView": False,
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": search_source(index_ref),
            },
        },
        [{"name": index_ref, "type": "index-pattern", "id": data_view_id}],
    )


def vega_saved_object(
    kibana_url: str,
    object_id: str,
    title: str,
    spec: dict[str, Any],
) -> None:
    vis_state = {
        "title": title,
        "type": "vega",
        "aggs": [],
        "params": {
            "spec": json.dumps(spec, ensure_ascii=False, indent=2),
        },
    }
    saved_object(
        kibana_url,
        "visualization",
        object_id,
        {
            "title": title,
            "description": "",
            "visState": json.dumps(vis_state, ensure_ascii=False, separators=(",", ":")),
            "uiStateJSON": "{}",
            "version": 1,
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": search_source(),
            },
        },
    )


def content_volume_spec() -> dict[str, Any]:
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "title": "Content volume over time",
        "data": {
            "url": {
                "%context%": True,
                "%timefield%": "event_time",
                "index": "public_content_events",
                "body": {
                    "size": 0,
                    "aggs": {
                        "by_time": {
                            "date_histogram": {
                                "field": "event_time",
                                "fixed_interval": "30m",
                                "min_doc_count": 0,
                            }
                        }
                    },
                },
            },
            "format": {"property": "aggregations.by_time.buckets"},
        },
        "mark": {"type": "bar", "color": "#2563eb"},
        "encoding": {
            "x": {"field": "key", "type": "temporal", "title": "Event time"},
            "y": {"field": "doc_count", "type": "quantitative", "title": "Documents"},
            "tooltip": [
                {"field": "key", "type": "temporal", "title": "Time"},
                {"field": "doc_count", "type": "quantitative", "title": "Documents"},
            ],
        },
    }


def top_topics_spec() -> dict[str, Any]:
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "title": "Top trending topics by mentions",
        "data": {
            "url": {
                "%context%": True,
                "%timefield%": "window_end",
                "index": "public_trend_metrics",
                "body": {
                    "size": 0,
                    "aggs": {
                        "topics": {
                            "terms": {
                                "field": "keyword.keyword",
                                "size": 12,
                                "order": {"mentions": "desc"},
                            },
                            "aggs": {
                                "mentions": {"sum": {"field": "content_count"}},
                                "score": {"sum": {"field": "trend_score"}},
                            },
                        }
                    },
                },
            },
            "format": {"property": "aggregations.topics.buckets"},
        },
        "mark": {"type": "bar", "color": "#16a34a"},
        "encoding": {
            "y": {"field": "key", "type": "nominal", "sort": "-x", "title": "Topic"},
            "x": {"field": "mentions.value", "type": "quantitative", "title": "Mentions"},
            "tooltip": [
                {"field": "key", "type": "nominal", "title": "Topic"},
                {"field": "mentions.value", "type": "quantitative", "title": "Mentions"},
                {"field": "score.value", "type": "quantitative", "title": "Trend score"},
            ],
        },
    }


def trend_strength_spec() -> dict[str, Any]:
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "title": "Trend mention volume over time",
        "data": {
            "url": {
                "%context%": True,
                "%timefield%": "window_end",
                "index": "public_trend_metrics",
                "body": {
                    "size": 0,
                    "aggs": {
                        "by_time": {
                            "date_histogram": {
                                "field": "window_end",
                                "fixed_interval": "30m",
                                "min_doc_count": 0,
                            },
                            "aggs": {
                                "mentions": {"sum": {"field": "content_count"}},
                                "score": {"sum": {"field": "trend_score"}},
                            },
                        }
                    },
                },
            },
            "format": {"property": "aggregations.by_time.buckets"},
        },
        "mark": {"type": "line", "point": True, "color": "#dc2626"},
        "encoding": {
            "x": {"field": "key", "type": "temporal", "title": "Window end"},
            "y": {"field": "mentions.value", "type": "quantitative", "title": "Mentions"},
            "tooltip": [
                {"field": "key", "type": "temporal", "title": "Window end"},
                {"field": "mentions.value", "type": "quantitative", "title": "Mentions"},
                {"field": "score.value", "type": "quantitative", "title": "Trend score"},
            ],
        },
    }


def source_distribution_spec() -> dict[str, Any]:
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "title": "Source distribution",
        "data": {
            "url": {
                "%context%": True,
                "%timefield%": "event_time",
                "index": "public_content_events",
                "body": {
                    "size": 0,
                    "aggs": {
                        "platforms": {
                            "terms": {
                                "field": "platform.keyword",
                                "size": 8,
                                "order": {"_count": "desc"},
                            }
                        }
                    },
                },
            },
            "format": {"property": "aggregations.platforms.buckets"},
        },
        "mark": {"type": "arc", "innerRadius": 45},
        "encoding": {
            "theta": {"field": "doc_count", "type": "quantitative", "title": "Documents"},
            "color": {
                "field": "key",
                "type": "nominal",
                "title": "Platform",
                "scale": {"range": ["#2563eb", "#16a34a", "#f59e0b", "#dc2626"]},
            },
            "tooltip": [
                {"field": "key", "type": "nominal", "title": "Platform"},
                {"field": "doc_count", "type": "quantitative", "title": "Documents"},
            ],
        },
    }


def alert_topics_spec() -> dict[str, Any]:
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "title": "Alert topics by trend score",
        "data": {
            "url": {
                "%context%": True,
                "%timefield%": "window_end",
                "index": "public_trend_alerts",
                "body": {
                    "size": 0,
                    "aggs": {
                        "topics": {
                            "terms": {
                                "field": "keyword.keyword",
                                "size": 10,
                                "order": {"score": "desc"},
                            },
                            "aggs": {
                                "score": {"sum": {"field": "trend_score"}},
                                "mentions": {"sum": {"field": "content_count"}},
                            },
                        }
                    },
                },
            },
            "format": {"property": "aggregations.topics.buckets"},
        },
        "mark": {"type": "bar", "color": "#f59e0b"},
        "encoding": {
            "y": {"field": "key", "type": "nominal", "sort": "-x", "title": "Alert topic"},
            "x": {"field": "score.value", "type": "quantitative", "title": "Trend score"},
            "tooltip": [
                {"field": "key", "type": "nominal", "title": "Topic"},
                {"field": "score.value", "type": "quantitative", "title": "Trend score"},
                {"field": "mentions.value", "type": "quantitative", "title": "Mentions"},
            ],
        },
    }


def seed_visualizations(kibana_url: str) -> None:
    visualizations = {
        "sma-content-volume-over-time": (
            "Content volume over time",
            content_volume_spec(),
        ),
        "sma-top-trending-topics": (
            "Top trending topics by mentions",
            top_topics_spec(),
        ),
        "sma-trend-mention-volume": (
            "Trend mention volume over time",
            trend_strength_spec(),
        ),
        "sma-source-distribution": (
            "Source distribution",
            source_distribution_spec(),
        ),
        "sma-alert-topics-by-score": (
            "Alert topics by trend score",
            alert_topics_spec(),
        ),
    }
    for object_id, (title, spec) in visualizations.items():
        vega_saved_object(kibana_url, object_id, title, spec)


def seed_searches(kibana_url: str) -> None:
    create_saved_search(
        kibana_url,
        "sma-latest-trend-alerts",
        "Latest trend alerts",
        "sma-public-trend-alerts",
        [
            "window_end",
            "keyword",
            "content_count",
            "trend_score",
            "representative_titles",
            "message",
        ],
        "window_end",
    )
    create_saved_search(
        kibana_url,
        "sma-representative-content",
        "Representative content events",
        "sma-public-content-events",
        [
            "event_time",
            "platform",
            "source",
            "source_category",
            "title",
            "keywords",
            "source_url",
        ],
        "event_time",
    )


def dashboard_panel(
    panel_type: str,
    object_id: str,
    ref_name: str,
    panel_index: str,
    x: int,
    y: int,
    w: int,
    h: int,
) -> dict[str, Any]:
    return {
        "version": KIBANA_VERSION,
        "type": panel_type,
        "gridData": {"x": x, "y": y, "w": w, "h": h, "i": panel_index},
        "panelIndex": panel_index,
        "embeddableConfig": {},
        "panelRefName": ref_name,
    }


def seed_dashboard(kibana_url: str) -> None:
    panels = [
        dashboard_panel("visualization", "sma-content-volume-over-time", "panel_0", "0", 0, 0, 24, 12),
        dashboard_panel("visualization", "sma-top-trending-topics", "panel_1", "1", 24, 0, 24, 16),
        dashboard_panel("visualization", "sma-trend-mention-volume", "panel_2", "2", 0, 12, 24, 12),
        dashboard_panel("visualization", "sma-source-distribution", "panel_3", "3", 0, 24, 12, 12),
        dashboard_panel("visualization", "sma-alert-topics-by-score", "panel_4", "4", 12, 24, 12, 12),
        dashboard_panel("search", "sma-latest-trend-alerts", "panel_5", "5", 24, 16, 24, 20),
        dashboard_panel("search", "sma-representative-content", "panel_6", "6", 0, 36, 48, 20),
    ]
    references = [
        {"name": "panel_0", "type": "visualization", "id": "sma-content-volume-over-time"},
        {"name": "panel_1", "type": "visualization", "id": "sma-top-trending-topics"},
        {"name": "panel_2", "type": "visualization", "id": "sma-trend-mention-volume"},
        {"name": "panel_3", "type": "visualization", "id": "sma-source-distribution"},
        {"name": "panel_4", "type": "visualization", "id": "sma-alert-topics-by-score"},
        {"name": "panel_5", "type": "search", "id": "sma-latest-trend-alerts"},
        {"name": "panel_6", "type": "search", "id": "sma-representative-content"},
    ]
    saved_object(
        kibana_url,
        "dashboard",
        DASHBOARD_ID,
        {
            "title": "Vietnam Public Trend Intelligence",
            "description": (
                "Demo dashboard for RSS and YouTube RSS trend analytics backed by Elasticsearch."
            ),
            "panelsJSON": json.dumps(panels, separators=(",", ":")),
            "optionsJSON": json.dumps(
                {
                    "useMargins": True,
                    "syncColors": True,
                    "syncCursor": True,
                    "syncTooltips": True,
                    "hidePanelTitles": False,
                },
                separators=(",", ":"),
            ),
            "version": 1,
            "timeRestore": True,
            "timeFrom": "now-24h",
            "timeTo": "now+12h",
            "refreshInterval": {
                "pause": False,
                "value": 60000,
            },
            "kibanaSavedObjectMeta": {
                "searchSourceJSON": search_source(),
            },
        },
        references,
    )


def seed_all(kibana_url: str) -> None:
    cleanup_legacy_objects(kibana_url)
    seed_data_views(kibana_url)
    seed_visualizations(kibana_url)
    seed_searches(kibana_url)
    seed_dashboard(kibana_url)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed Kibana saved objects for the public trend analytics demo."
    )
    parser.add_argument(
        "--kibana-url",
        default=DEFAULT_KIBANA_URL,
        help=f"Kibana base URL. Default: {DEFAULT_KIBANA_URL}",
    )
    parser.add_argument(
        "--wait-timeout",
        type=int,
        default=120,
        help="Seconds to wait for Kibana to become available before seeding.",
    )
    parser.add_argument(
        "--display-url",
        help="Public Kibana base URL to print after seeding. Defaults to --kibana-url.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    kibana_url = args.kibana_url.rstrip("/")
    wait_for_kibana(kibana_url, args.wait_timeout)
    seed_all(kibana_url)
    display_url = (args.display_url or kibana_url).rstrip("/")
    dashboard_url = f"{display_url}/app/dashboards#/view/{DASHBOARD_ID}"
    print(f"Seeded Kibana demo dashboard: {dashboard_url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
