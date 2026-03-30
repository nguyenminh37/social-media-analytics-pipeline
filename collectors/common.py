import json
import logging
import os
import re
import ssl
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from html import unescape

from kafka import KafkaProducer

from config.kafka_config import KAFKA_BOOTSTRAP_SERVERS, RAW_POSTS_TOPIC


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
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            return response.read()
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
                return response.read()
        raise


def create_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda value: json.dumps(value, ensure_ascii=False).encode(
            "utf-8"
        ),
    )


def publish_events(
    producer: KafkaProducer,
    events: list[dict],
    topic: str = RAW_POSTS_TOPIC,
) -> int:
    for event in events:
        producer.send(topic, event).get(timeout=10)
    producer.flush()
    return len(events)
