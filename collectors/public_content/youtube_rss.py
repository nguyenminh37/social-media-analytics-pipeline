import hashlib
import logging
import time
import xml.etree.ElementTree as ET

from kafka.errors import NoBrokersAvailable

from collectors.public_content.rss import filter_new_records
from collectors.shared.common import clean_text, create_producer, fetch_payload, now_iso8601, publish_keyed_events
from config.kafka_config import KAFKA_BOOTSTRAP_SERVERS, RAW_YOUTUBE_RSS_VIDEOS_TOPIC
from config.source_config import (
    YOUTUBE_RSS_CHANNELS,
    YOUTUBE_RSS_FETCH_INTERVAL_SECONDS,
    YouTubeRssChannel,
)


log = logging.getLogger(__name__)

ATOM_NS = {"atom": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}
MEDIA_NS = {"media": "http://search.yahoo.com/mrss/"}


def build_youtube_feed_url(channel_id: str) -> str:
    return f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"


def _find_text(element: ET.Element, path: str, namespaces: dict[str, str] | None = None) -> str | None:
    child = element.find(path, namespaces or {})
    if child is None or child.text is None:
        return None
    return child.text.strip()


def _video_record_id(channel_name: str, video_id: str | None, title: str | None) -> str:
    value = video_id or f"{channel_name}:{title or ''}"
    return f"{channel_name}:{hashlib.sha1(value.encode('utf-8')).hexdigest()}"


def parse_youtube_rss(payload: bytes, channel: YouTubeRssChannel) -> list[dict]:
    root = ET.fromstring(payload)
    records: list[dict] = []
    for entry in root.findall("atom:entry", ATOM_NS):
        video_id = _find_text(entry, "yt:videoId", ATOM_NS)
        title = clean_text(_find_text(entry, "atom:title", ATOM_NS))
        link_element = entry.find("atom:link", ATOM_NS)
        url = link_element.attrib.get("href") if link_element is not None else None
        description = clean_text(_find_text(entry, "media:group/media:description", {**ATOM_NS, **MEDIA_NS}))
        records.append(
            {
                "video_id": video_id or _video_record_id(channel.name, video_id, title),
                "platform": "youtube",
                "source": channel.name,
                "source_category": channel.category,
                "channel_id": channel.channel_id,
                "channel_title": _find_text(entry, "atom:author/atom:name", ATOM_NS) or channel.name,
                "title": title,
                "summary": description,
                "url": url,
                "published_at": _find_text(entry, "atom:published", ATOM_NS),
                "updated_at": _find_text(entry, "atom:updated", ATOM_NS),
                "ingested_at": now_iso8601(),
            }
        )
    return records


def fetch_channel(channel: YouTubeRssChannel) -> list[dict]:
    payload = fetch_payload(build_youtube_feed_url(channel.channel_id))
    return parse_youtube_rss(payload, channel)


def collect_youtube_rss_snapshot(
    channels: list[YouTubeRssChannel] | None = None,
    seen_video_ids: set[str] | None = None,
) -> list[dict]:
    channels = channels or YOUTUBE_RSS_CHANNELS
    seen_video_ids = seen_video_ids if seen_video_ids is not None else set()
    records: list[dict] = []
    for channel in channels:
        try:
            records.extend(filter_new_records(fetch_channel(channel), seen_video_ids, "video_id"))
        except Exception as exc:
            log.warning("Failed to fetch %s YouTube RSS feed: %s", channel.name, exc)
    return records


def publish_youtube_rss_snapshot(producer, records: list[dict]) -> int:
    return publish_keyed_events(producer, records, RAW_YOUTUBE_RSS_VIDEOS_TOPIC, "video_id")


def run_once(seen_video_ids: set[str] | None = None) -> dict:
    seen_video_ids = seen_video_ids if seen_video_ids is not None else set()
    try:
        producer = create_producer()
    except NoBrokersAvailable:
        logging.error("Cannot connect to Kafka at %s", KAFKA_BOOTSTRAP_SERVERS)
        return {"videos": 0}
    try:
        records = collect_youtube_rss_snapshot(seen_video_ids=seen_video_ids)
        published = publish_youtube_rss_snapshot(producer, records)
        log.info("Published %s YouTube RSS videos", published)
        return {"videos": published}
    finally:
        producer.close()


def main() -> None:
    logging.info("Publishing curated Vietnamese YouTube channel RSS videos")
    seen_video_ids: set[str] = set()
    try:
        while True:
            run_once(seen_video_ids)
            time.sleep(YOUTUBE_RSS_FETCH_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logging.info("Stopping YouTube RSS producer")


if __name__ == "__main__":
    main()
