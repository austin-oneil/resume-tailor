"""Writes accepted/flagged drafts to disk and logs each run to a CSV."""

import csv
import re
import shutil
from datetime import datetime
from pathlib import Path

import config
from src import docx_export, status as status_display, tracker
from src.draft_agent import Draft
from src.score_agent import ScoreResult

_PIPELINE_RESULT_LABELS = {
    "accepted": "Passed",
    "accepted_structurally_capped": "Passed (structurally capped)",
    "manual_review": "Needs manual review",
}

_UNSAFE_FILENAME_CHARS = re.compile(r'[/:*?"<>|\\]')


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return slug or "role"


def _safe_filename_part(text: str) -> str:
    return _UNSAFE_FILENAME_CHARS.sub("-", text).strip()


def _get_candidate_name() -> str:
    if not config.CANDIDATE_INFO_PATH.exists():
        return "Resume"
    for line in config.CANDIDATE_INFO_PATH.read_text().splitlines():
        if line.lower().startswith("name:"):
            return _safe_filename_part(line.split(":", 1)[1].strip())
    return "Resume"


def _build_filename(doc_type: str, job_title: str, company_name: str, candidate_name: str) -> str:
    """Company + doc type lead the filename so applications are easy to spot
    at a glance while scanning a folder, e.g.
    'Trivelta Resume - Austin O'Neil (Senior Frontend Software Engineer).docx'."""
    if company_name and job_title:
        company_part = _safe_filename_part(company_name)
        role_part = f" ({_safe_filename_part(job_title)})"
    else:
        company_part = _safe_filename_part(company_name or job_title)
        role_part = ""
    return f"{company_part} {doc_type} - {candidate_name}{role_part}.docx"


def _copy_to_documents(
    resume_docx: Path, cover_letter_docx: Path, job_title: str, company_name: str, platform: str
) -> None:
    platform_dir = config.DOCUMENTS_EXPORT_DIR / _safe_filename_part(platform or "Other")
    platform_dir.mkdir(parents=True, exist_ok=True)
    candidate_name = _get_candidate_name()

    resume_dest = platform_dir / _build_filename("Resume", job_title, company_name, candidate_name)
    cover_dest = platform_dir / _build_filename("Cover Letter", job_title, company_name, candidate_name)
    shutil.copy(resume_docx, resume_dest)
    shutil.copy(cover_letter_docx, cover_dest)
    status_display.substep(f"Also copied final .docx to: {platform_dir}")


def save(
    job_title: str,
    role_family: str,
    draft: Draft,
    result: ScoreResult,
    iterations: int,
    status: str,
    page_count: int,
    company_name: str = "",
    report_text: str = "",
    platform: str = "Other",
    hm_verdict: str = "",
) -> Path:
    timestamp = datetime.now()
    company_slug = _slugify(company_name) if company_name else ""
    role_slug = _slugify(job_title)
    folder_name = "-".join(part for part in (company_slug, role_slug, f"{timestamp:%Y-%m-%d}") if part)
    folder = config.OUTPUT_DIR / folder_name
    folder.mkdir(parents=True, exist_ok=True)

    (folder / "resume.md").write_text(draft.resume)
    (folder / "cover_letter.md").write_text(draft.cover_letter)

    docx_export.build_resume_docx(draft.resume).save(folder / "resume.docx")
    docx_export.build_cover_letter_docx(draft.cover_letter).save(folder / "cover_letter.docx")

    _copy_to_documents(folder / "resume.docx", folder / "cover_letter.docx", job_title, company_name, platform)

    if report_text:
        (folder / "report.md").write_text(report_text)

    _append_log(timestamp, job_title, role_family, result.score, iterations, status, page_count, folder)

    tracker.upsert(
        company=company_name or "Unknown",
        role=job_title,
        platform=platform,
        pipeline_result=_PIPELINE_RESULT_LABELS.get(status, status),
        score=result.score,
        pages=page_count,
        hiring_manager=hm_verdict,
        notes="",
        output_folder=str(folder),
        run_date=timestamp.date().isoformat(),
    )
    status_display.substep(f"Tracker updated: {tracker.TRACKER_PATH}")

    return folder


def _append_log(
    timestamp: datetime,
    job_title: str,
    role_family: str,
    score: int,
    iterations: int,
    status: str,
    page_count: int,
    folder: Path,
) -> None:
    config.LOGS_DIR.mkdir(parents=True, exist_ok=True)
    is_new = not config.LOG_CSV_PATH.exists()
    with config.LOG_CSV_PATH.open("a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(
                [
                    "timestamp", "job_title", "role_family", "final_score",
                    "iterations", "status", "resume_pages", "output_path",
                ]
            )
        writer.writerow(
            [
                timestamp.isoformat(timespec="seconds"), job_title, role_family, score,
                iterations, status, page_count, str(folder),
            ]
        )
