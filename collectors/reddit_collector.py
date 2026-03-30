import logging
import os
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import praw
from kafka.errors import NoBrokersAvailable

from collectors.common import create_producer, now_iso8601, publish_events
from config.kafka_config import KAFKA_BOOTSTRAP_SERVERS, RAW_POSTS_TOPIC


SUBREDDITS = os.getenv(
    "REDDIT_SUBREDDITS", "worldnews,technology,vietnam"
).split(",")
FETCH_INTERVAL_SECONDS = int(os.getenv("REDDIT_FETCH_INTERVAL_SECONDS", "30"))
FETCH_LIMIT = int(os.getenv("REDDIT_FETCH_LIMIT", "25"))


def create_reddit_client() -> praw.Reddit:
    return praw.Reddit(
        client_id=os.environ["REDDIT_CLIENT_ID"],
        client_secret=os.environ["REDDIT_CLIENT_SECRET"],
        user_agent=os.environ["REDDIT_USER_AGENT"],
    )


def build_event(submission: praw.models.Submission, subreddit_name: str) -> dict:
    return {
        "id": submission.id,
        "source": "reddit",
        "title": submission.title,
        "content": submission.selftext or submission.title,
        "url": submission.url,
        "author": getattr(submission.author, "name", None),
        "published_at": time.strftime(
            "%Y-%m-%dT%H:%M:%SZ", time.gmtime(submission.created_utc)
        ),
        "subreddit": subreddit_name,
        "feed_name": subreddit_name,
        "ingested_at": now_iso8601(),
    }


def fetch_new_posts(
    reddit_client: praw.Reddit,
    seen_ids: set[str],
) -> list[dict]:
    events = []
    for subreddit_name in [item.strip() for item in SUBREDDITS if item.strip()]:
        subreddit = reddit_client.subreddit(subreddit_name)
        for submission in subreddit.new(limit=FETCH_LIMIT):
            if submission.id in seen_ids:
                continue
            seen_ids.add(submission.id)
            events.append(build_event(submission, subreddit_name))
    return events


def main() -> None:
    missing_env_vars = [
        name
        for name in (
            "REDDIT_CLIENT_ID",
            "REDDIT_CLIENT_SECRET",
            "REDDIT_USER_AGENT",
        )
        if not os.getenv(name)
    ]
    if missing_env_vars:
        raise RuntimeError(
            f"Missing Reddit credentials: {', '.join(sorted(missing_env_vars))}"
        )

    reddit_client = create_reddit_client()

    try:
        producer = create_producer()
    except NoBrokersAvailable:
        logging.error("Cannot connect to Kafka at %s", KAFKA_BOOTSTRAP_SERVERS)
        return

    seen_ids: set[str] = set()
    logging.info("Publishing Reddit API posts to Kafka topic %s", RAW_POSTS_TOPIC)

    try:
        while True:
            events = fetch_new_posts(reddit_client, seen_ids)
            published = publish_events(producer, events)
            logging.info("Fetched and published %s Reddit posts", published)
            time.sleep(FETCH_INTERVAL_SECONDS)
    except KeyboardInterrupt:
        logging.info("Stopping Reddit collector")
    finally:
        producer.close()


if __name__ == "__main__":
    main()
