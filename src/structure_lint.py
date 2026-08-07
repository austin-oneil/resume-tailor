"""Deterministic structural checks for rules the LLM keeps missing on the
first pass despite being stated in the prompts (the Prospecta discipline
floor, stale credential language, heading/contact formatting, Kharon leaking
into the resume, and length limits). Same blocking treatment as
style_lint.py — findings here feed into the same revision loop.
"""

import re

_SEO_VOCAB_RE = re.compile(
    r"\b(SEO|keyword|visibility|crawl|indexation|AEO|AIO|technical audit|"
    r"conversion path|Core Web Vitals)\b",
    re.IGNORECASE,
)
# Requires an actual account-management activity, not the bare noun "client" —
# nearly every bullet on an agency resume contains "client," so that alone
# let dev-only bullets pass this check with zero real protection (verified
# against real runs: "coordinating with a dev team for a client" matched).
_ACCOUNT_VOCAB_RE = re.compile(
    r"\b(account executive|client conference|monthly client|"
    r"stakeholder management|point of contact|funnel diagnosis|"
    r"promoted to account|client-facing)\b",
    re.IGNORECASE,
)
# Scoped to the degree line only (see _check_stale_credentials) — matching
# anywhere in a 200-char window previously caught the AWS cert's legitimate
# "(in progress)" sitting on the adjacent certifications line, which fired on
# every single resume regardless of actual content. Never scope this loosely.
_STALE_CREDENTIAL_RE = re.compile(
    r"(currently completing|working toward (a|my)? ?BS|pursuing a (BS|Bachelor)|"
    r"in progress|in-progress|expected \d{4}|anticipated)",
    re.IGNORECASE,
)
# Real, shipped error (2026-08-06): Jeff Gray, DDS is 100% a Prospecta client
# (he appears in the [DEV] and [SALES-TECH] tagged sections, but both are
# Prospecta-context sections — tags describe discipline, not employer) and
# got placed under the Tangent Apps umbrella entry on a real generated
# resume anyway. Prompt-only attribution rules already existed and were
# ignored; this is a deterministic backstop, same principle as every other
# check in this file. Keep this list in sync with the master
# employer-attribution Calibration Note in background.md.
_PROSPECTA_ONLY_CLIENTS = [
    "jeff gray", "blake cameron", "stephen dankworth", "chris hammond",
    "perry kest", "jeff harrie", "robert mcculla", "eleanor endres",
    "stoneridge", "travis b. adams", "future of dentistry", "robbie schaack",
    "beveridge dental", "nammy patel", "elite dental aesthetics",
    "almeida & bell", "allan acton", "allison lesko",
    "center for dental anesthesia", "harris dental", "j. bryan mclaughlin",
    "ira handschuh", "karen williamson", "okc smiles", "priority dental",
    "bill dorfman", "coleman & dastrup", "clint blackwood", "nima massoomi",
    "yuma dentist", "david rice", "geren & mady", "stephanie teichmiller",
    "koch aesthetics", "gustafsen", "aspen ridge dental", "dennis wells",
    "kevin bass", "30a smiles",
]
_SECTION_HEADERS = ["Summary", "Core Skills", "Professional Experience", "Education & Certifications"]
_BACKTICK_RE = re.compile(r"`[^`\n]+`")
# Bullets phrased as a contrast against a hypothetical lesser version of
# themselves ("...not a tutorial project") read as defensive/taunting rather
# than confident. Observed reintroduced by the model even after a prompt-only
# ban (Calibration Note) — needs a deterministic backstop, same pattern as
# GAP_CONFESSION_PHRASES in style_lint.py.
_CONTRAST_TONE_RE = re.compile(
    r"\bnot (a|just a|merely a)? ?(demo|tutorial|toy|prototype|proof[- ]of[- ]concept|"
    r"side project|hobby project|sample|exercise)\b"
    r"|\bunlike a (toy|demo|tutorial)\b"
    r"|\brather than a (demo|tutorial|toy|proof[- ]of[- ]concept)\b",
    re.IGNORECASE,
)

COVER_LETTER_WORD_LIMIT = 400
RESUME_WORD_PRECHECK_LIMIT = 520


def _word_count(text: str) -> int:
    return len(text.split())


def _check_prospecta_floor(resume: str) -> list[dict]:
    """Presence floor only, not position. Ordering used to be enforced by
    only checking bullets[:3] (per Calibration Note 362's original 'SEO and
    AE bullets must lead' rule), but across 9 independent hiring-manager
    reviews on dev-family JDs, 0 objected to missing SEO/AE presence while 9
    objected to the engineering narrative being buried under SEO framing.
    Note 362 was revised to require presence without dictating position for
    dev-family JDs — check the whole entry, not just the top."""
    issues = []
    m = re.search(r"\*\*Prospecta Marketing\*\*(.*?)(?=\n\*\*[A-Z]|\Z)", resume, re.DOTALL)
    if not m:
        return issues  # not this role family's resume, or a structural miss caught elsewhere
    block = m.group(1)
    bullets = [b for b in block.splitlines() if b.strip().startswith(("- ", "* "))]
    if len(bullets) < 3:
        issues.append({
            "category": "Structure - Prospecta Floor",
            "detail": (
                f"Prospecta entry has only {len(bullets)} bullet(s); the per-employer "
                "floor requires at least one real SEO bullet and one real Account "
                "Executive/client bullet somewhere in the entry (not necessarily first)."
            ),
            # A hard, non-negotiable floor per background.md's Calibration
            # Notes, not a soft style preference — critical tier, same as
            # other non-negotiable-floor/integrity checks (audit v3 §3
            # Mechanism 2).
            "severity": "critical",
        })
        return issues
    has_seo = any(_SEO_VOCAB_RE.search(b) for b in bullets)
    has_account = any(_ACCOUNT_VOCAB_RE.search(b) for b in bullets)
    if not has_seo:
        issues.append({
            "category": "Structure - Prospecta Floor",
            "detail": "No SEO/technical-SEO bullet found anywhere in the Prospecta entry.",
            "severity": "critical",
        })
    if not has_account:
        issues.append({
            "category": "Structure - Prospecta Floor",
            "detail": "No Account Executive/client-relationship bullet found anywhere in the Prospecta entry.",
            "severity": "critical",
        })
    return issues


def _check_employer_attribution(resume: str) -> list[dict]:
    """A Prospecta-only client (see the master list in background.md's
    Calibration Notes) was placed under the Tangent Apps umbrella entry on a
    real shipped resume — the model conflated which tagged section a client's
    supporting detail lives in with which employer they actually belong to.
    This misrepresents which company real work was performed for, which is
    an integrity problem. Deterministic backstop, same principle as every
    other check here: a prompt-only attribution rule already existed and was
    ignored."""
    m = re.search(r"\*\*Tangent Apps[^*]*\*\*(.*?)(?=\n### |\Z)", resume, re.DOTALL)
    if not m:
        return []
    block_lower = m.group(1).lower()
    found = [name for name in _PROSPECTA_ONLY_CLIENTS if name in block_lower]
    if not found:
        return []
    return [{
        "category": "Integrity - Employer Attribution",
        "detail": (
            f"Prospecta client(s) found under the Tangent Apps entry: {', '.join(found)}. "
            "These are real Prospecta Marketing clients, not Tangent Apps freelance "
            "engagements — misattributing which company the work was performed for is "
            "an integrity problem, not a formatting one. Move this content into the "
            "Prospecta entry (or drop it if not needed for this JD), never leave it "
            "under Tangent Apps."
        ),
        # Misstates which company real work was performed for — critical
        # tier, not merely "high" alongside cosmetic tells (audit v3 §3
        # Mechanism 2).
        "severity": "critical",
    }]


def _check_stale_credentials(resume: str, background_subset: str) -> list[dict]:
    if "graduated" not in background_subset.lower():
        return []
    for line in resume.splitlines():
        # Only the line actually naming the degree — a certifications line
        # legitimately carries "(in progress)" for the AWS cert and must
        # never trip this (this was the exact bug: a 200-char window caught
        # the cert line from the adjacent degree line and fired on every
        # single resume regardless of content).
        if not re.search(r"bachelor|b\.?s\.?,|computer science", line, re.IGNORECASE):
            continue
        if re.search(r"certification", line, re.IGNORECASE):
            continue
        m = _STALE_CREDENTIAL_RE.search(line)
        if m:
            return [{
                "category": "Stale Credential Language",
                "detail": (
                    f"Degree line uses in-progress-sounding phrasing ('{m.group(0)}'), "
                    "but the background doc says the degree is already graduated. Use "
                    "the actual completion year, not present-tense/in-progress language."
                ),
                "severity": "medium",
            }]
    return []


_DEGREE_PAREN_RE = re.compile(r"\(([^)]*)\)")


def _check_degree_line_editorializing(resume: str) -> list[dict]:
    """Real, shipped error (2026-08-06, Coursera application): the model
    appended an unrequested parenthetical to the degree line rationalizing
    why the degree is relevant ('(technical foundation supporting hands-on
    schema markup...)'). The prompt already specified the exact format with
    an example and the model still freelanced commentary onto it — same
    prompt-rule-ignored pattern as every other check in this file.

    Scoped to sentence-length parentheticals only (5+ words) — a bare year
    like '(2026)' or a short date like '(graduated March 2026)' is a
    different, narrower formatting issue already covered by
    _check_stale_credentials, not the editorializing this check targets.
    Also scoped to the Education & Certifications section only — an earlier
    version matched any line mentioning "Computer Science" anywhere in the
    resume, which caught an unrelated parenthetical sitting elsewhere in the
    same run-on Summary paragraph on a real resume (false positive)."""
    edu_match = re.search(r"### Education[^\n]*\n(.*?)(?=\n### |\Z)", resume, re.DOTALL)
    if not edu_match:
        return []
    for line in edu_match.group(1).splitlines():
        if not re.search(r"bachelor|b\.?s\.?,|computer science", line, re.IGNORECASE):
            continue
        if re.search(r"certification", line, re.IGNORECASE):
            continue
        for m in _DEGREE_PAREN_RE.finditer(line):
            if len(m.group(1).split()) >= 5:
                return [{
                    "category": "Structure - Degree Line",
                    "detail": (
                        f"Degree line has a sentence-length parenthetical: {line.strip()!r}. "
                        "The degree line must be institution, degree, and year only — no "
                        "editorializing about why the degree is relevant. Remove the "
                        "parenthetical entirely, don't move it elsewhere."
                    ),
                    "severity": "medium",
                }]
    return []


def _check_heading_contract(resume: str) -> list[dict]:
    issues = []
    name_lines = [l for l in resume.splitlines() if l.startswith("## ") and not l.startswith("### ")]
    if len(name_lines) != 1:
        issues.append({
            "category": "Structure - Heading Contract",
            "detail": f"Expected exactly one '## ' name line, found {len(name_lines)}.",
            "severity": "medium",
        })
    lowered = resume.lower()
    for header in _SECTION_HEADERS:
        if f"### {header.lower()}" not in lowered:
            issues.append({
                "category": "Structure - Heading Contract",
                "detail": f"Expected section header '### {header}' not found (exact spelling/casing may be off).",
                "severity": "medium",
            })
    return issues


def _check_no_backticks(text: str, label: str = "Resume") -> list[dict]:
    """Real, shipped error (2026-08-06, USA Home Listings cover letter): this
    check only ever ran against the resume, so `dbDelta()`/`wp_ajax_*`/
    `$wpdb->prepare()` — the exact three terms draft_agent.py's own
    SYSTEM_INSTRUCTIONS use as the textbook example of what NOT to write —
    shipped straight into a cover letter completely unchecked. The rule was
    always meant to apply to both documents; only the resume ever had a
    backstop."""
    matches = _BACKTICK_RE.findall(text)
    if not matches:
        return []
    return [{
        "category": "Over-Specificity - Backtick-Wrapped Terms",
        "detail": (
            f"{label} contains backtick-wrapped implementation detail: {', '.join(matches[:6])}"
            f"{'...' if len(matches) > 6 else ''}. Per house style, default to the general "
            "technology name (e.g. 'Next.js') rather than specific function/hook/API names — "
            "these read as copy-pasted from the reference doc, not a resume or cover letter. "
            "Remove the backtick-wrapped detail entirely unless the JD itself names that "
            "exact term."
        ),
        "severity": "medium",
    }]


def _check_contrast_tone(text: str, label: str) -> list[dict]:
    m = _CONTRAST_TONE_RE.search(text)
    if not m:
        return []
    return [{
        "category": "Tone - Contrast Framing",
        "detail": (
            f"{label} phrases a claim as a contrast against a hypothetical lesser version "
            f"of itself ('{m.group(0)}'), which reads as defensive or as taunting a doubt "
            "the reader hasn't voiced. State the real thing plainly instead — e.g. 'live in "
            "production, used daily' carries the same information without the tone problem."
        ),
        "severity": "high",
    }]


def _check_differentiator_defaults(resume: str) -> list[dict]:
    lowered = resume.lower()
    missing = []
    if "dnvr" not in lowered and "phnx" not in lowered:
        missing.append("DNVR/PHNX (48-hour AWS launch crisis)")
    if "lacroix" not in lowered and "drill house" not in lowered:
        missing.append("Lacroix Hockey / Drill House Sports Center")
    if not missing:
        return []
    return [{
        "category": "Structure - Differentiator Default",
        "detail": (
            f"Missing from the Tangent Apps entry: {', '.join(missing)}. Calibration Notes "
            "mark these as default-included across nearly all resumes — their value is "
            "adaptability and client communication under pressure, not technical relevance, "
            "so JD-relevance and quantification are the wrong reasons to cut them. Compress "
            "to one line before removing entirely."
        ),
        "severity": "low",
    }]


def _check_contact_line(resume: str) -> list[dict]:
    lines = resume.splitlines()
    for line in lines[:6]:
        if "Email:" in line and ("Phone:" in line or "LinkedIn:" in line):
            return []
    return [{
        "category": "Structure - Contact Header",
        "detail": "No single header line found containing 'Email:' plus 'Phone:' or 'LinkedIn:' — check the contact line wasn't split across multiple lines.",
        "severity": "low",
    }]


def _check_kharon_containment(resume: str) -> list[dict]:
    if "kharon" in resume.lower():
        return [{
            "category": "Integrity - Kharon Containment",
            "detail": "The word 'Kharon' appears in the RESUME. Kharon is a take-home interview exercise, not employment, and must never appear in the resume — it's cover-letter-only material.",
            # Misrepresents a take-home exercise as employment — critical
            # tier (audit v3 §3 Mechanism 2).
            "severity": "critical",
        }]
    return []


def _check_cover_letter_salutation_closing(cover_letter: str) -> list[dict]:
    """House style, confirmed 2026-08-06: every cover letter opens with
    'Dear [Company] Team,' and closes with a fixed 4-line sign-off. Backed by
    a lint check on day one rather than waiting for it to be skipped, per the
    350/400-word-cap precedent (a prompt rule alone went unfollowed 7/10 times)."""
    issues = []
    stripped = cover_letter.strip()
    first_line = stripped.splitlines()[0].strip() if stripped else ""
    if not re.match(r"^Dear .+ Team,\s*$", first_line):
        issues.append({
            "category": "Structure - Cover Letter Salutation",
            "detail": f"Cover letter must open with 'Dear [Company] Team,' on its own line. Found: {first_line!r}",
            "severity": "medium",
        })
    tail = "\n".join(stripped.splitlines()[-5:])
    if "Best Regards" not in tail or "austinroneil@gmail.com" not in tail or "335-5761" not in tail:
        issues.append({
            "category": "Structure - Cover Letter Closing",
            "detail": "Cover letter must close with exactly: 'Best Regards,' / 'Austin O'Neil' / 'austinroneil@gmail.com' / '(303) 335-5761', each on its own line.",
            "severity": "medium",
        })
    return issues


def _check_cover_letter_length(cover_letter: str) -> list[dict]:
    """Advisory only (low severity) — a handful of words over target is not
    worth blocking acceptance or triggering a revision pass over. Only flag
    it loudly (medium) once it's meaningfully over, not technically over."""
    words = _word_count(cover_letter)
    if words > COVER_LETTER_WORD_LIMIT + 50:
        return [{
            "category": "Length - Cover Letter",
            "detail": f"Cover letter is {words} words, well over the {COVER_LETTER_WORD_LIMIT}-word target. Tighten it.",
            "severity": "medium",
        }]
    if words > COVER_LETTER_WORD_LIMIT:
        return [{
            "category": "Length - Cover Letter",
            "detail": f"Cover letter is {words} words, slightly over the {COVER_LETTER_WORD_LIMIT}-word target. Not worth a revision pass over a small overage.",
            "severity": "low",
        }]
    return []


def _check_resume_length_precheck(resume: str) -> list[dict]:
    words = _word_count(resume)
    if words > RESUME_WORD_PRECHECK_LIMIT:
        return [{
            "category": "Length - Resume Precheck",
            "detail": (
                f"Resume is {words} words. Empirically, one-page renders have stayed under "
                f"~{RESUME_WORD_PRECHECK_LIMIT} words and runs over that have needed shortening "
                "passes after rendering. Consider tightening now to save a shortening round-trip."
            ),
            "severity": "low",
        }]
    return []


def lint_draft(draft, background_subset: str = "") -> list[dict]:
    """draft is a src.draft_agent.Draft (resume + cover_letter)."""
    issues: list[dict] = []
    issues += _check_prospecta_floor(draft.resume)
    issues += _check_employer_attribution(draft.resume)
    issues += _check_degree_line_editorializing(draft.resume)
    issues += _check_stale_credentials(draft.resume, background_subset)
    issues += _check_no_backticks(draft.resume, "Resume")
    issues += _check_no_backticks(draft.cover_letter, "Cover letter")
    issues += _check_contrast_tone(draft.resume, "Resume")
    issues += _check_contrast_tone(draft.cover_letter, "Cover letter")
    issues += _check_differentiator_defaults(draft.resume)
    issues += _check_heading_contract(draft.resume)
    issues += _check_contact_line(draft.resume)
    issues += _check_kharon_containment(draft.resume)
    issues += _check_cover_letter_salutation_closing(draft.cover_letter)
    issues += _check_cover_letter_length(draft.cover_letter)
    issues += _check_resume_length_precheck(draft.resume)
    return issues
