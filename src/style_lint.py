"""Deterministic style checks that don't require an LLM call.

Catches mechanical, checkable AI-writing tells (em dashes, corporate/AI cliche
phrases) so they get fixed even if the model doesn't reliably follow the
prompt instruction on its own. Findings are treated as blocking, same as
integrity flags — a draft with a leftover em dash should never be "accepted".
"""

import re

EM_DASH = "—"

CLICHE_PHRASES = [
    "results-driven", "results driven", "detail-oriented", "detail oriented",
    "team player", "go-getter", "think outside the box", "synergy",
    "synergize", "leverage my", "leveraging my", "best-in-class",
    "cutting-edge", "paradigm shift", "seamlessly", "robust solution",
    "passionate about", "dynamic professional", "hardworking",
    "hard-working", "self-starter", "proven track record of being",
    "in today's fast-paced", "wide range of", "spearheaded the",
]

# Volunteering a missing qualification undermines the whole point of a resume/
# cover letter (put the best foot forward) even though every individual claim
# stays honest — not claiming a skill is fine, announcing its absence isn't.
# Caught deterministically since the model has repeatedly defaulted to this as
# its go-to "honest" way to address an unsupported JD requirement.
GAP_CONFESSION_PHRASES = [
    "i haven't", "i have not", "i don't have", "i do not have", "i lack",
    "i'm new to", "i am new to", "i've never", "i have never", "i can't yet",
    "i cannot yet", "no direct experience", "while i lack", "while i haven't",
    "admittedly, i", "i haven't yet", "i don't yet", "i do not yet",
    # Resume-voice / third-person confessions — observed as the model's
    # workaround once the first-person "I haven't..." forms above were caught.
    "new to ", "not yet production", "not production-scale",
    "comfortable picking up", "ready to own", "eager to learn",
    "ramp up on", "ramping up on", "limited experience",
    "less experience", "still building depth", "still developing",
    "where i'm still", "where i don't", "be direct about where",
    "areas i have", "haven't yet worked", "no concrete production",
    "aren't areas i", "transfers directly",
    # Real, shipped error (2026-08-07, ZeroTier + earlier USA Home Listings
    # letters): a third-person shape of the same confession — explaining WHY
    # a past evaluator passed on the candidate, citing a specific
    # quantifiable shortfall relative to other candidates. Root cause was a
    # background.md Calibration Note explicitly recommending this framing
    # for the Kharon anecdote (now fixed at the source too), but this stays
    # as a backstop in case the pattern resurfaces from elsewhere.
    "edged out", "didn't advance because", "did not advance because",
    "other finalists had more", "other candidates had more",
    "lost the final round", "lost out to candidates",
]

# Hedged skill claims read differently from an outright admission but do the
# same damage to a reviewer's confidence — they advertise the limit of the
# claim instead of stating the strongest accurate version of it. Regex, not a
# substring list, since these are common short phrases that need real
# boundaries to avoid false-triggering constantly.
HEDGED_CLAIM_PATTERNS = [
    r"\b(familiar|familiarity) with\b",
    r"\bworking knowledge\b",
    r"\bexposure to\b",
    r"\bplanning to\b",
    r"\bplan(?:ned)? to modernize\b",
    r"\bwould expect to pick (?:this|it|these) up\b",
]
_HEDGED_CLAIM_RE = re.compile("|".join(HEDGED_CLAIM_PATTERNS), re.IGNORECASE)


def lint(text: str, label: str) -> list[dict]:
    issues = []

    em_dash_count = text.count(EM_DASH)
    if em_dash_count:
        issues.append({
            "category": "AI-writing tell",
            "detail": (
                f"{label} uses {em_dash_count} em dash(es) ('—') — a well-known "
                "AI-generated-text signal that can hurt credibility with recruiters. "
                "Replace every instance with a comma, period, or parentheses."
            ),
            # Cosmetic, not an integrity failure — distinct from "high" checks
            # elsewhere that mean an actual honesty/fabrication problem (audit
            # v3 §3 Mechanism 2: both were "high" and competed equally for the
            # same repair pass, which is wrong).
            "severity": "medium",
        })

    lowered = text.lower()
    found = sorted({phrase for phrase in CLICHE_PHRASES if phrase in lowered})
    if found:
        issues.append({
            "category": "AI-writing tell",
            "detail": (
                f"{label} contains generic AI/corporate cliche phrase(s): "
                f"{', '.join(found)}. Replace with specific, concrete language "
                "grounded in the background doc."
            ),
            "severity": "medium",
        })

    confessions = sorted({phrase for phrase in GAP_CONFESSION_PHRASES if phrase in lowered})
    if confessions:
        issues.append({
            "category": "Gap disclosure",
            "detail": (
                f"{label} contains phrase(s) that volunteer a missing "
                f"qualification: {', '.join(confessions)}. Not claiming a "
                "skill is honest; announcing its absence undermines the "
                "letter's job of putting the candidate's best foot forward. "
                "Remove the admission and either strengthen a genuinely "
                "relevant adjacent bullet instead, or leave the requirement "
                "unaddressed entirely."
            ),
            # A genuine honesty problem (misrepresenting what the candidate
            # has/hasn't done), not a cosmetic tell — critical tier (audit v3
            # §3 Mechanism 2).
            "severity": "critical",
        })

    hedges = []
    for m in _HEDGED_CLAIM_RE.finditer(text):
        window = text[max(0, m.start() - 60):m.end() + 60]
        if re.search(r"\bIAM\b", window):
            continue  # Calibration Notes require this exact hedge for AWS IAM
        hedges.append(m.group(0))
    if hedges:
        issues.append({
            "category": "Hedged Skill Claim",
            "detail": (
                f"{label} contains hedged skill language: {', '.join(sorted(set(hedges)))}. "
                "This advertises the limit of the claim to a reviewer even though it reads "
                "less like an outright admission. Either state the strongest accurate version "
                "of what was actually done, or drop the item entirely — do not publish the hedge."
            ),
            "severity": "medium",
        })

    return issues


def lint_draft(draft) -> list[dict]:
    """draft is a src.draft_agent.Draft (resume + cover_letter)."""
    return lint(draft.resume, "Resume") + lint(draft.cover_letter, "Cover letter")
