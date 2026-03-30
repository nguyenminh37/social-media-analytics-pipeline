import logging

from kafka.admin import KafkaAdminClient, NewTopic
from kafka.errors import TopicAlreadyExistsError

from config.kafka_config import KAFKA_BOOTSTRAP_SERVERS, TOPIC_SPECS


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)


def build_topics() -> list[NewTopic]:
    return [
        NewTopic(
            name=spec["name"],
            num_partitions=spec["partitions"],
            replication_factor=spec["replication_factor"],
            topic_configs=spec["config"],
        )
        for spec in TOPIC_SPECS
    ]


def main() -> None:
    admin = KafkaAdminClient(bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS)

    try:
        existing_topics = set(admin.list_topics())
        topics_to_create = [
            topic for topic in build_topics() if topic.name not in existing_topics
        ]

        if not topics_to_create:
            logging.info("All Kafka topics already exist: %s", sorted(existing_topics))
            return

        admin.create_topics(new_topics=topics_to_create, validate_only=False)
        logging.info(
            "Created Kafka topics: %s",
            ", ".join(topic.name for topic in topics_to_create),
        )
    except TopicAlreadyExistsError:
        logging.info("Kafka topics already exist")
    finally:
        admin.close()


if __name__ == "__main__":
    main()
