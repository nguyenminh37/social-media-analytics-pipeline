from functools import reduce


def split_valid_and_dlq_rows(raw_df, schema, required_fields: list[str], source_pipeline: str):
    from pyspark.sql.functions import (
        col,
        current_timestamp,
        from_json,
        length,
        lit,
        trim,
        when,
    )

    raw_value = col("value").cast("string")
    parsed_col = from_json(raw_value, schema)

    base_df = raw_df.select(
        col("topic").alias("source_topic"),
        col("partition").alias("source_partition"),
        col("offset").alias("source_offset"),
        col("timestamp").alias("kafka_timestamp"),
        raw_value.alias("raw_value"),
        parsed_col.alias("data"),
    )

    malformed_condition = (
        col("raw_value").isNull()
        | (length(trim(col("raw_value"))) == 0)
        | (~trim(col("raw_value")).rlike(r"^\{.*\}$"))
    )
    parse_error_condition = col("data").isNull() & (~malformed_condition)
    invalid_required_condition = col("data").isNotNull() & reduce(
        lambda acc, next_cond: acc | next_cond,
        (
            col(f"data.{field_name}").isNull()
            | (length(trim(col(f"data.{field_name}"))) == 0)
            for field_name in required_fields
        ),
    )

    classified_df = (
        base_df.withColumn(
            "error_type",
            when(malformed_condition, lit("malformed_payload"))
            .when(parse_error_condition, lit("schema_parse_error"))
            .when(invalid_required_condition, lit("invalid_required_fields")),
        )
        .withColumn(
            "error_message",
            when(
                col("error_type") == "malformed_payload",
                lit("Kafka value is empty or not a JSON object"),
            )
            .when(
                col("error_type") == "schema_parse_error",
                lit("Kafka value could not be parsed into the expected schema"),
            )
            .when(
                col("error_type") == "invalid_required_fields",
                lit(
                    "Missing or blank required fields: "
                    + ", ".join(required_fields)
                ),
            ),
        )
    )

    valid_df = classified_df.filter(col("error_type").isNull()).select("data.*")
    dlq_df = classified_df.filter(col("error_type").isNotNull()).select(
        lit(source_pipeline).alias("source_pipeline"),
        "source_topic",
        "source_partition",
        "source_offset",
        "kafka_timestamp",
        "error_type",
        "error_message",
        "raw_value",
        current_timestamp().alias("occurred_at"),
    )
    return valid_df, dlq_df


def build_dlq_sink_df(dlq_df):
    from pyspark.sql.functions import col, struct, to_json

    return dlq_df.select(
        col("source_offset").cast("string").alias("key"),
        to_json(struct(*dlq_df.columns)).alias("value"),
    )
