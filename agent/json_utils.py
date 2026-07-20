import json
from typing import Any


def parse_json_object(text: str) -> dict[str, Any]:
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end < start:
        raise ValueError("Response contains no JSON object")

    value = json.loads(text[start : end + 1])

    if not isinstance(value, dict):
        raise ValueError("JSON response is not an object")

    return value
