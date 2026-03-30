from pyspark.sql import DataFrame
from pyspark.sql.functions import col, count, explode, length, split, window


def build_trending_keywords_df(enriched_df: DataFrame) -> DataFrame:
    keywords_df = (
        enriched_df.select(
            col("event_time"),
            explode(split(col("title"), r"\s+")).alias("keyword"),
        )
        .filter(length(col("keyword")) > 3)
    )

    return (
        keywords_df.groupBy(
            window(col("event_time"), "1 hour", "15 minutes"),
            col("keyword"),
        )
        .agg(count("*").alias("frequency"))
    )
