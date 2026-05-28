import os

from config.env import PROJECT_ROOT  # noqa: F401


def _csv_env(name: str, default: str) -> list[str]:
    raw_value = os.getenv(name, default)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _csv_env_optional(name: str) -> list[str]:
    raw_value = os.getenv(name)
    if raw_value is None:
        return []
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _csv_env_override(name: str) -> list[str] | None:
    raw_value = os.getenv(name)
    if raw_value is None:
        return None
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _merge_unique_csv_groups(*groups: list[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for group in groups:
        for item in group:
            normalized = item.strip()
            if not normalized:
                continue
            key = normalized.lower()
            if key in seen:
                continue
            seen.add(key)
            merged.append(normalized)
    return merged


YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
YOUTUBE_REGION_CODE = os.getenv("YOUTUBE_REGION_CODE", "VN")
YOUTUBE_REGION_CODES = _csv_env("YOUTUBE_REGION_CODES", YOUTUBE_REGION_CODE)
YOUTUBE_CATEGORY_IDS = _csv_env("YOUTUBE_CATEGORY_IDS", "0")
YOUTUBE_SEARCH_QUERIES_NEWS = _csv_env(
    "YOUTUBE_SEARCH_QUERIES_NEWS",
    "tin nóng hôm nay,thời sự hôm nay,tin mới nhất,tin nhanh 24h,sự kiện nóng,bản tin hôm nay",
)
YOUTUBE_SEARCH_QUERIES_SPORTS = _csv_env(
    "YOUTUBE_SEARCH_QUERIES_SPORTS",
    "bóng đá hôm nay,highlight bóng đá hôm nay,tin nóng bóng đá,highlight việt nam,u23 việt nam hôm nay",
)
YOUTUBE_SEARCH_QUERIES_ENTERTAINMENT = _csv_env(
    "YOUTUBE_SEARCH_QUERIES_ENTERTAINMENT",
    "showbiz việt hôm nay,drama hôm nay,clip viral hôm nay,livestream gây chú ý,sao việt hot",
)
YOUTUBE_SEARCH_QUERIES_GAMING = _csv_env(
    "YOUTUBE_SEARCH_QUERIES_GAMING",
    "streamer viral,livestream game hôm nay,highlight livestream game,giải đấu esport hôm nay,valorant việt nam highlight",
)
YOUTUBE_SEARCH_QUERIES_REACTION = _csv_env(
    "YOUTUBE_SEARCH_QUERIES_REACTION",
    "reaction viral,reaction drama,reaction clip nóng,tin hot streamer,livestream phản ứng",
)
YOUTUBE_SEARCH_QUERIES_HUMOR = _csv_env(
    "YOUTUBE_SEARCH_QUERIES_HUMOR",
    "meme viral,clip hài viral,tấu hài hot,clip đang viral,trending việt nam",
)
YOUTUBE_SEARCH_QUERIES_TECH = _csv_env(
    "YOUTUBE_SEARCH_QUERIES_TECH",
    "tin công nghệ hôm nay,ai hot hôm nay,ra mắt điện thoại mới,sản phẩm công nghệ mới",
)
YOUTUBE_SEARCH_QUERIES_MUSIC = _csv_env(
    "YOUTUBE_SEARCH_QUERIES_MUSIC",
    "mv mới,ca khúc mới phát hành,vpop mới,rap việt mới,live performance mới,nhạc viral tiktok",
)
_CUSTOM_SEARCH_QUERIES = _csv_env_override("YOUTUBE_SEARCH_QUERIES")
YOUTUBE_SEARCH_QUERIES = (
    _CUSTOM_SEARCH_QUERIES
    if _CUSTOM_SEARCH_QUERIES is not None
    else _merge_unique_csv_groups(
        YOUTUBE_SEARCH_QUERIES_NEWS,
        YOUTUBE_SEARCH_QUERIES_SPORTS,
        YOUTUBE_SEARCH_QUERIES_ENTERTAINMENT,
        YOUTUBE_SEARCH_QUERIES_GAMING,
        YOUTUBE_SEARCH_QUERIES_REACTION,
        YOUTUBE_SEARCH_QUERIES_HUMOR,
        YOUTUBE_SEARCH_QUERIES_TECH,
        YOUTUBE_SEARCH_QUERIES_MUSIC,
    )
)
YOUTUBE_RELEVANCE_LANGUAGE = os.getenv("YOUTUBE_RELEVANCE_LANGUAGE", "vi")
YOUTUBE_STRICT_VIETNAMESE_ONLY = (
    os.getenv("YOUTUBE_STRICT_VIETNAMESE_ONLY", "true").lower() == "true"
)
YOUTUBE_MIN_VIETNAMESE_SCORE = int(os.getenv("YOUTUBE_MIN_VIETNAMESE_SCORE", "2"))
YOUTUBE_PRIORITY_KEYWORDS = _csv_env(
    "YOUTUBE_PRIORITY_KEYWORDS",
    "tin tuc,thoi su,hôm nay,mới nhất,viral,highlight,livestream,bong da,am nhac,rap viet,giai tri,showbiz,cong nghe,trending,viet nam,drama,streamer,esport,meme,tấu hài,mv mới",
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
