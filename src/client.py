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


# Shared by any deterministic backstop that needs to check "does this LLM
# claim about missing/unsupported experience actually hold up against the
# full background document" — first built for supervisor.jd_coverage_backstop,
# then reused for fit_gate's disqualifying_requirements after a real, shipped
# error (2026-08-07): fit_gate (Haiku, 500-token budget) flagged "Required
# fluency in modern web platforms (e.g., Webflow)" as a hard disqualifier —
# blocking the application outright — even though background.md documents
# Webflow extensively (a TECH-STACK line and a full DEV subsection: "subject
# matter expert on a struggling Webflow site"). A cheap, fast model making a
# single high-stakes gating call needs a factual cross-check, not just a
# better prompt.
#
# Sentence-initial and common capitalized words that would otherwise pollute
# the capitalized-token extraction below (e.g. the "No" in "No experience
# with...", or "Demonstrated"/"Required" starting a sentence).
_CAPITALIZED_STOPWORDS = {
    "no", "not", "none", "nor", "the", "this", "that", "these", "those", "a", "an",
    "candidate", "candidates", "demonstrated", "demonstrable", "background",
    "experience", "experienced", "missing", "lacks", "lacking", "limited", "required",
    "preferred", "basic", "qualifications", "role", "position", "job", "jd",
    "nothing", "something", "everything", "anything", "someone", "everyone",
    "anyone", "here", "there", "while", "given", "note", "check",
    # Real-world false positives caught 2026-08-08 running fit_gate._debunk_missing
    # against an actual JD: these are technology-shaped-looking but too generic
    # (or, for "linkedin", contextually wrong) to count as corroborating evidence
    # on their own. "Public"/"Answer"/"Engine"/"Optimization" showed up as the
    # sole match debunking real gaps ("Public thought-leadership presence" was
    # cleared by a match on the word "Public" alone; "Answer Engine Optimization"
    # doesn't need "Answer"/"Engine"/"Optimization" individually since "AEO" itself
    # is still a valid distinct match when the doc genuinely has it). "Saas" showed
    # up matching a single unrelated mention of the word elsewhere in the document,
    # clearing a claim about owning a B2B SaaS site the candidate has never worked
    # on. "Linkedin" only ever appears in the document as the candidate's own
    # contact-info URL, which is never evidence of a "public thought-leadership
    # presence" claim — the token match was technically correct but the context is
    # never load-bearing for that kind of claim.
    # "Trust" is the same failure caught 2026-08-19: "Public Trust clearance" was
    # cleared by a match on "Trust" alone, which only appears in background.md in
    # ordinary prose ("building trust with the company") — nothing to do with a
    # security clearance.
    "public", "answer", "engine", "optimization", "saas", "linkedin", "trust",
    # Same failure class, caught the same day (2026-08-19) via
    # supervisor.jd_coverage_backstop on a real SMX run — three gaps got wrongly
    # flagged "possible oversight, verify by hand" on token matches that had
    # nothing to do with the actual claim: "Designer" matched the client name
    # "Jeff Harrie/Designer Smiles", not "SAC Analytics Designer" evidence;
    # "Federal"/"Higher" matched the candidate's own Work Authorization line
    # ("federal clearance", "Public Trust or higher"), not federal/higher-ed
    # client experience; "Local" matched "local-SEO services", not
    # state/local-government experience; "Action" matched the client name
    # "Vocation Action Network"; "Education" matched the resume's own EDUCATION
    # section heading, not industry experience; "US"/"Cloud" are too generic on
    # their own ("US" hits the common word "us"; "Cloud" alone doesn't specify a
    # platform) to count as corroborating evidence, same reasoning as "SaaS" above.
    "designer", "federal", "higher", "local", "action", "education", "us", "cloud",
    # "State" is the same failure — matches generic prose ("session state", "state
    # the specific window"), not state-government experience.
    "state",
}
# Proper-noun/technology-name-shaped tokens: a capitalized word, or an
# all-caps acronym, of 2+ characters. LLM-written gap/requirement
# descriptions reliably capitalize technology/skill names ("Webflow", "AWS
# Lambda", "SQL") while generic connective words in the same sentence stay
# lowercase — a much stronger signal than matching any lowercase word (an
# earlier, lowercase-word version of this false-positived on filler like
# "never"/"scale"/"data"/"demonstrated").
_PROPER_NOUN_RE = re.compile(r"\b[A-Z][A-Za-z0-9+.#]{1,}\b")


def find_technology_matches(text: str, full_document: str) -> list[str]:
    """Extracts capitalized/technology-shaped tokens from `text` and returns
    whichever ones actually appear (case-insensitive) in `full_document`.
    Empty list means no corroborating evidence was found — the caller
    decides what that means for its own claim.

    Matches on a-z0-9 word boundaries, not plain substring containment (bug
    found 2026-08-09 on a real run: a 2-letter acronym like "ML" or "CS"
    plain-`in`-matched inside unrelated words — "html", "css" — and falsely
    "corroborated" gaps the candidate didn't actually have evidence for).
    Punctuation in the token itself (Node.js, C++, C#) isn't treated as a
    boundary, so those still match correctly against their exact spelling."""
    candidates = {
        t for t in _PROPER_NOUN_RE.findall(text)
        if t.lower() not in _CAPITALIZED_STOPWORDS
    }
    full_lower = full_document.lower()
    matches = {
        t for t in candidates
        if re.search(rf"(?<![a-z0-9]){re.escape(t.lower())}(?![a-z0-9])", full_lower)
    }
    return sorted(matches, key=str.lower)
