"""Hiring-manager gate: an independent auditor loop.

Runs after the score/integrity supervisor loop and one-page enforcement have
already converged. Distinct from those — this simulates a real hiring
manager's gut-check review (src/hiring_manager.py) rather than mechanical
JD-match/ATS/integrity checking. On rejection, feeds the HM's specific
concerns back into draft_agent.revise() as a targeted fix, then re-verifies
one-page fit (a revision could add length back) before re-reviewing. Capped
at config.HM_MAX_ATTEMPTS so a stubborn case still terminates and gets
flagged for manual review rather than looping forever.

Concerns tagged 'structural' (a fact about the candidate's actual history —
years of experience, titles held, a technology never used) are never sent to
revise(): no rewrite of these two documents changes a structural fact, and
spending a Sonnet call trying has been observed to make the draft worse, not
better. When every concern on a reject is structural, the loop stops
immediately rather than burning the remaining attempt on nothing.

The revise()/shorten() calls in this loop can themselves reintroduce a lint
problem (an em dash, a gap confession, a broken Prospecta floor) that nothing
here used to check for — a revision aimed at satisfying the hiring manager
was free to break a rule the supervisor loop had already enforced. Each pass
now re-lints the mutated draft and folds any new issues into the next
revise() call's gaps, same treatment as the HM concerns.
"""

from dataclasses import dataclass

import config
from src import draft_agent, hiring_manager, length_fit, structure_lint, style_lint
from src import status as status_display
from src.draft_agent import Draft
from src.hiring_manager import HMResult


@dataclass
class HiringGateResult:
    draft: Draft
    hm_result: HMResult
    attempts: int
    passed: bool
    stopped_reason: str = ""


def run(
    job_title: str,
    jd_text: str,
    company_name: str,
    background_subset: str,
    best_practices: str,
    draft: Draft,
) -> HiringGateResult:
    hm_result = None
    lint_issues: list[dict] = []
    for attempt in range(1, config.HM_MAX_ATTEMPTS + 1):
        status_display.substep(f"Hiring manager review (attempt {attempt}/{config.HM_MAX_ATTEMPTS})...")
        hm_result = hiring_manager.review(job_title, jd_text, company_name, draft.resume, draft.cover_letter)
        status_display.detail(f"verdict: {hm_result.verdict} | concerns: {len(hm_result.concerns)}")

        if hm_result.verdict == "advance":
            return HiringGateResult(draft=draft, hm_result=hm_result, attempts=attempt, passed=True)

        gaps = hm_result.as_gap_dicts()
        fixable_gaps = [g for g in gaps if g.get("fixable", True)]

        if not fixable_gaps and not lint_issues:
            status_display.detail(
                "every hiring-manager concern is structural (a fact about your actual "
                "history, not a drafting defect) — stopping, no rewrite would change the verdict"
            )
            return HiringGateResult(
                draft=draft,
                hm_result=hm_result,
                attempts=attempt,
                passed=False,
                stopped_reason=(
                    "Every hiring-manager concern on this review was structural — a fact "
                    "about your actual history (years of experience, titles held, a "
                    "technology never used), not a defect in the drafting. No revision "
                    "was attempted because no rewrite of these documents would change it."
                ),
            )

        if attempt == config.HM_MAX_ATTEMPTS:
            break

        status_display.substep(f"Revising based on hiring manager feedback (attempt {attempt + 1}/{config.HM_MAX_ATTEMPTS})...")
        draft = draft_agent.revise(
            job_title, jd_text, background_subset, best_practices, draft, fixable_gaps + lint_issues, []
        )
        length_result = length_fit.enforce_one_page(job_title, jd_text, background_subset, best_practices, draft)
        draft = length_result.draft

        lint_issues = style_lint.lint_draft(draft) + structure_lint.lint_draft(draft, background_subset)
        if lint_issues:
            status_display.detail(
                f"post-revision check: {len(lint_issues)} lint issue(s) introduced — feeding into next pass"
            )

    return HiringGateResult(draft=draft, hm_result=hm_result, attempts=config.HM_MAX_ATTEMPTS, passed=False)
