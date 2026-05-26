# Social Media Analytics Pipeline

Project này triển khai pipeline Kappa để thu thập dữ liệu RSS và YouTube, đưa vào Kafka, xử lý bằng Spark Structured Streaming, rồi ghi ra MinIO, MongoDB, Elasticsearch.

Trong kiến trúc hiện tại:
- `MinIO` là lớp lưu trữ dài hạn cho parquet/checkpoint
- `MongoDB` là lớp hot storage cho document/query nhanh, có TTL để không giữ vô hạn
- `Elasticsearch` là lớp search/visualization cho bài viết đã xử lý

## Cấu trúc chính

- `collectors/rss/collector.py`: lấy tin từ RSS feed báo điện tử
- `collectors/historical/replay_producer.py`: replay dữ liệu lịch sử vào Kafka
- `collectors/youtube/collector.py`: crawl YouTube entities ra raw schema
- `collectors/youtube/producer.py`: lấy YouTube video/channel/comment và đẩy vào raw topics riêng
- `spark_jobs/legacy_posts/stream_processor.py`: xử lý RSS posts trên luồng `raw_posts`
- `spark_jobs/youtube/stream_processor.py`: xử lý YouTube Bronze -> Silver/Gold
- `batch_tools/create_topics.py`: tạo Kafka topics

## 1. Chạy hạ tầng MVP

```bash
docker compose up -d
```

Hệ thống sẽ chạy:
- Kafka + ZooKeeper
- MinIO
- MongoDB
- Elasticsearch
- Kibana
- Grafana

## 2. Cài thư viện Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Tạo file cấu hình local từ mẫu rồi điền secret của bạn vào `.env`:

```bash
cp .env.example .env
```

Nếu bạn dùng MongoDB Atlas, sửa `MONGO_URI` trong `.env`, ví dụ:

```bash
MONGO_URI=mongodb+srv://username:password@your-cluster.mongodb.net/analytics?appName=analytics
```

## 3. Tạo Kafka topics

```bash
python3 batch_tools/create_topics.py
```

## 4. Chạy collectors

### RSS collector

```bash
python3 -m collectors.rss.collector
```

### YouTube producer

Điền `YOUTUBE_API_KEY` trong `.env`, rồi chạy giới hạn nhỏ khi demo/test:

```bash
YOUTUBE_MAX_TRENDING_VIDEOS=2 \
YOUTUBE_MAX_COMMENTS_PER_VIDEO=5 \
python3 -m collectors.youtube.producer
```

## 5. Replay historical data

```bash
python3 -m collectors.historical.replay_producer sample_data/posts.json --sleep-seconds 0.5
```

## 6. Chạy Spark Structured Streaming

```bash
.venv/bin/spark-submit \
  spark_jobs/legacy_posts/stream_processor.py
```

Job này:
- đọc từ `raw_posts`
- clean + dedup
- gán sentiment
- tính sentiment metrics và trending keywords
- ghi sang `processed_posts`, `aggregated_metrics`
- lưu xuống MinIO, MongoDB, Elasticsearch

Nếu demo/dev cần reset state cũ của Spark tự động để tránh lỗi offset Kafka lệch checkpoint, bật:

```bash
RESET_CHECKPOINT_ON_START=true .venv/bin/spark-submit \
  spark_jobs/legacy_posts/stream_processor.py
```

### YouTube Spark job

```bash
RESET_CHECKPOINT_ON_START=true .venv/bin/spark-submit \
  spark_jobs/youtube/stream_processor.py
```

## 7. Kiểm tra topics

```bash
docker exec -it sma-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic raw_posts \
  --from-beginning
```

```bash
docker exec -it sma-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic processed_posts \
  --from-beginning
```

```bash
docker exec -it sma-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic aggregated_metrics \
  --from-beginning
```

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

## Biến môi trường chính

- `RSS_FETCH_INTERVAL_SECONDS`: mặc định `60`
- `YOUTUBE_API_KEY`: API key cho YouTube Data API v3
- `YOUTUBE_REGION_CODE`: mặc định `VN`
- `YOUTUBE_MAX_TRENDING_VIDEOS`: mặc định `50`
- `YOUTUBE_MAX_COMMENTS_PER_VIDEO`: mặc định `100`
- `KAFKA_BOOTSTRAP_SERVERS`: mặc định `localhost:9092`
- `MINIO_ENDPOINT`: mặc định `http://localhost:9000`
- `MONGO_URI`: mặc định `mongodb://localhost:27017`
- `MONGO_DATABASE`: mặc định `analytics`
- `MONGO_POSTS_TTL_DAYS`: số ngày giữ `posts` trong MongoDB, mặc định `7`
- `MONGO_METRICS_TTL_DAYS`: số ngày giữ `sentiment_metrics` và `trending_topics`, mặc định `30`
- `ELASTICSEARCH_HOST`: mặc định `http://localhost:9200`
