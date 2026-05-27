import unittest

from ai_insights.sentiment_enricher import (
    build_sentiment_prompt,
    build_template_sentiment,
    build_vnemolex_sentiment,
    score_vnemolex_sentiment,
)


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
            [
                {
                    "content_id": "a1",
                    "sentiment": "neutral",
                    "score": 0.0,
                    "model": "neutral_fallback",
                }
            ],
        )

    def test_score_vnemolex_sentiment_uses_public_lexicon(self):
        self.assertEqual(
            score_vnemolex_sentiment("Dự án thành công và tạo danh tiếng tốt")[0],
            "positive",
        )
        self.assertEqual(
            score_vnemolex_sentiment("Dịch bệnh và thất bại gây thiệt hại")[0],
            "negative",
        )

    def test_build_vnemolex_sentiment_marks_records_with_model(self):
        predictions = build_vnemolex_sentiment(
            [{"content_id": "a1", "title": "Dự án thành công", "summary": ""}]
        )

        self.assertEqual(predictions[0]["content_id"], "a1")
        self.assertEqual(predictions[0]["sentiment"], "positive")
        self.assertEqual(predictions[0]["model"], "vnemolex-cc-by-4.0")


if __name__ == "__main__":
    unittest.main()
