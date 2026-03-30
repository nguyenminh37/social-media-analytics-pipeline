from pyspark.sql.functions import udf
from pyspark.sql.types import StringType


def analyze_sentiment(text: str | None) -> str:
    from textblob import TextBlob

    if not text:
        return "neutral"
    polarity = TextBlob(str(text)).sentiment.polarity
    if polarity > 0.1:
        return "positive"
    if polarity < -0.1:
        return "negative"
    return "neutral"


sentiment_udf = udf(analyze_sentiment, StringType())
