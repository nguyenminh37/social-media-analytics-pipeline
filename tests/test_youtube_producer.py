import unittest
from unittest.mock import MagicMock, patch

from collectors.youtube.producer import publish_youtube_snapshot
from config.kafka_config import (
    RAW_YOUTUBE_CHANNELS_TOPIC,
    RAW_YOUTUBE_COMMENTS_TOPIC,
    RAW_YOUTUBE_VIDEOS_TOPIC,
)


class YouTubeProducerTests(unittest.TestCase):
    @patch("collectors.youtube.producer.publish_keyed_events")
    def test_publish_youtube_snapshot_routes_entities_to_raw_topics(self, mock_publish):
        mock_publish.side_effect = [1, 1, 1]
        producer = MagicMock()
        videos = [{"video_id": "video-1"}]
        channels = [{"channel_id": "channel-1"}]
        comments = [{"comment_id": "comment-1"}]

        result = publish_youtube_snapshot(producer, videos, channels, comments)

        self.assertEqual(result, {"videos": 1, "channels": 1, "comments": 1})
        mock_publish.assert_any_call(
            producer, videos, RAW_YOUTUBE_VIDEOS_TOPIC, "video_id"
        )
        mock_publish.assert_any_call(
            producer, channels, RAW_YOUTUBE_CHANNELS_TOPIC, "channel_id"
        )
        mock_publish.assert_any_call(
            producer, comments, RAW_YOUTUBE_COMMENTS_TOPIC, "comment_id"
        )


if __name__ == "__main__":
    unittest.main()
