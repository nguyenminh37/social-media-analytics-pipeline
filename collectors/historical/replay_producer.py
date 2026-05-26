import argparse
import csv
import json
import pathlib
import sys
import time

PROJECT_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from collectors.shared.common import create_producer, now_iso8601, publish_events
from config.kafka_config import RAW_POSTS_TOPIC
from schemas.legacy_posts.post_schema import POST_FIELDS


def normalize_event(record: dict) -> dict:
    event = {field: record.get(field) for field in POST_FIELDS}
    event["source"] = event.get("source") or "historical"
    event["ingested_at"] = now_iso8601()
    return event


def load_records(input_path: pathlib.Path) -> list[dict]:
    suffix = input_path.suffix.lower()
    if suffix == ".json":
        payload = json.loads(input_path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return [normalize_event(item) for item in payload]
        return [normalize_event(payload)]
    if suffix == ".csv":
        with input_path.open("r", encoding="utf-8", newline="") as handle:
            return [normalize_event(row) for row in csv.DictReader(handle)]
    if suffix == ".parquet":
        import pandas as pd

        dataframe = pd.read_parquet(input_path)
        return [normalize_event(row) for row in dataframe.to_dict(orient="records")]
    raise ValueError(f"Unsupported historical file format: {input_path.suffix}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_path", type=pathlib.Path)
    parser.add_argument("--sleep-seconds", type=float, default=0.0)
    parser.add_argument("--topic", default=RAW_POSTS_TOPIC)
    args = parser.parse_args()

    records = load_records(args.input_path)
    producer = create_producer()

    for record in records:
        publish_events(producer, [record], topic=args.topic)
        if args.sleep_seconds > 0:
            time.sleep(args.sleep_seconds)

    producer.close()


if __name__ == "__main__":
    main()
