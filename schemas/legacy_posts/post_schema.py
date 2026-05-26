from pyspark.sql.types import StringType, StructField, StructType


POST_FIELDS = [
    "id",
    "source",
    "title",
    "content",
    "url",
    "author",
    "published_at",
    "subreddit",
    "feed_name",
    "ingested_at",
]

POST_SCHEMA_DICT = {
    "id": str,
    "source": str,
    "title": str,
    "content": str,
    "url": str,
    "author": str,
    "published_at": str,
    "subreddit": str,
    "feed_name": str,
    "ingested_at": str,
}

POST_SPARK_SCHEMA = StructType(
    [StructField(field_name, StringType(), True) for field_name in POST_FIELDS]
)
