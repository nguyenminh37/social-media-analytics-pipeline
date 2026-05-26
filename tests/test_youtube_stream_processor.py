import unittest
from unittest.mock import MagicMock

from spark_jobs.youtube.stream_processor import (
    flatten_windowed_metric_record,
    run_optional_sink,
)


class YouTubeStreamProcessorTests(unittest.TestCase):
    def test_flatten_windowed_metric_record_promotes_window_fields(self) -> None:
        record = {
            "keyword": "python",
            "frequency": 7,
            "window": {
                "start": "2026-05-26T14:00:00",
                "end": "2026-05-26T15:00:00",
            },
        }

        normalized = flatten_windowed_metric_record(record)

        self.assertEqual(normalized["keyword"], "python")
        self.assertEqual(normalized["window_start"], "2026-05-26T14:00:00")
        self.assertEqual(normalized["window_end"], "2026-05-26T15:00:00")
        self.assertNotIn("window", normalized)

    def test_run_optional_sink_swallow_errors_when_not_strict(self) -> None:
        writer = MagicMock(side_effect=RuntimeError("sink unavailable"))

        run_optional_sink(
            "mongo_content",
            MagicMock(),
            7,
            writer,
            strict=False,
        )

        writer.assert_called_once()

    def test_run_optional_sink_raises_errors_in_strict_mode(self) -> None:
        writer = MagicMock(side_effect=RuntimeError("sink unavailable"))

        with self.assertRaises(RuntimeError):
            run_optional_sink(
                "mongo_content",
                MagicMock(),
                8,
                writer,
                strict=True,
            )

        writer.assert_called_once()


if __name__ == "__main__":
    unittest.main()
