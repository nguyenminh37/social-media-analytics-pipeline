import unittest

from ai_insights.hourly_trend_summarizer import build_prompt, build_template_briefing


class AiBriefingTests(unittest.TestCase):
    def test_build_template_briefing_uses_top_trend(self):
        context = {"trends": [{"keyword": "vang", "content_count": 7}]}

        briefing = build_template_briefing(context)

        self.assertIn("vang", briefing["headline"])
        self.assertEqual(briefing["watch_topics"], ["vang"])

    def test_build_prompt_requires_dataset_bound_output(self):
        prompt = build_prompt({"trends": []})

        self.assertIn("Chi dung du lieu JSON", prompt)
        self.assertIn("Tra ve JSON", prompt)


if __name__ == "__main__":
    unittest.main()
