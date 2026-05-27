#!/usr/bin/env python3
"""Build a compact JSON sentiment lexicon from the public VnEmoLex XLSX file."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree as ET
from zipfile import ZipFile


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_ROOT / "config" / "external" / "VnEmoLex.xlsx"
DEFAULT_OUTPUT = PROJECT_ROOT / "config" / "external" / "vnemolex_sentiment.json"
XLSX_NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"


def ascii_fold(text: str) -> str:
    value = unicodedata.normalize("NFD", text)
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    return value.replace("đ", "d").replace("Đ", "D").lower()


def tokenize(text: str) -> list[str]:
    return re.findall(r"[^\W_]+", unicodedata.normalize("NFC", text).lower(), re.UNICODE)


def cell_column(ref: str) -> str:
    return "".join(ch for ch in ref if ch.isalpha())


def load_shared_strings(workbook: ZipFile) -> list[str]:
    root = ET.fromstring(workbook.read("xl/sharedStrings.xml"))
    values: list[str] = []
    for item in root.findall(f"{XLSX_NS}si"):
        values.append("".join(text.text or "" for text in item.iter(f"{XLSX_NS}t")))
    return values


def cell_value(cell: ET.Element, shared_strings: list[str]) -> str:
    value = cell.find(f"{XLSX_NS}v")
    if value is None or value.text is None:
        return ""
    if cell.get("t") == "s":
        return shared_strings[int(value.text)]
    return value.text


def iter_sheet_rows(path: Path) -> list[dict[str, str]]:
    with ZipFile(path) as workbook:
        shared_strings = load_shared_strings(workbook)
        root = ET.fromstring(workbook.read("xl/worksheets/sheet1.xml"))
        rows: list[dict[str, str]] = []
        for row in root.findall(f".//{XLSX_NS}row"):
            values = {
                cell_column(cell.get("r", "")): cell_value(cell, shared_strings)
                for cell in row.findall(f"{XLSX_NS}c")
            }
            rows.append(values)
        return rows


def int_value(value: str) -> int:
    try:
        return int(float(value))
    except ValueError:
        return 0


def build_lexicon(input_path: Path) -> dict:
    entries: dict[tuple[str, ...], dict] = {}
    source_terms: defaultdict[tuple[str, ...], set[str]] = defaultdict(set)
    rows = iter_sheet_rows(input_path)
    for row in rows[1:]:
        term = (row.get("B") or "").strip()
        tokens = tuple(ascii_fold(token) for token in tokenize(term))
        if not tokens:
            continue
        source_terms[tokens].add(term)
        positive = int_value(row.get("C", "0"))
        negative = int_value(row.get("D", "0"))
        if positive == 0 and negative == 0:
            continue
        current = entries.setdefault(
            tokens,
            {
                "tokens": list(tokens),
                "positive": 0,
                "negative": 0,
            },
        )
        current["positive"] = max(current["positive"], positive)
        current["negative"] = max(current["negative"], negative)

    normalized_entries = []
    for tokens, entry in sorted(entries.items(), key=lambda item: (" ".join(item[0]))):
        normalized_entries.append(
            {
                **entry,
                "terms": sorted(source_terms[tokens]),
            }
        )

    return {
        "metadata": {
            "name": "VnEmoLex",
            "source_url": "https://zenodo.org/records/801610",
            "doi": "10.5281/zenodo.801610",
            "license": "CC-BY-4.0",
            "description": "Vietnamese emotion lexicon mapped to positive/negative sentiment.",
        },
        "entries": normalized_entries,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    payload = build_lexicon(args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(payload['entries'])} VnEmoLex entries to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
