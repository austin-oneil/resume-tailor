"""Independent hiring-manager auditor.

Deliberately a different lens than score_agent.py. score_agent does the
mechanical work: JD-keyword match, ATS readability, fact-checking claims
against the background doc, house-style compliance. This agent does the
human judgment call a real hiring manager makes — and critically, it only
ever sees what a real hiring manager would see: the resume, the cover
letter, and the job posting. It does NOT get the background doc, so it
can't fact-check; that's not its job and giving it ground truth would just
make it a worse copy of score_agent.

Verdict is binary (advance/reject) rather than a numeric score, because real
hiring decisions are binary (phone screen or no phone screen), not a
percentage.
"""
import re
from dataclasses import dataclass, field

import config
from src.client import as_str_list, get_client, print_cache_usage, today_str

_CONCERN_RE = re.compile(
    r"^\s*(?:"
    r"\[(?P<sev1>low|medium|high)\]\s*(?P<cat1>[a-z_]+)"       # [high] category:
    r"|(?P<sev2>low|medium|high)\s*\[(?P<cat2>[a-z_]+)\]"       # high[category]:
    r"|(?P<cat3>[a-z_]+)\s*\((?P<sev3>low|medium|high)\)"       # category (high):
    r")\s*:\s*(?P<detail>.+)$",
    re.IGNORECASE,
)
# Trailing "(fixable)" / "(structural)" tag on the detail text — see HM_TOOL's
# concerns description. Unknown/missing tag defaults to fixable so nothing is
# silently dropped from the revision budget.
_FIXABLE_TAG_RE = re.compile(r"\s*\((?P<tag>fixable|structural)\)\s*$", re.IGNORECASE)

# Observed failure mode distinct from client.py's _deep_flatten handling:
# rather than a well-formed <tag>...</tag> pair inside one string (which
# _deep_flatten already recovers), the model occasionally emits genuinely
# separate array elements that are semantically positive_signals content but
# landed in the concerns array, with the first misplaced element marked by a
# bare, unclosed '<positive_signals>' fragment — no closing tag, so there's
# nothing for _deep_flatten's tag-pair matcher to catch. Once that marker
# appears, treat it and everything after it in the list as leaked positive
# signals rather than concerns.
_POSITIVE_SIGNAL_LEAK_RE = re.compile(r"<\s*positive_signals\s*>\s*", re.IGNORECASE)

# Categories that describe the DOCUMENTS, not the candidate's history. The HM
# is deliberately denied background.md (see module docstring), so it cannot
# competently judge "structural" (a fact about the candidate no rewrite
# changes) for these — see HMResult.as_gap_dicts(). seniority_calibration,
# narrative_coherence, and red_flag legitimately can be structural and keep
# honoring the model's own tag.
_DOCUMENT_ONLY_CATEGORIES = {"cover_letter", "first_impression", "specificity"}


def _reroute_leaked_positive_signals(concerns: list[str], positive_signals: list[str]) -> tuple[list[str], list[str]]:
    clean_concerns = []
    leaked = []
    leaking = False
    for item in concerns:
        m = _POSITIVE_SIGNAL_LEAK_RE.search(item)
        if m:
            leaking = True
            item = (item[:m.start()] + item[m.end():]).strip()
        if leaking:
            if item:
                leaked.append(item)
        else:
            clean_concerns.append(item)
    return clean_concerns, positive_signals + leaked


# Real, shipped error (2026-08-07, Trivelta re-run): three purely positive
# sentences ("Genuine builder instincts...", "Cover letter is specifically
# written for this company...", "Demonstrated resourcefulness under
# pressure...") landed in `concerns` with none of the structured
# "[severity] category: detail" format the tool schema requires, and printed
# under a "concern:" label in the final report — exactly backwards. A
# different failure shape than the <positive_signals> tag leak above (no
# marker tag here at all), so it needs its own detection: a "concern" that
# doesn't match the required structured format AND contains no
# negative-indicator language at all is almost certainly misplaced
# positive_signals content, not a real (if malformed) concern.
_NEGATIVE_INDICATOR_RE = re.compile(
    r"\b(no|not|n't|nothing|lack|lacks|lacking|missing|weak|vague|thin|"
    r"unclear|absent|mismatch|inconsist|undermin|concern|risk|gap|red flag|"
    r"doesn't|don't|never|fails?|struggl|confus|question(able)?|shallow|"
    r"generic|oversell|undersell|disconnect)\b",
    re.IGNORECASE,
)
# A "rather than being X" / "instead of being X" contrast phrase praises the
# ABSENCE of a bad trait ("rather than being generic boilerplate") but still
# trips the negative-word scan above on the word inside it. Strip only this
# specific, unambiguous construction before scanning — deliberately NOT a
# bare "not X" strip, which would also eat the "not" out of a genuine
# malformed negative concern like "Not enough evidence of production-scale
# ownership" and cause a real concern to be mislabeled positive (verified
# this would happen before narrowing the pattern to just this case).
_NEGATED_TRAIT_RE = re.compile(
    r"\b(?:rather than|instead of)\s+being\s+\w+",
    re.IGNORECASE,
)


def _reroute_unformatted_positives(concerns: list[str], positive_signals: list[str]) -> tuple[list[str], list[str]]:
    clean_concerns = []
    leaked = []
    for item in concerns:
        scan_text = _NEGATED_TRAIT_RE.sub("", item)
        if not _CONCERN_RE.match(item) and not _NEGATIVE_INDICATOR_RE.search(scan_text):
            leaked.append(item)
        else:
            clean_concerns.append(item)
    return clean_concerns, positive_signals + leaked

HM_TOOL = {
    "name": "submit_hiring_manager_review",
    "description": "Submit your verdict as a senior hiring manager reviewing this application.",
    "input_schema": {
        "type": "object",
        "properties": {
            "verdict": {
                "type": "string",
                "enum": ["advance", "reject"],
                "description": "advance ONLY if you'd genuinely move this candidate to a phone screen.",
            },
            "overall_impression": {
                "type": "string",
                "description": (
                    "2-3 sentences, gut-level, as if leaving a note for a recruiter about "
                    "this candidate. Be direct, not diplomatic."
                ),
            },
            "concerns": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "Each concern as ONE self-contained string in the exact format "
                    "'[severity] category: detail (fixable|structural)' — e.g. '[high] "
                    "seniority_calibration: the resume claims more scope than the years "
                    "of experience support (structural)'. severity is one of "
                    "low/medium/high. category is one of first_impression/"
                    "narrative_coherence/seniority_calibration/specificity/red_flag/"
                    "cover_letter/other. Append '(fixable)' if a rewrite of these two "
                    "documents could plausibly resolve the concern (weak positioning, "
                    "buried evidence, a vague bullet, a generic letter, wrong emphasis), "
                    "or '(structural)' if it's a fact about the candidate's actual "
                    "history that no rewrite changes (years of experience, job titles "
                    "actually held, a technology never used, an employer never worked "
                    "at). Be honest about this split — a structural concern mislabeled "
                    "fixable just wastes a revision pass on something no phrasing can "
                    "fix."
                ),
            },
            "positive_signals": {
                "type": "array",
                "items": {"type": "string"},
                "description": "What genuinely excited you about this candidate, specifically — not generic praise.",
            },
        },
        "required": ["verdict", "overall_impression", "concerns", "positive_signals"],
    },
}

SYSTEM_INSTRUCTIONS = (
    "You are a senior hiring manager evaluating this resume and cover letter as if "
    "they landed in your inbox for a real open role at your company. You are NOT "
    "doing a mechanical keyword or ATS check — a separate system already handles "
    "that. You are making the human judgment call: after reading this, would you "
    "actually want to get this person on a call? You do not have access to any "
    "'ground truth' about the candidate beyond what's on the page, exactly like a "
    "real hiring manager wouldn't — judge only what's in front of you.\n\n"
    "Ground your evaluation in how real hiring managers actually behave, not an "
    "idealized checklist:\n\n"
    "1. THE 6-SECOND SCAN. Real reviewers skim the top third first — name, title "
    "line, summary, and the first bullet or two of the lead role. If that doesn't "
    "immediately signal 'this person can do this specific job,' most reviewers "
    "move on before reading the rest carefully, no matter what's buried further "
    "down. Judge the top third as if you only had 6 seconds, then read the rest.\n\n"
    "2. NARRATIVE COHERENCE. Does the career story cohere into something you could "
    "repeat back in one sentence, or does it read as disconnected jobs with no "
    "explainable arc? A career spanning different disciplines isn't automatically "
    "a red flag if the resume itself makes the connective tissue clear — but if it "
    "doesn't, that's worth raising.\n\n"
    "3. COVER LETTER FIT AND VOICE — judge this deliberately, it has been missed "
    "before on a real submitted letter. Four specific questions, not a generic "
    "'is it personalized' check:\n"
    "   a) CONTEXT FIT: does any opening hook, analogy, or scenario in the "
    "letter actually make sense for THIS company's real business and "
    "industry? A hook built around a completely different kind of business "
    "(e.g. a dental-practice analogy sent to an education company, a retail "
    "scenario sent to a fintech) is not a minor stylistic quibble — it reads "
    "as a copy-paste error and would make a real hiring manager question "
    "whether the candidate actually read the posting. Flag this as a "
    "high-severity, fixable concern whenever it happens, distinct from "
    "generic-template concerns.\n"
    "   b) COMPELLING: would this letter make you want to read the resume "
    "next, or does it read as forgettable filler? Say so honestly either "
    "way.\n"
    "   c) VOICE: does it sound like a specific person wrote it in their own "
    "voice, not a generic 'professional register that could describe "
    "anyone' — beyond just avoiding literal AI-tell phrases (a separate "
    "system checks those).\n"
    "   d) UNIQUE COMBINATION: does the letter actually convey what's "
    "distinctive about this candidate's particular mix of experience (not "
    "just restate that they meet the JD's requirements), or would swapping "
    "in a generic candidate with the same title produce a similar letter?\n\n"
    "4. SENIORITY CALIBRATION. Does the tone, scope, and confidence of the claims "
    "match the seniority of the role being applied to? Both directions are red "
    "flags: underselling (reads junior for a role wanting ownership) and "
    "overselling (buzzwords and scope claims that outrun the evidence behind "
    "them — real hiring managers specifically distrust resumes claiming more "
    "ownership or scope than the underlying experience plausibly supports).\n\n"
    "5. SPECIFICITY VS VAGUENESS. Experienced reviewers distrust vague claims "
    "('worked on various projects', 'helped improve X') and reward specific, "
    "checkable ones. Flag any bullet vague enough that a recruiter would "
    "silently discount it.\n\n"
    "6. CLASSIC RED FLAGS — actively check for these:\n"
    "   - Job-hopping without an explanation the resume itself provides (several "
    "short stints, especially under a year, with no context given)\n"
    "   - Unexplained gaps or timeline inconsistencies (dates that don't add up)\n"
    "   - Claims that read as too-good-to-be-true with no grounding evidence\n"
    "   - A cover letter that could have been sent to any company — no sign it "
    "was written for THIS role or company specifically\n"
    "   - Excessive length or density that doesn't respect the reader's time\n"
    "   - Anything that reads as generic AI-boilerplate rather than a specific "
    "person's voice describing real work (a separate system already checks for "
    "literal tells like em dashes; you're judging the higher-level impression)\n\n"
    "7. WHAT ACTUALLY EXCITES A HIRING MANAGER — look for these too, don't only "
    "hunt for problems:\n"
    "   - Quantified impact tied to a business outcome, not just activity\n"
    "   - Evidence of initiative or ownership beyond the minimum of the role\n"
    "   - Specific technologies or domain knowledge mapping to what this team "
    "actually needs, based on the job posting\n"
    "   - A cover letter demonstrating real understanding of this company's "
    "situation, not a template\n"
    "   - Signs of growth or increasing responsibility over time\n\n"
    "8. THE GUT CHECK. After all of the above: does this packet make you curious "
    "to talk to this person, or does it feel like one of a thousand generic "
    "applications? Be honest about this even if the mechanical boxes are checked.\n\n"
    "Verdict: 'advance' only if you would genuinely move this candidate to a phone "
    "screen at a real company for this real role. 'reject' otherwise. Be a REAL "
    "hiring manager, not a lenient rubber stamp — most submitted resumes do NOT "
    "get an interview in real hiring, so don't advance by default. But don't "
    "invent problems that aren't there either — if it's genuinely strong, say so "
    "and advance it."
)


@dataclass
class HMResult:
    verdict: str
    overall_impression: str = ""
    concerns: list[str] = field(default_factory=list)
    positive_signals: list[str] = field(default_factory=list)

    def as_gap_dicts(self) -> list[dict]:
        """Parses each concern string back into a dict shape, for reuse with
        draft_agent.revise()'s gaps param. Handles a few observed malformed
        shapes: multiple concerns landing in one array element separated by
        newlines (splits on those first), and severity/category written in
        an order _CONCERN_RE doesn't expect (matched via its alternation).
        Sorted high -> medium -> low so a capped revision budget spends its
        attention on whatever actually drove the reject. Each gap also
        carries fixable=True/False, parsed from a trailing (fixable)/
        (structural) tag — defaults to fixable when the tag is missing so
        nothing is silently dropped."""
        severity_rank = {"high": 0, "medium": 1, "low": 2}
        gaps = []
        for raw in self.concerns:
            for line in (l for l in raw.splitlines() if l.strip()):
                severity = "medium"
                category = "other"
                detail = line.strip()
                m = _CONCERN_RE.match(line)
                if m:
                    severity = (m.group("sev1") or m.group("sev2") or m.group("sev3") or "medium").lower()
                    category = (m.group("cat1") or m.group("cat2") or m.group("cat3") or "other").strip()
                    detail = m.group("detail").strip()
                fixable = True
                tag_m = _FIXABLE_TAG_RE.search(detail)
                if tag_m:
                    fixable = tag_m.group("tag").lower() == "fixable"
                    detail = detail[:tag_m.start()].strip()
                if category.lower() in _DOCUMENT_ONLY_CATEGORIES:
                    # The HM has no access to background.md (by design — see
                    # module docstring), so it cannot competently judge
                    # "structural" (a fact about the candidate's history) for
                    # a category that's inherently a property of the
                    # documents themselves, not the candidate. A false
                    # structural tag here previously terminated the gate on
                    # attempt 1 with no revision attempted (audit v3 §2.3) —
                    # e.g. a cover-letter opening that makes no sense for the
                    # target company cannot be a fact about Austin's work
                    # history under any reading.
                    fixable = True
                gaps.append({
                    "category": f"hiring_manager_{category}",
                    "detail": detail,
                    "severity": severity,
                    "fixable": fixable,
                })
        gaps.sort(key=lambda g: severity_rank.get(g["severity"], 1))
        return gaps


def review(
    job_title: str,
    jd_text: str,
    company_name: str,
    resume: str,
    cover_letter: str,
) -> HMResult:
    client = get_client()
    company_phrase = company_name or "your company"
    system = [
        {
            "type": "text",
            "text": f"Today's date is {today_str()}.\n\n{SYSTEM_INSTRUCTIONS}",
        }
    ]
    user_message = (
        f"You are hiring for: {job_title} at {company_phrase}.\n\n"
        f"Job posting:\n{jd_text}\n\n"
        f"--- Candidate's resume ---\n{resume}\n\n"
        f"--- Candidate's cover letter ---\n{cover_letter}\n\n"
        "Give your verdict as the hiring manager for this role."
    )
    last_result = None
    for attempt in range(1, 3):
        message = client.messages.create(
            model=config.HM_MODEL,
            max_tokens=3000,
            system=system,
            tools=[HM_TOOL],
            tool_choice={"type": "tool", "name": "submit_hiring_manager_review"},
            messages=[{"role": "user", "content": user_message}],
        )
        print_cache_usage("hiring_manager", message.usage)
        if message.stop_reason == "max_tokens":
            print("    [hiring_manager] WARNING: response truncated at max_tokens — output may be incomplete")

        for block in message.content:
            if block.type == "tool_use":
                raw_concerns = as_str_list(block.input.get("concerns", []))
                raw_positive = as_str_list(block.input.get("positive_signals", []))
                concerns, positive_signals = _reroute_leaked_positive_signals(raw_concerns, raw_positive)
                concerns, positive_signals = _reroute_unformatted_positives(concerns, positive_signals)
                last_result = HMResult(
                    verdict=block.input.get("verdict", "reject"),
                    overall_impression=str(block.input.get("overall_impression", "")),
                    concerns=concerns,
                    positive_signals=positive_signals,
                )
                break

        if last_result is None:
            raise RuntimeError("Hiring manager agent did not return a tool_use block")

        # Occasionally the model's output is genuinely degenerate (all fields
        # empty) regardless of shape — not just a recoverable formatting
        # quirk. One retry catches this without masking real "everything
        # checks out" reviews (which would still have a real impression).
        is_degenerate = (
            not last_result.overall_impression
            and not last_result.concerns
            and not last_result.positive_signals
        )
        if not is_degenerate or attempt == 2:
            return last_result
        print("    [hiring_manager] response looked empty/degenerate, retrying once...")

    return last_result
