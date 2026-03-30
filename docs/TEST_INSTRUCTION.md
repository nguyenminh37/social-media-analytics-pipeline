Demo 1: chứng minh ingest chạy
chạy reddit_producer.py hoặc rss_producer.py
cho thấy dữ liệu mới đang được đẩy vào Kafka
mở Kafka UI hoặc log producer để thấy message vào topic raw_posts

Tài liệu của bạn xác định bước đầu là collector lấy dữ liệu từ Reddit/RSS rồi gửi Kafka.

Demo 2: chứng minh Spark Streaming xử lý thật
chạy Spark job
show log Spark đang đọc từ Kafka
show dữ liệu sau parse/clean/dedup
nói rõ có event_time, watermark, sentiment, keywords/topics

Đây là lõi đề tài vì Spark Structured Streaming là tầng xử lý duy nhất trong kiến trúc Kappa.

Demo 3: chứng minh dữ liệu được ghi ra đúng nơi
MinIO: show file Parquet xuất hiện trong raw/, processed/, hoặc curated/
MongoDB: query vài document processed
Elasticsearch: search thử một keyword

Tài liệu cũng chia rõ vai trò lưu trữ: MinIO/HDFS cho Parquet, MongoDB cho processed docs/metrics, Elasticsearch cho full-text search.

Demo 4: chứng minh có kết quả nghiệp vụ

Bạn nên show ít nhất 3 kết quả:

số bài viết theo thời gian
sentiment distribution
top trending topics

Đây chính là 3 thứ MVP yêu cầu cho dashboard cơ bản.

Demo 5: chứng minh tinh thần Kappa bằng replay

Đây là phần ăn điểm:

lấy một file lịch sử
chạy replay_producer.py
bơm lại vào Kafka
Spark job cũ vẫn xử lý
dashboard / metrics thay đổi theo replay

Tài liệu nhấn mạnh đây là phần rất quan trọng để chứng minh Kappa: dữ liệu lịch sử không đi qua batch pipeline riêng mà replay lại vào cùng pipeline streaming