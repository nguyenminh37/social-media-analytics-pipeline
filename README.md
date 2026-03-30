# Social Media Analytics Pipeline

## Kafka step 1

Project này đã được scaffold sẵn để chạy Kafka và đẩy tin RSS từ VnExpress vào topic `news-stream`.

### 1. Chạy Kafka bằng Docker

```bash
docker compose up -d
```

Lưu ý: project này pin `cp-kafka` và `cp-zookeeper` về bản `7.5.11` để chạy theo mô hình ZooKeeper đơn giản. Dùng `latest` hiện có thể lỗi vì Confluent 8.x mặc định chuyển sang KRaft.

### 2. Cài thư viện Python

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Chạy producer

```bash
python3 producer.py
```

Kỳ vọng:

```text
Sent: ...
Sent: ...
```

### 4. Test consumer

```bash
docker exec -it sma-kafka kafka-console-consumer \
  --bootstrap-server localhost:9092 \
  --topic news-stream \
  --from-beginning
```

Nếu thấy JSON article thì Kafka đang nhận data đúng.

## Biến môi trường hỗ trợ

- `KAFKA_BOOTSTRAP_SERVERS` mặc định `localhost:9092`
- `KAFKA_TOPIC` mặc định `news-stream`
- `RSS_URL` mặc định `https://vnexpress.net/rss/tin-moi-nhat.rss`
- `FETCH_INTERVAL_SECONDS` mặc định `10`
