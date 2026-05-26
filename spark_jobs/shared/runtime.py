import os
from datetime import datetime, timezone

from pyspark.sql import DataFrame, SparkSession

from config.minio_config import (
    CHECKPOINTS_BUCKET,
    MINIO_ACCESS_KEY,
    MINIO_ENDPOINT,
    MINIO_SECRET_KEY,
)


SPARK_KAFKA_PACKAGE = os.getenv(
    "SPARK_KAFKA_PACKAGE",
    "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1",
)
SPARK_ES_PACKAGE = os.getenv(
    "SPARK_ES_PACKAGE",
    "org.elasticsearch:elasticsearch-spark-30_2.12:8.10.0",
)
SPARK_AWS_PACKAGE = os.getenv(
    "SPARK_AWS_PACKAGE", "org.apache.hadoop:hadoop-aws:3.3.4"
)


def parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def normalize_mongo_records(
    records: list[dict], datetime_fields: tuple[str, ...]
) -> list[dict]:
    normalized_records: list[dict] = []
    for record in records:
        normalized = record.copy()
        for field_name in datetime_fields:
            normalized[field_name] = parse_iso_datetime(normalized.get(field_name))
        normalized_records.append(normalized)
    return normalized_records


def create_spark_session(app_name: str) -> SparkSession:
    return (
        SparkSession.builder.appName(app_name)
        .config("spark.streaming.stopGracefullyOnShutdown", "true")
        .config("spark.sql.shuffle.partitions", "2")
        .config(
            "spark.jars.packages",
            ",".join([SPARK_KAFKA_PACKAGE, SPARK_ES_PACKAGE, SPARK_AWS_PACKAGE]),
        )
        .config("spark.hadoop.fs.s3a.endpoint", MINIO_ENDPOINT)
        .config("spark.hadoop.fs.s3a.access.key", MINIO_ACCESS_KEY)
        .config("spark.hadoop.fs.s3a.secret.key", MINIO_SECRET_KEY)
        .config("spark.hadoop.fs.s3a.path.style.access", "true")
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false")
        .getOrCreate()
    )


def reset_checkpoint_if_requested(
    spark: SparkSession,
    checkpoint_base: str,
    enabled: bool,
) -> None:
    if not enabled:
        return

    jvm = spark._jvm
    hadoop_conf = spark._jsc.hadoopConfiguration()
    checkpoint_path = jvm.org.apache.hadoop.fs.Path(checkpoint_base)
    filesystem = checkpoint_path.getFileSystem(hadoop_conf)

    if filesystem.exists(checkpoint_path):
        filesystem.delete(checkpoint_path, True)
        print(f"Deleted checkpoint state at {checkpoint_base}")
    else:
        print(f"No checkpoint state found at {checkpoint_base}")


def default_checkpoint_base(job_name: str) -> str:
    return f"s3a://{CHECKPOINTS_BUCKET}/{job_name}"


def write_dataframe_to_parquet(batch_df: DataFrame, target_path: str) -> None:
    if batch_df.rdd.isEmpty():
        return
    batch_df.write.mode("append").format("parquet").save(target_path)
