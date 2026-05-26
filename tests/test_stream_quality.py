import unittest
from importlib.util import find_spec

if find_spec("pyspark") is not None:
    from pyspark.sql import SparkSession
    from pyspark.sql.types import IntegerType, StringType, StructField, StructType
else:  # pragma: no cover - environment guard
    SparkSession = None

from schemas.legacy_posts.post_schema import POST_SPARK_SCHEMA
from spark_jobs.shared.quality import split_valid_and_dlq_rows


@unittest.skipUnless(SparkSession is not None, "pyspark is not installed")
class StreamQualityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.spark = (
            SparkSession.builder.master("local[1]")
            .appName("stream-quality-tests")
            .getOrCreate()
        )

    @classmethod
    def tearDownClass(cls) -> None:
        cls.spark.stop()

    def test_split_valid_and_dlq_rows_routes_invalid_payloads(self) -> None:
        rows = [
            ("raw_posts", 0, 1, None, '{"id":"1","title":"hello"}'),
            ("raw_posts", 0, 2, None, "not-json"),
            ("raw_posts", 0, 3, None, '{"id":"2","title":" "}'),
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
            POST_SPARK_SCHEMA,
            required_fields=["id", "title"],
            source_pipeline="rss",
        )

        valid_rows = [row.asDict() for row in valid_df.collect()]
        dlq_rows = [row.asDict() for row in dlq_df.collect()]

        self.assertEqual(len(valid_rows), 1)
        self.assertEqual(valid_rows[0]["id"], "1")
        self.assertEqual(len(dlq_rows), 2)
        self.assertEqual(
            {row["error_type"] for row in dlq_rows},
            {"malformed_payload", "invalid_required_fields"},
        )


if __name__ == "__main__":
    unittest.main()
