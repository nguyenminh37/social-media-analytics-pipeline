import argparse
import json
import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import pyarrow.fs as pafs

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.minio_config import (
    MINIO_ACCESS_KEY,
    MINIO_ENDPOINT,
    MINIO_REGION,
    MINIO_SECRET_KEY,
    RAW_POSTS_BUCKET,
)
from config.storage_config import RAW_ARCHIVE_PREFIX
from serving_api.repository import YouTubeAnalyticsRepository
from spark_jobs.shared.runtime import default_checkpoint_base


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check sink freshness for YouTube pipeline")
    parser.add_argument("--max-age-minutes", type=int, default=60)
    return parser


def build_s3_filesystem() -> pafs.S3FileSystem:
    parsed_endpoint = urlparse(MINIO_ENDPOINT)
    endpoint_override = parsed_endpoint.netloc or parsed_endpoint.path
    return pafs.S3FileSystem(
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        endpoint_override=endpoint_override,
        scheme=parsed_endpoint.scheme or "http",
        region=MINIO_REGION,
    )


def parse_s3_path(path: str) -> tuple[str, str]:
    normalized = path.replace("s3a://", "", 1).replace("s3://", "", 1)
    bucket, _, key = normalized.partition("/")
    return bucket, key


def latest_object_mtime(filesystem: pafs.FileSystem, bucket: str, prefix: str) -> tuple[str | None, str | None]:
    try:
        selector = pafs.FileSelector(
            f"{bucket}/{prefix}",
            recursive=True,
            allow_not_found=True,
        )
        file_infos = filesystem.get_file_info(selector)
        files = [info for info in file_infos if info.type == pafs.FileType.File and info.mtime]
        if not files:
            return None, None
        latest = max(files, key=lambda info: info.mtime)
        return latest.mtime.isoformat(), None
    except Exception as exc:
        return None, str(exc)


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def evaluate_freshness(observed_at: datetime, max_age_minutes: int) -> bool:
    return observed_at >= datetime.now(UTC) - timedelta(minutes=max_age_minutes)


def main() -> None:
    args = build_parser().parse_args()
    filesystem = build_s3_filesystem()
    repository = YouTubeAnalyticsRepository()
    freshness = repository.fetch_freshness()

    raw_archive_mtime, raw_archive_error = latest_object_mtime(
        filesystem,
        RAW_POSTS_BUCKET,
        RAW_ARCHIVE_PREFIX,
    )
    checkpoint_path = os.getenv(
        "YOUTUBE_CHECKPOINT_BASE", default_checkpoint_base("youtube_stream_processor")
    )
    checkpoint_bucket, checkpoint_prefix = parse_s3_path(checkpoint_path)
    checkpoint_mtime, checkpoint_error = latest_object_mtime(
        filesystem,
        checkpoint_bucket,
        checkpoint_prefix,
    )

    latest_content = freshness.get("latest_content") or {}
    latest_sentiment = freshness.get("latest_sentiment_window") or {}
    latest_trending = freshness.get("latest_trending_window") or {}
    latest_content_time = latest_content.get("event_time")
    latest_sentiment_time = latest_sentiment.get("window_end")
    latest_trending_time = latest_trending.get("window_end")

    response = {
        "max_age_minutes": args.max_age_minutes,
        "mongo": {
            "latest_content_event_time": latest_content_time.isoformat()
            if latest_content_time
            else None,
            "latest_sentiment_window_end": latest_sentiment_time.isoformat()
            if latest_sentiment_time
            else None,
            "latest_trending_window_end": latest_trending_time.isoformat()
            if latest_trending_time
            else None,
        },
        "minio": {
            "latest_raw_archive_object": raw_archive_mtime,
            "latest_raw_archive_error": raw_archive_error,
            "latest_youtube_checkpoint_object": checkpoint_mtime,
            "latest_youtube_checkpoint_error": checkpoint_error,
        },
        "status": {
            "content_fresh": evaluate_freshness(latest_content_time, args.max_age_minutes)
            if latest_content_time
            else False,
            "checkpoint_fresh": evaluate_freshness(
                parse_datetime(checkpoint_mtime), args.max_age_minutes
            )
            if checkpoint_mtime
            else False,
        },
    }
    print(json.dumps(response, indent=2))


if __name__ == "__main__":
    main()
