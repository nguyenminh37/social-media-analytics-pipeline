import os
import csv
import time
import logging
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

from collectors.shared.common import now_iso8601
from config.youtube_config import (
    YOUTUBE_API_KEY,
    YOUTUBE_CATEGORY_IDS,
    YOUTUBE_COMMENT_FETCH_SLEEP_SECONDS,
    YOUTUBE_MAX_COMMENTS_PER_VIDEO,
    YOUTUBE_MAX_SEARCH_VIDEOS,
    YOUTUBE_MAX_TRENDING_VIDEOS,
    YOUTUBE_OUTPUT_DIR,
    YOUTUBE_PRIORITY_KEYWORDS,
    YOUTUBE_REGION_CODE,
    YOUTUBE_REGION_CODES,
    YOUTUBE_RELEVANCE_LANGUAGE,
    YOUTUBE_SEARCH_PUBLISHED_WITHIN_HOURS,
    YOUTUBE_SEARCH_QUERIES,
    YOUTUBE_STRICT_VIETNAMESE_ONLY,
    YOUTUBE_MIN_VIETNAMESE_SCORE,
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

API_KEY = YOUTUBE_API_KEY
REGION_CODE = YOUTUBE_REGION_CODE
MAX_TRENDING_VIDEOS = YOUTUBE_MAX_TRENDING_VIDEOS
MAX_COMMENTS_PER_VIDEO = YOUTUBE_MAX_COMMENTS_PER_VIDEO
OUTPUT_DIR = YOUTUBE_OUTPUT_DIR
VIETNAMESE_DIACRITICS_PATTERN = re.compile(
    r"[ăâđêôơưáàảãạấầẩẫậắằẳẵặéèẻẽẹếềểễệíìỉĩịóòỏõọốồổỗộớờởỡợúùủũụứừửữựýỳỷỹỵ]",
    re.IGNORECASE,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("crawler.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger(__name__)


def _normalize_text(value: str | None) -> str:
    return (value or "").strip().lower()


def compute_vietnamese_relevance_score(record: dict) -> int:
    haystack = " ".join(
        [
            _normalize_text(record.get("title")),
            _normalize_text(record.get("description")),
            _normalize_text(record.get("tags")),
            _normalize_text(record.get("channel_title")),
            _normalize_text(record.get("channel_name")),
        ]
    )
    score = 0

    if record.get("country") == "VN":
        score += 3

    if VIETNAMESE_DIACRITICS_PATTERN.search(haystack):
        score += 3

    if any(keyword in haystack for keyword in YOUTUBE_PRIORITY_KEYWORDS):
        score += 2

    if " việt " in f" {haystack} " or " vn " in f" {haystack} ":
        score += 1

    return score


def is_preferred_youtube_record(record: dict) -> bool:
    if not YOUTUBE_STRICT_VIETNAMESE_ONLY:
        return True
    return compute_vietnamese_relevance_score(record) >= YOUTUBE_MIN_VIETNAMESE_SCORE


def prioritize_preferred_videos(records: list[dict]) -> list[dict]:
    enriched_records: list[dict] = []
    for record in records:
        normalized = record.copy()
        normalized["vi_relevance_score"] = compute_vietnamese_relevance_score(record)
        enriched_records.append(normalized)

    preferred_records = [
        record for record in enriched_records if is_preferred_youtube_record(record)
    ]
    target_records = preferred_records or enriched_records
    target_records.sort(
        key=lambda record: (
            -record["vi_relevance_score"],
            -int(record.get("view_count") or 0),
            -int(record.get("like_count") or 0),
            -int(record.get("comment_count") or 0),
        )
    )
    return [
        {key: value for key, value in record.items() if key != "vi_relevance_score"}
        for record in target_records
    ]


def get_youtube_client():
    if not API_KEY:
        raise RuntimeError("Missing YOUTUBE_API_KEY in environment.")
    return build("youtube", "v3", developerKey=API_KEY)


def normalize_video_item(item: dict) -> dict:
    snippet = item.get("snippet", {})
    stats = item.get("statistics", {})
    content = item.get("contentDetails", {})
    video_id = item["id"]
    crawled_at = now_iso8601()
    return {
        "platform": "youtube",
        "entity_type": "video",
        "entity_id": video_id,
        "video_id": video_id,
        "title": snippet.get("title", ""),
        "channel_id": snippet.get("channelId", ""),
        "channel_title": snippet.get("channelTitle", ""),
        "published_at": snippet.get("publishedAt", ""),
        "description": snippet.get("description", ""),
        "tags": "|".join(snippet.get("tags", [])),
        "category_id": snippet.get("categoryId", ""),
        "duration": content.get("duration", ""),
        "view_count": stats.get("viewCount", 0),
        "like_count": stats.get("likeCount", 0),
        "comment_count": stats.get("commentCount", 0),
        "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
        "source_url": f"https://www.youtube.com/watch?v={video_id}",
        "crawled_at": crawled_at,
        "ingested_at": crawled_at,
    }


def dedupe_entities(records: list[dict], key_field: str) -> list[dict]:
    unique_records: list[dict] = []
    seen_keys: set[str] = set()
    for record in records:
        key = record.get(key_field)
        if not key or key in seen_keys:
            continue
        seen_keys.add(key)
        unique_records.append(record)
    return unique_records


def fetch_video_details(youtube, video_ids: list[str]) -> list[dict]:
    videos: list[dict] = []
    for index in range(0, len(video_ids), 50):
        batch = video_ids[index:index + 50]
        if not batch:
            continue
        try:
            response = youtube.videos().list(
                part="snippet,statistics,contentDetails",
                id=",".join(batch),
                maxResults=len(batch),
            ).execute()
            videos.extend(
                normalize_video_item(item) for item in response.get("items", [])
            )
        except HttpError as exc:
            log.error("Error fetching video details: %s", exc)
    return prioritize_preferred_videos(dedupe_entities(videos, "video_id"))


def fetch_multi_source_trending_videos(
    youtube,
    region_codes: list[str] | None = None,
    category_ids: list[str] | None = None,
    max_results: int = MAX_TRENDING_VIDEOS,
):
    """Fetch trending videos across regions/categories to avoid narrow repeated snapshots."""
    region_codes = region_codes or YOUTUBE_REGION_CODES or [REGION_CODE]
    category_ids = category_ids or YOUTUBE_CATEGORY_IDS or ["0"]
    videos: list[dict] = []

    for region_code in region_codes:
        for category_id in category_ids:
            request_params = {
                "part": "snippet,statistics,contentDetails",
                "chart": "mostPopular",
                "regionCode": region_code,
                "maxResults": max_results,
            }
            if category_id != "0":
                request_params["videoCategoryId"] = category_id
            label = f"{region_code}:{category_id}"
            log.info("Fetching top %s trending videos for %s", max_results, label)
            try:
                response = youtube.videos().list(**request_params).execute()
                videos.extend(
                    normalize_video_item(item) for item in response.get("items", [])
                )
            except HttpError as exc:
                log.error("Error fetching trending videos for %s: %s", label, exc)

    deduped_videos = prioritize_preferred_videos(dedupe_entities(videos, "video_id"))
    log.info("Fetched %s unique trending videos.", len(deduped_videos))
    return deduped_videos


def fetch_recent_search_videos(
    youtube,
    queries: list[str] | None = None,
    max_results: int = YOUTUBE_MAX_SEARCH_VIDEOS,
    published_within_hours: int = YOUTUBE_SEARCH_PUBLISHED_WITHIN_HOURS,
):
    queries = queries or YOUTUBE_SEARCH_QUERIES
    published_after = (
        datetime.now(UTC) - timedelta(hours=published_within_hours)
    ).isoformat().replace("+00:00", "Z")
    video_ids: list[str] = []

    for query in queries:
        log.info(
            "Fetching recent YouTube search videos for query '%s' within %s hours",
            query,
            published_within_hours,
        )
        try:
            response = youtube.search().list(
                part="snippet",
                q=query,
                type="video",
                order="date",
                maxResults=max_results,
                publishedAfter=published_after,
                regionCode=REGION_CODE,
                relevanceLanguage=YOUTUBE_RELEVANCE_LANGUAGE,
            ).execute()
            for item in response.get("items", []):
                video_id = item.get("id", {}).get("videoId")
                if video_id:
                    video_ids.append(video_id)
        except HttpError as exc:
            log.error("Error searching recent videos for query '%s': %s", query, exc)

    return fetch_video_details(youtube, list(dict.fromkeys(video_ids)))


def fetch_diverse_videos(youtube) -> list[dict]:
    trending_videos = fetch_multi_source_trending_videos(youtube)
    recent_search_videos = fetch_recent_search_videos(youtube)
    all_videos = trending_videos + recent_search_videos
    deduped_videos = prioritize_preferred_videos(dedupe_entities(all_videos, "video_id"))
    log.info(
        "Collected %s unique videos from trending + recent search sources.",
        len(deduped_videos),
    )
    return deduped_videos


def fetch_single_region_trending_videos(
    youtube, region_code=REGION_CODE, max_results=MAX_TRENDING_VIDEOS
):
    """Backward-compatible helper used by tests and simple CSV crawling."""
    return fetch_multi_source_trending_videos(
        youtube,
        region_codes=[region_code],
        category_ids=["0"],
        max_results=max_results,
    )


def fetch_trending_videos_legacy(youtube, region_code=REGION_CODE, max_results=MAX_TRENDING_VIDEOS):
    return fetch_single_region_trending_videos(youtube, region_code, max_results)


def fetch_trending_videos(youtube, region_code=REGION_CODE, max_results=MAX_TRENDING_VIDEOS):
    """Backward-compatible signature for tests and existing callers."""
    return fetch_single_region_trending_videos(youtube, region_code, max_results)


def fetch_diverse_videos_for_pipeline(youtube) -> list[dict]:
    return fetch_diverse_videos(youtube)


def _fetch_comments_impl(youtube, video_id, max_results=MAX_COMMENTS_PER_VIDEO):
    """Fetch top-level comments for a video."""
    comments = []
    next_page_token = None

    try:
        while len(comments) < max_results:
            request_params = {
                "part": "snippet",
                "videoId": video_id,
                "maxResults": min(100, max_results - len(comments)),
                "order": "relevance",
                "textFormat": "plainText"
            }
            if next_page_token:
                request_params["pageToken"] = next_page_token

            response = youtube.commentThreads().list(**request_params).execute()

            for item in response.get("items", []):
                top_comment = item["snippet"]["topLevelComment"]["snippet"]
                comment_id = item["id"]
                crawled_at = now_iso8601()
                comments.append({
                    "platform": "youtube",
                    "entity_type": "comment",
                    "entity_id": comment_id,
                    "comment_id": comment_id,
                    "video_id": video_id,
                    "author": top_comment.get("authorDisplayName", ""),
                    "author_channel_id": top_comment.get("authorChannelId", {}).get("value", ""),
                    "text": top_comment.get("textDisplay", ""),
                    "like_count": top_comment.get("likeCount", 0),
                    "reply_count": item["snippet"].get("totalReplyCount", 0),
                    "published_at": top_comment.get("publishedAt", ""),
                    "updated_at": top_comment.get("updatedAt", ""),
                    "source_url": f"https://www.youtube.com/watch?v={video_id}&lc={comment_id}",
                    "crawled_at": crawled_at,
                    "ingested_at": crawled_at,
                })

            next_page_token = response.get("nextPageToken")
            if not next_page_token:
                break

    except HttpError as e:
        if "commentsDisabled" in str(e):
            log.warning(f"Comments disabled for video {video_id}")
        else:
            log.error(f"Error fetching comments for {video_id}: {e}")

    return comments


def fetch_channel_info(youtube, channel_ids):
    """Fetch channel details for a list of channel IDs."""
    log.info(f"Fetching info for {len(channel_ids)} channels...")
    channels = []

    for i in range(0, len(channel_ids), 50):
        batch = channel_ids[i:i+50]
        try:
            response = youtube.channels().list(
                part="snippet,statistics,brandingSettings",
                id=",".join(batch)
            ).execute()

            for item in response.get("items", []):
                snippet = item.get("snippet", {})
                stats = item.get("statistics", {})
                channel_id = item["id"]
                crawled_at = now_iso8601()
                channels.append({
                    "platform": "youtube",
                    "entity_type": "channel",
                    "entity_id": channel_id,
                    "channel_id": channel_id,
                    "channel_name": snippet.get("title", ""),
                    "description": snippet.get("description", ""),
                    "country": snippet.get("country", ""),
                    "published_at": snippet.get("publishedAt", ""),
                    "subscriber_count": stats.get("subscriberCount", 0),
                    "video_count": stats.get("videoCount", 0),
                    "view_count": stats.get("viewCount", 0),
                    "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
                    "source_url": f"https://www.youtube.com/channel/{channel_id}",
                    "crawled_at": crawled_at,
                    "ingested_at": crawled_at,
                })

            time.sleep(0.5)

        except HttpError as e:
            log.error(f"Error fetching channel info: {e}")

    channels = dedupe_entities(channels, "channel_id")
    log.info(f"Fetched info for {len(channels)} channels.")
    return channels


def fetch_comments(youtube, video_id, max_results=MAX_COMMENTS_PER_VIDEO):
    return _fetch_comments_impl(youtube, video_id, max_results)


def save_to_csv(data, filename, fieldnames):
    """Save a list of dicts to a CSV file."""
    if not data:
        log.warning(f"No data to save for {filename}")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)

    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)

    log.info(f"Saved {len(data)} rows → {filepath}")


def run_crawler():
    log.info("=" * 50)
    log.info("YouTube Big Data Crawler Started")
    log.info("=" * 50)

    youtube = get_youtube_client()
    timestamp = now_iso8601().replace(":", "").replace("-", "").replace("Z", "")

    # ── Step 1: Trending Videos ──
    videos = fetch_diverse_videos_for_pipeline(youtube)

    if not videos:
        log.error("No videos fetched. Check your API key and region code.")
        return

    save_to_csv(
        videos,
        f"trending_videos_{timestamp}.csv",
        fieldnames=list(videos[0].keys())
    )

    # ── Step 2: Channel Info ──
    channel_ids = list(set(v["channel_id"] for v in videos))
    channels = fetch_channel_info(youtube, channel_ids)

    save_to_csv(
        channels,
        f"channels_{timestamp}.csv",
        fieldnames=list(channels[0].keys()) if channels else []
    )

    # ── Step 3: Comments for Each Video ──
    all_comments = []
    for i, video in enumerate(videos):
        video_id = video["video_id"]
        title = video["title"][:50]
        log.info(f"[{i+1}/{len(videos)}] Fetching comments for: {title}")

        comments = fetch_comments(youtube, video_id)
        all_comments.extend(comments)

        time.sleep(YOUTUBE_COMMENT_FETCH_SLEEP_SECONDS)

    if all_comments:
        save_to_csv(
            all_comments,
            f"comments_{timestamp}.csv",
            fieldnames=list(all_comments[0].keys())
        )

    
    log.info("=" * 50)
    log.info("Crawl Complete! Summary:")
    log.info(f"  Videos collected   : {len(videos)}")
    log.info(f"  Channels collected : {len(channels)}")
    log.info(f"  Comments collected : {len(all_comments)}")
    log.info(f"  Output folder      : {OUTPUT_DIR}/")
    log.info("=" * 50)


if __name__ == "__main__":
    run_crawler()
