import argparse
import json
import sys
from pathlib import Path

from kafka import KafkaConsumer, TopicPartition

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.kafka_config import (
    KAFKA_BOOTSTRAP_SERVERS,
    RAW_ARCHIVER_GROUP_ID,
    RAW_ARCHIVER_TOPICS,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Check Kafka consumer lag by group")
    parser.add_argument("--group", default=RAW_ARCHIVER_GROUP_ID)
    parser.add_argument(
        "--topics",
        default=",".join(RAW_ARCHIVER_TOPICS),
        help="Comma separated topics to inspect",
    )
    return parser


def compute_lag(group_id: str, topics: list[str]) -> dict:
    consumer = KafkaConsumer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        group_id=group_id,
        enable_auto_commit=False,
    )
    try:
        topic_partitions: list[TopicPartition] = []
        for topic in topics:
            partitions = consumer.partitions_for_topic(topic) or set()
            topic_partitions.extend(
                TopicPartition(topic, partition_id)
                for partition_id in sorted(partitions)
            )

        consumer.assign(topic_partitions)
        end_offsets = consumer.end_offsets(topic_partitions)

        items = []
        total_lag = 0
        for topic_partition in topic_partitions:
            committed = consumer.committed(topic_partition) or 0
            end_offset = end_offsets.get(topic_partition, 0)
            lag = max(end_offset - committed, 0)
            total_lag += lag
            items.append(
                {
                    "topic": topic_partition.topic,
                    "partition": topic_partition.partition,
                    "current_offset": committed,
                    "log_end_offset": end_offset,
                    "lag": lag,
                }
            )
        return {"group": group_id, "total_lag": total_lag, "items": items}
    finally:
        consumer.close()


def main() -> None:
    args = build_parser().parse_args()
    topics = [topic for topic in args.topics.split(",") if topic]
    print(json.dumps(compute_lag(args.group, topics), indent=2))


if __name__ == "__main__":
    main()
