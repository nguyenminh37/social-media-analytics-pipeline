import unittest

from spark_jobs.public_content.text_features import extract_keywords


class TextFeatureTests(unittest.TestCase):
    def test_extract_keywords_removes_common_vietnamese_stopwords(self):
        keywords = extract_keywords(
            "Tin moi ve gia vang va chung khoan Viet Nam tang manh https://example.com/a.html"
        )

        self.assertIn("gia vang", keywords)
        self.assertIn("chung khoan", keywords)
        self.assertNotIn("gia", keywords)
        self.assertNotIn("tin", keywords)
        self.assertNotIn("viet", keywords)
        self.assertNotIn("https", keywords)
        self.assertNotIn("com", keywords)

    def test_extract_keywords_prefers_meaningful_vietnamese_phrases(self):
        keywords = extract_keywords(
            "Chay dua phat trien vac-xin Ebola, cap nhat moi nhat tu chau Phi"
        )

        self.assertIn("vac xin ebola", keywords)
        self.assertNotIn("moi", keywords)
        self.assertNotIn("nhat", keywords)


if __name__ == "__main__":
    unittest.main()
