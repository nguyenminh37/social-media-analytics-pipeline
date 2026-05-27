import unittest

from ai_insights.sentiment_enricher import build_sentiment_prompt


class SentimentEnricherTests(unittest.TestCase):
    def test_build_sentiment_prompt_requests_json_labels(self):
        prompt = build_sentiment_prompt(
            [{"content_id": "a1", "title": "Gia vang tang", "summary": "Thi truong soi dong"}]
        )

        self.assertIn("positive, neutral, negative", prompt)
        self.assertIn("valid JSON array", prompt)
        self.assertIn("a1", prompt)


if __name__ == "__main__":
    unittest.main()
