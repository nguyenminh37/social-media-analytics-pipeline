import json
import logging
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
import gzip
from datetime import UTC, datetime
from html import unescape
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from kafka import KafkaProducer

from config.kafka_config import KAFKA_BOOTSTRAP_SERVERS


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (compatible; social-media-analytics-pipeline/1.0)"
)
ALLOW_INSECURE_SSL_FALLBACK = (
    os.getenv("ALLOW_INSECURE_SSL_FALLBACK", "true").lower() == "true"
)


def now_iso8601() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def to_iso8601(parsed_time: time.struct_time | None) -> str | None:
    if parsed_time is None:
        return None
    return datetime(*parsed_time[:6], tzinfo=UTC).isoformat().replace("+00:00", "Z")


def clean_text(value: str | None) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def fetch_payload(url: str, user_agent: str = DEFAULT_USER_AGENT) -> bytes:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": user_agent,
            "Accept-Encoding": "gzip",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            payload = response.read()
            if response.headers.get("Content-Encoding") == "gzip" or payload.startswith(
                b"\x1f\x8b"
            ):
                return gzip.decompress(payload)
            return payload
    except urllib.error.URLError as exc:
        reason = getattr(exc, "reason", None)
        if (
            ALLOW_INSECURE_SSL_FALLBACK
            and isinstance(reason, ssl.SSLCertVerificationError)
        ):
            logging.warning(
                "SSL verification failed for %s. Retrying without verification.",
                url,
            )
            insecure_context = ssl._create_unverified_context()
            with urllib.request.urlopen(
                request, timeout=20, context=insecure_context
            ) as response:
                payload = response.read()
                if response.headers.get("Content-Encoding") == "gzip" or payload.startswith(
                    b"\x1f\x8b"
                ):
                    return gzip.decompress(payload)
                return payload
        raise


def create_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda value: json.dumps(value, ensure_ascii=False).encode(
            "utf-8"
        ),
        key_serializer=lambda value: value.encode("utf-8") if value else None,
    )


def publish_events(
    producer: KafkaProducer,
    events: list[dict],
    topic: str,
) -> int:
    for event in events:
        producer.send(topic, event).get(timeout=10)
    producer.flush()
    return len(events)


def publish_keyed_events(
    producer: KafkaProducer,
    events: list[dict],
    topic: str,
    key_field: str,
) -> int:
    for event in events:
        key = event.get(key_field)
        producer.send(topic, key=str(key) if key else None, value=event).get(timeout=10)
    producer.flush()
    return len(events)
