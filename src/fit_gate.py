"""Pre-draft fit/red-flag gate.

Runs before the expensive Sonnet draft call. A deterministic keyword scan of
the JD text (free) flags common compensation/culture red flags, and a single
small Haiku call (cheap) estimates coverage of the JD's *required*
qualifications against the candidate background. The goal is to let the CLI
warn and ask for confirmation before spending real tokens tailoring for a
job that's a clear bad fit, rather than a full "should I apply" report.
"""

import re
from dataclasses import dataclass, field

import config
from src.client import as_str_list, find_technology_matches, get_client, print_cache_usage, today_str

# A disqualifier phrased as a tenure/years requirement — keyword matching
# can't verify or refute this (a term's presence proves nothing about how
# many years the candidate has done it), so these are never eligible for
# the technology-match downgrade in _debunk_disqualifiers below.
_YEARS_OF_EXPERIENCE_RE = re.compile(r"\d+\+?\s*years?|years?\s+of\s+experience|years?['’]?\s+experience", re.IGNORECASE)

# A missing_requirements item phrased as a degree ask ("BA/BS degree",
# "bachelor's or equivalent") won't match find_technology_matches's
# proper-noun regex reliably ("B.S." has a period; "BA/BS" isn't a single
# capitalized token), so it gets its own dedicated evidence check below.
_DEGREE_MENTION_RE = re.compile(r"\bdegree\b|\bbachelor'?s?\b", re.IGNORECASE)
_DEGREE_EVIDENCE_RE = re.compile(
    r"\bbachelor'?s?\b|\bassociate'?s?\s+degree\b|\bmaster'?s?\s+degree\b|\bph\.?d\.?\b",
    re.IGNORECASE,
)

# A missing_requirements item naming a security clearance ("Public Trust",
# "Secret clearance") relies on "Public"/"Trust"/"Secret" as its only
# capitalized tokens — all three are excluded from find_technology_matches's
# stopword list because standing alone they false-positive on ordinary prose
# ("Trust" matched "building trust with the company"; see
# _CAPITALIZED_STOPWORDS in client.py). That means genuine clearance evidence
# can never clear this kind of item through the generic path either, so it
# gets its own dedicated phrase-level check, same pattern as the degree check
# above.
_CLEARANCE_MENTION_RE = re.compile(
    r"\bpublic trust\b|\bsecurity clearance\b|\bclearance\b|\bsecret\b|\bts/sci\b", re.IGNORECASE
)
_CLEARANCE_EVIDENCE_RE = re.compile(
    r"\bpublic trust\b|\bsecurity clearance\b|\bfederal clearance\b|\bclearance\b", re.IGNORECASE
)

COMP_RED_FLAGS = [
    "competitive salary", "competitive pay", "competitive compensation",
    "salary doe", "compensation doe", "doe based on experience",
    "commission-based", "commission only", "equity in lieu of", "equity-heavy",
]

CULTURE_RED_FLAGS = [
    "rockstar", "ninja", "guru", "work hard, play hard", "work hard play hard",
    "unlimited vacation", "unlimited pto", "like a family", "wear many hats",
    "fast-paced environment", "hit the ground running",
    "self-starter in ambiguous", "always-on culture", "always on culture",
]

FIT_GATE_TOOL = {
    "name": "submit_fit_estimate",
    "description": "Submit a quick pre-draft fit estimate for this job description.",
    "input_schema": {
        "type": "object",
        "properties": {
            "estimated_match": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "description": (
                    "Estimated % coverage of the JD's REQUIRED/must-have "
                    "qualifications by the candidate background."
                ),
            },
            "missing_requirements": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Specific must-have requirements from the JD that the "
                    "background document gives NO support for at all, not "
                    "even adjacent or transferable experience."
                ),
            },
            "company_name": {
                "type": "string",
                "description": (
                    "The hiring company's name as stated in the job posting "
                    "(short form suitable for a file name, e.g. 'NeuroHire' "
                    "not 'NeuroHire.ai, Inc.'). Empty string if genuinely not "
                    "stated anywhere in the posting."
                ),
            },
            "background_gaps": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "For a human-readable report, not a scoring input: specific "
                    "suggestions for what the candidate might want to add or "
                    "expand in their background doc based on THIS JD — things "
                    "that are thin, underdeveloped, or entirely absent but that "
                    "this JD cares about. Broader than missing_requirements — "
                    "include areas that are technically present but weakly "
                    "documented (e.g. 'background doc mentions Docker once with "
                    "no detail, but this JD leans heavily on containerization — "
                    "worth expanding if there's more real experience there'). "
                    "Skip this if the background doc already covers the JD well."
                ),
            },
            "disqualifying_requirements": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "A SUBSET of missing_requirements (verbatim, same wording) that are "
                    "hard blockers rather than adjacent-coverable gaps: an explicit "
                    "years-of-experience minimum the candidate's actual tenure can't "
                    "meet (e.g. '5+ years as a software engineer' against ~2 years), or "
                    "a named core-stack technology the background document shows zero "
                    "evidence of (e.g. 'PostgreSQL' or 'Kubernetes' required, and "
                    "genuinely absent). These trigger a confirmation prompt regardless "
                    "of the overall match percentage, because no amount of drafting "
                    "closes them. Leave empty if every missing_requirements item is "
                    "the softer 'not explicitly demonstrated but plausibly adjacent' "
                    "kind."
                ),
            },
            "seniority_band": {
                "type": "string",
                "enum": ["junior", "mid", "senior", "lead/staff", "unclear"],
                "description": (
                    "The seniority level this posting is actually targeting, "
                    "based on its title, years-of-experience asks, and scope "
                    "language — not the candidate's fit for it. Used to calibrate "
                    "how confidently the resume should present itself (a junior "
                    "req wants a different register than a staff req)."
                ),
            },
        },
        "required": [
            "estimated_match", "missing_requirements", "company_name",
            "background_gaps", "disqualifying_requirements", "seniority_band",
        ],
    },
}

SYSTEM_INSTRUCTIONS = (
    "You are doing a FAST pre-screen before any resume is drafted, not a full "
    "review. Estimate 0-100 how well the candidate background below covers "
    "this JD's REQUIRED (must-have) qualifications specifically — ignore "
    "nice-to-have/preferred qualifications entirely, they don't count against "
    "the score. Only list a missing_requirements entry if it is explicitly "
    "stated as required/must-have in the JD and the background document gives "
    "NO support for it at all, not even adjacent or transferable experience. "
    "Also extract the hiring company's name from the posting text, in a short "
    "form usable as part of a file/folder name. Separately, note "
    "background_gaps — a broader, advisory list (for a report the candidate "
    "reads later, not the score) of specific things worth adding or expanding "
    "in the background doc given what this particular JD emphasizes. Within "
    "missing_requirements, also identify disqualifying_requirements — the "
    "subset that are hard blockers (an explicit years-of-experience minimum "
    "the candidate's actual tenure can't meet, or a named core-stack "
    "technology with zero background-doc evidence) rather than the softer "
    "'not explicitly demonstrated but plausibly adjacent' kind. Also classify "
    "seniority_band — the level this posting is actually targeting "
    "(junior/mid/senior/lead-staff/unclear), based on its title, any explicit "
    "years-of-experience ask, and scope language (e.g. 'own the architecture,' "
    "'mentor others' reads senior+; 'growth opportunity,' 'entry-level' reads "
    "junior) — this calibrates how the resume should present itself, "
    "independent of whether the candidate is actually a good fit. When a "
    "required qualification is phrased as 'N years of X experience,' check "
    "the candidate background for dated, hands-on experience doing X across "
    "ALL roles/employers — including freelance, contract, and agency work, "
    "and roles filed under a different job title than the one being applied "
    "for (e.g. front-end web development performed while titled 'SEO "
    "Specialist' still counts as front-end experience). Sum or span the "
    "relevant dated experience across roles rather than requiring one single "
    "role/title to cover the full tenure on its own; only treat a "
    "years-of-experience ask as missing/disqualifying if the background "
    "document, taken as a whole, genuinely doesn't support that many years "
    "of real hands-on work in that specific area. Be efficient — this is a "
    "quick gate, not a scored draft review."
)


@dataclass
class GateResult:
    match_estimate: int
    missing_requirements: list[str] = field(default_factory=list)
    red_flags: list[str] = field(default_factory=list)
    company_name: str = ""
    background_gaps: list[str] = field(default_factory=list)
    seniority_band: str = "unclear"
    disqualifying_requirements: list[str] = field(default_factory=list)
    debunked_requirements: list[str] = field(default_factory=list)


def scan_red_flags(jd_text: str) -> list[str]:
    lowered = jd_text.lower()
    found = []

    has_dollar_sign = "$" in jd_text
    for phrase in COMP_RED_FLAGS:
        if phrase in lowered and not has_dollar_sign:
            found.append(
                f"Compensation vagueness: contains '{phrase}' with no salary "
                "figure given anywhere in the posting"
            )

    for phrase in CULTURE_RED_FLAGS:
        if phrase in lowered:
            found.append(f"Culture language: contains '{phrase}'")

    return found


def _estimate_fit(
    job_title: str, jd_text: str, background_subset: str
) -> tuple[int, list[str], str, list[str], str, list[str]]:
    client = get_client()
    system = [
        {"type": "text", "text": f"Today's date is {today_str()}.\n\n{SYSTEM_INSTRUCTIONS}"},
        {
            "type": "text",
            "text": f"# Candidate Background\n\n{background_subset}",
            "cache_control": {"type": "ephemeral"},
        },
    ]
    user_message = f"Job title: {job_title}\n\nJob description:\n{jd_text}"
    message = client.messages.create(
        model=config.FIT_GATE_MODEL,
        max_tokens=500,
        system=system,
        tools=[FIT_GATE_TOOL],
        tool_choice={"type": "tool", "name": "submit_fit_estimate"},
        messages=[{"role": "user", "content": user_message}],
    )
    print_cache_usage("fit_gate", message.usage)
    for block in message.content:
        if block.type == "tool_use":
            return (
                block.input["estimated_match"],
                as_str_list(block.input.get("missing_requirements", [])),
                str(block.input.get("company_name", "") or ""),
                as_str_list(block.input.get("background_gaps", [])),
                str(block.input.get("seniority_band", "") or "unclear"),
                as_str_list(block.input.get("disqualifying_requirements", [])),
            )
    raise RuntimeError("Fit gate did not return a tool_use block")


def _debunk_missing(missing: list[str], disqualifying: list[str]) -> tuple[list[str], list[str], list[str]]:
    """Cross-checks EVERY missing_requirements item — not just the
    disqualifying_requirements subset — against the FULL background.md
    before trusting one cheap, fast Haiku call with a 500-token budget to
    declare something absent. (background_loader.build_subset() has passed
    fit_gate the full document, not a role-family slice, since 2026-08-08 —
    this re-read from disk is now redundant with what fit_gate already saw,
    but harmless, and kept for a still-real reason: a cheap gate model can
    overlook or misjudge evidence that's right in front of it, subset or
    not.) Originally this only ran against disqualifying_requirements
    (real, shipped error 2026-08-07: "Required fluency in modern web
    platforms (e.g., Webflow)" got flagged as a hard disqualifier, blocking
    the run outright, even though background.md documents Webflow
    extensively). Widened 2026-08-08 after a Gladly run flagged "BA/BS
    degree or equivalent experience", AEO, and hands-on Webflow
    landing-page experience as plain missing_requirements — none blocking,
    but all three demonstrably false and printed straight to the user
    ("missing: ..."), which is exactly the same class of error at a lower
    stake. The disqualifying case is just the highest-consequence instance
    of a general problem: a cheap gate model asserting absence it hasn't
    actually verified against the full document.

    Two exclusions from the technology-match check, because keyword
    presence can't verify or refute these:
    - years-of-experience-shaped items (a term appearing proves nothing
      about tenure — caught case: "5+ years... SaaS..." wrongly downgraded
      because "SaaS" appears in background.md in a line that CONFIRMS the
      gap, not fills it)
    - degree-shaped items get their own dedicated evidence check instead of
      find_technology_matches, since "B.S." / "BA/BS" aren't tokens its
      proper-noun regex reliably catches

    Returns (confirmed_missing, confirmed_disqualifying, downgraded).
    disqualifying_requirements is defined as a verbatim subset of
    missing_requirements, so anything downgraded out of missing is dropped
    from disqualifying too. Downgraded items are removed from both lists and
    surfaced to Austin with a "verify by hand" hedge, since a keyword/tech
    match can still be wrong.

    Degree items are the one exception: _DEGREE_EVIDENCE_RE is a binary
    check (does background.md show a bachelor's-or-higher degree at all),
    not a fuzzy keyword match, and Austin has a real B.S. in Computer
    Science on file. Confirmed 2026-08-22 after a WordPress Developer run
    printed "auto-corrected: ...Bachelor's degree in Computer Science...
    verify by hand" for a JD that has zero ambiguity — Austin's degree isn't
    "adjacent" or "transferable," it's an exact field-of-study match. That
    hedge is appropriate for a keyword/tech-match downgrade (a term's
    presence really can be a false positive); it's just noise for a degree
    the candidate unambiguously holds. So degree downgrades are dropped from
    the gap list silently — never re-surfaced via the debunked_requirements
    hedge."""
    confirmed_missing, downgraded = [], []
    full_background = config.BACKGROUND_PATH.read_text()
    has_degree_evidence = bool(_DEGREE_EVIDENCE_RE.search(full_background))
    has_clearance_evidence = bool(_CLEARANCE_EVIDENCE_RE.search(full_background))
    for item in missing:
        if _CLEARANCE_MENTION_RE.search(item) and has_clearance_evidence:
            downgraded.append(item)
        elif _YEARS_OF_EXPERIENCE_RE.search(item):
            confirmed_missing.append(item)
        elif _DEGREE_MENTION_RE.search(item) and has_degree_evidence:
            pass  # confirmed degree holder — drop silently, no hedge needed
        elif find_technology_matches(item, full_background):
            downgraded.append(item)
        else:
            confirmed_missing.append(item)
    confirmed_disqualifying = [item for item in disqualifying if item in confirmed_missing]
    return confirmed_missing, confirmed_disqualifying, downgraded


TENURE_VERIFY_TOOL = {
    "name": "submit_tenure_verdicts",
    "description": (
        "Submit a verdict for each years-of-experience requirement: does the "
        "candidate background actually support it?"
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "verdicts": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "requirement": {
                            "type": "string",
                            "description": "The requirement text, verbatim, as given.",
                        },
                        "meets_requirement": {
                            "type": "boolean",
                            "description": (
                                "True if the candidate's dated, hands-on work — summed "
                                "or spanned across ALL roles/employers, including "
                                "freelance/contract work and roles filed under a "
                                "different job title — genuinely covers the required "
                                "number of years in that specific area. False only if "
                                "the background document, taken as a whole, really "
                                "doesn't support that many years of real hands-on work "
                                "there."
                            ),
                        },
                    },
                    "required": ["requirement", "meets_requirement"],
                },
            },
        },
        "required": ["verdicts"],
    },
}


def _verify_tenure_claims(items: list[str], job_title: str, jd_text: str, full_background: str) -> dict[str, bool]:
    """Years-of-experience items are excluded from the keyword-match debunk
    in _debunk_missing on purpose — a term's presence proves nothing about
    tenure. But that means a tenure claim the cheap Haiku gate got wrong has
    no factual cross-check at all, unlike every other requirement type here
    (tech names via find_technology_matches, degrees via
    _DEGREE_EVIDENCE_RE, clearances via _CLEARANCE_EVIDENCE_RE). Real case,
    2026-08-19: Haiku flagged "2 years of software engineering experience
    working across front-end web technologies" as a hard disqualifier even
    though the candidate has 5+ years of continuous, dated front-end work —
    just spread across freelance/agency engagements titled things other than
    "Software Engineer." A second, stronger-model read of the SAME full
    background document, focused only on the handful of items that already
    triggered a hard stop, is a cheap enough cross-check for the
    highest-consequence case this gate produces (it blocks the run outright)."""
    client = get_client()
    system = [
        {
            "type": "text",
            "text": (
                "You are re-checking a small number of years-of-experience "
                "requirements that a faster, cheaper pre-screen flagged as "
                "hard disqualifiers. For each one, decide whether the "
                "candidate's dated work history — summed or spanned across "
                "ALL roles, employers, and job titles, including freelance "
                "and contract work — genuinely covers that many years of "
                "real hands-on experience in that specific area. A role's "
                "job title (e.g. 'SEO Specialist') does NOT disqualify the "
                "real, dated hands-on work performed within that role from "
                "counting toward a skill/technology tenure requirement. Only "
                "mark meets_requirement false if the background document, "
                "read as a whole, genuinely does not support that many years "
                "of real experience in that area."
            ),
        },
        {
            "type": "text",
            "text": f"# Candidate Background\n\n{full_background}",
            "cache_control": {"type": "ephemeral"},
        },
    ]
    requirements_list = "\n".join(f"- {item}" for item in items)
    user_message = (
        f"Job title: {job_title}\n\nJob description:\n{jd_text}\n\n"
        f"Requirements to re-check:\n{requirements_list}"
    )
    message = client.messages.create(
        model=config.FINAL_SCORE_MODEL,
        max_tokens=500,
        system=system,
        tools=[TENURE_VERIFY_TOOL],
        tool_choice={"type": "tool", "name": "submit_tenure_verdicts"},
        messages=[{"role": "user", "content": user_message}],
    )
    print_cache_usage("fit_gate_tenure_verify", message.usage)
    for block in message.content:
        if block.type == "tool_use":
            return {
                str(v.get("requirement", "")): bool(v.get("meets_requirement", False))
                for v in block.input.get("verdicts", [])
                if isinstance(v, dict)
            }
    return {}


def run(job_title: str, jd_text: str, background_subset: str) -> GateResult:
    red_flags = scan_red_flags(jd_text)
    match_estimate, missing, company_name, background_gaps, seniority_band, disqualifying = _estimate_fit(
        job_title, jd_text, background_subset
    )
    confirmed_missing, confirmed_disqualifying, downgraded = _debunk_missing(missing, disqualifying)

    tenure_candidates = [item for item in confirmed_disqualifying if _YEARS_OF_EXPERIENCE_RE.search(item)]
    if tenure_candidates:
        full_background = config.BACKGROUND_PATH.read_text()
        verdicts = _verify_tenure_claims(tenure_candidates, job_title, jd_text, full_background)
        cleared = {item for item, met in verdicts.items() if met}
        if cleared:
            confirmed_missing = [item for item in confirmed_missing if item not in cleared]
            confirmed_disqualifying = [item for item in confirmed_disqualifying if item not in cleared]
            downgraded += list(cleared)

    return GateResult(
        match_estimate=match_estimate,
        disqualifying_requirements=confirmed_disqualifying,
        debunked_requirements=downgraded,
        missing_requirements=confirmed_missing,
        red_flags=red_flags,
        company_name=company_name,
        background_gaps=background_gaps,
        seniority_band=seniority_band,
    )
