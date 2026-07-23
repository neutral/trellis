"""The sole raw-JSON parser boundary for the Trellis audit."""

from __future__ import annotations

import json
import math

from .models import FrozenJson, freeze_json


def _unique_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON object key")
        result[key] = value
    return result


def _reject_nonstandard_number(_value: str) -> None:
    raise ValueError("non-standard JSON number")


def _finite_float(value: str) -> float:
    parsed = float(value)
    if not math.isfinite(parsed):
        raise ValueError("non-finite JSON number")
    return parsed


def parse_json(content: str) -> FrozenJson:
    """Parse untrusted JSON once, then recursively freeze the result."""
    parsed = json.loads(
        content,
        object_pairs_hook=_unique_object,
        parse_constant=_reject_nonstandard_number,
        parse_float=_finite_float,
    )
    return freeze_json(parsed)
