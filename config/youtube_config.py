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
    "tin tuc,tin nóng việt nam,thời sự việt nam,tin nóng 24h,thời sự quốc tế,bản tin hôm nay",
)
YOUTUBE_SEARCH_QUERIES_SPORTS = _csv_env(
    "YOUTUBE_SEARCH_QUERIES_SPORTS",
    "bóng đá việt nam,highlight bóng đá việt nam,tin chuyển nhượng,bóng đá hôm nay,u23 việt nam",
)
YOUTUBE_SEARCH_QUERIES_ENTERTAINMENT = _csv_env(
    "YOUTUBE_SEARCH_QUERIES_ENTERTAINMENT",
    "giai tri việt nam,showbiz việt,drama việt nam,drama tiktok,clip gây tranh cãi,video gây sốc",
)
YOUTUBE_SEARCH_QUERIES_GAMING = _csv_env(
    "YOUTUBE_SEARCH_QUERIES_GAMING",
    "gaming vietnam,livestream game vietnam,highlight gaming vietnam,free fire vietnam,liên quân mobile,pubg mobile vietnam,valorant vietnam,minecraft vietnam,roblox vietnam,genshin impact vietnam,streamer vietnam,best moments gaming vn,rank cao thủ,top 1 server",
)
YOUTUBE_SEARCH_QUERIES_REACTION = _csv_env(
    "YOUTUBE_SEARCH_QUERIES_REACTION",
    "reaction viral,reaction video vietnam,reaction phim,reaction nhạc,tin hot streamer,drama youtube",
)
YOUTUBE_SEARCH_QUERIES_HUMOR = _csv_env(
    "YOUTUBE_SEARCH_QUERIES_HUMOR",
    "meme vietnam,video hài việt nam,clip hài,try not to laugh vietnam,fails vietnam,tấu hài,content bựa",
)
YOUTUBE_SEARCH_QUERIES_TECH = _csv_env(
    "YOUTUBE_SEARCH_QUERIES_TECH",
    "công nghệ,review điện thoại,review laptop,tin công nghệ,ai việt nam,thủ thuật công nghệ",
)
YOUTUBE_SEARCH_QUERIES_MUSIC = _csv_env(
    "YOUTUBE_SEARCH_QUERIES_MUSIC",
    "rap việt,nhạc trẻ việt nam,vpop trending,ballad việt,live acoustic việt nam,nhạc remix việt nam",
)
YOUTUBE_SEARCH_QUERIES = _merge_unique_csv_groups(
    _csv_env_optional("YOUTUBE_SEARCH_QUERIES"),
    YOUTUBE_SEARCH_QUERIES_NEWS,
    YOUTUBE_SEARCH_QUERIES_SPORTS,
    YOUTUBE_SEARCH_QUERIES_ENTERTAINMENT,
    YOUTUBE_SEARCH_QUERIES_GAMING,
    YOUTUBE_SEARCH_QUERIES_REACTION,
    YOUTUBE_SEARCH_QUERIES_HUMOR,
    YOUTUBE_SEARCH_QUERIES_TECH,
    YOUTUBE_SEARCH_QUERIES_MUSIC,
)
YOUTUBE_RELEVANCE_LANGUAGE = os.getenv("YOUTUBE_RELEVANCE_LANGUAGE", "vi")
YOUTUBE_STRICT_VIETNAMESE_ONLY = (
    os.getenv("YOUTUBE_STRICT_VIETNAMESE_ONLY", "true").lower() == "true"
)
YOUTUBE_MIN_VIETNAMESE_SCORE = int(os.getenv("YOUTUBE_MIN_VIETNAMESE_SCORE", "2"))
YOUTUBE_PRIORITY_KEYWORDS = _csv_env(
    "YOUTUBE_PRIORITY_KEYWORDS",
    "tin tuc,thoi su,bong da,am nhac,rap viet,giai tri,showbiz,review,cong nghe,trending,viet nam,drama,streamer,free fire,liên quân,pubg,valorant,minecraft,roblox,genshin,meme,tấu hài",
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
