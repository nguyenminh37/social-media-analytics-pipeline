# Social Media Analytics - YouTube Architecture

Tài liệu này mô tả kiến trúc Kappa hiện tại của dự án sau khi chỉ giữ lại YouTube pipeline.

## Data Flow

```mermaid
graph TD
    Y0[YouTube Data API] -->|Producer| Y1(Kafka: raw_youtube_*)
    Y1 -->|Archive| A[raw_archiver -> MinIO raw parquet]
    Y1 -->|Consume| Y2[YouTube Spark Streaming]
    Y2 -->|Publish| Y3(Kafka: silver_youtube_* / youtube_aggregated_metrics)
    Y2 -->|Sink| M[(MongoDB youtube_*)]
    Y2 -->|Sink| E[(Elasticsearch youtube_*)]
    Y2 -->|Sink| P[(MinIO youtube parquet)]
    M --> S[serving_api]
    E --> K[Kibana / Grafana]
```

## Thành phần

- **Ingestion**: `collectors.youtube.producer` thu thập video trending, search results, comments và channel snapshots.
- **Message Broker**: Kafka tách ingest khỏi processing bằng các raw topics riêng cho video, comment, channel.
- **Stream Processing**: `spark_jobs/youtube/stream_processor.py` chuẩn hóa entity, gán sentiment, tính trending keywords và aggregated metrics.
- **Storage**:
  - MongoDB cho operational reads của `serving_api`
  - Elasticsearch cho search và dashboard
  - MinIO cho raw archive, parquet sinks và checkpoints
- **Serving**: `serving_api` chỉ expose read APIs cho dashboard/frontend YouTube.
