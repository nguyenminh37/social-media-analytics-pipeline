# Hướng dẫn triển khai: Social Media & News Analytics Pipeline (Kappa Architecture)

## Tổng quan dự án

Xây dựng hệ thống xử lý dữ liệu lớn theo kiến trúc **Kappa**, thu thập và phân tích dữ liệu từ mạng xã hội (Reddit) và báo điện tử (RSS feed) theo thời gian thực.

### Luồng xử lý tổng thể

```
Reddit API / RSS Feed / Historical Data
        ↓
   Collector (Python)
        ↓
   Apache Kafka (message bus)
        ↓
Spark Structured Streaming (processing)
        ↓
  ┌─────────────────────────┐
  │   MinIO (Parquet raw)   │
  │   MongoDB (metrics)     │
  │   Elasticsearch (text)  │
  └─────────────────────────┘
        ↓
  Kibana / Grafana (dashboard)
```

---

## Cấu trúc thư mục dự án

```
project-root/
├── collectors/
│   ├── reddit_collector.py
│   ├── rss_collector.py
│   └── historical_replay_producer.py
├── spark_jobs/
│   ├── stream_processor.py
│   ├── sentiment_udf.py
│   └── trending_analyzer.py
├── config/
│   ├── kafka_config.py
│   ├── minio_config.py
│   ├── mongo_config.py
│   └── elasticsearch_config.py
├── docker/
│   ├── docker-compose.yml
│   └── Dockerfile.collector
├── k8s/                        # (ngoài phạm vi MVP)
│   ├── kafka-deployment.yaml
│   └── spark-deployment.yaml
├── dashboards/
│   ├── kibana_dashboard.ndjson
│   └── grafana_dashboard.json
├── schemas/
│   └── post_schema.py
├── tests/
│   └── test_pipeline.py
└── README.md
```

---

## Bước 1 — Data Ingestion (Thu thập dữ liệu)

### Mục tiêu
- Kết nối Reddit API và RSS feed
- Chuẩn hóa về schema chung
- Đẩy raw events vào Kafka topic `raw_posts`

### Schema chung cho mọi bài viết

```python
# schemas/post_schema.py
POST_SCHEMA = {
    "id": str,           # unique ID của bài viết
    "source": str,       # "reddit" hoặc "rss"
    "title": str,
    "content": str,      # body text hoặc description
    "url": str,
    "author": str,
    "published_at": str, # ISO 8601 timestamp
    "subreddit": str,    # chỉ có với Reddit, None với RSS
    "feed_name": str,    # tên báo/subreddit
    "ingested_at": str,  # thời điểm collector nhận dữ liệu
}
```

### Reddit Collector (`collectors/reddit_collector.py`)

**Thư viện cần dùng:** `praw`, `kafka-python`

**Yêu cầu:**
- Kết nối Reddit API qua `praw` với credentials từ biến môi trường
- Lấy bài viết từ danh sách subreddit cấu hình sẵn (ví dụ: `r/worldnews`, `r/technology`, `r/vietnam`)
- Polling liên tục mỗi 30 giây, dùng `submission.id` để tránh trùng lặp
- Serialize sang JSON và gửi vào Kafka topic `raw_posts`

**Biến môi trường cần:**
```
REDDIT_CLIENT_ID=...
REDDIT_CLIENT_SECRET=...
REDDIT_USER_AGENT=...
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
```

### RSS Collector (`collectors/rss_collector.py`)

**Thư viện cần dùng:** `feedparser`, `kafka-python`

**Yêu cầu:**
- Đọc danh sách RSS URL từ file config hoặc biến môi trường
- Polling mỗi 60 giây, dùng `entry.id` hoặc `entry.link` để dedup
- Chuẩn hóa theo POST_SCHEMA và gửi vào Kafka topic `raw_posts`

**Danh sách RSS feed gợi ý:**
```python
RSS_FEEDS = [
    {"name": "VnExpress", "url": "https://vnexpress.net/rss/tin-moi-nhat.rss"},
    {"name": "Tuoi Tre", "url": "https://tuoitre.vn/rss/tin-moi-nhat.rss"},
    {"name": "BBC Vietnamese", "url": "https://feeds.bbci.co.uk/vietnamese/rss.xml"},
]
```

### Historical Replay Producer (`collectors/historical_replay_producer.py`)

**Yêu cầu:**
- Đọc file CSV/JSON/Parquet từ MinIO hoặc local
- Phát lại dữ liệu vào Kafka theo đúng format POST_SCHEMA
- Có thể giả lập timestamp để replay đúng thứ tự thời gian
- Quan trọng: đây là cách Kappa Architecture xử lý reprocessing, không cần batch pipeline riêng

---

## Bước 2 — Kafka Setup (Message Bus)

### Kafka Topics cần tạo

| Topic | Mục đích | Retention |
|---|---|---|
| `raw_posts` | Raw events từ collectors | 7 ngày |
| `processed_posts` | Sau khi Spark clean + enrich | 3 ngày |
| `aggregated_metrics` | Metrics tổng hợp (trending, sentiment counts) | 1 ngày |

### Cấu hình Kafka (docker-compose)

```yaml
kafka:
  image: confluentinc/cp-kafka:7.5.0
  environment:
    KAFKA_BROKER_ID: 1
    KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
    KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092
    KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
    KAFKA_LOG_RETENTION_HOURS: 168
```

### Tạo topics

```bash
kafka-topics.sh --create --topic raw_posts --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
kafka-topics.sh --create --topic processed_posts --bootstrap-server localhost:9092 --partitions 3 --replication-factor 1
kafka-topics.sh --create --topic aggregated_metrics --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1
```

---

## Bước 3 — Spark Structured Streaming (Xử lý luồng)

### Mục tiêu
- Đọc từ Kafka topic `raw_posts`
- Làm sạch, chuẩn hóa, dedup
- Chạy sentiment analysis
- Tính trending topics theo sliding window
- Ghi ra MinIO, MongoDB, Elasticsearch

### `spark_jobs/stream_processor.py`

**Thư viện cần dùng:**
```
pyspark>=3.4
pyspark[sql]
kafka-python
pymongo
elasticsearch
```

**Cấu hình Spark session:**
```python
spark = SparkSession.builder \
    .appName("SocialMediaPipeline") \
    .config("spark.streaming.stopGracefullyOnShutdown", "true") \
    .config("spark.sql.streaming.checkpointLocation", "s3a://checkpoints/stream/") \
    .config("spark.hadoop.fs.s3a.endpoint", MINIO_ENDPOINT) \
    .config("spark.hadoop.fs.s3a.access.key", MINIO_ACCESS_KEY) \
    .config("spark.hadoop.fs.s3a.secret.key", MINIO_SECRET_KEY) \
    .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    .getOrCreate()
```

**Schema đọc từ Kafka:**
```python
from pyspark.sql.types import *

post_schema = StructType([
    StructField("id", StringType()),
    StructField("source", StringType()),
    StructField("title", StringType()),
    StructField("content", StringType()),
    StructField("url", StringType()),
    StructField("author", StringType()),
    StructField("published_at", StringType()),
    StructField("subreddit", StringType()),
    StructField("feed_name", StringType()),
    StructField("ingested_at", StringType()),
])
```

**Pipeline xử lý:**

```python
# 1. Đọc từ Kafka
raw_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", KAFKA_SERVERS) \
    .option("subscribe", "raw_posts") \
    .option("startingOffsets", "latest") \
    .load()

# 2. Parse JSON
parsed_df = raw_df.select(
    from_json(col("value").cast("string"), post_schema).alias("data")
).select("data.*")

# 3. Làm sạch
clean_df = parsed_df \
    .filter(col("title").isNotNull()) \
    .filter(length(col("title")) > 0) \
    .withColumn("title", trim(lower(col("title")))) \
    .withColumn("event_time", to_timestamp(col("published_at"))) \
    .dropDuplicates(["id"])

# 4. Watermark để xử lý dữ liệu đến trễ
watermarked_df = clean_df.withWatermark("event_time", "10 minutes")
```

### Sentiment Analysis UDF (`spark_jobs/sentiment_udf.py`)

**Thư viện:** `textblob` hoặc `vaderSentiment` (đơn giản), hoặc `transformers` nếu muốn nâng cao

```python
from pyspark.sql.functions import pandas_udf
import pandas as pd

@pandas_udf("string")
def sentiment_udf(texts: pd.Series) -> pd.Series:
    from textblob import TextBlob
    def analyze(text):
        if not text:
            return "neutral"
        polarity = TextBlob(str(text)).sentiment.polarity
        if polarity > 0.1:
            return "positive"
        elif polarity < -0.1:
            return "negative"
        return "neutral"
    return texts.apply(analyze)

# Áp dụng vào dataframe
enriched_df = watermarked_df.withColumn(
    "sentiment", sentiment_udf(col("title"))
)
```

### Trending Topics (`spark_jobs/trending_analyzer.py`)

```python
from pyspark.sql.functions import explode, split, window, count, rank
from pyspark.sql.window import Window

# Tách từ khóa từ title
keywords_df = enriched_df \
    .select(
        col("event_time"),
        explode(split(col("title"), r"\s+")).alias("keyword")
    ) \
    .filter(length(col("keyword")) > 3)  # bỏ stop words ngắn

# Tính tần suất theo sliding window 1 giờ, slide 15 phút
trending_df = keywords_df \
    .groupBy(
        window(col("event_time"), "1 hour", "15 minutes"),
        col("keyword")
    ) \
    .agg(count("*").alias("frequency")) \
    .orderBy(col("frequency").desc())
```

---

## Bước 4 — Storage Layer (Lưu trữ)

### 4.1 MinIO (thay thế HDFS)

**Cấu hình MinIO (docker-compose):**
```yaml
minio:
  image: minio/minio:latest
  command: server /data --console-address ":9001"
  ports:
    - "9000:9000"   # API
    - "9001:9001"   # Web Console
  environment:
    MINIO_ROOT_USER: minioadmin
    MINIO_ROOT_PASSWORD: minioadmin123
  volumes:
    - minio_data:/data
```

**Buckets cần tạo:**
| Bucket | Nội dung |
|---|---|
| `raw-posts` | Raw Parquet từ Kafka |
| `clean-posts` | Đã clean + normalize |
| `aggregates` | Trending metrics, sentiment counts |
| `checkpoints` | Spark Structured Streaming checkpoints |

**Ghi Parquet vào MinIO từ Spark:**
```python
clean_df.writeStream \
    .format("parquet") \
    .option("path", "s3a://clean-posts/") \
    .option("checkpointLocation", "s3a://checkpoints/clean/") \
    .trigger(processingTime="30 seconds") \
    .start()
```

### 4.2 MongoDB

**Cấu hình (docker-compose):**
```yaml
mongodb:
  image: mongo:6.0
  ports:
    - "27017:27017"
  environment:
    MONGO_INITDB_DATABASE: analytics
```

**Collections:**
| Collection | Nội dung |
|---|---|
| `posts` | Bài viết đã xử lý đầy đủ |
| `sentiment_metrics` | Phân bố sentiment theo thời gian |
| `trending_topics` | Top keywords theo window |

**Ghi vào MongoDB từ Spark (dùng foreachBatch):**
```python
def write_to_mongo(batch_df, batch_id):
    batch_df.write \
        .format("mongo") \
        .mode("append") \
        .option("uri", MONGO_URI) \
        .option("database", "analytics") \
        .option("collection", "posts") \
        .save()

enriched_df.writeStream \
    .foreachBatch(write_to_mongo) \
    .trigger(processingTime="30 seconds") \
    .start()
```

### 4.3 Elasticsearch

**Cấu hình (docker-compose):**
```yaml
elasticsearch:
  image: elasticsearch:8.10.0
  environment:
    - discovery.type=single-node
    - xpack.security.enabled=false
    - ES_JAVA_OPTS=-Xms512m -Xmx512m
  ports:
    - "9200:9200"
```

**Index mapping:**
```json
{
  "mappings": {
    "properties": {
      "id": { "type": "keyword" },
      "title": { "type": "text", "analyzer": "standard" },
      "content": { "type": "text" },
      "source": { "type": "keyword" },
      "sentiment": { "type": "keyword" },
      "feed_name": { "type": "keyword" },
      "event_time": { "type": "date" }
    }
  }
}
```

**Ghi vào Elasticsearch từ Spark:**
```python
def write_to_es(batch_df, batch_id):
    batch_df.write \
        .format("org.elasticsearch.spark.sql") \
        .option("es.nodes", ES_HOST) \
        .option("es.port", "9200") \
        .option("es.resource", "posts") \
        .mode("append") \
        .save()
```

---

## Bước 5 — Dashboard (Trực quan hóa)

### Kibana (kết nối Elasticsearch)

**Cấu hình (docker-compose):**
```yaml
kibana:
  image: kibana:8.10.0
  ports:
    - "5601:5601"
  environment:
    ELASTICSEARCH_HOSTS: http://elasticsearch:9200
```

**Dashboards cần tạo:**
1. **Post Volume Over Time** — Line chart, trục x là `event_time`, trục y là count
2. **Sentiment Distribution** — Pie chart theo field `sentiment`
3. **Top Trending Keywords** — Tag cloud hoặc Bar chart theo `keyword`
4. **Posts by Source** — Bar chart nhóm theo `source` và `feed_name`
5. **Full-text Search Panel** — Search bar để tìm kiếm theo nội dung

### Grafana (kết nối MongoDB/Prometheus)

**Cấu hình (docker-compose):**
```yaml
grafana:
  image: grafana/grafana:latest
  ports:
    - "3000:3000"
  environment:
    GF_SECURITY_ADMIN_PASSWORD: admin
```

**Plugin cần cài:**
```bash
grafana-cli plugins install grafana-mongodb-datasource
```

---

## Bước 6 — Ops (Vận hành)

> Phần này nằm ngoài phạm vi MVP. Triển khai sau khi pipeline ổn định.

### Checkpoint & Fault Tolerance

Spark Structured Streaming tự động checkpoint vào MinIO. Khi restart, pipeline tiếp tục từ offset đã lưu:

```python
.option("checkpointLocation", "s3a://checkpoints/main-stream/")
```

### Monitoring với Prometheus (ngoài MVP)

```yaml
prometheus:
  image: prom/prometheus
  volumes:
    - ./prometheus.yml:/etc/prometheus/prometheus.yml
  ports:
    - "9090:9090"
```

**Các metrics cần theo dõi:**
- Kafka consumer lag
- Spark batch processing time
- Records processed per second
- MongoDB write latency

### Kubernetes Deployment (ngoài MVP)

Khi sẵn sàng, mỗi service cần một `Deployment` + `Service` YAML. Thứ tự deploy:
1. Zookeeper → Kafka
2. MinIO → MongoDB → Elasticsearch
3. Collectors
4. Spark job
5. Kibana → Grafana

---

## docker-compose.yml hoàn chỉnh cho MVP

```yaml
version: "3.8"

services:
  zookeeper:
    image: confluentinc/cp-zookeeper:7.5.0
    environment:
      ZOOKEEPER_CLIENT_PORT: 2181

  kafka:
    image: confluentinc/cp-kafka:7.5.0
    depends_on: [zookeeper]
    ports:
      - "9092:9092"
    environment:
      KAFKA_BROKER_ID: 1
      KAFKA_ZOOKEEPER_CONNECT: zookeeper:2181
      KAFKA_ADVERTISED_LISTENERS: PLAINTEXT://kafka:9092,PLAINTEXT_HOST://localhost:9092
      KAFKA_LISTENER_SECURITY_PROTOCOL_MAP: PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT
      KAFKA_AUTO_CREATE_TOPICS_ENABLE: "true"
      KAFKA_LOG_RETENTION_HOURS: 168

  minio:
    image: minio/minio:latest
    command: server /data --console-address ":9001"
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin123
    volumes:
      - minio_data:/data

  mongodb:
    image: mongo:6.0
    ports:
      - "27017:27017"
    environment:
      MONGO_INITDB_DATABASE: analytics

  elasticsearch:
    image: elasticsearch:8.10.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
      - ES_JAVA_OPTS=-Xms512m -Xmx512m
    ports:
      - "9200:9200"

  kibana:
    image: kibana:8.10.0
    depends_on: [elasticsearch]
    ports:
      - "5601:5601"
    environment:
      ELASTICSEARCH_HOSTS: http://elasticsearch:9200

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3000:3000"
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin

  reddit-collector:
    build:
      context: .
      dockerfile: docker/Dockerfile.collector
    command: python collectors/reddit_collector.py
    depends_on: [kafka]
    environment:
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092
      REDDIT_CLIENT_ID: ${REDDIT_CLIENT_ID}
      REDDIT_CLIENT_SECRET: ${REDDIT_CLIENT_SECRET}
      REDDIT_USER_AGENT: ${REDDIT_USER_AGENT}

  rss-collector:
    build:
      context: .
      dockerfile: docker/Dockerfile.collector
    command: python collectors/rss_collector.py
    depends_on: [kafka]
    environment:
      KAFKA_BOOTSTRAP_SERVERS: kafka:9092

volumes:
  minio_data:
```

---

## Thứ tự triển khai MVP

```
1. docker-compose up zookeeper kafka          # Kafka trước
2. docker-compose up minio mongodb elasticsearch   # Storage layer
3. Tạo Kafka topics + MinIO buckets + ES index    # Setup
4. docker-compose up reddit-collector rss-collector # Bắt đầu ingest
5. spark-submit spark_jobs/stream_processor.py     # Chạy Spark job
6. docker-compose up kibana grafana                # Dashboard
7. Kiểm tra dữ liệu chạy xuyên suốt pipeline
```

---

## Checklist MVP hoàn thành

- [ ] Reddit Collector gửi dữ liệu vào `raw_posts` topic
- [ ] RSS Collector gửi dữ liệu vào `raw_posts` topic
- [ ] Spark đọc được từ Kafka và parse JSON đúng schema
- [ ] Deduplication hoạt động (không có bài trùng `id`)
- [ ] Watermark xử lý được late data
- [ ] Sentiment được gắn nhãn cho mỗi bài
- [ ] Trending topics tính được theo sliding window
- [ ] Parquet file được ghi vào MinIO bucket `clean-posts`
- [ ] Bài viết đã xử lý được lưu vào MongoDB collection `posts`
- [ ] Dữ liệu được đánh index vào Elasticsearch
- [ ] Kibana hiển thị được dashboard cơ bản
- [ ] Checkpoint hoạt động — restart Spark vẫn tiếp tục đúng offset

---

## Các thành phần KHÔNG làm trong MVP

- GraphFrames để phân tích đồ thị đồng xuất hiện topic
- Spike detection nâng cao
- Prometheus monitoring
- Kubernetes deployment
- Machine learning / NLP phức tạp
- Tối ưu hiệu năng Spark trên cluster lớn
