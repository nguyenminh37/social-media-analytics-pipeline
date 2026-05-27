import importlib
import os
import unittest


YOUTUBE_QUERY_ENV_KEYS = [
    "YOUTUBE_SEARCH_QUERIES",
    "YOUTUBE_SEARCH_QUERIES_NEWS",
    "YOUTUBE_SEARCH_QUERIES_SPORTS",
    "YOUTUBE_SEARCH_QUERIES_ENTERTAINMENT",
    "YOUTUBE_SEARCH_QUERIES_GAMING",
    "YOUTUBE_SEARCH_QUERIES_REACTION",
    "YOUTUBE_SEARCH_QUERIES_HUMOR",
    "YOUTUBE_SEARCH_QUERIES_TECH",
    "YOUTUBE_SEARCH_QUERIES_MUSIC",
]


class YouTubeConfigTests(unittest.TestCase):
    def test_default_search_queries_favor_short_term_trending_signals(self) -> None:
        original_values = {key: os.environ.get(key) for key in YOUTUBE_QUERY_ENV_KEYS}
        for key in YOUTUBE_QUERY_ENV_KEYS:
            os.environ.pop(key, None)

        try:
            module = importlib.import_module("config.youtube_config")
            module = importlib.reload(module)
        finally:
            for key, value in original_values.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

        queries = module.YOUTUBE_SEARCH_QUERIES

        self.assertIn("tin nóng hôm nay", queries)
        self.assertIn("clip viral hôm nay", queries)
        self.assertIn("mv mới", queries)
        self.assertNotIn("ballad việt", queries)
        self.assertNotIn("nhạc remix việt nam", queries)
        self.assertNotIn("minecraft vietnam", queries)


if __name__ == "__main__":
    unittest.main()
