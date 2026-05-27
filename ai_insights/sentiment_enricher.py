import logging
import time
from datetime import UTC, datetime, timedelta

from pymongo import MongoClient, UpdateOne

from config.ai_config import SENTIMENT_BATCH_LIMIT, SENTIMENT_MODEL_NAME
from config.mongo_config import MONGO_DATABASE, MONGO_URI
from config.storage_config import PUBLIC_CONTENT_EVENTS_COLLECTION


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)


def _load_pipeline():
    from transformers import pipeline

    return pipeline("sentiment-analysis", model=SENTIMENT_MODEL_NAME, truncation=True)


def _normalize_label(label: str) -> str:
    normalized = label.lower()
    if "positive" in normalized or normalized in {"5 stars", "4 stars"}:
        return "positive"
    if "negative" in normalized or normalized in {"1 star", "2 stars"}:
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


def run_once(model_pipeline=None) -> int:
    records = fetch_unscored_content()
    if not records:
        return 0
    model_pipeline = model_pipeline or _load_pipeline()
    texts = [
        " ".join(
            part for part in [record.get("title"), record.get("summary")] if part
        )[:512]
        or " "
        for record in records
    ]
    predictions = model_pipeline(texts)
    operations = []
    for record, prediction in zip(records, predictions):
        operations.append(
            UpdateOne(
                {"content_id": record["content_id"]},
                {
                    "$set": {
                        "sentiment": _normalize_label(prediction.get("label", "")),
                        "sentiment_score": float(prediction.get("score", 0.0)),
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
    model_pipeline = _load_pipeline()
    while True:
        try:
            run_once(model_pipeline)
        except Exception as exc:
            log.exception("Sentiment enrichment failed: %s", exc)
        time.sleep(300)


if __name__ == "__main__":
    main()
