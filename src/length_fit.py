"""Post-loop one-page enforcement.

Runs after the main quality/integrity supervisor loop finishes. Renders the
resume to an actual .docx and checks its TRUE page count via Microsoft Word
(src/word_pagecount.py) — not a word-count guess. If it overflows, asks the
draft agent to shorten (not rewrite) and re-checks, capped at a few attempts
so a stubborn case still terminates and gets flagged rather than looping
forever.
"""

from dataclasses import dataclass

from src import docx_export, draft_agent, status as status_display, word_pagecount
from src.draft_agent import Draft

MAX_LENGTH_ATTEMPTS = 3


@dataclass
class LengthFitResult:
    draft: Draft
    page_count: int
    fits_one_page: bool
    attempts: int
    tailoring_notes: list[str]


def enforce_one_page(
    job_title: str,
    jd_text: str,
    background_subset: str,
    best_practices: str,
    draft: Draft,
) -> LengthFitResult:
    page_count = None
    tailoring_notes: list[str] = []
    for attempt in range(1, MAX_LENGTH_ATTEMPTS + 1):
        doc = docx_export.build_resume_docx(draft.resume)
        page_count = word_pagecount.get_page_count(doc)
        status_display.detail(f"check {attempt}/{MAX_LENGTH_ATTEMPTS}: resume renders as {page_count} page(s)")

        if page_count <= 1:
            return LengthFitResult(
                draft=draft, page_count=page_count, fits_one_page=True, attempts=attempt,
                tailoring_notes=tailoring_notes,
            )

        if attempt == MAX_LENGTH_ATTEMPTS:
            break

        status_display.substep(f"Shortening draft to fit one page (attempt {attempt + 1}/{MAX_LENGTH_ATTEMPTS})...")
        draft = draft_agent.shorten(job_title, jd_text, background_subset, best_practices, draft, page_count)
        tailoring_notes += [f"[shortening, attempt {attempt + 1}] {note}" for note in draft.tailoring_notes]

    return LengthFitResult(
        draft=draft, page_count=page_count, fits_one_page=False, attempts=MAX_LENGTH_ATTEMPTS,
        tailoring_notes=tailoring_notes,
    )
