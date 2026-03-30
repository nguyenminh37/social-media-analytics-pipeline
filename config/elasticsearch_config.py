import os


ELASTICSEARCH_HOST = os.getenv("ELASTICSEARCH_HOST", "http://localhost:9200")
POSTS_INDEX = os.getenv("ELASTICSEARCH_POSTS_INDEX", "posts")
