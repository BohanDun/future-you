"""Deterministic checks for model-written simulation explanations."""

import re

from pydantic import BaseModel

_NUMBER = re.compile(r"(?<![\w.])[-+]?\$?\s*([0-9][\d,]*(?:\.\d+)?)")


def _numbers(text: str) -> list[float]:
    return [float(value.replace(",", "")) for value in _NUMBER.findall(text)]


def explanation_is_grounded(
    explanation: str,
    *sources: BaseModel,
) -> bool:
    """Reject numeric claims that do not occur in trusted calculation data."""

    allowed: list[float] = []
    for source in sources:
        allowed.extend(_numbers(source.model_dump_json()))
    return all(
        any(abs(claim - value) <= 0.02 for value in allowed)
        for claim in _numbers(explanation)
    )
