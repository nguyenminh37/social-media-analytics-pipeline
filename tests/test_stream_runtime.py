import os
import unittest
from unittest.mock import patch

from spark_jobs.shared.runtime import build_kafka_source_options


class StreamRuntimeTests(unittest.TestCase):
    def test_build_kafka_source_options_defaults_to_earliest(self) -> None:
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("KAFKA_STREAM_STARTING_TIMESTAMP", None)
            os.environ.pop("KAFKA_STREAM_STARTING_OFFSETS", None)

            options = build_kafka_source_options("raw_youtube_videos")

        self.assertEqual(options["subscribe"], "raw_youtube_videos")
        self.assertEqual(options["startingOffsets"], "earliest")

    def test_build_kafka_source_options_prefers_timestamp_replay(self) -> None:
        with patch.dict(
            os.environ,
            {
                "KAFKA_STREAM_STARTING_TIMESTAMP": "1716710400000",
                "KAFKA_STREAM_STARTING_OFFSETS_BY_TIMESTAMP_STRATEGY": "latest",
            },
            clear=False,
        ):
            options = build_kafka_source_options("raw_youtube_videos")

        self.assertEqual(options["startingTimestamp"], "1716710400000")
        self.assertEqual(options["startingOffsetsByTimestampStrategy"], "latest")
        self.assertNotIn("startingOffsets", options)


if __name__ == "__main__":
    unittest.main()
