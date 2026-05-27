# Hướng Dẫn Sử Dụng và Kiểm Thử

Tài liệu này chỉ áp dụng cho **YouTube pipeline** hiện tại.

## User Guide

### 1. Khởi chạy hạ tầng

```bash
docker compose up -d
```

### 2. Thiết lập Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Điền `YOUTUBE_API_KEY` trong `.env`.

### 3. Khởi tạo topics và storage

```bash
python3 batch_tools/create_topics.py
python3 scripts/init_elasticsearch.py
python3 scripts/init_mongodb.py
```

### 4. Chạy các tiến trình chính

```bash
python3 -m consumers.raw_archiver
```

```bash
YOUTUBE_MAX_TRENDING_VIDEOS=2 \
YOUTUBE_MAX_COMMENTS_PER_VIDEO=5 \
python3 -m collectors.youtube.producer
```

```bash
RESET_CHECKPOINT_ON_START=true .venv/bin/spark-submit \
  spark_jobs/youtube/stream_processor.py
```

```bash
python3 -m serving_api.server
```

### 5. Dashboard

- Grafana: `http://localhost:3000`
- Kibana: `http://localhost:5601`
- MinIO: `http://localhost:7001`
- Kafka UI: `http://localhost:8080`

## Testing

### 1. Unit tests

```bash
pytest -v
```

Trọng tâm test hiện tại:

- YouTube collector/producer
- YouTube stream processor
- shared runtime/quality
- MongoDB/Elasticsearch init scripts
- serving API

### 2. Healthcheck

```bash
python3 scripts/healthcheck.py
```

### 3. Manual diagnostics

```bash
docker exec -it sma-kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic raw_youtube_videos --from-beginning
```

```bash
docker exec -it sma-kafka kafka-console-consumer --bootstrap-server localhost:9092 --topic silver_youtube_content_events --from-beginning
```

```bash
curl http://localhost:8081/health
curl "http://localhost:8081/api/youtube/top-videos?window_minutes=1440&limit=5"
```
