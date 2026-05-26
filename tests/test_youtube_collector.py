import unittest
from unittest.mock import MagicMock, patch

from collectors.youtube.collector import (
    compute_vietnamese_relevance_score,
    fetch_channel_info,
    fetch_comments,
    fetch_recent_search_videos,
    fetch_trending_videos,
    get_youtube_client,
    prioritize_preferred_videos,
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

    def test_prioritize_preferred_videos_prefers_vietnamese_hot_content(self):
        records = [
            {
                "video_id": "global-1",
                "title": "Apple Original Vs Cheap Aftermarket Parts",
                "description": "repair short",
                "tags": "",
                "channel_title": "Tech Shorts",
                "view_count": "900000",
                "like_count": "5000",
                "comment_count": "100",
            },
            {
                "video_id": "vn-1",
                "title": "Tin tức thời sự mới nhất hôm nay",
                "description": "Cập nhật thời sự Việt Nam nóng nhất",
                "tags": "tin tuc|thoi su|viet nam",
                "channel_title": "Tin Nóng 24h",
                "view_count": "120000",
                "like_count": "1200",
                "comment_count": "90",
            },
        ]

        prioritized = prioritize_preferred_videos(records)

        self.assertEqual(prioritized[0]["video_id"], "vn-1")
        self.assertEqual(len(prioritized), 1)
        self.assertGreater(compute_vietnamese_relevance_score(prioritized[0]), 0)

    def test_fetch_recent_search_videos_sets_relevance_language(self):
        youtube = MagicMock()
        youtube.search.return_value.list.return_value = RequestStub({"items": []})

        fetch_recent_search_videos(
            youtube,
            queries=["tin tuc"],
            max_results=1,
            published_within_hours=1,
        )

        youtube.search.return_value.list.assert_called_once()
        _, kwargs = youtube.search.return_value.list.call_args
        self.assertEqual(kwargs["relevanceLanguage"], "vi")


if __name__ == "__main__":
    unittest.main()
