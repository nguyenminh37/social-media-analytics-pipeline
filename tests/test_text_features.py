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

    def test_public_stopwords_do_not_break_accent_folded_topics(self):
        keywords = extract_keywords(
            "Vâng, giá vàng tăng mạnh trong lúc Thái Lan mở rộng hợp tác"
        )

        self.assertIn("gia vang", keywords)
        self.assertIn("thai lan", keywords)
        self.assertNotIn("vang", keywords)

    def test_context_phrases_are_canonicalized_to_protected_topics(self):
        keywords = extract_keywords(
            "Tong Bi thu tham chinh thuc tai Thai Lan. Thai Lan tong hop tin moi."
        )

        self.assertIn("thai lan", keywords)
        self.assertNotIn("tai thai", keywords)
        self.assertNotIn("tai thai lan", keywords)
        self.assertNotIn("thai lan tong", keywords)


if __name__ == "__main__":
    unittest.main()
