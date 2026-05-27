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
def _load_text_filters() -> tuple[
    set[str],
    set[tuple[str, ...]],
    set[str],
    set[str],
    set[tuple[str, ...]],
    set[str],
]:
    filters_path = Path(
        os.getenv("PUBLIC_CONTENT_TEXT_FILTERS_PATH", DEFAULT_FILTERS_PATH)
    )
    with filters_path.open(encoding="utf-8") as file:
        payload = json.load(file)

    public_stopword_terms: set[str] = set()
    public_stopword_phrases: set[tuple[str, ...]] = set()
    public_stopwords_config = payload.get("public_stopwords", {})
    public_stopwords_path = public_stopwords_config.get("path")
    if public_stopwords_path:
        public_path = Path(public_stopwords_path)
        if not public_path.is_absolute():
            public_path = filters_path.parent / public_path
        with public_path.open(encoding="utf-8") as file:
            for line in file:
                tokens = tuple(_tokenize(line.strip()))
                if not tokens:
                    continue
                if len(tokens) == 1:
                    public_stopword_terms.add(tokens[0])
                else:
                    public_stopword_phrases.add(tokens)

    supplemental_values = payload.get(
        "supplemental_stopwords", payload.get("stopwords", [])
    )
    supplemental_stopwords = {
        _ascii_fold(token)
        for value in supplemental_values
        for token in _tokenize(value)
    }
    weak_single_terms = {
        _ascii_fold(token)
        for value in payload.get("weak_single_terms", [])
        for token in _tokenize(value)
    }
    protected_phrases = {
        tuple(_ascii_fold(token) for token in _tokenize(value))
        for value in payload.get("protected_phrases", [])
    }
    protected_phrases.discard(())
    phrase_context_terms = {
        _ascii_fold(token)
        for value in payload.get("phrase_context_terms", [])
        for token in _tokenize(value)
    }
    return (
        public_stopword_terms,
        public_stopword_phrases,
        supplemental_stopwords,
        weak_single_terms,
        protected_phrases,
        phrase_context_terms,
    )


def _public_stopword_terms() -> set[str]:
    return _load_text_filters()[0]


def _public_stopword_phrases() -> set[tuple[str, ...]]:
    return _load_text_filters()[1]


def _supplemental_stopwords() -> set[str]:
    return _load_text_filters()[2]


def _weak_single_terms() -> set[str]:
    return _load_text_filters()[3]


def _protected_phrases() -> set[tuple[str, ...]]:
    return _load_text_filters()[4]


def _phrase_context_terms() -> set[str]:
    return _load_text_filters()[5]


def _ascii_fold(text: str) -> str:
    import unicodedata

    value = unicodedata.normalize("NFD", text)
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    return value.replace("đ", "d").replace("Đ", "D").lower()


def _normalize_text(text: str | None) -> str:
    import unicodedata

    return unicodedata.normalize("NFC", text or "").lower()


def _tokenize(text: str | None) -> list[str]:
    normalized = _normalize_text(text)
    normalized = re.sub(r"https?://\S+|www\.\S+", " ", normalized)
    return re.findall(r"[^\W_]+", normalized, flags=re.UNICODE)


def _folded_words(words: tuple[str, ...]) -> tuple[str, ...]:
    return tuple(_ascii_fold(word) for word in words)


def _strong_term_count(words: tuple[str, ...]) -> int:
    weak_terms = _weak_single_terms()
    return sum(1 for word in _folded_words(words) if word not in weak_terms)


def _canonical_phrase(words: tuple[str, ...]) -> tuple[str, ...]:
    folded_words = _folded_words(words)
    if folded_words in _protected_phrases():
        return folded_words

    context_terms = _phrase_context_terms()
    for protected_phrase in sorted(_protected_phrases(), key=len, reverse=True):
        size = len(protected_phrase)
        if size >= len(folded_words):
            continue
        for index in range(0, len(folded_words) - size + 1):
            if tuple(folded_words[index : index + size]) != protected_phrase:
                continue
            surrounding_terms = folded_words[:index] + folded_words[index + size :]
            if surrounding_terms and all(term in context_terms for term in surrounding_terms):
                return protected_phrase

    return folded_words


def _is_content_token(token: str) -> bool:
    folded = _ascii_fold(token)
    return (
        len(folded) >= 3
        and token not in _public_stopword_terms()
        and folded not in _supplemental_stopwords()
        and not folded.isdigit()
    )


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
    if words in _public_stopword_phrases():
        return False
    folded_words = _folded_words(words)
    if len(set(folded_words)) != len(folded_words):
        return False
    weak_terms = _weak_single_terms()
    if all(word in weak_terms for word in folded_words):
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


def _conflicts_with_selected_protected_phrase(phrase: str, selected: list[str]) -> bool:
    phrase_words = set(phrase.split())
    for existing in selected:
        existing_words = tuple(existing.split())
        if existing_words not in _protected_phrases():
            continue
        if phrase != existing and phrase_words.intersection(existing_words):
            return True
    return False


def extract_keywords(text: str | None, limit: int = 8) -> list[str]:
    tokens = _tokenize(text)
    phrase_counts: Counter[str] = Counter()
    folded_tokens = [_ascii_fold(token) for token in tokens]

    for protected_phrase in _protected_phrases():
        size = len(protected_phrase)
        if size < 2:
            continue
        for index in range(0, len(folded_tokens) - size + 1):
            if tuple(folded_tokens[index : index + size]) == protected_phrase:
                phrase_counts[" ".join(protected_phrase)] += size * size + size * 3

    for segment in _segments(tokens):
        max_size = min(3, len(segment))
        for size in range(max_size, 1, -1):
            for index in range(0, len(segment) - size + 1):
                words = tuple(segment[index : index + size])
                if _is_good_phrase(words):
                    phrase_counts[" ".join(_canonical_phrase(words))] += (
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
        if _conflicts_with_selected_protected_phrase(phrase, selected):
            continue
        selected.append(phrase)
        if len(selected) >= limit:
            return selected

    single_counts = Counter(
        _ascii_fold(token)
        for token in tokens
        if _is_content_token(token)
        and _ascii_fold(token) not in _weak_single_terms()
        and len(_ascii_fold(token)) >= 4
        and all(_ascii_fold(token) not in phrase.split() for phrase in selected)
    )
    for token, _ in single_counts.most_common(limit - len(selected)):
        if token not in selected:
            selected.append(token)

    return selected[:limit]
