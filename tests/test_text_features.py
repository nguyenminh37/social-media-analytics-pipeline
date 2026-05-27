import unittest

from spark_jobs.public_content.text_features import extract_keywords


class TextFeatureTests(unittest.TestCase):
    def test_extract_keywords_removes_common_vietnamese_stopwords(self):
        keywords = extract_keywords(
            "Tin moi ve gia vang va chung khoan Viet Nam tang manh https://example.com/a.html"
        )

        self.assertIn("gia", keywords)
        self.assertIn("vang", keywords)
        self.assertIn("chung", keywords)
        self.assertNotIn("tin", keywords)
        self.assertNotIn("viet", keywords)
        self.assertNotIn("https", keywords)
        self.assertNotIn("com", keywords)


if __name__ == "__main__":
    unittest.main()
