# Demo End-to-End

## Mục tiêu

Demo luồng hiện tại của dự án:

`YouTube Data API -> Kafka -> Spark -> MongoDB / MinIO / Elasticsearch -> Kibana / Grafana / Serving API`

## Chuẩn bị

```bash
docker compose up -d
.venv/bin/python scripts/healthcheck.py
.venv/bin/python batch_tools/create_topics.py
.venv/bin/python scripts/init_elasticsearch.py
.venv/bin/python scripts/init_mongodb.py
```

## Chạy demo

### Terminal 1: YouTube Spark

```bash
source .venv/bin/activate
RESET_CHECKPOINT_ON_START=true spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,org.elasticsearch:elasticsearch-spark-30_2.12:8.10.0,org.apache.hadoop:hadoop-aws:3.3.4 \
  spark_jobs/youtube/stream_processor.py
```

### Terminal 2: raw archiver

```bash
.venv/bin/python -m consumers.raw_archiver
```

### Terminal 3: YouTube producer

```bash
YOUTUBE_MAX_TRENDING_VIDEOS=2 \
YOUTUBE_MAX_COMMENTS_PER_VIDEO=5 \
.venv/bin/python -m collectors.youtube.producer
```

### Terminal 4: serving API

```bash
.venv/bin/python -m serving_api.server
```

## Điểm cần trình bày

- Kafka UI có `raw_youtube_videos`, `raw_youtube_comments`, `raw_youtube_channels`
- Kafka UI có `silver_youtube_content_events`, `silver_youtube_channel_snapshots`, `youtube_aggregated_metrics`
- MinIO có `kafka_raw/topic=raw_youtube_*`
- Kibana/Grafana đọc index YouTube
- Serving API trả về dữ liệu từ `/api/youtube/*`
