import json
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
load_dotenv(PROJECT_ROOT / ".env")

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from elasticsearch import Elasticsearch
from config.storage_config import (
    PUBLIC_CONTENT_EVENTS_INDEX,
    PUBLIC_TREND_ALERTS_INDEX,
    PUBLIC_TREND_METRICS_INDEX,
    YOUTUBE_CHANNEL_SNAPSHOTS_INDEX,
    YOUTUBE_CONTENT_EVENTS_INDEX,
)


ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")

logging.basicConfig(level=logging.INFO)

def init_elasticsearch(es_client: Elasticsearch, index_name: str, mapping_path: Path):
    if not mapping_path.exists():
        logging.error(f"Mapping file not found at {mapping_path}")
        return False
        
    with open(mapping_path, 'r', encoding='utf-8') as f:
        mapping = json.load(f)

    if not es_client.indices.exists(index=index_name):
        es_client.indices.create(index=index_name, body=mapping)
        logging.info(f"Created index '{index_name}' with mapping.")
    else:
        # We can try to put mapping, but some changes might require reindex
        try:
            es_client.indices.put_mapping(index=index_name, body=mapping["mappings"])
            logging.info(f"Updated mapping for existing index '{index_name}'.")
        except Exception as e:
            logging.warning(f"Could not update mapping for existing index: {e}")
    return True

def main():
    es = Elasticsearch([ELASTICSEARCH_HOST])
    index_mappings = [
        (
            YOUTUBE_CONTENT_EVENTS_INDEX,
            PROJECT_ROOT / "schemas" / "youtube" / "elasticsearch_content_events_mapping.json",
        ),
        (
            YOUTUBE_CHANNEL_SNAPSHOTS_INDEX,
            PROJECT_ROOT
            / "schemas"
            / "youtube"
            / "elasticsearch_channel_snapshots_mapping.json",
        ),
        (
            PUBLIC_CONTENT_EVENTS_INDEX,
            PROJECT_ROOT
            / "schemas"
            / "public_content"
            / "elasticsearch_content_events_mapping.json",
        ),
        (
            PUBLIC_TREND_METRICS_INDEX,
            PROJECT_ROOT
            / "schemas"
            / "public_content"
            / "elasticsearch_trend_metrics_mapping.json",
        ),
        (
            PUBLIC_TREND_ALERTS_INDEX,
            PROJECT_ROOT
            / "schemas"
            / "public_content"
            / "elasticsearch_trend_alerts_mapping.json",
        ),
    ]

    for index_name, mapping_path in index_mappings:
        init_elasticsearch(es, index_name, mapping_path)

if __name__ == "__main__":
    main()
