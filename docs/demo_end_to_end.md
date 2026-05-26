# Demo End-to-End

## Mục tiêu

Demo ngắn gọn luồng hoàn chỉnh của dự án:

`RSS + YouTube -> Kafka -> Spark -> MongoDB / MinIO / Elasticsearch -> Kibana / Grafana`

---

## 1. Kiến trúc hệ thống

```mermaid
flowchart LR
    A[RSS Feeds<br/>VnExpress / Tuoi Tre / BBC]
    C[Historical Replay]
    Y[YouTube Data API]

    A --> D[Kafka<br/>raw_posts]
    C --> D
    Y --> YR[Kafka<br/>raw_youtube_*]

    D --> E[Spark Structured Streaming<br/>stream_processor.py]
    YR --> YS[Spark Structured Streaming<br/>youtube/stream_processor.py]

    E --> F[Kafka<br/>processed_posts]
    E --> G[Kafka<br/>aggregated_metrics]
    E --> H[MongoDB<br/>hot storage]
    E --> I[MinIO<br/>parquet + checkpoint]
    E --> J[Elasticsearch<br/>search index]
    YS --> YC[Kafka<br/>silver_youtube_* / youtube_aggregated_metrics]
    YS --> YM[MongoDB / MinIO / Elasticsearch<br/>youtube_*]

    J --> K[Kibana]
    J --> L[Grafana]
```

---

## 2. Pipeline dữ liệu

```mermaid
flowchart TD
    A[Collector chạy định kỳ] --> B[Đọc RSS]
    B --> C[Publish vào Kafka raw_posts]
    C --> D[Spark đọc stream]
    D --> E[Clean + trim + chuẩn hóa schema]
    E --> F[Dedup theo id]
    F --> G[Gán sentiment]
    G --> H[Tính trending + sentiment metrics]
    H --> I[processed_posts]
    H --> J[aggregated_metrics]
    H --> K[MongoDB posts / sentiment_metrics / trending_topics]
    H --> L[MinIO clean-posts / aggregates / checkpoints]
    H --> M[Elasticsearch posts]

    Y[YouTube producer] --> Y1[raw_youtube_videos / comments / channels]
    Y1 --> Y2[YouTube Spark job]
    Y2 --> Y3[silver_youtube_content_events]
    Y2 --> Y4[youtube_content_events / youtube_channel_snapshots]
```

---

## 3. Chuẩn bị demo

```bash
cd /Volumes/plxg2/Project/bigdata/social-media-analytics-pipeline
docker compose up -d
.venv/bin/python scripts/healthcheck.py
.venv/bin/python batch_tools/create_topics.py
.venv/bin/python scripts/init_elasticsearch.py
.venv/bin/python scripts/init_mongodb.py
```

Kỳ vọng:
- `kafka: ok`
- `mongodb: ok`
- `elasticsearch: ok`
- `minio: ok`

---

## 4. Chạy demo

### Terminal 1: Spark legacy RSS

```bash
cd /Volumes/plxg2/Project/bigdata/social-media-analytics-pipeline
source .venv/bin/activate
RESET_CHECKPOINT_ON_START=true spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,org.elasticsearch:elasticsearch-spark-30_2.12:8.10.0,org.apache.hadoop:hadoop-aws:3.3.4 \
  spark_jobs/legacy_posts/stream_processor.py
```

### Terminal 2: RSS collector

```bash
cd /Volumes/plxg2/Project/bigdata/social-media-analytics-pipeline
.venv/bin/python -m collectors.rss.collector
```

Đợi log:
- `Feed VnExpress: Fetched ...`
- `Feed Tuoi Tre: Fetched ...`
- `Feed BBC Vietnamese: Fetched ...`

### Terminal 3: YouTube Spark

```bash
cd /Volumes/plxg2/Project/bigdata/social-media-analytics-pipeline
source .venv/bin/activate
RESET_CHECKPOINT_ON_START=true spark-submit \
  --packages org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.1,org.elasticsearch:elasticsearch-spark-30_2.12:8.10.0,org.apache.hadoop:hadoop-aws:3.3.4 \
  spark_jobs/youtube/stream_processor.py
```

### Terminal 4: YouTube producer

```bash
cd /Volumes/plxg2/Project/bigdata/social-media-analytics-pipeline
YOUTUBE_MAX_TRENDING_VIDEOS=2 \
YOUTUBE_MAX_COMMENTS_PER_VIDEO=5 \
.venv/bin/python -m collectors.youtube.producer
```

---

## 5. Mở UI để trình bày

- Kafka UI: `http://localhost:8080`
- MinIO: `http://localhost:9001`
- Kibana: `http://localhost:5601`
- Grafana: `http://localhost:3000`

---

## 6. Thứ tự demo chuẩn

### 6.1 Kafka UI

Cho xem:
- `raw_posts`: dữ liệu thô vừa crawl
- `processed_posts`: dữ liệu đã qua Spark, có `sentiment`
- `aggregated_metrics`: dữ liệu tổng hợp
- `raw_youtube_videos`, `raw_youtube_comments`, `raw_youtube_channels`: dữ liệu YouTube thô
- `silver_youtube_content_events`, `silver_youtube_channel_snapshots`: dữ liệu YouTube đã chuẩn hóa
- `youtube_aggregated_metrics`: metric tổng hợp YouTube

### 6.2 MinIO

Cho xem các bucket:
- `clean-posts`
- `aggregates`
- `checkpoints`

Ý nghĩa:
- `clean-posts`, `aggregates`: lưu trữ dài hạn
- `checkpoints`: state kỹ thuật của Spark

### 6.3 Kibana

Vào `Discover`:
- Data view: `posts`
- Data view YouTube: `youtube_content_events`
- Timestamp field: `published_at`

Cho xem:
- `title`
- `source`
- `feed_name`
- `sentiment`

### 6.4 Grafana

Đăng nhập:
- user: `admin`
- password: `admin`

Cho xem dashboard:
- `Social Media Analytics`

---

## 7. Cách nói ngắn gọn

> Hệ thống có pipeline RSS trên `raw_posts` và pipeline YouTube riêng trên `raw_youtube_*`. Dữ liệu sau Spark được chuẩn hóa, ghi ra Kafka, MongoDB, MinIO và Elasticsearch để quan sát qua Kafka UI, Kibana và Grafana.

---

## 8. 3 điểm cần chứng minh

- `raw_posts` có dữ liệu mới
- `processed_posts` có dữ liệu đã xử lý
- MinIO hoặc Kibana có dữ liệu đầu ra
- `raw_youtube_*` có dữ liệu mới
- `silver_youtube_content_events` có dữ liệu đã xử lý
- `youtube_content_events` hoặc MinIO path YouTube có dữ liệu đầu ra

Nếu đủ 3 điểm này thì demo end-to-end đã pass.
