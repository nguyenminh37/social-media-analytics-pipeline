import os
from dataclasses import dataclass

from config.env import PROJECT_ROOT  # noqa: F401


@dataclass(frozen=True)
class RssSource:
    name: str
    url: str
    category: str = "general"


@dataclass(frozen=True)
class YouTubeRssChannel:
    name: str
    channel_id: str
    category: str = "news"


DEFAULT_NEWS_RSS_SOURCES = [
    RssSource("vnexpress", "https://vnexpress.net/rss/tin-moi-nhat.rss", "mainstream"),
    RssSource("tuoitre", "https://tuoitre.vn/rss/tin-moi-nhat.rss", "mainstream"),
    RssSource("thanhnien", "https://thanhnien.vn/rss/home.rss", "mainstream"),
    RssSource("dantri", "https://dantri.com.vn/rss/tin-moi-nhat.rss", "mainstream"),
    RssSource("tienphong", "https://tienphong.vn/rss/home.rss", "mainstream"),
    RssSource("nld", "https://nld.com.vn/rss/home.rss", "mainstream"),
    RssSource("vtv", "https://vtv.vn/rss/home.rss", "mainstream"),
    RssSource("vtcnews", "https://vtcnews.vn/rss/trang-chu.rss", "mainstream"),
    RssSource("nhandan", "https://nhandan.vn/rss/tin-moi.rss", "mainstream"),
    RssSource("vietnamplus", "https://www.vietnamplus.vn/rss/home.rss", "mainstream"),
    RssSource("suckhoedoisong", "https://suckhoedoisong.vn/rss/home.rss", "health"),
    RssSource("cand", "https://cand.com.vn/rss/thoi-su.rss", "public_security"),
    RssSource("genk", "https://genk.vn/rss/home.rss", "tech"),
    RssSource("kenh14", "https://kenh14.vn/rss/home.rss", "youth_entertainment"),
    RssSource("cafebiz", "https://cafebiz.vn/rss/home.rss", "business"),
    RssSource("soha", "https://soha.vn/rss/home.rss", "general"),
]


DEFAULT_YOUTUBE_RSS_CHANNELS = [
    YouTubeRssChannel("vtv24", "UCabsTV34JwALXKGMqHpvUiA"),
    YouTubeRssChannel("vnexpress", "UCpK5nl5llhUL4QKq03qan8g"),
    YouTubeRssChannel("thanhnien", "UCIW9cGgoRuGJnky3K3tbzNg"),
    YouTubeRssChannel("dantri", "UCHZ_b_qC_k_ORdCkiPCpFsw"),
    YouTubeRssChannel("tienphong", "UCPhPBJ3qE719TgLYVcNY8yg"),
    YouTubeRssChannel("nld", "UCzkyOx_0O1pGOqHiUMOe2KQ"),
    YouTubeRssChannel("vtv_online", "UCsWMcnVUYQZc-ugInnw_0LA"),
    YouTubeRssChannel("vtc_van_de_hom_nay", "UClYUCB6tyZl50_7OcbgUHCA"),
    YouTubeRssChannel("nhandan", "UCPJfjHrW3-zIeSaZTgmckmg"),
    YouTubeRssChannel("tuoitre_media", "UCrwJa6KRHWnJpJPZNeKKcvA"),
    YouTubeRssChannel("baotuoitre", "UC47WI-kZXFf0H_f7pvaNCEQ"),
]


def _parse_rss_sources(raw_value: str | None) -> list[RssSource]:
    if not raw_value:
        return DEFAULT_NEWS_RSS_SOURCES
    sources: list[RssSource] = []
    for item in raw_value.split(","):
        parts = [part.strip() for part in item.split("|")]
        if len(parts) < 2 or not parts[0] or not parts[1]:
            continue
        category = parts[2] if len(parts) > 2 and parts[2] else "general"
        sources.append(RssSource(parts[0], parts[1], category))
    return sources or DEFAULT_NEWS_RSS_SOURCES


def _parse_youtube_channels(raw_value: str | None) -> list[YouTubeRssChannel]:
    if not raw_value:
        return DEFAULT_YOUTUBE_RSS_CHANNELS
    channels: list[YouTubeRssChannel] = []
    for item in raw_value.split(","):
        parts = [part.strip() for part in item.split("|")]
        if len(parts) < 2 or not parts[0] or not parts[1]:
            continue
        category = parts[2] if len(parts) > 2 and parts[2] else "news"
        channels.append(YouTubeRssChannel(parts[0], parts[1], category))
    return channels or DEFAULT_YOUTUBE_RSS_CHANNELS


NEWS_RSS_SOURCES = _parse_rss_sources(os.getenv("NEWS_RSS_SOURCES"))
YOUTUBE_RSS_CHANNELS = _parse_youtube_channels(os.getenv("YOUTUBE_RSS_CHANNELS"))

NEWS_RSS_FETCH_INTERVAL_SECONDS = int(os.getenv("NEWS_RSS_FETCH_INTERVAL_SECONDS", "300"))
YOUTUBE_RSS_FETCH_INTERVAL_SECONDS = int(
    os.getenv("YOUTUBE_RSS_FETCH_INTERVAL_SECONDS", "600")
)
