#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta, timezone
from itertools import cycle


DEFAULT_NAMESPACE = "social-media-analytics"
DEFAULT_ELASTICSEARCH_URL = "http://127.0.0.1:9201"
DEFAULT_MONGO_DEPLOYMENT = "deploy/social-media-mongodb"

CONTENT_INDEX = "public_content_events"
TREND_INDEX = "public_trend_metrics"
ALERT_INDEX = "public_trend_alerts"

NEWS_SOURCES = [
    ("vnexpress", "mainstream"),
    ("tuoitre", "mainstream"),
    ("thanhnien", "mainstream"),
    ("dantri", "mainstream"),
    ("vtv", "mainstream"),
    ("vietnamplus", "mainstream"),
    ("genk", "tech"),
    ("cafebiz", "business"),
]

YOUTUBE_SOURCES = [
    ("vtv24", "news"),
    ("vnexpress_youtube", "news"),
    ("thanhnien_youtube", "news"),
    ("tuoitre_media", "news"),
]

DEMO_WINDOW_COUNT = 48
DEMO_WINDOW_STEP_MINUTES = 30


def message_for_topic(keyword: str, content_count: int, titles: list[str]) -> str:
    return (
        f"Chủ đề {keyword} đang tăng mạnh với {content_count} lượt nhắc. "
        f"Nguồn nổi bật: {'; '.join(titles[:2])}."
    )


TOPICS = [
    {
        "keyword": "sáp nhập tỉnh thành",
        "score": 96,
        "sentiment": "neutral",
        "titles": [
            "Các địa phương công bố phương án vận hành sau sáp nhập",
            "Người dân quan tâm thủ tục hành chính khi thay đổi địa giới",
            "Chuyên gia: cần giữ ổn định dịch vụ công trong giai đoạn chuyển tiếp",
        ],
        "summary": "Các nguồn tin tập trung vào thủ tục, dữ liệu dân cư và dịch vụ công sau điều chỉnh địa giới.",
    },
    {
        "keyword": "giá vàng",
        "score": 88,
        "sentiment": "mixed",
        "titles": [
            "Giá vàng trong nước biến động mạnh trước giờ mở cửa",
            "Nhà đầu tư theo dõi sát chênh lệch vàng miếng và thế giới",
            "Thị trường vàng tăng nhiệt, chuyên gia khuyến nghị quản trị rủi ro",
        ],
        "summary": "Thảo luận xoay quanh biến động giá, nhu cầu phòng thủ và tâm lý nhà đầu tư.",
    },
    {
        "keyword": "nắng nóng miền bắc",
        "score": 82,
        "sentiment": "negative",
        "titles": [
            "Miền Bắc bước vào đợt nắng nóng diện rộng",
            "Ngành điện khuyến nghị tiết kiệm trong giờ cao điểm",
            "Bệnh viện cảnh báo nguy cơ sốc nhiệt ở trẻ em và người cao tuổi",
        ],
        "summary": "Nhiệt độ cao kéo theo cảnh báo sức khỏe, tiêu thụ điện và thay đổi lịch sinh hoạt.",
    },
    {
        "keyword": "thi tốt nghiệp",
        "score": 74,
        "sentiment": "positive",
        "titles": [
            "Thí sinh hoàn tất đăng ký dự thi tốt nghiệp THPT",
            "Nhiều trường mở kênh tư vấn tuyển sinh trực tuyến",
            "Bộ Giáo dục nhắc thí sinh kiểm tra thông tin trước hạn cuối",
        ],
        "summary": "Dòng tin tập trung vào lịch thi, hồ sơ đăng ký và tư vấn lựa chọn ngành.",
    },
    {
        "keyword": "chuyển đổi số",
        "score": 68,
        "sentiment": "positive",
        "titles": [
            "Doanh nghiệp nhỏ tăng đầu tư vào nền tảng số",
            "Dịch vụ công trực tuyến ghi nhận lượng truy cập tăng",
            "AI nội bộ được thử nghiệm trong chăm sóc khách hàng",
        ],
        "summary": "Các tín hiệu tích cực đến từ dịch vụ công, SME và ứng dụng AI trong vận hành.",
    },
    {
        "keyword": "du lịch hè",
        "score": 61,
        "sentiment": "positive",
        "titles": [
            "Các điểm đến biển kín phòng vào cuối tuần",
            "Hãng bay tăng chuyến phục vụ cao điểm hè",
            "Du khách ưu tiên combo gia đình và lịch trình ngắn ngày",
        ],
        "summary": "Nhu cầu du lịch hè tăng, nổi bật ở nhóm gia đình và các tuyến biển ngắn ngày.",
    },
]


def iso_z(value: datetime) -> str:
    return value.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def es_request(base_url: str, method: str, path: str, payload: dict | None = None) -> dict:
    body = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        response_body = response.read().decode("utf-8")
    return json.loads(response_body) if response_body else {}


def build_demo_documents(now: datetime) -> tuple[list[dict], list[dict], list[dict]]:
    content_events: list[dict] = []
    trend_metrics: list[dict] = []
    trend_alerts: list[dict] = []
    news_sources = cycle(NEWS_SOURCES)
    youtube_sources = cycle(YOUTUBE_SOURCES)
    aligned_now = now.replace(second=0, microsecond=0)

    for topic_index, topic in enumerate(TOPICS):
        keyword = topic["keyword"]
        for window_index in range(DEMO_WINDOW_COUNT):
            window_end = aligned_now - timedelta(minutes=DEMO_WINDOW_STEP_MINUTES * window_index)
            minute = (window_end.minute // 15) * 15
            window_end = window_end.replace(minute=minute)
            window_start = window_end - timedelta(hours=1)
            decay = max(0.18, 1 - (window_index / (DEMO_WINDOW_COUNT - 1)) ** 1.35)
            spike_boost = 1.35 if window_index < 3 else 1.0
            baseline = 1 + (topic_index % 3)
            content_count = max(
                1,
                int(round(((topic["score"] / 18) * decay + baseline) * spike_boost)),
            )
            trend_score = round(content_count * (1 + topic["score"] / 100), 2)
            metric = {
                "keyword": keyword,
                "content_count": content_count,
                "window_start": iso_z(window_start),
                "window_end": iso_z(window_end),
                "trend_score": trend_score,
                "news_count": max(1, content_count - 2),
                "youtube_count": min(2, content_count),
                "representative_titles": topic["titles"],
                "sentiment": topic["sentiment"],
            }
            trend_metrics.append(metric)
            if window_index < 6 and content_count >= 5:
                trend_alerts.append(
                    {
                        **metric,
                        "alert_type": "trend_spike",
                        "message": message_for_topic(keyword, content_count, topic["titles"]),
                    }
                )

            if window_index % 6 == 0:
                title_index = (window_index // 6) % len(topic["titles"])
                event_time = window_end - timedelta(minutes=7 + topic_index)
                source, category = next(news_sources)
                content_events.append(
                    {
                        "content_id": f"demo:news:{topic_index}:{window_index}",
                        "content_type": "article",
                        "platform": "news",
                        "source": source,
                        "source_category": category,
                        "title": topic["titles"][title_index],
                        "summary": topic["summary"],
                        "source_url": f"https://demo.local/news/{topic_index}-{window_index}",
                        "published_at": iso_z(event_time),
                        "ingested_at": iso_z(event_time + timedelta(minutes=2)),
                        "event_time": iso_z(event_time),
                        "keywords": [keyword, "việt nam", "thời sự"],
                        "keyword_text": f"{keyword} việt nam thời sự",
                        "sentiment": topic["sentiment"],
                        "sentiment_score": round((topic["score"] - 50) / 50, 2),
                        "sentiment_model": "demo-curated",
                    }
                )

            if window_index % 8 == 1:
                title_index = (window_index // 8) % len(topic["titles"])
                event_time = window_end - timedelta(minutes=11 + topic_index)
                source, category = next(youtube_sources)
                content_events.append(
                    {
                        "content_id": f"demo:youtube-rss:{topic_index}:{window_index}",
                        "content_type": "video",
                        "platform": "youtube",
                        "source": source,
                        "source_category": category,
                        "title": f"{topic['titles'][title_index]} | bản tin nhanh",
                        "summary": topic["summary"],
                        "source_url": f"https://www.youtube.com/watch?v=demo{topic_index}{window_index}",
                        "published_at": iso_z(event_time),
                        "ingested_at": iso_z(event_time + timedelta(minutes=1)),
                        "event_time": iso_z(event_time),
                        "channel_id": f"demo-channel-{source}",
                        "channel_title": source.replace("_", " ").title(),
                        "keywords": [keyword, "youtube", "bản tin"],
                        "keyword_text": f"{keyword} youtube bản tin",
                        "sentiment": topic["sentiment"],
                        "sentiment_score": round((topic["score"] - 50) / 50, 2),
                        "sentiment_model": "demo-curated",
                    }
                )

    return content_events, trend_metrics, trend_alerts


def bulk_index(base_url: str, index_name: str, documents: list[dict], id_fields: list[str]) -> None:
    lines: list[str] = []
    for document in documents:
        document_id = ":".join(str(document[field]) for field in id_fields)
        lines.append(json.dumps({"index": {"_index": index_name, "_id": document_id}}, ensure_ascii=False))
        lines.append(json.dumps(document, ensure_ascii=False))
    body = ("\n".join(lines) + "\n").encode("utf-8")
    request = urllib.request.Request(
        f"{base_url.rstrip('/')}/_bulk?refresh=true",
        data=body,
        method="POST",
        headers={"Content-Type": "application/x-ndjson"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    if payload.get("errors"):
        raise RuntimeError(f"Elasticsearch bulk index failed for {index_name}")


def seed_elasticsearch(
    base_url: str,
    content: list[dict],
    metrics: list[dict],
    alerts: list[dict],
    from_time: datetime,
    to_time: datetime,
) -> None:
    for index_name in [CONTENT_INDEX, TREND_INDEX, ALERT_INDEX]:
        es_request(base_url, "PUT", f"/{index_name}/_settings", {"index": {"number_of_replicas": 0}})
    es_request(
        base_url,
        "POST",
        f"/{CONTENT_INDEX}/_delete_by_query?conflicts=proceed&refresh=true",
        {"query": {"range": {"event_time": {"gte": iso_z(from_time), "lte": iso_z(to_time)}}}},
    )
    for index_name in [TREND_INDEX, ALERT_INDEX]:
        es_request(
            base_url,
            "POST",
            f"/{index_name}/_delete_by_query?conflicts=proceed&refresh=true",
            {"query": {"range": {"window_end": {"gte": iso_z(from_time), "lte": iso_z(to_time)}}}},
        )
        es_request(
            base_url,
            "POST",
            f"/{index_name}/_update_by_query?conflicts=proceed&refresh=true",
            {
                "script": {
                    "source": (
                        "ctx._source.remove('first_news_time'); "
                        "ctx._source.remove('first_youtube_time'); "
                        "ctx._source.remove('youtube_lag_minutes');"
                    ),
                    "lang": "painless",
                },
                "query": {"match_all": {}},
            },
        )
    bulk_index(base_url, CONTENT_INDEX, content, ["content_id"])
    bulk_index(base_url, TREND_INDEX, metrics, ["keyword", "window_start", "window_end"])
    bulk_index(base_url, ALERT_INDEX, alerts, ["keyword", "window_start", "window_end", "alert_type"])


def mongosh_literal(value) -> str:
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, list):
        return "[" + ",".join(mongosh_literal(item) for item in value) + "]"
    if isinstance(value, dict):
        return "{" + ",".join(f"{json.dumps(key, ensure_ascii=False)}:{mongosh_literal(item)}" for key, item in value.items()) + "}"
    return json.dumps(value, ensure_ascii=False)


def mongo_script(
    content: list[dict],
    metrics: list[dict],
    alerts: list[dict],
    from_time: datetime,
    to_time: datetime,
) -> str:
    def with_dates(document: dict, date_fields: list[str]) -> str:
        converted = document.copy()
        date_values = {field: converted.pop(field) for field in date_fields if field in converted}
        parts = [mongosh_literal(converted).rstrip("}")]
        for field, value in date_values.items():
            parts.append(f",{json.dumps(field)}: new Date({json.dumps(value)})")
        return "".join(parts) + "}"

    content_docs = ",".join(
        with_dates(document, ["published_at", "ingested_at", "event_time"]) for document in content
    )
    metric_docs = ",".join(
        with_dates(document, ["window_start", "window_end"]) for document in metrics
    )
    alert_docs = ",".join(
        with_dates(document, ["window_start", "window_end"]) for document in alerts
    )
    return f"""
const demoFrom = new Date({json.dumps(iso_z(from_time))});
const demoTo = new Date({json.dumps(iso_z(to_time))});
db.public_content_events.deleteMany({{event_time: {{$gte: demoFrom, $lte: demoTo}}}});
db.public_trend_metrics.deleteMany({{window_end: {{$gte: demoFrom, $lte: demoTo}}}});
db.public_trend_alerts.deleteMany({{window_end: {{$gte: demoFrom, $lte: demoTo}}}});
db.public_trend_metrics.updateMany({{}}, {{$unset: {{first_news_time: "", first_youtube_time: "", youtube_lag_minutes: ""}}}});
db.public_trend_alerts.updateMany({{}}, {{$unset: {{first_news_time: "", first_youtube_time: "", youtube_lag_minutes: ""}}}});
db.public_content_events.insertMany([{content_docs}]);
db.public_trend_metrics.insertMany([{metric_docs}]);
db.public_trend_alerts.insertMany([{alert_docs}]);
db.public_content_events.createIndex({{event_time:-1}});
db.public_trend_metrics.createIndex({{window_end:-1, keyword:1}});
db.public_trend_alerts.createIndex({{window_end:-1, trend_score:-1}});
printjson({{
  public_content_events: db.public_content_events.countDocuments({{content_id: /^demo:/}}),
  public_trend_metrics: db.public_trend_metrics.countDocuments({{keyword: {{$in: {mongosh_literal([topic["keyword"] for topic in TOPICS])}}}}}),
  public_trend_alerts: db.public_trend_alerts.countDocuments({{keyword: {{$in: {mongosh_literal([topic["keyword"] for topic in TOPICS])}}}}})
}});
"""


def seed_mongo(
    namespace: str,
    deployment: str,
    content: list[dict],
    metrics: list[dict],
    alerts: list[dict],
    from_time: datetime,
    to_time: datetime,
) -> None:
    script = mongo_script(content, metrics, alerts, from_time, to_time)
    command = [
        "kubectl",
        "exec",
        "-i",
        "-n",
        namespace,
        deployment,
        "--",
        "mongosh",
        "analytics",
        "--quiet",
    ]
    subprocess.run(command, input=script, text=True, check=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed polished public trend demo data.")
    parser.add_argument("--namespace", default=DEFAULT_NAMESPACE)
    parser.add_argument("--mongo-deployment", default=DEFAULT_MONGO_DEPLOYMENT)
    parser.add_argument("--elasticsearch-url", default=DEFAULT_ELASTICSEARCH_URL)
    parser.add_argument("--skip-mongo", action="store_true")
    parser.add_argument("--skip-elasticsearch", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    now = datetime.now(timezone.utc)
    reset_from = now - timedelta(hours=36)
    reset_to = now + timedelta(hours=12)
    content, metrics, alerts = build_demo_documents(now)
    if not args.skip_elasticsearch:
        seed_elasticsearch(args.elasticsearch_url, content, metrics, alerts, reset_from, reset_to)
    if not args.skip_mongo:
        seed_mongo(args.namespace, args.mongo_deployment, content, metrics, alerts, reset_from, reset_to)
    print(
        f"Seeded demo public trend data: {len(content)} content, "
        f"{len(metrics)} metrics, {len(alerts)} alerts"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
