"""Pre-draft fit/red-flag gate.

Runs before the expensive Sonnet draft call. A deterministic keyword scan of
the JD text (free) flags common compensation/culture red flags, and a single
small Haiku call (cheap) estimates coverage of the JD's *required*
qualifications against the candidate background. The goal is to let the CLI
warn and ask for confirmation before spending real tokens tailoring for a
job that's a clear bad fit, rather than a full "should I apply" report.
"""

from dataclasses import dataclass, field

import config
from src.client import as_str_list, get_client, print_cache_usage, today_str

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
    "independent of whether the candidate is actually a good fit. Be "
    "efficient — this is a quick gate, not a scored draft review."
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


def run(job_title: str, jd_text: str, background_subset: str) -> GateResult:
    red_flags = scan_red_flags(jd_text)
    match_estimate, missing, company_name, background_gaps, seniority_band, disqualifying = _estimate_fit(
        job_title, jd_text, background_subset
    )
    return GateResult(
        match_estimate=match_estimate,
        disqualifying_requirements=disqualifying,
        missing_requirements=missing,
        red_flags=red_flags,
        company_name=company_name,
        background_gaps=background_gaps,
        seniority_band=seniority_band,
    )
