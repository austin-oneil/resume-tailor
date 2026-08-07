"""Central configuration for the resume-tailor CLI."""

from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
LOGS_DIR = BASE_DIR / "logs"

BACKGROUND_PATH = DATA_DIR / "background.md"
BEST_PRACTICES_PATH = DATA_DIR / "resume_best_practices.md"
CANDIDATE_INFO_PATH = DATA_DIR / "candidate_info.md"
LOG_CSV_PATH = LOGS_DIR / "applications_log.csv"

# Final .docx (only — not the working .md files) also get copied here after
# every run, with clean human-readable names, so there's no need to dig into
# OUTPUT_DIR and "Save As" to get a submittable copy.
DOCUMENTS_EXPORT_DIR = Path.home() / "Documents" / "Resume Applications"

# Models
DRAFT_MODEL = "claude-sonnet-5"
SCORE_MODEL = "claude-haiku-4-5-20251001"
# Used only for main.py's stage-5 final verification, the one score that
# actually decides accepted vs. manual_review. Across 10 real runs the Haiku
# score collapsed to just 4 distinct values (72/78/87/88, 8 of 10 landing on
# exactly 72 or 78) — not discriminating enough for the call that gates the
# outcome, even though Haiku is fine for the cheap in-loop iterations.
FINAL_SCORE_MODEL = "claude-sonnet-5"
CLASSIFIER_MODEL = "claude-haiku-4-5-20251001"  # only used as a fallback
FIT_GATE_MODEL = "claude-haiku-4-5-20251001"
HM_MODEL = "claude-sonnet-5"  # judgment call needs the stronger model

# Supervisor loop
SCORE_THRESHOLD = 85
MAX_ITERATIONS = 3

# Hiring-manager gate: independent human-judgment auditor, runs after the
# score/integrity loop and one-page enforcement. Capped separately since it's
# an outer loop wrapping an already-converged draft.
HM_MAX_ATTEMPTS = 2

# Pre-draft fit gate: below this estimated match on required qualifications
# (or if any red flags are found, or if a disqualifying requirement is
# detected — see fit_gate.py), the CLI asks for confirmation before spending
# a Sonnet draft call on a likely-poor-fit JD. Reverted from 70 back to 55 per
# 2026-08-06 v2 system audit: raising it to 70 made the gate fire on nearly
# every run (every historical run scored 62-78%), and a gate that always
# fires just trains reflexive "y" answers — worse than no gate, since it
# stops being a real signal. disqualifying_requirements (checked
# independently, unconditional on the percentage) is the actual discriminating
# trip condition; this percentage is a softer, secondary check.
FIT_GATE_MIN_SCORE = 55

# Role-family -> background tags to load (in addition to the always-on tags below)
ROLE_FAMILY_TAGS = {
    "dev": ["DEV", "PROJECTS"],
    "sales-technical": ["SALES-TECH", "NON-TECH"],
    "seo-growth": ["SEO", "SALES-TECH"],
    "hybrid": ["DEV", "SALES-TECH", "SEO", "PROJECTS"],
}

# Always included regardless of role family
ALWAYS_ON_TAGS = ["ABOUT_ME", "UNIVERSAL", "TECH-STACK", "EDUCATION"]

# Extended 1-hour cache TTL (optional, for batch sessions). Leave False for the
# default 5-minute ephemeral cache, which needs no extra header.
USE_EXTENDED_CACHE_TTL = False
EXTENDED_CACHE_BETA_HEADER = "extended-cache-ttl-2025-04-11"
