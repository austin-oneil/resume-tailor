"""Parses the tagged background.md into sections and builds per-role-family subsets."""

import re
from pathlib import Path

import config

_HEADER_RE = re.compile(r"^## (?:\[(?P<tag>[A-Z-]+)\])?\s*(?P<title>.*)$")
_ABOUT_ME_RE = re.compile(r"^About Me\b", re.IGNORECASE)


def _extract_preamble_about_me(text: str) -> str:
    """Picks up any "About Me..." lines sitting above the first `## ` header
    (e.g. free-form intro text that isn't wrapped in a tagged section)."""
    first_header_idx = text.find("\n## ")
    preamble = text[:first_header_idx] if first_header_idx != -1 else text
    about_lines = [line for line in preamble.splitlines() if _ABOUT_ME_RE.match(line.strip())]
    return "\n\n".join(about_lines).strip()


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

    about_me = _extract_preamble_about_me(text)
    if about_me:
        sections["ABOUT_ME"] = about_me

    return sections


def load_candidate_info(path: Path = config.CANDIDATE_INFO_PATH) -> str:
    """Loads the candidate's own contact info, so the draft agent uses real
    values instead of inventing or blanking them out."""
    if not path.exists():
        return ""
    return path.read_text().strip()


def build_subset(sections: dict[str, str], role_family: str, candidate_info: str = "") -> str:
    """Concatenates the sections relevant to a role family, always including
    candidate contact info (if provided), UNIVERSAL, TECH-STACK, and Calibration Notes."""
    tags = config.ROLE_FAMILY_TAGS[role_family] + config.ALWAYS_ON_TAGS
    parts = []
    if candidate_info:
        parts.append(f"## Candidate Contact Info\n\n{candidate_info}")
    parts += [sections[tag] for tag in tags if tag in sections]
    if "CALIBRATION" in sections:
        parts.append(sections["CALIBRATION"])
    return "\n\n---\n\n".join(parts)
