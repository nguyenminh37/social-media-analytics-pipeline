import hashlib
import logging
import time
import xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from html import unescape

from kafka.errors import NoBrokersAvailable

from collectors.shared.common import (
    clean_text,
    create_producer,
    fetch_payload,
    now_iso8601,
    publish_keyed_events,
)
from config.kafka_config import KAFKA_BOOTSTRAP_SERVERS, RAW_NEWS_ARTICLES_TOPIC
from config.source_config import NEWS_RSS_FETCH_INTERVAL_SECONDS, NEWS_RSS_SOURCES, RssSource


log = logging.getLogger(__name__)


def _iso_from_rss_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).isoformat()
    except (TypeError, ValueError, IndexError):
        return None


def _find_text(element: ET.Element, tag: str) -> str | None:
    child = element.find(tag)
    if child is None or child.text is None:
        return None
    return unescape(child.text).strip()


def _article_id(source: str, link: str | None, title: str | None) -> str:
    value = link or f"{source}:{title or ''}"
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()
    return f"{source}:{digest}"


def parse_news_rss(payload: bytes, source: RssSource) -> list[dict]:
    root = ET.fromstring(payload)
    records: list[dict] = []
    for item in root.findall(".//item"):
        title = clean_text(_find_text(item, "title"))
        link = _find_text(item, "link") or _find_text(item, "guid")
        description = clean_text(_find_text(item, "description"))
        published_at = _iso_from_rss_date(
            _find_text(item, "pubDate") or _find_text(item, "published")
        )
        if not title and not link:
            continue
        records.append(
            {
                "article_id": _article_id(source.name, link, title),
                "platform": "news",
                "source": source.name,
                "source_category": source.category,
                "title": title,
                "summary": description,
                "url": link,
                "published_at": published_at,
                "ingested_at": now_iso8601(),
            }
        )
    return records


def fetch_source(source: RssSource) -> list[dict]:
    payload = fetch_payload(source.url)
    return parse_news_rss(payload, source)


def filter_new_records(records: list[dict], seen_ids: set[str], key_field: str) -> list[dict]:
    new_records: list[dict] = []
    for record in records:
        record_id = record.get(key_field)
        if not record_id or record_id in seen_ids:
            continue
        seen_ids.add(record_id)
        new_records.append(record)
    return new_records


def collect_news_snapshot(
    sources: list[RssSource] | None = None,
    seen_article_ids: set[str] | None = None,
) -> list[dict]:
    sources = sources or NEWS_RSS_SOURCES
    seen_article_ids = seen_article_ids if seen_article_ids is not None else set()
    records: list[dict] = []
    for source in sources:
        try:
            records.extend(filter_new_records(fetch_source(source), seen_article_ids, "article_id"))
        except Exception as exc:
            log.warning("Failed to fetch %s RSS feed: %s", source.name, exc)
    return records


def publish_news_snapshot(producer, records: list[dict]) -> int:
    return publish_keyed_events(producer, records, RAW_NEWS_ARTICLES_TOPIC, "article_id")


def run_once(seen_article_ids: set[str] | None = None) -> dict:
    seen_article_ids = seen_article_ids or set()
    try:
        producer = create_producer()
    except NoBrokersAvailable:
        logging.error("Cannot connect to Kafka at %s", KAFKA_BOOTSTRAP_SERVERS)
        return {"articles": 0}
    try:
        records = collect_news_snapshot(seen_article_ids=seen_article_ids)
        published = publish_news_snapshot(producer, records)
        log.info("Published %s news RSS articles", published)
        return {"articles": published}
    finally:
        producer.close()


def main() -> None:
    logging.info("Publishing Vietnamese news RSS articles")
    seen_article_ids: set[str] = set()
    try:
        while True:
            run_once(seen_article_ids)
            time.sleep(NEWS_RSS_FETCH_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logging.info("Stopping news RSS producer")


if __name__ == "__main__":
    main()
