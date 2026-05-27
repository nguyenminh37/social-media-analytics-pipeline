import unittest
from unittest.mock import MagicMock, patch

from collectors.public_content.rss import parse_news_rss, publish_news_snapshot
from collectors.public_content.youtube_rss import parse_youtube_rss, publish_youtube_rss_snapshot
from config.kafka_config import RAW_NEWS_ARTICLES_TOPIC, RAW_YOUTUBE_RSS_VIDEOS_TOPIC
from config.source_config import RssSource, YouTubeRssChannel


class PublicContentCollectorTests(unittest.TestCase):
    def test_parse_news_rss_normalizes_article_records(self):
        payload = b"""<?xml version="1.0" encoding="UTF-8"?>
        <rss><channel><item>
          <title><![CDATA[Gia vang tang manh]]></title>
          <link>https://example.test/gia-vang</link>
          <description><![CDATA[<p>Gia vang trong nuoc tang.</p>]]></description>
          <pubDate>Wed, 27 May 2026 22:00:36 +0700</pubDate>
        </item></channel></rss>"""

        records = parse_news_rss(payload, RssSource("example", "https://example.test/rss", "business"))

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["platform"], "news")
        self.assertEqual(records[0]["source"], "example")
        self.assertEqual(records[0]["source_category"], "business")
        self.assertEqual(records[0]["title"], "Gia vang tang manh")
        self.assertEqual(records[0]["summary"], "Gia vang trong nuoc tang.")
        self.assertIn("article_id", records[0])

    def test_parse_youtube_rss_normalizes_video_records(self):
        payload = b"""<?xml version="1.0" encoding="UTF-8"?>
        <feed xmlns:yt="http://www.youtube.com/xml/schemas/2015"
              xmlns:media="http://search.yahoo.com/mrss/"
              xmlns="http://www.w3.org/2005/Atom">
          <entry>
            <yt:videoId>abc123</yt:videoId>
            <title>Ban tin toi</title>
            <link rel="alternate" href="https://www.youtube.com/watch?v=abc123"/>
            <author><name>News TV</name></author>
            <published>2026-05-27T16:30:25+00:00</published>
            <updated>2026-05-27T16:35:33+00:00</updated>
            <media:group><media:description>Mo ta video</media:description></media:group>
          </entry>
        </feed>"""

        records = parse_youtube_rss(
            payload,
            YouTubeRssChannel("news_tv", "UCabc", "news"),
        )

        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["platform"], "youtube")
        self.assertEqual(records[0]["video_id"], "abc123")
        self.assertEqual(records[0]["channel_title"], "News TV")
        self.assertEqual(records[0]["summary"], "Mo ta video")

    @patch("collectors.public_content.rss.publish_keyed_events")
    def test_publish_news_snapshot_routes_to_raw_news_topic(self, mock_publish):
        mock_publish.return_value = 1
        producer = MagicMock()
        records = [{"article_id": "article-1"}]

        self.assertEqual(publish_news_snapshot(producer, records), 1)
        mock_publish.assert_called_once_with(
            producer, records, RAW_NEWS_ARTICLES_TOPIC, "article_id"
        )

    @patch("collectors.public_content.youtube_rss.publish_keyed_events")
    def test_publish_youtube_rss_snapshot_routes_to_raw_topic(self, mock_publish):
        mock_publish.return_value = 1
        producer = MagicMock()
        records = [{"video_id": "video-1"}]

        self.assertEqual(publish_youtube_rss_snapshot(producer, records), 1)
        mock_publish.assert_called_once_with(
            producer, records, RAW_YOUTUBE_RSS_VIDEOS_TOPIC, "video_id"
        )


if __name__ == "__main__":
    unittest.main()
