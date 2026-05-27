import unittest
from unittest.mock import MagicMock
from importlib.util import find_spec

from spark_jobs.youtube.stream_processor import (
    build_trending_keywords_df,
    flatten_windowed_metric_record,
    run_optional_sink,
)

if find_spec("pyspark") is not None:
    from pyspark.errors.exceptions.base import PySparkRuntimeError
    from pyspark.sql import SparkSession
    from pyspark.sql.types import StringType, StructField, StructType
else:  # pragma: no cover - environment guard
    PySparkRuntimeError = None
    SparkSession = None


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


@unittest.skipUnless(SparkSession is not None, "pyspark is not installed")
class YouTubeTrendingAggregationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            cls.spark = (
                SparkSession.builder.master("local[1]")
                .appName("youtube-trending-aggregation-tests")
                .getOrCreate()
            )
        except PySparkRuntimeError as exc:
            raise unittest.SkipTest(f"Spark is unavailable in this environment: {exc}")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.spark.stop()

    def test_build_trending_keywords_df_preserves_entity_type(self) -> None:
        schema = StructType(
            [
                StructField("event_time", StringType(), False),
                StructField("entity_type", StringType(), False),
                StructField("title", StringType(), True),
                StructField("body_text", StringType(), True),
            ]
        )
        rows = [
            ("2026-05-27T01:10:00", "video", "Spark travel", None),
            ("2026-05-27T01:20:00", "comment", None, "travel spark"),
        ]
        content_df = (
            self.spark.createDataFrame(rows, schema)
            .selectExpr(
                "timestamp(event_time) as event_time",
                "entity_type",
                "title",
                "body_text",
            )
        )

        trending_df = build_trending_keywords_df(content_df)
        records = [row.asDict(recursive=True) for row in trending_df.collect()]

        self.assertTrue(records)
        self.assertEqual(
            {record["entity_type"] for record in records},
            {"video", "comment"},
        )
        self.assertTrue(all("keyword" in record for record in records))


if __name__ == "__main__":
    unittest.main()
