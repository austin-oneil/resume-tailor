"""CLI entrypoint: intake -> classify -> load background -> supervisor loop -> save.

Thin now — all orchestration lives in src/pipeline.py so the GUI (gui_app.py)
runs the exact same logic. This file is just the terminal-specific bits:
interactive input() prompts and the final printed summary.
"""

from src import pipeline
from src.intake import get_job_posting


def main() -> None:
    posting = get_job_posting()
    if not posting.title or not posting.description:
        print("Job title and description are both required.")
        return

    context = pipeline.run_fit_gate(posting)
    gate = context.gate

    if pipeline.gate_requires_confirmation(gate):
        if gate.disqualifying_requirements:
            print("Disqualifying requirement(s) detected — no draft, however well written, closes these:")
            for req in gate.disqualifying_requirements:
                print(f"  - {req}")
        answer = input("Weak fit and/or red flags detected — proceed with full tailoring anyway? [y/N]: ")
        if answer.strip().lower() not in ("y", "yes"):
            print("Skipped — no draft generated.")
            return

    result = pipeline.run_from_gate(context)

    if result.final_status == "accepted_structurally_capped":
        print(
            "This packet is as strong as these two documents can be made. What's left is a "
            "fact about your history (see the hiring-manager concerns below), not a drafting "
            "defect — the fix is real new material in background.md or a different target "
            "role, not another draft."
        )
        for concern in result.hiring_gate_result.hm_result.concerns:
            print(f"  concern: {concern}")
    elif result.final_status == "manual_review":
        print("Flagged for manual review — remaining items:")
        if not result.length_result.fits_one_page:
            print(
                f"  length: resume still renders as {result.length_result.page_count} pages "
                f"after {result.length_result.attempts} shortening attempt(s)"
            )
        for gap in result.final_score_result.gaps:
            kind_tag = " (real gap, not fixable by drafting)" if gap.get("kind") == "jd_coverage" else ""
            print(f"  gap [{gap.get('severity')}] {gap.get('category')}: {gap.get('detail')}{kind_tag}")
        for flag in result.final_score_result.integrity_flags:
            print(f"  integrity: {flag.get('claim')} -- {flag.get('issue')}")
        for issue in result.final_style_issues:
            print(f"  style [{issue.get('severity')}] {issue.get('category')}: {issue.get('detail')}")
        if not result.hiring_gate_result.passed:
            print(f"  hiring manager: {result.hiring_gate_result.hm_result.overall_impression}")
            for concern in result.hiring_gate_result.hm_result.concerns:
                print(f"    concern: {concern}")


if __name__ == "__main__":
    main()
