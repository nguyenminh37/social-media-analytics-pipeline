import unittest
from unittest.mock import MagicMock, patch

from collectors.youtube.collector import (
    fetch_channel_info,
    fetch_comments,
    fetch_trending_videos,
    get_youtube_client,
)
from schemas.youtube.raw_schema import (
    YOUTUBE_CHANNEL_FIELDS,
    YOUTUBE_COMMENT_FIELDS,
    YOUTUBE_VIDEO_FIELDS,
)


class RequestStub:
    def __init__(self, payload: dict):
        self.payload = payload

    def execute(self) -> dict:
        return self.payload


class YouTubeCollectorTests(unittest.TestCase):
    @patch("collectors.youtube.collector.build")
    @patch("collectors.youtube.collector.API_KEY", "test-key")
    def test_get_youtube_client_uses_api_key(self, mock_build):
        get_youtube_client()
        mock_build.assert_called_once_with("youtube", "v3", developerKey="test-key")

    @patch("collectors.youtube.collector.API_KEY", None)
    def test_get_youtube_client_requires_api_key(self):
        with self.assertRaises(RuntimeError):
            get_youtube_client()

    def test_fetch_trending_videos_shape(self):
        youtube = MagicMock()
        youtube.videos.return_value.list.return_value = RequestStub(
            {
                "items": [
                    {
                        "id": "vid123",
                        "snippet": {
                            "title": "AI in Vietnam is growing fast",
                            "channelId": "chan123",
                            "channelTitle": "Tech VN",
                            "publishedAt": "2026-05-25T10:00:00Z",
                            "description": "desc",
                            "tags": ["AI", "Vietnam"],
                            "categoryId": "28",
                            "thumbnails": {"high": {"url": "https://example.com/thumb.jpg"}},
                        },
                        "statistics": {
                            "viewCount": "120000",
                            "likeCount": "8500",
                            "commentCount": "420",
                        },
                        "contentDetails": {"duration": "PT12M34S"},
                    }
                ]
            }
        )

        records = fetch_trending_videos(youtube, max_results=1)

        self.assertEqual(len(records), 1)
        self.assertEqual(set(records[0].keys()), set(YOUTUBE_VIDEO_FIELDS))
        self.assertEqual(records[0]["video_id"], "vid123")
        self.assertEqual(records[0]["tags"], "AI|Vietnam")

    def test_fetch_channel_info_shape(self):
        youtube = MagicMock()
        youtube.channels.return_value.list.return_value = RequestStub(
            {
                "items": [
                    {
                        "id": "chan123",
                        "snippet": {
                            "title": "Tech VN",
                            "description": "Channel description",
                            "country": "VN",
                            "publishedAt": "2020-01-15T08:00:00Z",
                            "thumbnails": {"high": {"url": "https://example.com/channel.jpg"}},
                        },
                        "statistics": {
                            "subscriberCount": "990000",
                            "videoCount": "450",
                            "viewCount": "120000000",
                        },
                    }
                ]
            }
        )

        records = fetch_channel_info(youtube, ["chan123"])

        self.assertEqual(len(records), 1)
        self.assertEqual(set(records[0].keys()), set(YOUTUBE_CHANNEL_FIELDS))
        self.assertEqual(records[0]["channel_id"], "chan123")

    def test_fetch_comments_shape(self):
        youtube = MagicMock()
        youtube.commentThreads.return_value.list.return_value = RequestStub(
            {
                "items": [
                    {
                        "id": "cmt001",
                        "snippet": {
                            "totalReplyCount": 12,
                            "topLevelComment": {
                                "snippet": {
                                    "authorDisplayName": "Viewer A",
                                    "authorChannelId": {"value": "viewer123"},
                                    "textDisplay": "Video qua hay",
                                    "likeCount": 55,
                                    "publishedAt": "2026-05-25T11:00:00Z",
                                    "updatedAt": "2026-05-25T11:05:00Z",
                                }
                            },
                        },
                    }
                ],
                "nextPageToken": None,
            }
        )

        records = fetch_comments(youtube, "vid123", max_results=1)

        self.assertEqual(len(records), 1)
        self.assertEqual(set(records[0].keys()), set(YOUTUBE_COMMENT_FIELDS))
        self.assertEqual(records[0]["comment_id"], "cmt001")
        self.assertEqual(records[0]["video_id"], "vid123")


if __name__ == "__main__":
    unittest.main()
