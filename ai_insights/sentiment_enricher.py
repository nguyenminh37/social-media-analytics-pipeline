import logging
import json
import os
import re
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime, timedelta
from functools import lru_cache

from elasticsearch import Elasticsearch
from pymongo import MongoClient, UpdateOne

from config.ai_config import (
    GEMINI_API_KEY,
    SENTIMENT_BATCH_LIMIT,
    SENTIMENT_LEXICON_PATH,
    SENTIMENT_MODEL_NAME,
    SENTIMENT_PROVIDER,
)
from config.mongo_config import MONGO_DATABASE, MONGO_URI
from config.storage_config import PUBLIC_CONTENT_EVENTS_COLLECTION, PUBLIC_CONTENT_EVENTS_INDEX


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)
ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
VNEMOLEX_MODEL_NAME = "vnemolex-cc-by-4.0"
NEUTRAL_FALLBACK_MODEL_NAME = "neutral_fallback"


def _normalize_label(label: str) -> str:
    normalized = str(label or "").lower()
    if "positive" in normalized:
        return "positive"
    if "negative" in normalized:
        return "negative"
    return "neutral"


def _ascii_fold(text: str) -> str:
    value = unicodedata.normalize("NFD", text)
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    return value.replace("đ", "d").replace("Đ", "D").lower()


def _tokenize(text: str | None) -> list[str]:
    normalized = unicodedata.normalize("NFC", text or "").lower()
    return [_ascii_fold(token) for token in re.findall(r"[^\W_]+", normalized, re.UNICODE)]


@lru_cache(maxsize=1)
def _load_vnemolex() -> tuple[dict[tuple[str, ...], tuple[int, int]], int]:
    with open(SENTIMENT_LEXICON_PATH, encoding="utf-8") as file:
        payload = json.load(file)
    lexicon: dict[tuple[str, ...], tuple[int, int]] = {}
    max_size = 1
    for entry in payload.get("entries", []):
        tokens = tuple(entry.get("tokens") or [])
        if not tokens:
            continue
        positive = int(entry.get("positive", 0) or 0)
        negative = int(entry.get("negative", 0) or 0)
        if positive == 0 and negative == 0:
            continue
        lexicon[tokens] = (positive, negative)
        max_size = max(max_size, len(tokens))
    return lexicon, max_size


def score_vnemolex_sentiment(text: str | None) -> tuple[str, float]:
    tokens = _tokenize(text)
    if not tokens:
        return "neutral", 0.0
    lexicon, max_size = _load_vnemolex()
    used = [False] * len(tokens)
    positive_score = 0
    negative_score = 0

    for size in range(min(max_size, len(tokens)), 0, -1):
        for index in range(0, len(tokens) - size + 1):
            if any(used[index : index + size]):
                continue
            scores = lexicon.get(tuple(tokens[index : index + size]))
            if scores is None:
                continue
            positive, negative = scores
            positive_score += positive
            negative_score += negative
            for used_index in range(index, index + size):
                used[used_index] = True

    total = positive_score + negative_score
    if total == 0 or positive_score == negative_score:
        return "neutral", 0.0
    if positive_score > negative_score:
        return "positive", round((positive_score - negative_score) / total, 3)
    return "negative", round((negative_score - positive_score) / total, 3)


def build_template_sentiment(records: list[dict]) -> list[dict]:
    return [
        {
            "content_id": record["content_id"],
            "sentiment": "neutral",
            "score": 0.0,
            "model": NEUTRAL_FALLBACK_MODEL_NAME,
        }
        for record in records
    ]


def build_vnemolex_sentiment(records: list[dict]) -> list[dict]:
    predictions = []
    for record in records:
        text = " ".join(
            value
            for value in [record.get("title") or "", record.get("summary") or ""]
            if value
        )
        sentiment, score = score_vnemolex_sentiment(text)
        predictions.append(
            {
                "content_id": record["content_id"],
                "sentiment": sentiment,
                "score": score,
                "model": VNEMOLEX_MODEL_NAME,
            }
        )
    return predictions


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
                "summary": (record.get("summary") or "")[:160],
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
    if not isinstance(parsed, list):
        return []
    for item in parsed:
        if isinstance(item, dict):
            item.setdefault("model", SENTIMENT_MODEL_NAME)
    return parsed


def classify_sentiment(records: list[dict]) -> list[dict]:
    if SENTIMENT_PROVIDER == "gemini":
        try:
            return call_gemini_sentiment(records)
        except Exception as exc:
            log.warning("Falling back to VnEmoLex sentiment labels: %s", exc)
    if SENTIMENT_PROVIDER == "neutral":
        return build_template_sentiment(records)
    try:
        return build_vnemolex_sentiment(records)
    except Exception as exc:
        log.warning("Falling back to neutral sentiment labels: %s", exc)
        return build_template_sentiment(records)


def run_once() -> int:
    records = fetch_unscored_content()
    if not records:
        return 0
    sentiment_items = classify_sentiment(records)
    predictions = {item.get("content_id"): item for item in sentiment_items}
    operations = []
    scored_records = []
    for record in records:
        prediction = predictions.get(record["content_id"], {})
        sentiment = _normalize_label(prediction.get("sentiment", ""))
        score = float(prediction.get("score", 0.0) or 0.0)
        model = prediction.get("model") or SENTIMENT_MODEL_NAME
        scored_at = datetime.now(UTC)
        operations.append(
            UpdateOne(
                {"content_id": record["content_id"]},
                {
                    "$set": {
                        "sentiment": sentiment,
                        "sentiment_score": score,
                        "sentiment_model": model,
                        "sentiment_scored_at": scored_at,
                    }
                },
            )
        )
        scored_records.append(
            {
                "content_id": record["content_id"],
                "sentiment": sentiment,
                "sentiment_score": score,
                "sentiment_model": model,
                "sentiment_scored_at": scored_at.isoformat(),
            }
        )
    with MongoClient(MONGO_URI) as client:
        client[MONGO_DATABASE][PUBLIC_CONTENT_EVENTS_COLLECTION].bulk_write(
            operations, ordered=False
        )
    update_elasticsearch(scored_records)
    log.info("Scored sentiment for %s content records", len(operations))
    return len(operations)


def update_elasticsearch(scored_records: list[dict]) -> None:
    try:
        client = Elasticsearch(ELASTICSEARCH_HOST)
        for record in scored_records:
            client.update(
                index=PUBLIC_CONTENT_EVENTS_INDEX,
                id=record["content_id"],
                doc={key: value for key, value in record.items() if key != "content_id"},
                doc_as_upsert=False,
            )
    except Exception as exc:
        log.warning("Skipping Elasticsearch sentiment update: %s", exc)


def main() -> None:
    while True:
        try:
            run_once()
        except Exception as exc:
            log.exception("Sentiment enrichment failed: %s", exc)
        time.sleep(300)


if __name__ == "__main__":
    main()
