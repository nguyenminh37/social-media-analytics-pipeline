# Social Media Analytics Pipeline

Project này hiện chỉ giữ **YouTube pipeline** theo kiến trúc Kappa:

`YouTube Data API -> Kafka -> Spark Structured Streaming -> MinIO / MongoDB / Elasticsearch -> Serving API / Dashboard`

## Thành phần chính

- `collectors/youtube/collector.py`: lấy dữ liệu video, comment, channel từ YouTube Data API.
- `collectors/youtube/producer.py`: publish raw entities vào các Kafka topics YouTube.
- `consumers/raw_archiver.py`: ghi `raw_youtube_*` từ Kafka xuống MinIO theo partition thời gian.
- `spark_jobs/youtube/stream_processor.py`: chuẩn hóa raw YouTube thành silver/gold datasets, aggregate metrics và ghi sink.
- `serving_api/server.py`: HTTP API read-only cho top videos, sentiment metrics, trending keywords, freshness.
- `batch_tools/create_topics.py`: tạo Kafka topics cho YouTube pipeline.

## Khởi chạy hạ tầng

```bash
docker compose up -d
```

Hệ thống sẽ chạy Kafka, ZooKeeper, MinIO, MongoDB, Elasticsearch, Kibana và Grafana.

## Cài dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Điền `YOUTUBE_API_KEY` trong `.env`.

## Khởi tạo topics và storage

```bash
python3 batch_tools/create_topics.py
python3 scripts/init_mongodb.py
python3 scripts/init_elasticsearch.py
```

## Chạy pipeline

### 1. Raw archiver

```bash
python3 -m consumers.raw_archiver
```

### 2. YouTube producer

```bash
YOUTUBE_MAX_TRENDING_VIDEOS=2 \
YOUTUBE_MAX_COMMENTS_PER_VIDEO=5 \
python3 -m collectors.youtube.producer
```

### 3. YouTube Spark job

```bash
RESET_CHECKPOINT_ON_START=true .venv/bin/spark-submit \
  spark_jobs/youtube/stream_processor.py
```

Nếu cần fail-fast cho các sink phụ để debug:

```bash
FAIL_ON_OPTIONAL_SINK_ERROR=true RESET_CHECKPOINT_ON_START=true .venv/bin/spark-submit \
  spark_jobs/youtube/stream_processor.py
```

Replay cho query mới:

```bash
KAFKA_STREAM_STARTING_OFFSETS=earliest
KAFKA_STREAM_STARTING_TIMESTAMP=1716710400000
```

## Chạy serving API

```bash
python3 -m serving_api.server
```

Endpoints chính:

- `GET /health`
- `GET /api/youtube/top-videos?filter_mode=hours&window_hours=72&page=1&page_size=10`
- `GET /api/youtube/top-videos?filter_mode=date_range&date_from=2026-05-20&date_to=2026-05-27&page=1&page_size=10`
- `GET /api/youtube/sentiment-metrics?filter_mode=hours&window_hours=72&page=1&page_size=10`
- `GET /api/youtube/sentiment-metrics?filter_mode=date_range&date_from=2026-05-20&date_to=2026-05-27&page=1&page_size=10`
- `GET /api/youtube/trending-keywords?filter_mode=hours&window_hours=72&page=1&page_size=10`
- `GET /api/youtube/trending-keywords?filter_mode=date_range&date_from=2026-05-20&date_to=2026-05-27&page=1&page_size=10`
- `GET /api/youtube/freshness`

## Kiểm tra topics

```bash
docker exec -it sma-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic raw_youtube_videos \
  --from-beginning
```

```bash
docker exec -it sma-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic silver_youtube_content_events \
  --from-beginning
```

```bash
docker exec -it sma-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic youtube_aggregated_metrics \
  --from-beginning
```

```bash
docker exec -it sma-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic pipeline_dlq \
  --from-beginning
```

## Quan sát tối thiểu

```bash
python3 scripts/check_kafka_lag.py --group raw-archiver
python3 scripts/check_sink_freshness.py --max-age-minutes 60
```

## Biến môi trường chính

- `YOUTUBE_API_KEY`
- `YOUTUBE_REGION_CODE`
- `YOUTUBE_MAX_TRENDING_VIDEOS`
- `YOUTUBE_MAX_COMMENTS_PER_VIDEO`
- `KAFKA_BOOTSTRAP_SERVERS`
- `KAFKA_PIPELINE_DLQ_TOPIC`
- `KAFKA_STREAM_STARTING_OFFSETS`
- `KAFKA_STREAM_STARTING_TIMESTAMP`
- `KAFKA_RAW_ARCHIVER_GROUP_ID`
- `MINIO_ENDPOINT`
- `MINIO_RAW_ARCHIVE_PREFIX`
- `MONGO_URI`
