"""Parses the tagged background.md into sections and builds per-role-family subsets."""

import re
from pathlib import Path

import config

_HEADER_RE = re.compile(r"^## (?:\[(?P<tag>[A-Z-]+)\])?\s*(?P<title>.*)$")


def _extract_preamble(text: str) -> str:
    """Returns the ENTIRE preamble above the first `## ` header.

    Was `_extract_preamble_about_me`, which kept only lines literally starting
    with "About Me" and silently discarded everything else up there. That threw
    away two load-bearing facts on every single run since they were written
    (found 2026-08-22):

      - "Work Authorization: U.S. citizen, eligible to hold and maintain a
        federal security clearance..." — so no agent could state citizenship or
        clearance eligibility on a federal req. The 2026-08-22 SMX run (a
        cleared federal role) shipped with neither mentioned and the simulated
        hiring manager rejected partly on that, calling it a required
        non-negotiable left unaddressed.
      - "Front-End Experience Tenure..." — a paragraph written specifically to
        answer JD asks for "N years of front-end experience," documenting 5+
        years of continuous front-end work across five engagements. Invisible to
        every agent, so the pre-draft fit gate had no way to answer a front-end
        tenure requirement and flagged it as genuinely missing (observed on the
        SMX run, which asks for 2 years of front-end experience).

    Deliberately returns the whole preamble rather than a smarter filter: the
    bug here WAS the filter, and the same class of silent drop already bit this
    codebase once before at the section level (see build_subset's docstring on
    role-family gating). A few lines of document metadata reaching the agents is
    harmless; another invisible fact is not."""
    first_header_idx = text.find("\n## ")
    preamble = text[:first_header_idx] if first_header_idx != -1 else text
    return preamble.strip()


def parse_background(path: Path = config.BACKGROUND_PATH) -> dict[str, str]:
    """Splits background.md on top-level `## [TAG] ...` headers.

    Returns {tag: section_text}, plus a "CALIBRATION" key for the
    Calibration Notes section (which has no bracket tag), and an "ABOUT_ME"
    key for any free-form "About Me" intro text above the first header.
    """
    text = path.read_text()
    sections: dict[str, str] = {}
    current_tag = None
    current_lines: list[str] = []

    for line in text.splitlines():
        match = _HEADER_RE.match(line) if line.startswith("## ") else None
        if match:
            if current_tag is not None:
                sections[current_tag] = "\n".join(current_lines).strip()
            tag = match.group("tag")
            title = match.group("title").strip()
            if tag:
                current_tag = tag
            elif title.lower().startswith("calibration notes"):
                current_tag = "CALIBRATION"
            else:
                current_tag = title.upper().replace(" ", "_")
            current_lines = [line]
        elif current_tag is not None:
            current_lines.append(line)

    if current_tag is not None:
        sections[current_tag] = "\n".join(current_lines).strip()

    # Keyed ABOUT_ME for compatibility: config.ALWAYS_ON_TAGS and several
    # draft_agent prompt references name it, and the About Me intro is still
    # the bulk of what it carries — it now also carries the rest of the
    # preamble (work authorization, front-end tenure) instead of dropping it.
    preamble = _extract_preamble(text)
    if preamble:
        sections["ABOUT_ME"] = preamble

    return sections


def load_candidate_info(path: Path = config.CANDIDATE_INFO_PATH) -> str:
    """Loads the candidate's own contact info, so the draft agent uses real
    values instead of inventing or blanking them out."""
    if not path.exists():
        return ""
    return path.read_text().strip()


def build_subset(sections: dict[str, str], role_family: str, candidate_info: str = "") -> str:
    """Concatenates the ENTIRE background document for the drafting/scoring
    agents, always leading with candidate contact info (if provided) and
    trailing with Calibration Notes.

    Previously this filtered sections down to just the tags relevant to
    `role_family` (see config.ROLE_FAMILY_TAGS, now unused here) — a JD
    classified as "seo-growth" would only ever see SEO + SALES-TECH, never
    DEV. That silently walled off real, relevant evidence: a real, shipped
    incident (2026-08-08, a Webflow-adjacent Senior Marketing Manager JD)
    classified as seo-growth and never saw the DEV-section narrative of the
    candidate's actual hands-on Webflow ownership work (the SALES-TECH
    version of the same client relationship never names Webflow at all), so
    the drafting agent had no way to know that experience existed. The
    codebase already had a partial acknowledgment of this exact failure mode
    (see supervisor.jd_coverage_backstop's docstring) but only flagged it
    after the fact rather than fixing the actual information gap.
    `role_family` is kept as a parameter for now (output.py still uses the
    classifier's label for logging/report naming) but no longer gates what
    the model gets to see — the drafting/scoring agents are trusted to judge
    JD-relevance themselves across the full document rather than having
    candidate evidence pre-filtered out by a cheap title-keyword guess."""
    parts = []
    if candidate_info:
        parts.append(f"## Candidate Contact Info\n\n{candidate_info}")
    parts += [text for tag, text in sections.items() if tag != "CALIBRATION"]
    if "CALIBRATION" in sections:
        parts.append(sections["CALIBRATION"])
    return "\n\n---\n\n".join(parts)
