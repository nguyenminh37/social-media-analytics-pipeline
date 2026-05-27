import json
import logging
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta

from elasticsearch import Elasticsearch
from pymongo import DESCENDING, MongoClient

from config.ai_config import (
    AI_BRIEFING_INTERVAL_MINUTES,
    AI_BRIEFING_LOOKBACK_HOURS,
    AI_BRIEFING_TOPICS_LIMIT,
    GEMINI_API_KEY,
    GEMINI_MODEL,
)
from config.mongo_config import MONGO_DATABASE, MONGO_URI
from config.storage_config import (
    AI_TREND_BRIEFINGS_COLLECTION,
    AI_TREND_BRIEFINGS_INDEX,
    PUBLIC_CONTENT_EVENTS_COLLECTION,
    PUBLIC_TREND_METRICS_COLLECTION,
)


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _json_ready(value):
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_json_ready(item) for item in value]
    if isinstance(value, dict):
        return {key: _json_ready(item) for key, item in value.items()}
    return value


def fetch_briefing_context(now: datetime | None = None) -> dict:
    now = now or _utc_now()
    from_time = now - timedelta(hours=AI_BRIEFING_LOOKBACK_HOURS)
    with MongoClient(MONGO_URI) as client:
        database = client[MONGO_DATABASE]
        trends = list(
            database[PUBLIC_TREND_METRICS_COLLECTION]
            .find(
                {"window_end": {"$gte": from_time}},
                {"_id": 0},
            )
            .sort([("window_end", DESCENDING), ("content_count", DESCENDING)])
            .limit(AI_BRIEFING_TOPICS_LIMIT)
        )
        topic_samples = {}
        for trend in trends[:5]:
            keyword = trend.get("keyword")
            if not keyword:
                continue
            topic_samples[keyword] = list(
                database[PUBLIC_CONTENT_EVENTS_COLLECTION]
                .find(
                    {
                        "keywords": keyword,
                        "event_time": {"$gte": from_time},
                    },
                    {
                        "_id": 0,
                        "platform": 1,
                        "source": 1,
                        "title": 1,
                        "source_url": 1,
                        "event_time": 1,
                    },
                )
                .sort([("event_time", DESCENDING)])
                .limit(4)
            )

    return _json_ready(
        {
            "window_start": from_time,
            "window_end": now,
            "trends": trends,
            "topic_samples": topic_samples,
        }
    )


def build_prompt(context: dict) -> str:
    return (
        "Ban la analyst cho dashboard xu huong thoi su Viet Nam. "
        "Chi dung du lieu JSON duoc cung cap, khong suy doan ngoai dataset. "
        "Tra ve JSON hop le voi cac field: headline, summary, key_insights, "
        "watch_topics, anomalies, recommended_filters. Viet ngan gon bang tieng Viet.\n\n"
        f"DATA:\n{json.dumps(context, ensure_ascii=False)}"
    )


def call_gemini(prompt: str) -> dict:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is required")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{urllib.parse.quote(GEMINI_MODEL)}:generateContent"
        f"?key={urllib.parse.quote(GEMINI_API_KEY)}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json"},
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Gemini request failed: {exc.code} {detail[:300]}") from exc

    text = (
        result.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "{}")
    )
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {"headline": "AI briefing parse failed", "summary": text, "key_insights": []}


def build_template_briefing(context: dict) -> dict:
    trends = context.get("trends", [])
    top = trends[0] if trends else {}
    headline = (
        f"Topic '{top.get('keyword')}' dang dan dau voi {top.get('content_count')} tin"
        if top
        else "Chua co du lieu trend trong khung gio hien tai"
    )
    return {
        "headline": headline,
        "summary": "Briefing fallback duoc tao tu metric rule-based.",
        "key_insights": [
            f"{trend.get('keyword')}: {trend.get('content_count')} mentions"
            for trend in trends[:5]
        ],
        "watch_topics": [trend.get("keyword") for trend in trends[:5]],
        "anomalies": [],
        "recommended_filters": {"time_range": "last_6h"},
    }


def persist_briefing(context: dict, briefing: dict) -> dict:
    now = _utc_now()
    document = {
        "briefing_id": f"briefing:{now.strftime('%Y%m%d%H%M%S')}",
        "created_at": now,
        "model": GEMINI_MODEL if GEMINI_API_KEY else "rule_based_fallback",
        "window_start": context.get("window_start"),
        "window_end": context.get("window_end"),
        "input_topic_count": len(context.get("trends", [])),
        "briefing": briefing,
    }
    with MongoClient(MONGO_URI) as client:
        client[MONGO_DATABASE][AI_TREND_BRIEFINGS_COLLECTION].replace_one(
            {"briefing_id": document["briefing_id"]},
            document,
            upsert=True,
        )
    try:
        es = Elasticsearch(ELASTICSEARCH_HOST)
        es.index(
            index=AI_TREND_BRIEFINGS_INDEX,
            id=document["briefing_id"],
            document=_json_ready(document),
        )
    except Exception as exc:
        log.warning("Skipping Elasticsearch AI briefing sink: %s", exc)
    return document


def run_once() -> dict:
    context = fetch_briefing_context()
    if GEMINI_API_KEY and context.get("trends"):
        briefing = call_gemini(build_prompt(context))
    else:
        briefing = build_template_briefing(context)
    document = persist_briefing(context, briefing)
    log.info("Created AI trend briefing %s", document["briefing_id"])
    return _json_ready(document)


def main() -> None:
    while True:
        try:
            run_once()
        except Exception as exc:
            log.exception("AI briefing job failed: %s", exc)
        time.sleep(AI_BRIEFING_INTERVAL_MINUTES * 60)


if __name__ == "__main__":
    main()
