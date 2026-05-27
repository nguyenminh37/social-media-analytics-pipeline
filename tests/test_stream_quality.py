import unittest
from importlib.util import find_spec

if find_spec("pyspark") is not None:
    from pyspark.errors.exceptions.base import PySparkRuntimeError
    from pyspark.sql import SparkSession
    from pyspark.sql.types import IntegerType, StringType, StructField, StructType
else:  # pragma: no cover - environment guard
    PySparkRuntimeError = None
    SparkSession = None

from schemas.youtube.raw_schema import RAW_YOUTUBE_VIDEO_SPARK_SCHEMA
from spark_jobs.shared.quality import split_valid_and_dlq_rows


@unittest.skipUnless(SparkSession is not None, "pyspark is not installed")
class StreamQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        try:
            cls.spark = (
                SparkSession.builder.master("local[1]")
                .appName("stream-quality-tests")
                .getOrCreate()
            )
        except PySparkRuntimeError as exc:
            raise unittest.SkipTest(f"Spark is unavailable in this environment: {exc}")

    @classmethod
    def tearDownClass(cls) -> None:
        cls.spark.stop()

    def test_split_valid_and_dlq_rows_routes_invalid_payloads(self) -> None:
        rows = [
            (
                "raw_youtube_videos",
                0,
                1,
                None,
                '{"entity_id":"video-1","title":"hello","platform":"youtube"}',
            ),
            ("raw_youtube_videos", 0, 2, None, "not-json"),
            (
                "raw_youtube_videos",
                0,
                3,
                None,
                '{"entity_id":"video-2","title":" ","platform":"youtube"}',
            ),
        ]
        schema = StructType(
            [
                StructField("topic", StringType(), False),
                StructField("partition", IntegerType(), False),
                StructField("offset", IntegerType(), False),
                StructField("timestamp", StringType(), True),
                StructField("value", StringType(), True),
            ]
        )
        raw_df = self.spark.createDataFrame(
            rows,
            schema,
        )

        valid_df, dlq_df = split_valid_and_dlq_rows(
            raw_df,
            RAW_YOUTUBE_VIDEO_SPARK_SCHEMA,
            required_fields=["entity_id", "title"],
            source_pipeline="youtube",
        )

        valid_rows = [row.asDict() for row in valid_df.collect()]
        dlq_rows = [row.asDict() for row in dlq_df.collect()]

        self.assertEqual(len(valid_rows), 1)
        self.assertEqual(valid_rows[0]["entity_id"], "video-1")
        self.assertEqual(len(dlq_rows), 2)
        self.assertEqual(
            {row["error_type"] for row in dlq_rows},
            {"malformed_payload", "invalid_required_fields"},
        )


if __name__ == "__main__":
    unittest.main()
