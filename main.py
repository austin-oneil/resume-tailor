"""CLI entrypoint: intake -> classify -> load background -> supervisor loop -> save."""

from dataclasses import replace

import config
from src import background_loader, classifier, draft_agent, fit_gate, hiring_gate, hiring_manager, length_fit, output, report, score_agent, status, structure_lint, style_lint, supervisor
from src.intake import get_job_posting


def main() -> None:
    posting = get_job_posting()
    if not posting.title or not posting.description:
        print("Job title and description are both required.")
        return

    sections = background_loader.parse_background()
    candidate_info = background_loader.load_candidate_info()

    role_family = classifier.classify_role_family(posting.title, posting.description)
    print(f"Classified as: {role_family}")

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

    if gate.match_estimate < config.FIT_GATE_MIN_SCORE or gate.red_flags or gate.disqualifying_requirements:
        if gate.disqualifying_requirements:
            print("Disqualifying requirement(s) detected — no draft, however well written, closes these:")
            for req in gate.disqualifying_requirements:
                print(f"  - {req}")
        answer = input("Weak fit and/or red flags detected — proceed with full tailoring anyway? [y/N]: ")
        if answer.strip().lower() not in ("y", "yes"):
            print("Skipped — no draft generated.")
            return

    status.stage(2, "Draft & Refine (Score / Integrity Loop)", f"{config.DRAFT_MODEL} + {config.SCORE_MODEL}")
    result = supervisor.run(
        posting.title, posting.description, background_subset, best_practices,
        company_name=gate.company_name, seniority_band=gate.seniority_band,
        known_missing=gate.missing_requirements,
    )

    status.stage(3, "One-Page Enforcement", config.DRAFT_MODEL)
    length_result = length_fit.enforce_one_page(
        posting.title, posting.description, background_subset, best_practices, result.draft
    )

    status.stage(4, "Hiring Manager Review", config.HM_MODEL)
    hm_gate_result = hiring_gate.run(
        posting.title, posting.description, gate.company_name, background_subset, best_practices, length_result.draft
    )

    # hiring_gate and length_fit both may have mutated the draft after the
    # supervisor loop's last score/lint check — re-verify the document that's
    # actually about to be saved, not the pre-mutation one, so the report and
    # the CSV log describe what was really shipped. Uses FINAL_SCORE_MODEL
    # (Sonnet), not the cheap in-loop Haiku model, since this is the one
    # score that actually decides accepted vs. manual_review.
    status.stage(5, "Final Verification", f"{config.FINAL_SCORE_MODEL} + local")
    final_draft = hm_gate_result.draft
    final_score_result = score_agent.score(
        posting.title, posting.description, background_subset, best_practices, final_draft,
        model=config.FINAL_SCORE_MODEL,
    )
    final_style_issues = style_lint.lint_draft(final_draft) + structure_lint.lint_draft(
        final_draft, background_subset
    )
    # audit v3 §2.4 — this is the ScoreResult that actually reaches report.py
    # and the manual_review printout below (supervisor.py already runs this
    # on its own stage-2 result, but that's not what ships in the report).
    final_score_result.gaps += supervisor.jd_coverage_backstop(final_score_result.gaps)
    status.detail(
        f"final check: score={final_score_result.score} "
        f"integrity_flags={len(final_score_result.integrity_flags)} "
        f"style_issues={len(final_style_issues)}"
    )

    # Bounded, one-shot repair: if the final check found lint issues OR
    # integrity flags (which the earlier stages had no way to see, since they
    # mutate the draft after the supervisor loop's last checks), try once to
    # fix them rather than just reporting them and leaving Austin to fix it
    # by hand. Integrity flags are included here (audit v3 §2.2) — a
    # fabricated claim found at this stage previously got zero automated
    # repair while a stray em dash got one.
    #
    # The repair is a PROPOSAL, not an unconditional overwrite (fixed after a
    # real, shipped regression on the Trivelta re-run, 2026-08-06): a repair
    # aimed at one low-severity lint issue came back scoring 8 points lower
    # and hadn't even fixed the issue it was sent to fix. Nothing compared
    # the before/after, so the worse draft shipped as final. Keep the
    # pre-repair state on hand and only accept the repair if it's actually
    # at least as good by the same quality_key the supervisor loop already
    # uses to protect against exactly this — a fabricating or lower-scoring
    # "fix" is discarded, not shipped.
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
            candidate_draft, background_subset
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

    # Unconditional final length re-check (audit v3 §2.1) — previously this
    # only ran inside the repair branch, so a run that repaired nothing at
    # this stage still shipped whatever length_result was computed back at
    # stage 3, before hiring_gate had a chance to mutate the draft. Cheap on
    # the common path: enforce_one_page returns immediately when already one
    # page, no API call.
    length_result = length_fit.enforce_one_page(
        posting.title, posting.description, background_subset, best_practices, final_draft
    )
    final_draft = length_result.draft

    # Re-review with the hiring manager if anything mutated the draft after
    # its original approval (audit v3 §1) — the stage-5 repair pass above,
    # or a shortening pass here that actually ran (attempts > 1 means
    # shorten() was called at least once). draft_agent.revise()/shorten()
    # return a full Draft; their "change only these items" scope is prompt
    # text, not a code guarantee, and the repair triggers are disproportionately
    # cover-letter issues — exactly the class of thing only the HM can judge
    # (does the rewritten opening still make sense for this company). Without
    # this, the report/tracker present a verdict describing a document that
    # no longer exists.
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
            # A fresh reject here is not the hiring_gate's own all-structural
            # early stop, so don't carry that (now-inaccurate) label forward.
            stopped_reason=hm_gate_result.stopped_reason if post_repair_hm.verdict == "advance" else "",
        )

    # Only high/medium lint issues block acceptance — a low-severity issue is
    # explicitly advisory (e.g. the resume-length precheck says "consider
    # tightening," not "this is wrong") and shouldn't force manual_review on
    # its own.
    blocking_style_issues = [i for i in final_style_issues if i.get("severity") in ("critical", "high", "medium")]

    fully_accepted = (
        final_score_result.score >= config.SCORE_THRESHOLD
        and not final_score_result.integrity_flags
        and not blocking_style_issues
        and length_result.fits_one_page
        and hm_gate_result.passed
    )
    # The hiring gate stopped early specifically because every remaining
    # concern was structural (a fact about Austin's history, not a drafting
    # defect) — see hiring_gate.py. If everything else about the document is
    # clean, "manual_review" is a misleading label; there's no revision left
    # to make. Report it as its own status so the report can say so plainly
    # instead of implying there's a fixable defect left.
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
    if final_status == "accepted_structurally_capped":
        print(
            "This packet is as strong as these two documents can be made. What's left is a "
            "fact about your history (see the hiring-manager concerns below), not a drafting "
            "defect — the fix is real new material in background.md or a different target "
            "role, not another draft."
        )
        for concern in hm_gate_result.hm_result.concerns:
            print(f"  concern: {concern}")
    elif final_status == "manual_review":
        print("Flagged for manual review — remaining items:")
        if not length_result.fits_one_page:
            print(f"  length: resume still renders as {length_result.page_count} pages after {length_result.attempts} shortening attempt(s)")
        for gap in final_score_result.gaps:
            kind_tag = " (real gap, not fixable by drafting)" if gap.get("kind") == "jd_coverage" else ""
            print(f"  gap [{gap.get('severity')}] {gap.get('category')}: {gap.get('detail')}{kind_tag}")
        for flag in final_score_result.integrity_flags:
            print(f"  integrity: {flag.get('claim')} -- {flag.get('issue')}")
        for issue in final_style_issues:
            print(f"  style [{issue.get('severity')}] {issue.get('category')}: {issue.get('detail')}")
        if not hm_gate_result.passed:
            print(f"  hiring manager: {hm_gate_result.hm_result.overall_impression}")
            for concern in hm_gate_result.hm_result.concerns:
                print(f"    concern: {concern}")


if __name__ == "__main__":
    main()
