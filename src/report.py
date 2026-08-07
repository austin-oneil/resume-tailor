"""Assembles the human-readable per-application report.

Everything here is captured from data the pipeline already produces — no
extra API calls. The fit gate, draft agent, and score agent were extended to
each return a bit of reasoning (background_gaps, tailoring_notes, strengths)
specifically so this report could be built for free.
"""

from datetime import datetime

from src.fit_gate import GateResult
from src.hiring_gate import HiringGateResult
from src.length_fit import LengthFitResult
from src.score_agent import ScoreResult
from src.supervisor import SupervisorResult


def _bullet_list(items: list[str], empty_note: str = "(none)") -> str:
    if not items:
        return f"- {empty_note}"
    return "\n".join(f"- {item}" for item in items)


def build_report(
    job_title: str,
    company_name: str,
    gate: GateResult,
    supervisor_result: SupervisorResult,
    length_result: LengthFitResult,
    final_status: str,
    hiring_gate_result: HiringGateResult,
    final_score_result: ScoreResult,
    final_style_issues: list[dict],
) -> str:
    """final_score_result/final_style_issues are re-checked against the
    actual document being saved (post length-fit, post hiring-manager
    revision) — supervisor_result is kept only for the iteration-history
    table, since its score/gaps describe an earlier, possibly superseded,
    version of the draft."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    score_result = final_score_result
    company_display = company_name or "(company not detected)"
    hm_result = hiring_gate_result.hm_result
    hm_concern_lines = hm_result.concerns  # already formatted strings: "[severity] category: detail"

    fixable_gap_lines = [
        f"[{g.get('severity', '?')}] {g.get('category', '')}: {g.get('detail', '')}"
        for g in score_result.gaps
        if g.get("kind") != "jd_coverage"
    ]
    jd_coverage_lines = [
        f"[{g.get('severity', '?')}] {g.get('category', '')}: {g.get('detail', '')}"
        for g in score_result.gaps
        if g.get("kind") == "jd_coverage"
    ]
    integrity_lines = [
        f"Claim: {f.get('claim', '')} — Issue: {f.get('issue', '')}"
        for f in score_result.integrity_flags
    ]
    style_lines = [
        f"[{s.get('severity', '?')}] {s.get('category', '')}: {s.get('detail', '')}"
        for s in final_style_issues
    ]

    all_tailoring_notes = supervisor_result.tailoring_notes + length_result.tailoring_notes

    history_rows = "\n".join(
        f"| {h['iteration']} | {h['score']} | {h['gaps']} | {h['integrity_flags']} | {h['style_issues']} |"
        for h in supervisor_result.iteration_history
    )

    return f"""# Application Report — {job_title} at {company_display}

Generated: {timestamp}

## Outcome

- **Status:** {final_status}
- **Final score:** {score_result.score}/100 (acceptance threshold: 85)
- **Iterations:** {supervisor_result.iterations} (shipped iteration {supervisor_result.shipped_iteration} of {supervisor_result.iterations}{" — a later iteration scored worse and was discarded" if supervisor_result.shipped_iteration != supervisor_result.iterations else ""})
- **Resume length:** {length_result.page_count} page(s) {"(fits)" if length_result.fits_one_page else "(still over one page after shortening attempts)"}
- **Hiring manager verdict:** {hm_result.verdict} (after {hiring_gate_result.attempts} review(s))

## Pre-Draft Fit Assessment

Estimated *before* any drafting happened, based on your background doc vs. this JD's
stated required qualifications.

- **Estimated match on required qualifications:** {gate.match_estimate}%

**Missing requirements** (no support anywhere in your background doc):
{_bullet_list(gate.missing_requirements)}

**Red flags detected in the posting:**
{_bullet_list(gate.red_flags)}

## What Works

What the score agent judged as genuinely strong in the final draft, and why:

{_bullet_list(score_result.strengths, "No specific strengths called out this pass.")}

## What Doesn't / Remaining Gaps

These are what kept the score below the acceptance threshold, or flagged for manual
review, as of the final draft:

### Fixable issues remaining
{_bullet_list(fixable_gap_lines)}

### Real gaps between your background and this JD
Nothing in the draft can close these — they're informational, not a defect in the
writing, and no amount of rephrasing would fix them. Worth knowing before the interview.
{_bullet_list(jd_coverage_lines, "None — the background doc covers this JD's stated requirements.")}

### Integrity flags (unresolved)
{_bullet_list(integrity_lines)}

### Style issues (unresolved)
{_bullet_list(style_lines)}

## Hiring Manager Review

An independent gut-check from a simulated senior hiring manager, evaluating only what a
real hiring manager would actually see (resume, cover letter, job posting — not your
background doc). Deliberately a different lens than the score/gaps above: this is a
human-judgment call ("would I put this person on a phone screen?"), not a mechanical
JD-match or fact-check. If it rejected and had fixable concerns, those were fed back
into a revision automatically before landing on the final version; concerns tagged
structural (a fact about your actual history, not a drafting defect) are never sent to
revision, since no rewrite changes them.

**Verdict:** {hm_result.verdict}

**Overall impression:** {hm_result.overall_impression or "(not provided)"}

**Concerns raised:**
{_bullet_list(hm_concern_lines)}

**What genuinely stood out:**
{_bullet_list(hm_result.positive_signals, "Nothing specifically called out.")}
{f'''
**Why this application will not clear a hiring-manager bar, regardless of drafting:**
{hiring_gate_result.stopped_reason}
''' if hiring_gate_result.stopped_reason else ""}

## Why Certain Things Were Chosen — Tailoring Decisions

Collected from every draft/revise/shorten pass, in order. This is the model's own
reasoning for what it emphasized, cut, or traded off — useful for understanding *why*
the resume looks the way it does, not just *what* it says.

{_bullet_list(all_tailoring_notes)}

## Score Progression

| Iteration | Score | Gaps | Integrity Flags | Style Issues |
|---|---|---|---|---|
{history_rows}

## Suggestions For Your Background Doc

Broader than the missing-requirements list above — things that are thin, underdeveloped,
or absent in `background.md` that this specific JD cares about. Worth considering adding
or expanding if you actually have relevant experience:

{_bullet_list(gate.background_gaps, "Background doc already covers this JD well — nothing flagged.")}
"""
