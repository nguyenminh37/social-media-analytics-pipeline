import unittest

from collectors.historical_replay_producer import normalize_event
from schemas.post_schema import POST_FIELDS


class PipelineTests(unittest.TestCase):
    def test_normalize_event_contains_required_fields(self) -> None:
        event = normalize_event({"id": "1", "title": "hello"})
        self.assertTrue(set(POST_FIELDS).issubset(set(event)))
        self.assertEqual(event["id"], "1")
        self.assertEqual(event["title"], "hello")
        self.assertEqual(event["source"], "historical")


if __name__ == "__main__":
    unittest.main()
