import logging
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta

from pymongo import MongoClient, UpdateOne

from config.ai_config import GEMINI_API_KEY, SENTIMENT_BATCH_LIMIT, SENTIMENT_MODEL_NAME
from config.mongo_config import MONGO_DATABASE, MONGO_URI
from config.storage_config import PUBLIC_CONTENT_EVENTS_COLLECTION


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def _normalize_label(label: str) -> str:
    normalized = label.lower()
    if "positive" in normalized:
        return "positive"
    if "negative" in normalized:
        return "negative"
    return "neutral"


def fetch_unscored_content(limit: int = SENTIMENT_BATCH_LIMIT) -> list[dict]:
    since = datetime.now(UTC) - timedelta(days=7)
    with MongoClient(MONGO_URI) as client:
        return list(
            client[MONGO_DATABASE][PUBLIC_CONTENT_EVENTS_COLLECTION]
            .find(
                {
                    "$or": [
                        {"sentiment_model": {"$exists": False}},
                        {"sentiment_model": None},
                    ],
                    "event_time": {"$gte": since},
                },
                {"_id": 0, "content_id": 1, "title": 1, "summary": 1},
            )
            .limit(limit)
        )


def build_sentiment_prompt(records: list[dict]) -> str:
    items = []
    for record in records:
        items.append(
            {
                "content_id": record["content_id"],
                "title": record.get("title") or "",
                "summary": (record.get("summary") or "")[:400],
            }
        )
    return (
        "Classify sentiment for Vietnamese news/video titles. "
        "Use only one label per item: positive, neutral, negative. "
        "Return valid JSON array, each item with content_id, sentiment, score. "
        "Score is confidence from 0 to 1. No markdown.\n\n"
        f"DATA:\n{json.dumps(items, ensure_ascii=False)}"
    )


def call_gemini_sentiment(records: list[dict]) -> list[dict]:
    if not GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY is required for sentiment enrichment")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{urllib.parse.quote(SENTIMENT_MODEL_NAME)}:generateContent"
        f"?key={urllib.parse.quote(GEMINI_API_KEY)}"
    )
    payload = {
        "contents": [{"parts": [{"text": build_sentiment_prompt(records)}]}],
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
        raise RuntimeError(f"Gemini sentiment request failed: {exc.code} {detail[:300]}") from exc

    text = (
        result.get("candidates", [{}])[0]
        .get("content", {})
        .get("parts", [{}])[0]
        .get("text", "[]")
    )
    parsed = json.loads(text)
    return parsed if isinstance(parsed, list) else []


def run_once() -> int:
    records = fetch_unscored_content()
    if not records:
        return 0
    predictions = {
        item.get("content_id"): item for item in call_gemini_sentiment(records)
    }
    operations = []
    for record in records:
        prediction = predictions.get(record["content_id"], {})
        operations.append(
            UpdateOne(
                {"content_id": record["content_id"]},
                {
                    "$set": {
                        "sentiment": _normalize_label(prediction.get("sentiment", "")),
                        "sentiment_score": float(prediction.get("score", 0.0) or 0.0),
                        "sentiment_model": SENTIMENT_MODEL_NAME,
                        "sentiment_scored_at": datetime.now(UTC),
                    }
                },
            )
        )
    with MongoClient(MONGO_URI) as client:
        client[MONGO_DATABASE][PUBLIC_CONTENT_EVENTS_COLLECTION].bulk_write(
            operations, ordered=False
        )
    log.info("Scored sentiment for %s content records", len(operations))
    return len(operations)


def main() -> None:
    while True:
        try:
            run_once()
        except Exception as exc:
            log.exception("Sentiment enrichment failed: %s", exc)
        time.sleep(300)


if __name__ == "__main__":
    main()
