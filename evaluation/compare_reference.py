"""Compare categorical machine findings with an approved reference manifest."""
from __future__ import annotations

from typing import Any


def evaluate(machine: list[dict[str, Any]], reference: list[dict[str, Any]]) -> dict[str, float]:
    key = lambda row: (str(row.get("ruleId") or row.get("rule")), str(row.get("pageId") or row.get("page")))
    predicted = {key(row) for row in machine if row.get("outcome") == "fail"}
    expected = {key(row) for row in reference if row.get("outcome") == "fail"}
    tp, fp, fn = len(predicted & expected), len(predicted - expected), len(expected - predicted)
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return {"precision": precision, "recall": recall, "f1": 2 * precision * recall / (precision + recall) if precision + recall else 0.0, "falsePositiveRate": fp / len(predicted) if predicted else 0.0, "falseNegativeRate": fn / len(expected) if expected else 0.0, "coverage": len(predicted) / len(expected) if expected else 0.0}
