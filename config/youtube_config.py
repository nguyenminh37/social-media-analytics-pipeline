import os

from config.env import PROJECT_ROOT  # noqa: F401


def _csv_env(name: str, default: str) -> list[str]:
    raw_value = os.getenv(name, default)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_REGION_CODE = os.getenv("YOUTUBE_REGION_CODE", "VN")
YOUTUBE_REGION_CODES = _csv_env("YOUTUBE_REGION_CODES", YOUTUBE_REGION_CODE)
YOUTUBE_CATEGORY_IDS = _csv_env("YOUTUBE_CATEGORY_IDS", "0")
YOUTUBE_SEARCH_QUERIES = _csv_env(
    "YOUTUBE_SEARCH_QUERIES",
    "tin tuc,trending,am nhac,hau truong,giai tri,cong nghe,the thao",
)
YOUTUBE_MAX_TRENDING_VIDEOS = int(os.getenv("YOUTUBE_MAX_TRENDING_VIDEOS", "50"))
YOUTUBE_MAX_COMMENTS_PER_VIDEO = int(os.getenv("YOUTUBE_MAX_COMMENTS_PER_VIDEO", "100"))
YOUTUBE_OUTPUT_DIR = os.getenv("YOUTUBE_OUTPUT_DIR", "youtube_data")
YOUTUBE_FETCH_INTERVAL_SECONDS = int(os.getenv("YOUTUBE_FETCH_INTERVAL_SECONDS", "300"))
YOUTUBE_COMMENT_FETCH_SLEEP_SECONDS = float(
    os.getenv("YOUTUBE_COMMENT_FETCH_SLEEP_SECONDS", "1")
)
YOUTUBE_MAX_SEARCH_VIDEOS = int(os.getenv("YOUTUBE_MAX_SEARCH_VIDEOS", "20"))
YOUTUBE_SEARCH_PUBLISHED_WITHIN_HOURS = int(
    os.getenv("YOUTUBE_SEARCH_PUBLISHED_WITHIN_HOURS", "24")
)
