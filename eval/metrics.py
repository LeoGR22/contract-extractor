from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable
from difflib import SequenceMatcher
from typing import Any


def normalize(text: Any) -> str:
    if text is None:
        return ""
    text = unicodedata.normalize("NFKD", str(text))
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"\s+", " ", text.casefold()).strip()
    return text.strip(" .,;")


def text_equal(expected: Any, predicted: Any) -> bool:
    return normalize(expected) == normalize(predicted)


def digits_equal(expected: Any, predicted: Any) -> bool:
    def digits(v: Any) -> str:
        return re.sub(r"\D", "", str(v or ""))

    return digits(expected) == digits(predicted)


def number_equal(expected: Any, predicted: Any) -> bool:
    if expected is None or predicted is None:
        return expected is predicted
    try:
        return abs(float(expected) - float(predicted)) < 0.01
    except (TypeError, ValueError):
        return False


def exact(expected: Any, predicted: Any) -> bool:
    return expected == predicted


def similar(threshold: float) -> Callable[[Any, Any], bool]:
    def compare(expected: Any, predicted: Any) -> bool:
        return SequenceMatcher(None, normalize(expected), normalize(predicted)).ratio() >= threshold

    return compare


def index_equal(expected: Any, predicted: Any) -> bool:
    return normalize(expected).replace("-", "") == normalize(predicted).replace("-", "")


def contains_keywords(keywords: list[str], predicted: Any) -> bool:
    pred = normalize(predicted)
    return all(normalize(k) in pred for k in keywords)


RULES: dict[str, Callable[[Any, Any], bool]] = {
    "landlord.name": text_equal,
    "landlord.document": digits_equal,
    "tenant.name": text_equal,
    "tenant.document": digits_equal,
    "client.name": text_equal,
    "client.document": digits_equal,
    "provider.name": text_equal,
    "provider.document": digits_equal,
    "property_address": similar(0.9),
    "monthly_rent": number_equal,
    "due_day": exact,
    "start_date": exact,
    "term_months": exact,
    "adjustment_index": index_equal,
    "guarantee_type": exact,
    "termination_penalty_months": number_equal,
    "total_value": number_equal,
    "end_date": exact,
    "jurisdiction": text_equal,
}

KEYWORD_FIELDS = {"scope", "payment_terms"}


def flatten(data: dict | None, prefix: str = "") -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, value in (data or {}).items():
        if key.startswith("_"):
            continue
        path = f"{prefix}{key}"
        if isinstance(value, dict):
            out.update(flatten(value, f"{path}."))
        else:
            out[path] = value
    return out


def score_document(label: dict, prediction: dict | None) -> dict[str, bool]:
    expected = flatten(label)
    predicted = flatten(prediction)
    keywords = label.get("_keywords", {})

    results: dict[str, bool] = {}
    for field, exp_value in expected.items():
        pred_value = predicted.get(field)
        if field in KEYWORD_FIELDS:
            results[field] = contains_keywords(keywords.get(field, []), pred_value)
        else:
            results[field] = RULES.get(field, text_equal)(exp_value, pred_value)
    return results
