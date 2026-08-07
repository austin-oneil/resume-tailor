"""Haiku score agent: JD-match scoring + strict fact-check integrity pass."""

from dataclasses import dataclass, field

import config
from src.client import as_dict_list, as_str_list, get_client, print_cache_usage, today_str
from src.draft_agent import Draft

SCORE_TOOL = {
    "name": "submit_score",
    "description": (
        "Submit the JD-match score, gap list, and integrity flags for a resume/"
        "cover letter draft."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "score": {"type": "integer", "minimum": 0, "maximum": 100},
            "strengths": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "What's genuinely working well in this draft and why — specific "
                    "bullets, phrasing, or structural choices that land well for this "
                    "JD. For a human-readable report, not just a scoring input. 2-5 "
                    "items, concrete (name the actual bullet/claim), not generic "
                    "praise like 'well written'."
                ),
            },
            "gaps": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "category": {"type": "string"},
                        "detail": {"type": "string"},
                        "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                        "kind": {
                            "type": "string",
                            "enum": ["draft_defect", "jd_coverage"],
                            "description": (
                                "draft_defect = something a revision of these documents "
                                "can actually fix (structure, ordering, vague phrasing, a "
                                "real background-doc bullet that should have been "
                                "surfaced, a house-style violation, a stale fact). "
                                "jd_coverage = the JD asks for experience that genuinely "
                                "does not appear anywhere in the candidate background "
                                "material provided below (note: you only receive a "
                                "role-family-filtered subset of the full background doc, "
                                "not the whole thing — 'not in what I was given' is the "
                                "honest claim, not 'the candidate doesn't have this'). A "
                                "jd_coverage gap is INFORMATIONAL ONLY — it reports a real "
                                "limitation to the candidate, it is not a defect in the "
                                "draft and no rewrite can close it."
                            ),
                        },
                    },
                    "required": ["category", "detail", "severity", "kind"],
                },
            },
            "integrity_flags": {
                "type": "array",
                "description": (
                    "ONLY claims that are NOT fully supported by the background "
                    "document — unsupported, overstated, or in violation of a "
                    "Calibration Note. Claims you checked and found accurate/"
                    "properly caveated must NOT appear here at all. An empty "
                    "array means every claim checked out."
                ),
                "items": {
                    "type": "object",
                    "properties": {
                        "claim": {"type": "string"},
                        "issue": {"type": "string"},
                        "background_support": {"type": "string", "enum": ["none", "partial"]},
                    },
                    "required": ["claim", "issue", "background_support"],
                },
            },
        },
        "required": ["score", "strengths", "gaps", "integrity_flags"],
    },
}

SYSTEM_INSTRUCTIONS = (
    "You are a strict resume/cover-letter reviewer performing three tasks:\n"
    "0. Identify strengths — what's genuinely working well and specifically why, "
    "for a human-readable report the candidate will read later. Be concrete: name "
    "the actual bullet or phrase, not generic praise.\n"
    "1. Score JD compatibility 0-100 based on keyword/skill match, ATS-readability, "
    "clarity of quantified achievements, and a genuine, specific, non-generic "
    "voice (deduct for corporate/AI cliche filler like 'results-driven' or "
    "'leverage' used without a concrete claim behind it).\n"
    "2. Perform a strict fact-check integrity pass — check every concrete claim "
    "(technology, employer, metric, outcome, and employment dates) in the draft "
    "against the candidate background document below. This is not a keyword "
    "check. Also check claims about HOW the candidate works, not just what they "
    "did: a workflow, methodology, tool-usage habit (e.g. a described AI-tool "
    "process), or a claimed personality/culture-fit trait is just as much a "
    "fabrication risk as a false metric or employer if the background document "
    "has nothing supporting it — flag a specific-sounding but ungrounded process "
    "or personality narrative as an integrity_flags entry the same way you would "
    "a false technology claim. Employment dates are a two-way fabrication risk: flag it if the "
    "draft states a date range for a role that the background document does "
    "not actually give, AND separately add a gap (not an integrity flag) if "
    "the background document DOES give real dates for a role but the draft "
    "shows '[dates not in background doc]' or omits them anyway — real dates "
    "should always be used when available. When checking a 'years of "
    "experience' claim against an 'X – Present' date range, compute the "
    "duration using the actual current date given above as 'Present' — do "
    "not guess or assume a different current date.\n"
    "Only add an entry to integrity_flags for a claim that FAILS this check: it "
    "is unsupported, overstated, generalized beyond what the background document "
    "says, or violates a Calibration Note caveat. If a claim is accurate and any "
    "applicable caveat is properly respected, do NOT add it to integrity_flags — "
    "leave it out entirely, even if you reasoned about it. integrity_flags should "
    "end up empty when the draft has no real problems.\n"
    "Also check structure as part of gaps (not integrity_flags): every employer "
    "should appear as exactly ONE experience entry, never split into separate "
    "entries by discipline for the same company; if the background document's "
    "Calibration Notes specify which employer must be listed first or how "
    "entries should be grouped, verify the draft follows that; and check the "
    "house layout is followed — name+tagline+labeled contact header, a 'Core "
    "Skills' section organized into bold-labeled categories (not a flat list), "
    "a 'Professional Experience' section with company name bolded above an "
    "italicized title+dates line, and an Education & Certifications section "
    "present when the background document has EDUCATION content. Add a gap for "
    "any of these that's missing or reverted to a generic format. If the "
    "background document has a 'PROJECTS' section (e.g. a take-home interview "
    "exercise), this is a HARD integrity check: if the draft lists it as a "
    "Professional Experience entry (a company-name header, a tenure-style "
    "date range, or any phrasing implying it was a paid job), add a 'high' "
    "severity integrity_flags entry — this is a fabrication risk, not a style "
    "preference. It's fine for its tech stack to appear in Core Skills or for "
    "it to appear as a clearly-labeled interview anecdote in the cover letter.\n"
    "NON-NEGOTIABLE, always check regardless of JD: if the Calibration Notes "
    "specify a per-employer minimum (e.g. Prospecta must show at least one real "
    "SEO bullet AND at least one real Account Executive bullet, ahead of the "
    "dev bullets), verify the draft actually has them — not just skill-list "
    "mentions, but real bullets describing that work. If either is missing or "
    "reduced to zero bullets, add a 'high' severity gap explicitly calling out "
    "which discipline is missing.\n"
    "Be strict — a score of 85+ should mean a genuinely strong, accurate, ATS-ready "
    "match with no unresolved integrity flags.\n"
    "Classify every gap as 'draft_defect' or 'jd_coverage'. Be honest about the split: "
    "if the background material you were given contains no support for a JD "
    "requirement, that is "
    "jd_coverage, not a draft defect, and you must NOT phrase it as something the "
    "writer should 'address,' 'acknowledge,' or 'surface' — the correct handling of a "
    "jd_coverage gap is silence in the documents. Score the draft on how well it "
    "presents the candidate's ACTUAL material against this JD, not on how much of the "
    "JD the candidate covers. A draft that leads perfectly with everything genuinely "
    "available should be able to reach 90+ even when the candidate is missing several "
    "JD requirements; do not deduct for jd_coverage gaps at all. Deduct only for "
    "draft_defect items, weak or missing quantification of claims the background doc "
    "DOES support, ATS/keyword problems, house-style violations, and generic voice."
)


@dataclass
class ScoreResult:
    score: int
    strengths: list[str] = field(default_factory=list)
    gaps: list[dict] = field(default_factory=list)
    integrity_flags: list[dict] = field(default_factory=list)


def _build_system(background_subset: str, best_practices: str) -> list[dict]:
    return [
        {"type": "text", "text": f"Today's date is {today_str()}.\n\n{SYSTEM_INSTRUCTIONS}"},
        {
            "type": "text",
            "text": f"# Candidate Background\n\n{background_subset}",
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": f"# Resume & Cover Letter Best Practices\n\n{best_practices}",
            "cache_control": {"type": "ephemeral"},
        },
    ]


def score(
    job_title: str,
    jd_text: str,
    background_subset: str,
    best_practices: str,
    draft: Draft,
    model: str = config.SCORE_MODEL,
) -> ScoreResult:
    """model defaults to the cheap in-loop Haiku model; main.py's stage-5
    final verification overrides it to config.FINAL_SCORE_MODEL (Sonnet) —
    across 10 real runs the Haiku score collapsed to just 2 distinct values,
    which isn't discriminating enough to gate accepted vs. manual_review on
    for the one call that actually decides that."""
    client = get_client()
    system = _build_system(background_subset, best_practices)
    user_message = (
        f"Job title: {job_title}\n\nJob description:\n{jd_text}\n\n"
        f"Resume draft:\n{draft.resume}\n\n"
        f"Cover letter draft:\n{draft.cover_letter}\n\n"
        "Score this draft and report gaps and integrity flags."
    )
    message = client.messages.create(
        model=model,
        max_tokens=2000,
        system=system,
        tools=[SCORE_TOOL],
        tool_choice={"type": "tool", "name": "submit_score"},
        messages=[{"role": "user", "content": user_message}],
    )
    print_cache_usage("score", message.usage)
    for block in message.content:
        if block.type == "tool_use":
            return ScoreResult(
                score=block.input["score"],
                strengths=as_str_list(block.input.get("strengths", [])),
                gaps=as_dict_list(block.input.get("gaps", [])),
                integrity_flags=as_dict_list(block.input.get("integrity_flags", [])),
            )
    raise RuntimeError("Score agent did not return a tool_use block")
