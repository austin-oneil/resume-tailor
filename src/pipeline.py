"""Shared run orchestration for both front ends (main.py's CLI and
gui_app.py's desktop window). Extracted from main.py so the two can never
drift apart — every future pipeline change (a new stage, a new repair pass)
happens once, here, and both front ends pick it up automatically.

Split into two phases because the fit-gate confirmation ("weak fit
detected — proceed anyway?") is a front-end decision, not pipeline logic:
the CLI asks via input(), the GUI asks via a button click in the activity
feed. run_fit_gate() stops right before that decision; run_from_gate()
is everything after it, uninterrupted through to saved output.
"""

from dataclasses import dataclass, field, replace
from pathlib import Path

import config
from src import (
    background_loader, classifier, draft_agent, fit_gate, hiring_gate,
    hiring_manager, length_fit, output, report, score_agent, status,
    structure_lint, style_lint, supervisor,
)
from src.draft_agent import Draft
from src.fit_gate import GateResult
from src.hiring_gate import HiringGateResult
from src.intake import JobPosting
from src.length_fit import LengthFitResult
from src.score_agent import ScoreResult
from src.supervisor import SupervisorResult


@dataclass
class GateContext:
    """Everything computed up through the fit gate that run_from_gate()
    needs to pick back up with, once a front end has resolved the
    confirmation decision (or found none was needed)."""
    posting: JobPosting
    role_family: str
    background_subset: str
    best_practices: str
    gate: GateResult


@dataclass
class PipelineResult:
    final_status: str
    score: int
    pages: int
    hm_verdict: str
    folder: Path
    report_text: str
    job_title: str
    company_name: str
    gate: GateResult
    supervisor_result: SupervisorResult
    length_result: LengthFitResult
    hiring_gate_result: HiringGateResult
    final_score_result: ScoreResult
    final_style_issues: list[dict] = field(default_factory=list)
    resume_docx: Path = None
    cover_letter_docx: Path = None
    resume_md: Path = None
    cover_letter_md: Path = None
    report_path: Path = None


def gate_requires_confirmation(gate: GateResult) -> bool:
    return bool(
        gate.match_estimate < config.FIT_GATE_MIN_SCORE
        or gate.red_flags
        or gate.disqualifying_requirements
    )


def run_fit_gate(posting: JobPosting) -> GateContext:
    sections = background_loader.parse_background()
    candidate_info = background_loader.load_candidate_info()

    role_family = classifier.classify_role_family(posting.title, posting.description)
    status.classified(role_family)

    background_subset = background_loader.build_subset(sections, role_family, candidate_info)
    best_practices = config.BEST_PRACTICES_PATH.read_text()

    status.stage(1, "Pre-Draft Fit Check", config.FIT_GATE_MODEL)
    gate = fit_gate.run(posting.title, posting.description, background_subset)
    status.substep(f"Estimated match on required qualifications: {gate.match_estimate}%")
    for req in gate.missing_requirements:
        tag = " [DISQUALIFYING]" if req in gate.disqualifying_requirements else ""
        status.detail(f"missing: {req}{tag}")
    for flag in gate.red_flags:
        status.detail(f"red flag: {flag}")
    for item in gate.debunked_requirements:
        status.detail(
            f'auto-corrected: "{item}" was flagged as missing/disqualifying, but '
            "background.md contains matching evidence for it — dropped from the gap "
            "list (verify by hand, this could still be a real gap phrased differently)"
        )

    return GateContext(
        posting=posting,
        role_family=role_family,
        background_subset=background_subset,
        best_practices=best_practices,
        gate=gate,
    )


def run_from_gate(context: GateContext) -> PipelineResult:
    posting = context.posting
    gate = context.gate
    role_family = context.role_family
    background_subset = context.background_subset
    best_practices = context.best_practices

    status.stage(2, "Draft & Refine (Score / Integrity Loop)", f"{config.DRAFT_MODEL} + {config.SCORE_MODEL}")
    result = supervisor.run(
        posting.title, posting.description, background_subset, best_practices,
        company_name=gate.company_name, seniority_band=gate.seniority_band,
        known_missing=gate.missing_requirements, role_family=role_family,
    )

    status.stage(3, "One-Page Enforcement", config.DRAFT_MODEL)
    length_result = length_fit.enforce_one_page(
        posting.title, posting.description, background_subset, best_practices, result.draft, role_family
    )

    status.stage(4, "Hiring Manager Review", config.HM_MODEL)
    hm_gate_result = hiring_gate.run(
        posting.title, posting.description, gate.company_name, background_subset, best_practices,
        length_result.draft, role_family,
    )

    status.stage(5, "Final Verification", f"{config.FINAL_SCORE_MODEL} + local")
    final_draft = hm_gate_result.draft
    final_score_result = score_agent.score(
        posting.title, posting.description, background_subset, best_practices, final_draft,
        model=config.FINAL_SCORE_MODEL,
    )
    final_style_issues = style_lint.lint_draft(final_draft) + structure_lint.lint_draft(
        final_draft, background_subset, role_family
    )
    final_score_result.gaps += supervisor.jd_coverage_backstop(final_score_result.gaps)
    status.detail(
        f"final check: score={final_score_result.score} "
        f"integrity_flags={len(final_score_result.integrity_flags)} "
        f"style_issues={len(final_style_issues)}"
    )

    repaired = False
    if final_style_issues or final_score_result.integrity_flags:
        pre_repair_draft = final_draft
        pre_repair_score_result = final_score_result
        pre_repair_style_issues = final_style_issues

        status.substep("Repairing lint/integrity issues found in final verification (one bounded attempt)...")
        candidate_draft = draft_agent.revise(
            posting.title, posting.description, background_subset, best_practices,
            final_draft, final_style_issues, final_score_result.integrity_flags,
        )
        candidate_score_result = score_agent.score(
            posting.title, posting.description, background_subset, best_practices, candidate_draft,
            model=config.FINAL_SCORE_MODEL,
        )
        candidate_style_issues = style_lint.lint_draft(candidate_draft) + structure_lint.lint_draft(
            candidate_draft, background_subset, role_family
        )
        candidate_score_result.gaps += supervisor.jd_coverage_backstop(candidate_score_result.gaps)
        status.detail(
            f"post-repair check: score={candidate_score_result.score} "
            f"integrity_flags={len(candidate_score_result.integrity_flags)} "
            f"style_issues={len(candidate_style_issues)}"
        )

        if supervisor.quality_key(candidate_score_result, candidate_style_issues) >= supervisor.quality_key(
            pre_repair_score_result, pre_repair_style_issues
        ):
            final_draft = candidate_draft
            final_score_result = candidate_score_result
            final_style_issues = candidate_style_issues
            repaired = True
        else:
            status.detail(
                f"repair made things worse (score {pre_repair_score_result.score} -> "
                f"{candidate_score_result.score}) — discarding it, keeping the pre-repair draft"
            )
            final_draft = pre_repair_draft
            final_score_result = pre_repair_score_result
            final_style_issues = pre_repair_style_issues

    pre_length_draft = final_draft
    length_result = length_fit.enforce_one_page(
        posting.title, posting.description, background_subset, best_practices, final_draft, role_family
    )
    final_draft = length_result.draft

    # This shortening pass runs AFTER the stage-5 score and lint, so when it
    # actually rewrites the draft, final_score_result/final_style_issues
    # describe the pre-shortening document while the post-shortening one is
    # what gets saved and reported on. Rescore only when the text really
    # changed — enforce_one_page returns the draft untouched whenever it
    # already fits, which is the common case, so this normally costs nothing.
    if final_draft.resume != pre_length_draft.resume or final_draft.cover_letter != pre_length_draft.cover_letter:
        status.substep("Draft changed during one-page enforcement — rescoring so the report matches what ships...")
        final_score_result = score_agent.score(
            posting.title, posting.description, background_subset, best_practices, final_draft,
            model=config.FINAL_SCORE_MODEL,
        )
        final_style_issues = style_lint.lint_draft(final_draft) + structure_lint.lint_draft(
            final_draft, background_subset, role_family
        )
        final_score_result.gaps += supervisor.jd_coverage_backstop(final_score_result.gaps)
        status.detail(
            f"post-shortening check: score={final_score_result.score} "
            f"integrity_flags={len(final_score_result.integrity_flags)} "
            f"style_issues={len(final_style_issues)}"
        )

    if repaired or length_result.attempts > 1:
        status.substep("Re-reviewing repaired draft with the hiring manager...")
        post_repair_hm = hiring_manager.review(
            posting.title, posting.description, gate.company_name,
            final_draft.resume, final_draft.cover_letter,
        )
        status.detail(f"post-repair hiring manager verdict: {post_repair_hm.verdict}")
        hm_gate_result = replace(
            hm_gate_result,
            draft=final_draft,
            hm_result=post_repair_hm,
            passed=post_repair_hm.verdict == "advance",
            stopped_reason=hm_gate_result.stopped_reason if post_repair_hm.verdict == "advance" else "",
        )

    blocking_style_issues = [i for i in final_style_issues if i.get("severity") in ("critical", "high", "medium")]

    fully_accepted = (
        final_score_result.score >= config.SCORE_THRESHOLD
        and not final_score_result.integrity_flags
        and not blocking_style_issues
        and length_result.fits_one_page
        and hm_gate_result.passed
    )
    structurally_capped = (
        not fully_accepted
        and not hm_gate_result.passed
        and bool(hm_gate_result.stopped_reason)
        and final_score_result.score >= config.SCORE_THRESHOLD
        and not final_score_result.integrity_flags
        and not blocking_style_issues
        and length_result.fits_one_page
    )

    if fully_accepted:
        final_status = "accepted"
    elif structurally_capped:
        final_status = "accepted_structurally_capped"
    else:
        final_status = "manual_review"

    status.stage(6, "Saving Output & Report", "local")
    report_text = report.build_report(
        posting.title, gate.company_name, gate, result, length_result, final_status, hm_gate_result,
        final_score_result, final_style_issues,
    )

    folder = output.save(
        posting.title,
        role_family,
        final_draft,
        final_score_result,
        result.iterations,
        final_status,
        length_result.page_count,
        gate.company_name,
        report_text,
        posting.platform,
        hm_gate_result.hm_result.verdict,
    )
    status.substep(f"Saved to: {folder}")
    status.done(final_status, final_score_result.score, length_result.page_count, hm_gate_result.hm_result.verdict)

    return PipelineResult(
        final_status=final_status,
        score=final_score_result.score,
        pages=length_result.page_count,
        hm_verdict=hm_gate_result.hm_result.verdict,
        folder=folder,
        report_text=report_text,
        job_title=posting.title,
        company_name=gate.company_name,
        gate=gate,
        supervisor_result=result,
        length_result=length_result,
        hiring_gate_result=hm_gate_result,
        final_score_result=final_score_result,
        final_style_issues=final_style_issues,
        resume_docx=folder / "resume.docx",
        cover_letter_docx=folder / "cover_letter.docx",
        resume_md=folder / "resume.md",
        cover_letter_md=folder / "cover_letter.md",
        report_path=folder / "report.md",
    )
