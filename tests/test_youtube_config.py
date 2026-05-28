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
    def reload_config_with_env(self, values: dict[str, str | None]):
        original_values = {key: os.environ.get(key) for key in YOUTUBE_QUERY_ENV_KEYS}
        for key in YOUTUBE_QUERY_ENV_KEYS:
            os.environ.pop(key, None)
        for key, value in values.items():
            if value is not None:
                os.environ[key] = value

        try:
            module = importlib.import_module("config.youtube_config")
            return importlib.reload(module)
        finally:
            for key, value in original_values.items():
                if value is None:
                    os.environ.pop(key, None)
                else:
                    os.environ[key] = value

    def test_default_search_queries_favor_short_term_trending_signals(self) -> None:
        module = self.reload_config_with_env({})
        queries = module.YOUTUBE_SEARCH_QUERIES

        self.assertIn("tin nóng hôm nay", queries)
        self.assertIn("clip viral hôm nay", queries)
        self.assertIn("mv mới", queries)
        self.assertNotIn("ballad việt", queries)
        self.assertNotIn("nhạc remix việt nam", queries)
        self.assertNotIn("minecraft vietnam", queries)

    def test_custom_search_queries_replace_default_groups(self) -> None:
        module = self.reload_config_with_env(
            {
                "YOUTUBE_SEARCH_QUERIES": "tin nóng hôm nay,giá vàng hôm nay",
            }
        )

        self.assertEqual(
            ["tin nóng hôm nay", "giá vàng hôm nay"],
            module.YOUTUBE_SEARCH_QUERIES,
        )
        self.assertNotIn("clip viral hôm nay", module.YOUTUBE_SEARCH_QUERIES)
        self.assertNotIn("mv mới", module.YOUTUBE_SEARCH_QUERIES)


if __name__ == "__main__":
    unittest.main()
