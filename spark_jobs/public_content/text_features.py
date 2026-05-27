import re
from collections import Counter


VIETNAMESE_STOPWORDS = {
    "anh",
    "ban",
    "bao",
    "cac",
    "cach",
    "cho",
    "con",
    "cua",
    "dang",
    "day",
    "den",
    "duoc",
    "gio",
    "hai",
    "hay",
    "hon",
    "khi",
    "khong",
    "lai",
    "lam",
    "len",
    "mot",
    "nay",
    "neu",
    "nhieu",
    "nhung",
    "qua",
    "sau",
    "the",
    "theo",
    "thi",
    "tin",
    "toi",
    "trong",
    "tren",
    "truoc",
    "tu",
    "voi",
    "vua",
    "va",
    "ve",
    "vi",
    "viet",
    "nam",
}

def _ascii_fold(text: str) -> str:
    import unicodedata

    value = unicodedata.normalize("NFD", text)
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    return value.replace("đ", "d").replace("Đ", "D").lower()


def extract_keywords(text: str | None, limit: int = 8) -> list[str]:
    folded = _ascii_fold(text or "")
    tokens = re.findall(r"[a-z0-9]+", folded)
    candidates = [
        token
        for token in tokens
        if len(token) >= 3 and token not in VIETNAMESE_STOPWORDS and not token.isdigit()
    ]
    counts = Counter(candidates)
    return [token for token, _ in counts.most_common(limit)]
