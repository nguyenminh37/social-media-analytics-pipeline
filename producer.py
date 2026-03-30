import json
import logging
import os
import ssl
import time
import urllib.error
import urllib.request

import feedparser
from kafka import KafkaProducer
from kafka.errors import NoBrokersAvailable


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)

KAFKA_BOOTSTRAP_SERVERS = os.getenv("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092")
TOPIC = os.getenv("KAFKA_TOPIC", "news-stream")
RSS_URL = os.getenv("RSS_URL", "https://vnexpress.net/rss/tin-moi-nhat.rss")
FETCH_INTERVAL_SECONDS = int(os.getenv("FETCH_INTERVAL_SECONDS", "10000"))
ALLOW_INSECURE_SSL_FALLBACK = (
    os.getenv("ALLOW_INSECURE_SSL_FALLBACK", "true").lower() == "true"
)


def create_producer() -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda value: json.dumps(value, ensure_ascii=False).encode(
            "utf-8"
        ),
    )


def fetch_rss() -> list[dict]:
    request = urllib.request.Request(
        RSS_URL,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; social-media-analytics-pipeline/1.0)"
        },
    )

    try:
        payload = fetch_payload(request)
    except urllib.error.URLError as exc:
        logging.error("Failed to fetch RSS from %s: %s", RSS_URL, exc)
        return []

    feed = feedparser.parse(payload)
    articles = []

    if getattr(feed, "bozo", 0):
        logging.warning("RSS parse warning for %s: %s", RSS_URL, feed.bozo_exception)

    for entry in feed.entries:
        articles.append(
            {
                "title": getattr(entry, "title", ""),
                "link": getattr(entry, "link", ""),
                "published": getattr(entry, "published", ""),
                "summary": getattr(entry, "summary", ""),
            }
        )

    if not articles:
        logging.warning("RSS feed returned no entries from %s", RSS_URL)

    return articles


def fetch_payload(request: urllib.request.Request) -> bytes:
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
                "SSL verification failed for %s. Retrying with insecure SSL fallback for local development.",
                RSS_URL,
            )
            insecure_context = ssl._create_unverified_context()
            with urllib.request.urlopen(
                request, timeout=20, context=insecure_context
            ) as response:
                return response.read()
        raise


def main() -> None:
    try:
        producer = create_producer()
    except NoBrokersAvailable:
        logging.error(
            "Cannot connect to Kafka at %s. Start Docker/OrbStack and run `docker compose up -d` first.",
            KAFKA_BOOTSTRAP_SERVERS,
        )
        return

    logging.info("Kafka producer connected to %s", KAFKA_BOOTSTRAP_SERVERS)
    logging.info("Publishing RSS feed from %s to topic %s", RSS_URL, TOPIC)

    try:
        while True:
            articles = fetch_rss()
            logging.info("Fetched %s articles", len(articles))

            for article in articles:
                future = producer.send(TOPIC, article)
                future.get(timeout=10)
                print(f"Sent: {article['title']}")

            producer.flush()
            time.sleep(FETCH_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logging.info("Stopping producer")
    finally:
        producer.flush()
        producer.close()


if __name__ == "__main__":
    main()
