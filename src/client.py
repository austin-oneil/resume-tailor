"""Shared Anthropic client construction."""

import json
import os
import re
from datetime import datetime
from functools import lru_cache

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()


def today_str() -> str:
    """Current date, for grounding any 'years of experience' or 'Present'
    date-math reasoning — without this, the model has no reliable way to know
    what 'today' is and can miscalculate tenure against its training cutoff."""
    return datetime.now().strftime("%B %-d, %Y")


@lru_cache(maxsize=1)
def get_client() -> Anthropic:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise RuntimeError(
            "ANTHROPIC_API_KEY not set. Copy .env.example to .env and fill in your key."
        )
    return Anthropic(api_key=api_key)


def print_cache_usage(label: str, usage) -> None:
    """Prints token usage for a call, including cache write/read counts, so
    caching can be visually confirmed as it kicks in on the 2nd+ call."""
    created = getattr(usage, "cache_creation_input_tokens", 0) or 0
    read = getattr(usage, "cache_read_input_tokens", 0) or 0
    print(
        f"    [{label}] input={usage.input_tokens} "
        f"cache_write={created} cache_read={read} output={usage.output_tokens}"
    )


def _try_json_loads(s: str):
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return None


def _unwrap_json_string(value):
    """Despite a forced tool schema, models occasionally stuff an array field
    with a JSON-encoded string instead of the actual array (sometimes even
    re-wrapped in an object with the same key, sometimes prefixed with stray
    tag-like text such as '<parameter name="...">'), and that inner JSON is
    itself sometimes missing its final closing bracket(s) — apparent
    generation quirks when a model writes JSON as a string value rather than
    structured output. Try a few repairs rather than silently discarding
    otherwise-good data."""
    if not isinstance(value, str):
        return value

    candidates = [value]
    first_bracket_positions = [i for i in (value.find("["), value.find("{")) if i > 0]
    if first_bracket_positions:
        candidates.append(value[min(first_bracket_positions):])

    parsed = None
    for candidate in candidates:
        parsed = _try_json_loads(candidate)
        if parsed is None:
            for suffix in ("}", "]}", '"}', '"]}', "]"):
                parsed = _try_json_loads(candidate + suffix)
                if parsed is not None:
                    break
        if parsed is not None:
            break

    if parsed is None:
        return value
    if isinstance(parsed, dict):
        for inner in parsed.values():
            if isinstance(inner, list):
                return inner
        return value
    return parsed


_TAG_BLOCK_RE = re.compile(r"<(\w+)>(.*?)</\1>", re.DOTALL)


def _deep_flatten(value, _depth: int = 0) -> list:
    """Recursively pulls real leaf values (str or dict) out of a tool-use
    field that may be corrupted at any nesting depth: JSON encoded as a
    string, a dict wrapping the real list under some key, or — observed on a
    real hiring_manager run — a plain-string list item that is itself a
    blob of stray XML-tag-wrapped JSON (e.g. '<concerns>[...]</concerns>').
    Depth-capped as a safety valve against pathological input."""
    if _depth > 6:
        return [value] if isinstance(value, (str, dict)) else []

    if isinstance(value, dict):
        return [value]

    if isinstance(value, list):
        out: list = []
        for item in value:
            out.extend(_deep_flatten(item, _depth + 1))
        return out

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return []
        matches = _TAG_BLOCK_RE.findall(stripped)
        if matches:
            out = []
            for _, inner in matches:
                out.extend(_deep_flatten(inner, _depth + 1))
            return out
        parsed = _unwrap_json_string(stripped)
        if isinstance(parsed, str) and parsed == stripped:
            return [stripped]
        return _deep_flatten(parsed, _depth + 1)

    return []


def as_dict_list(value) -> list[dict]:
    """Coerces a tool-use field that's supposed to be a list of objects,
    recovering it from any of the corruption shapes _deep_flatten handles.
    Anything still malformed after that is dropped rather than crashing
    downstream code that assumes dicts."""
    return [item for item in _deep_flatten(value) if isinstance(item, dict)]


def as_str_list(value) -> list[str]:
    """Same recovery/coercion, for fields that should be a list of strings."""
    return [item for item in _deep_flatten(value) if isinstance(item, str)]
