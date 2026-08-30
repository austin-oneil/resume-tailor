"""Post-loop one-page enforcement.

Runs after the main quality/integrity supervisor loop finishes. Renders the
resume to an actual .docx and checks its TRUE page count via Microsoft Word
(src/word_pagecount.py) — not a word-count guess. If it overflows, asks the
draft agent to shorten (not rewrite) and re-checks, capped at a few attempts
so a stubborn case still terminates and gets flagged rather than looping
forever.

Each shortening attempt is scored and lint-checked, same as the supervisor
loop (Austin's own diagnosis, 2026-08-07): a shorten pass is a
content-removal operation with real risk of quietly cutting something that
mattered, and until this fix it had zero quality feedback — unlike the
supervisor loop, nothing here ever compared attempts or tracked which one
was actually best. If no attempt fits within the cap, the best-SCORING
attempt ships, not just whichever one happened to run last.
"""

from dataclasses import dataclass

from src import docx_export, draft_agent, score_agent, status as status_display, structure_lint, style_lint, supervisor, word_pagecount
from src.draft_agent import Draft

MAX_LENGTH_ATTEMPTS = 3


@dataclass
class LengthFitResult:
    draft: Draft
    page_count: int
    fits_one_page: bool
    attempts: int
    tailoring_notes: list[str]


def _lint(draft: Draft, background_subset: str, role_family: str = "") -> list[dict]:
    return style_lint.lint_draft(draft) + structure_lint.lint_draft(draft, background_subset, role_family)


def enforce_one_page(
    job_title: str,
    jd_text: str,
    background_subset: str,
    best_practices: str,
    draft: Draft,
    role_family: str = "",
) -> LengthFitResult:
    page_count = None
    tailoring_notes: list[str] = []
    best = None  # (quality_key, draft, page_count, attempt)

    for attempt in range(1, MAX_LENGTH_ATTEMPTS + 1):
        doc = docx_export.build_resume_docx(draft.resume)
        page_count = word_pagecount.get_page_count(doc)
        status_display.detail(f"check {attempt}/{MAX_LENGTH_ATTEMPTS}: resume renders as {page_count} page(s)")

        if page_count <= 1:
            return LengthFitResult(
                draft=draft, page_count=page_count, fits_one_page=True, attempts=attempt,
                tailoring_notes=tailoring_notes,
            )

        # Doesn't fit yet. Score this attempt (cheap in-loop model, same as
        # the supervisor loop) so that if nothing ever fits within the cap,
        # the best-scoring attempt ships instead of whichever ran last.
        score_result = score_agent.score(job_title, jd_text, background_subset, best_practices, draft)
        lint_issues = _lint(draft, background_subset, role_family)
        key = supervisor.quality_key(score_result, lint_issues)
        if best is None or key > best[0]:
            best = (key, draft, page_count, attempt)

        if attempt == MAX_LENGTH_ATTEMPTS:
            break

        status_display.substep(f"Shortening draft to fit one page (attempt {attempt + 1}/{MAX_LENGTH_ATTEMPTS})...")
        draft = draft_agent.shorten(job_title, jd_text, background_subset, best_practices, draft, page_count)
        tailoring_notes += [f"[shortening, attempt {attempt + 1}] {note}" for note in draft.tailoring_notes]

    _, best_draft, best_page_count, best_attempt = best
    if best_attempt != MAX_LENGTH_ATTEMPTS:
        status_display.detail(
            f"keeping attempt {best_attempt}'s draft over the later attempt "
            f"{MAX_LENGTH_ATTEMPTS}, which scored worse — none fit one page, "
            "so shipping the best-scoring one tried"
        )
    return LengthFitResult(
        draft=best_draft, page_count=best_page_count, fits_one_page=False, attempts=MAX_LENGTH_ATTEMPTS,
        tailoring_notes=tailoring_notes,
    )
