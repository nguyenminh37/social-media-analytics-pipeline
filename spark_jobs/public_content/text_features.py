import json
import os
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path


DEFAULT_FILTERS_PATH = (
    Path(__file__).resolve().parents[2] / "config" / "public_content_text_filters.json"
)


@lru_cache(maxsize=1)
def _load_text_filters() -> tuple[set[str], set[str]]:
    filters_path = Path(os.getenv("PUBLIC_CONTENT_TEXT_FILTERS_PATH", DEFAULT_FILTERS_PATH))
    with filters_path.open(encoding="utf-8") as file:
        payload = json.load(file)
    return set(payload.get("stopwords", [])), set(payload.get("weak_single_terms", []))


def _stopwords() -> set[str]:
    return _load_text_filters()[0]


def _weak_single_terms() -> set[str]:
    return _load_text_filters()[1]


def _strong_term_count(words: tuple[str, ...]) -> int:
    weak_terms = _weak_single_terms()
    return sum(1 for word in words if word not in weak_terms)


def _ascii_fold(text: str) -> str:
    import unicodedata

    value = unicodedata.normalize("NFD", text)
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    return value.replace("đ", "d").replace("Đ", "D").lower()


def _tokenize(text: str | None) -> list[str]:
    folded = _ascii_fold(text or "")
    folded = re.sub(r"https?://\S+|www\.\S+", " ", folded)
    return re.findall(r"[a-z0-9]+", folded)


def _is_content_token(token: str) -> bool:
    return len(token) >= 3 and token not in _stopwords() and not token.isdigit()


def _segments(tokens: list[str]) -> list[list[str]]:
    groups: list[list[str]] = []
    current: list[str] = []
    for token in tokens:
        if not _is_content_token(token):
            if current:
                groups.append(current)
                current = []
            continue
        current.append(token)
    if current:
        groups.append(current)
    return groups


def _is_good_phrase(words: tuple[str, ...]) -> bool:
    if len(words) < 2:
        return False
    if len(set(words)) != len(words):
        return False
    weak_terms = _weak_single_terms()
    if all(word in weak_terms for word in words):
        return False
    return _strong_term_count(words) > 0 and any(len(word) >= 4 for word in words)


def _contained_by_selected(phrase: str, selected: list[str]) -> bool:
    phrase_words = phrase.split()
    if len(phrase_words) <= 2:
        return False
    for existing in selected:
        existing_words = existing.split()
        if len(existing_words) < len(phrase_words):
            continue
        if phrase in " ".join(existing_words):
            return True
    return False


def extract_keywords(text: str | None, limit: int = 8) -> list[str]:
    tokens = _tokenize(text)
    phrase_counts: Counter[str] = Counter()

    for segment in _segments(tokens):
        max_size = min(3, len(segment))
        for size in range(max_size, 1, -1):
            for index in range(0, len(segment) - size + 1):
                words = tuple(segment[index : index + size])
                if _is_good_phrase(words):
                    phrase_counts[" ".join(words)] += (
                        size * size
                        + _strong_term_count(words) * 2
                        - (size - _strong_term_count(words))
                    )

    selected: list[str] = []
    for phrase, _ in sorted(
        phrase_counts.items(),
        key=lambda item: (-item[1], -len(item[0].split()), item[0]),
    ):
        if _contained_by_selected(phrase, selected):
            continue
        selected.append(phrase)
        if len(selected) >= limit:
            return selected

    single_counts = Counter(
        token
        for token in tokens
        if _is_content_token(token)
        and token not in _weak_single_terms()
        and len(token) >= 4
        and all(token not in phrase.split() for phrase in selected)
    )
    for token, _ in single_counts.most_common(limit - len(selected)):
        if token not in selected:
            selected.append(token)

    return selected[:limit]
