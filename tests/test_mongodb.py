import unittest
from unittest.mock import MagicMock

from scripts.init_mongodb import init_mongodb
from config.storage_config import (
    YOUTUBE_CHANNEL_SNAPSHOTS_COLLECTION,
    YOUTUBE_CONTENT_EVENTS_COLLECTION,
    YOUTUBE_SENTIMENT_COLLECTION,
    YOUTUBE_TRENDING_COLLECTION,
)

class MongoDBTests(unittest.TestCase):
    def test_init_mongodb_creates_indexes(self):
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db
        
        mock_content = MagicMock()
        mock_channels = MagicMock()
        mock_sentiment = MagicMock()
        mock_trending = MagicMock()
        mock_trending.index_information.return_value = {}
        
        def mock_get_collection(name):
            if name == YOUTUBE_CONTENT_EVENTS_COLLECTION:
                return mock_content
            if name == YOUTUBE_CHANNEL_SNAPSHOTS_COLLECTION:
                return mock_channels
            if name == YOUTUBE_SENTIMENT_COLLECTION:
                return mock_sentiment
            if name == YOUTUBE_TRENDING_COLLECTION:
                return mock_trending
            return MagicMock()
            
        mock_db.__getitem__.side_effect = mock_get_collection
        
        init_mongodb(mock_client, "test_db")
        
        self.assertEqual(mock_content.create_index.call_count, 7)
        self.assertEqual(mock_channels.create_index.call_count, 4)
        self.assertEqual(mock_sentiment.create_index.call_count, 3)
        self.assertEqual(mock_trending.create_index.call_count, 3)
        mock_trending.drop_index.assert_not_called()

    def test_init_mongodb_drops_legacy_trending_unique_index(self):
        mock_client = MagicMock()
        mock_db = MagicMock()
        mock_client.__getitem__.return_value = mock_db

        mock_content = MagicMock()
        mock_channels = MagicMock()
        mock_sentiment = MagicMock()
        mock_trending = MagicMock()
        mock_trending.index_information.return_value = {
            "window_start_1_window_end_1_keyword_1": {
                "key": [
                    ("window_start", 1),
                    ("window_end", 1),
                    ("keyword", 1),
                ],
                "unique": True,
            }
        }

        def mock_get_collection(name):
            if name == YOUTUBE_CONTENT_EVENTS_COLLECTION:
                return mock_content
            if name == YOUTUBE_CHANNEL_SNAPSHOTS_COLLECTION:
                return mock_channels
            if name == YOUTUBE_SENTIMENT_COLLECTION:
                return mock_sentiment
            if name == YOUTUBE_TRENDING_COLLECTION:
                return mock_trending
            return MagicMock()

        mock_db.__getitem__.side_effect = mock_get_collection

        init_mongodb(mock_client, "test_db")

        mock_trending.drop_index.assert_called_once_with(
            "window_start_1_window_end_1_keyword_1"
        )

if __name__ == "__main__":
    unittest.main()
