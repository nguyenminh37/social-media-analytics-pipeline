import unittest

from ai_insights.sentiment_enricher import build_sentiment_prompt, build_template_sentiment


class SentimentEnricherTests(unittest.TestCase):
    def test_build_sentiment_prompt_requests_json_labels(self):
        prompt = build_sentiment_prompt(
            [{"content_id": "a1", "title": "Gia vang tang", "summary": "Thi truong soi dong"}]
        )

        self.assertIn("positive, neutral, negative", prompt)
        self.assertIn("valid JSON array", prompt)
        self.assertIn("a1", prompt)

    def test_build_template_sentiment_marks_records_neutral(self):
        predictions = build_template_sentiment([{"content_id": "a1"}])

        self.assertEqual(
            predictions,
            [{"content_id": "a1", "sentiment": "neutral", "score": 0.0}],
        )


if __name__ == "__main__":
    unittest.main()
