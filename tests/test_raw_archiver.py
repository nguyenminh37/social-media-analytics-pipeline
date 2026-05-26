import tempfile
import unittest
from importlib.util import find_spec
from pathlib import Path
from types import SimpleNamespace

if find_spec("pyarrow") is not None:
    import pyarrow.parquet as pq
    from pyarrow.fs import LocalFileSystem
else:  # pragma: no cover - environment guard
    pq = None
    LocalFileSystem = None

from consumers.raw_archiver import (
    build_archive_partition,
    group_records_by_archive_partition,
    write_archive_batch,
)


@unittest.skipUnless(pq is not None and LocalFileSystem is not None, "pyarrow is not installed")
class RawArchiverTests(unittest.TestCase):
    def make_record(self, topic: str, partition: int, offset: int, timestamp_ms: int):
        return SimpleNamespace(
            topic=topic,
            partition=partition,
            offset=offset,
            timestamp=timestamp_ms,
            key=b"key-1",
            value=b'{"id":"1"}',
        )

    def test_group_records_by_archive_partition_groups_by_hour(self) -> None:
        record_a = self.make_record("raw_posts", 0, 1, 1716710400000)
        record_b = self.make_record("raw_posts", 0, 2, 1716712200000)

        grouped = group_records_by_archive_partition([record_a, record_b])

        self.assertEqual(len(grouped), 1)
        archive_partition = next(iter(grouped))
        self.assertEqual(archive_partition.topic, "raw_posts")
        self.assertEqual(archive_partition.hour, build_archive_partition(record_a).hour)

    def test_write_archive_batch_writes_parquet_with_offsets_in_path(self) -> None:
        record = self.make_record("raw_posts", 1, 42, 1716710400000)
        archive_partition = build_archive_partition(record)
        with tempfile.TemporaryDirectory() as temp_dir:
            target_path = write_archive_batch(
                LocalFileSystem(),
                temp_dir,
                archive_partition,
                [record],
            )

            self.assertIn("offsets_42_42.parquet", target_path)
            table = pq.ParquetFile(Path(target_path)).read()
            self.assertEqual(table.num_rows, 1)
            self.assertEqual(table.column("offset").to_pylist(), [42])


if __name__ == "__main__":
    unittest.main()
