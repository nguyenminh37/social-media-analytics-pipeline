import json
import os
import signal
import tempfile
import time
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

try:
    import pyarrow as pa
    import pyarrow.fs as pafs
    import pyarrow.parquet as pq
except ImportError:  # pragma: no cover - runtime dependency guard
    pa = None
    pafs = None
    pq = None

try:
    from kafka import KafkaConsumer, TopicPartition
    from kafka.consumer.fetcher import ConsumerRecord
    from kafka.structs import OffsetAndMetadata
except ImportError:  # pragma: no cover - runtime dependency guard
    KafkaConsumer = None
    TopicPartition = None
    ConsumerRecord = object
    OffsetAndMetadata = None

from config.kafka_config import (
    KAFKA_BOOTSTRAP_SERVERS,
    RAW_ARCHIVER_GROUP_ID,
    RAW_ARCHIVER_TOPICS,
)
from config.minio_config import (
    MINIO_ACCESS_KEY,
    MINIO_ENDPOINT,
    MINIO_REGION,
    MINIO_SECRET_KEY,
    RAW_POSTS_BUCKET,
)
from config.storage_config import RAW_ARCHIVE_PREFIX


RAW_ARCHIVER_FLUSH_SECONDS = float(os.getenv("RAW_ARCHIVER_FLUSH_SECONDS", "5"))
RAW_ARCHIVER_MAX_RECORDS = int(os.getenv("RAW_ARCHIVER_MAX_RECORDS", "500"))
RAW_ARCHIVER_AUTO_OFFSET_RESET = os.getenv("RAW_ARCHIVER_AUTO_OFFSET_RESET", "earliest")
RAW_ARCHIVER_POLL_TIMEOUT_MS = int(os.getenv("RAW_ARCHIVER_POLL_TIMEOUT_MS", "1000"))


@dataclass(frozen=True)
class ArchivePartition:
    topic: str
    partition: int
    year: int
    month: int
    day: int
    hour: int


def kafka_timestamp_to_datetime(record: ConsumerRecord) -> datetime:
    if record.timestamp is None or record.timestamp < 0:
        return datetime.now(UTC)
    return datetime.fromtimestamp(record.timestamp / 1000, tz=UTC)


def decode_bytes(value: bytes | None) -> str | None:
    if value is None:
        return None
    return value.decode("utf-8", errors="replace")


def build_archive_partition(record: ConsumerRecord) -> ArchivePartition:
    event_time = kafka_timestamp_to_datetime(record)
    return ArchivePartition(
        topic=record.topic,
        partition=record.partition,
        year=event_time.year,
        month=event_time.month,
        day=event_time.day,
        hour=event_time.hour,
    )


def build_archive_object_path(
    base_prefix: str,
    partition: ArchivePartition,
    start_offset: int,
    end_offset: int,
) -> str:
    return (
        f"{base_prefix}/topic={partition.topic}/year={partition.year:04d}/"
        f"month={partition.month:02d}/day={partition.day:02d}/hour={partition.hour:02d}/"
        f"partition={partition.partition}/offsets_{start_offset}_{end_offset}.parquet"
    )


def build_archive_row(record: ConsumerRecord) -> dict:
    return {
        "topic": record.topic,
        "partition": record.partition,
        "offset": record.offset,
        "timestamp": kafka_timestamp_to_datetime(record).isoformat(),
        "key": decode_bytes(record.key),
        "raw_value": decode_bytes(record.value),
    }


def group_records_by_archive_partition(
    records: Iterable[ConsumerRecord],
) -> dict[ArchivePartition, list[ConsumerRecord]]:
    grouped: dict[ArchivePartition, list[ConsumerRecord]] = defaultdict(list)
    for record in records:
        grouped[build_archive_partition(record)].append(record)
    return grouped


def write_archive_batch(
    filesystem,
    root_path: str,
    partition: ArchivePartition,
    records: list[ConsumerRecord],
) -> str:
    if pa is None or pq is None:
        raise RuntimeError("pyarrow is required for raw archiving")
    rows = [build_archive_row(record) for record in records]
    table = pa.Table.from_pylist(rows)
    start_offset = min(record.offset for record in records)
    end_offset = max(record.offset for record in records)
    object_path = build_archive_object_path(root_path, partition, start_offset, end_offset)

    if isinstance(filesystem, pafs.LocalFileSystem):
        target_path = Path(object_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(table, target_path)
        return object_path

    with tempfile.NamedTemporaryFile(suffix=".parquet", delete=False) as tmp_file:
        temp_path = Path(tmp_file.name)
    try:
        pq.write_table(table, temp_path)
        file_info = filesystem.get_file_info([object_path])[0]
        if file_info.type == pafs.FileType.File:
            filesystem.delete_file(object_path)
        with temp_path.open("rb") as source_stream:
            with filesystem.open_output_stream(object_path) as destination_stream:
                destination_stream.write(source_stream.read())
        return object_path
    finally:
        temp_path.unlink(missing_ok=True)


def build_s3_filesystem():
    if pafs is None:
        raise RuntimeError("pyarrow is required for MinIO raw archiving")
    parsed_endpoint = urlparse(MINIO_ENDPOINT)
    endpoint_override = parsed_endpoint.netloc or parsed_endpoint.path
    return pafs.S3FileSystem(
        access_key=MINIO_ACCESS_KEY,
        secret_key=MINIO_SECRET_KEY,
        endpoint_override=endpoint_override,
        scheme=parsed_endpoint.scheme or "http",
        region=MINIO_REGION,
    )


def create_consumer() -> KafkaConsumer:
    if KafkaConsumer is None:
        raise RuntimeError("kafka-python-ng is required for raw archiving")
    return KafkaConsumer(
        *RAW_ARCHIVER_TOPICS,
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=RAW_ARCHIVER_GROUP_ID,
        enable_auto_commit=False,
        auto_offset_reset=RAW_ARCHIVER_AUTO_OFFSET_RESET,
        consumer_timeout_ms=0,
    )


def archive_records(filesystem, root_path: str, polled_records) -> dict:
    committed_offsets: dict[TopicPartition, int] = {}
    for topic_partition, records in polled_records.items():
        if not records:
            continue
        for archive_partition, archive_records_batch in group_records_by_archive_partition(
            records
        ).items():
            write_archive_batch(filesystem, root_path, archive_partition, archive_records_batch)
        committed_offsets[topic_partition] = max(record.offset for record in records) + 1
    return committed_offsets


def commit_offsets(consumer: KafkaConsumer, offsets: dict[TopicPartition, int]) -> None:
    if not offsets:
        return
    consumer.commit(
        {
            partition: OffsetAndMetadata(offset, None)
            for partition, offset in offsets.items()
        }
    )


def run_archiver(once: bool = False) -> None:
    filesystem = build_s3_filesystem()
    root_path = f"{RAW_POSTS_BUCKET}/{RAW_ARCHIVE_PREFIX}"
    consumer = create_consumer()
    running = True

    def handle_signal(signum, frame) -> None:
        nonlocal running
        running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    try:
        while running:
            polled_records = consumer.poll(
                timeout_ms=RAW_ARCHIVER_POLL_TIMEOUT_MS,
                max_records=RAW_ARCHIVER_MAX_RECORDS,
            )
            offsets = archive_records(filesystem, root_path, polled_records)
            commit_offsets(consumer, offsets)
            if once:
                return
            if not polled_records:
                time.sleep(RAW_ARCHIVER_FLUSH_SECONDS)
    finally:
        consumer.close()


def main() -> None:
    run_archiver()


if __name__ == "__main__":
    main()
