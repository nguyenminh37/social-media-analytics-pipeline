import pandas as pd
from pyspark.sql.functions import pandas_udf


@pandas_udf("string")
def sentiment_udf(texts: pd.Series) -> pd.Series:
    from textblob import TextBlob

    def analyze(text: str | None) -> str:
        if not text:
            return "neutral"
        polarity = TextBlob(str(text)).sentiment.polarity
        if polarity > 0.1:
            return "positive"
        if polarity < -0.1:
            return "negative"
        return "neutral"

    return texts.apply(analyze)
