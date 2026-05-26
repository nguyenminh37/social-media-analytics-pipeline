import logging
import time

from kafka.errors import NoBrokersAvailable

from collectors.shared.common import create_producer, publish_keyed_events
from collectors.youtube.collector import (
    fetch_channel_info,
    fetch_comments,
    fetch_diverse_videos_for_pipeline,
    get_youtube_client,
)
from config.kafka_config import (
    KAFKA_BOOTSTRAP_SERVERS,
    RAW_YOUTUBE_CHANNELS_TOPIC,
    RAW_YOUTUBE_COMMENTS_TOPIC,
    RAW_YOUTUBE_VIDEOS_TOPIC,
)
from config.youtube_config import (
    YOUTUBE_COMMENT_FETCH_SLEEP_SECONDS,
    YOUTUBE_FETCH_INTERVAL_SECONDS,
)


log = logging.getLogger(__name__)


def filter_new_entities(records: list[dict], seen_ids: set[str], key_field: str) -> list[dict]:
    new_records: list[dict] = []
    for record in records:
        key = record.get(key_field)
        if not key or key in seen_ids:
            continue
        seen_ids.add(key)
        new_records.append(record)
    return new_records


def collect_youtube_snapshot(
    youtube_client,
    seen_video_ids: set[str],
    seen_channel_ids: set[str],
    seen_comment_ids: set[str],
) -> tuple[list[dict], list[dict], list[dict]]:
    videos = filter_new_entities(
        fetch_diverse_videos_for_pipeline(youtube_client),
        seen_video_ids,
        "video_id",
    )
    channel_ids = sorted({video["channel_id"] for video in videos if video.get("channel_id")})
    channels = (
        filter_new_entities(
            fetch_channel_info(youtube_client, channel_ids),
            seen_channel_ids,
            "channel_id",
        )
        if channel_ids
        else []
    )

    comments: list[dict] = []
    for video in videos:
        video_id = video["video_id"]
        comments.extend(
            filter_new_entities(
                fetch_comments(youtube_client, video_id),
                seen_comment_ids,
                "comment_id",
            )
        )
        time.sleep(YOUTUBE_COMMENT_FETCH_SLEEP_SECONDS)

    return videos, channels, comments


def publish_youtube_snapshot(producer, videos: list[dict], channels: list[dict], comments: list[dict]) -> dict:
    return {
        "videos": publish_keyed_events(
            producer, videos, RAW_YOUTUBE_VIDEOS_TOPIC, "video_id"
        ),
        "channels": publish_keyed_events(
            producer, channels, RAW_YOUTUBE_CHANNELS_TOPIC, "channel_id"
        ),
        "comments": publish_keyed_events(
            producer, comments, RAW_YOUTUBE_COMMENTS_TOPIC, "comment_id"
        ),
    }


def run_once(
    seen_video_ids: set[str] | None = None,
    seen_channel_ids: set[str] | None = None,
    seen_comment_ids: set[str] | None = None,
) -> dict:
    seen_video_ids = seen_video_ids or set()
    seen_channel_ids = seen_channel_ids or set()
    seen_comment_ids = seen_comment_ids or set()
    youtube_client = get_youtube_client()
    try:
        producer = create_producer()
    except NoBrokersAvailable:
        logging.error("Cannot connect to Kafka at %s", KAFKA_BOOTSTRAP_SERVERS)
        return {"videos": 0, "channels": 0, "comments": 0}

    try:
        videos, channels, comments = collect_youtube_snapshot(
            youtube_client,
            seen_video_ids,
            seen_channel_ids,
            seen_comment_ids,
        )
        published = publish_youtube_snapshot(producer, videos, channels, comments)
        log.info(
            "Published YouTube snapshot: %s videos, %s channels, %s comments",
            published["videos"],
            published["channels"],
            published["comments"],
        )
        return published
    finally:
        producer.close()


def main() -> None:
    logging.info("Publishing YouTube entities to dedicated raw Kafka topics")
    seen_video_ids: set[str] = set()
    seen_channel_ids: set[str] = set()
    seen_comment_ids: set[str] = set()
    try:
        while True:
            youtube_client = get_youtube_client()
            try:
                producer = create_producer()
            except NoBrokersAvailable:
                logging.error("Cannot connect to Kafka at %s", KAFKA_BOOTSTRAP_SERVERS)
                return
            try:
                videos, channels, comments = collect_youtube_snapshot(
                    youtube_client,
                    seen_video_ids,
                    seen_channel_ids,
                    seen_comment_ids,
                )
                published = publish_youtube_snapshot(producer, videos, channels, comments)
                log.info(
                    "Published YouTube snapshot: %s videos, %s channels, %s comments",
                    published["videos"],
                    published["channels"],
                    published["comments"],
                )
            finally:
                producer.close()
            time.sleep(YOUTUBE_FETCH_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logging.info("Stopping YouTube producer")


if __name__ == "__main__":
    main()
