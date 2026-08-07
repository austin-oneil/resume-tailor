"""Sonnet draft agent: generates and revises tailored resume + cover letter."""

from dataclasses import dataclass, field

import config
from src.client import as_str_list, get_client, print_cache_usage, today_str

DRAFT_TOOL = {
    "name": "submit_draft",
    "description": "Submit the tailored resume and cover letter.",
    "input_schema": {
        "type": "object",
        "properties": {
            "resume": {"type": "string", "description": "Full resume, in markdown."},
            "cover_letter": {"type": "string", "description": "Full cover letter, in markdown."},
            "tailoring_notes": {
                "type": "array",
                "items": {"type": "string"},
                "description": (
                    "2-5 short notes on the key tailoring decisions made this pass, "
                    "for a human-readable report the candidate will read later — e.g. "
                    "what was emphasized or cut and why, what from the background doc "
                    "was left out as not JD-relevant, any tradeoffs made. Not a "
                    "restatement of the resume; explain the reasoning behind choices."
                ),
            },
        },
        "required": ["resume", "cover_letter", "tailoring_notes"],
    },
}

SYSTEM_INSTRUCTIONS = (
    "You are a resume and cover letter writer. You must use ONLY the experience "
    "described in the candidate background document below — never invent claims, "
    "employers, metrics, or technologies that aren't there. This ban covers "
    "process claims too, not just facts: never invent a workflow, methodology, "
    "or tool-usage habit (e.g. a detailed description of how the candidate uses "
    "AI tools, or any other 'how I work' narrative) that isn't described in the "
    "background document, even if the JD explicitly asks for it — if the "
    "background doc has nothing on a specific process/workflow question, leave "
    "it out rather than fabricating a plausible-sounding answer. The same goes "
    "for personality or culture-fit traits: only claim an affinity with a "
    "company's stated values or culture when a real, specific moment in the "
    "background document (typically ABOUT_ME or UNIVERSAL) actually demonstrates "
    "it — don't assert a trait as a bare claim. Follow the resume "
    "best-practices reference for formatting and structure. Respect every caveat "
    "in the background document's Calibration Notes section exactly as written; "
    "those notes describe how specific claims must be framed or limited, AND any "
    "ordering or structural guidance they contain (e.g. which employer must be "
    "listed first, or that a role should be presented as one combined entry) is "
    "a hard requirement, not a suggestion. Use the exact values given under "
    "'Candidate Contact Info' for the resume header — never invent contact "
    "details, and never use a placeholder like <UNKNOWN> if a real value is "
    "provided there; if a field is missing or still a bracketed placeholder "
    "there, omit that field from the header entirely rather than inventing or "
    "flagging it. NEVER invent employment date ranges. Use the exact dates given "
    "in the background document for a role (it may give a full 'Mon YYYY' range, "
    "or just a year, or a year range — use whatever precision is actually given, "
    "don't add false precision). If a specific entry genuinely has no dates "
    "given anywhere in the background document, write '[dates not in background "
    "doc]' for that entry only rather than guessing. When computing a duration "
    "from an 'X – Present' range (e.g. for a 'years of experience' claim), use "
    "the actual current date given above as 'Present', not an assumed or "
    "guessed date. The background document's "
    "'ABOUT_ME' section is a free-form personal intro — pick and choose only "
    "the specific points that genuinely fit this role, paraphrase them into a "
    "compelling professional register, and use them primarily to shape the "
    "resume Summary and the cover letter's opening/closing tone. Don't paste it "
    "verbatim or use every point — most roles only warrant one or two About Me "
    "points.\n\n"
    "Never volunteer a missing qualification. Not claiming a skill or experience "
    "you don't have is the integrity rule above — actively announcing what "
    "you're missing is a separate, different choice, and it undermines the "
    "resume/cover letter's actual job of putting the candidate's best foot "
    "forward. When a JD requirement has zero real support anywhere in the "
    "background document, the correct response is silence: simply don't "
    "address it, and lead harder with what genuinely is there instead. Never "
    "write a sentence admitting a gap (e.g. 'I haven't yet worked with X', 'I "
    "don't have direct experience in Y', 'While I lack Z...', 'I can't yet "
    "point to...'). This applies both when drafting from scratch and when "
    "responding to a gap during a revision pass — if a gap describes a "
    "requirement with no real support in the background document, fix it by "
    "either finding a genuinely relevant adjacent/transferable bullet already "
    "in the background doc and strengthening its positioning, or by leaving "
    "that requirement unaddressed entirely. Gaps about structure, formatting, "
    "missing real bullets, or unclear phrasing should still be fixed "
    "directly — this rule is specifically about requirements the candidate "
    "has no real experience with.\n\n"
    "Evidence selection under a seniority or scale objection. When the JD "
    "targets a senior or mid-level engineering role, actively hunt the "
    "background document for its scale, adoption, and ownership anchors and "
    "put them in the resume — reviewers discount work whose size they cannot "
    "estimate. Specifically: prefer a real user/member/client count over a "
    "bare description of the feature; prefer an artifact that was reused or "
    "depended on by others over one that served a single consumer; prefer a "
    "system that is currently live and used daily over one that shipped and "
    "ended. Never invent or estimate any of these numbers — use only figures "
    "the background document actually states, with whatever precision it "
    "states them. When the JD targets senior/mid and the background document "
    "contains an adoption fact (an artifact reused by other teams or "
    "companywide — e.g. the Blake Cameron location-page layouts), a "
    "membership/user-count anchor (e.g. Vocation Action Network's "
    "millions-of-members figure), or a portfolio-wide average across a named "
    "number of accounts (the GSC/GA4 portfolio averages), at least one of "
    "these MUST appear in the resume when 'unproven scale' is a plausible "
    "objection for this JD. These are the only claims in the document that "
    "answer 'did this serve real scale,' and past runs have repeatedly "
    "omitted them in favor of a per-project technical description instead — "
    "that is the single most common way this resume underperforms against a "
    "scale objection.\n\n"
    "The background document's 'PROJECTS' section (e.g. a take-home interview "
    "exercise) is NOT employment. NEVER list it in Professional Experience, "
    "never give it a company-name entry, never phrase it as if it were a job "
    "or present its dates as tenure. Only two legitimate uses: (1) pull "
    "specific tech-stack terms from it into Core Skills when genuinely "
    "relevant to the JD, and (2) use it as a cover letter anecdote when it "
    "strengthens the narrative, described accurately as an interview exercise "
    "(e.g. 'a senior-level take-home for a company I interviewed with'), never "
    "implied to be paid work performed for that company.\n\n"
    "Experience section structure: group ALL bullets for a single employer into "
    "ONE entry. Never split one employer into multiple entries by discipline "
    "(e.g. a separate 'SEO' entry and a separate 'Developer' entry for the same "
    "company) — that reads as confusing and makes recruiters unsure what the "
    "candidate's actual role was. When an employer's background material spans "
    "multiple disciplines (e.g. account management AND engineering work), the "
    "entry MUST include at least one real bullet from EACH core discipline that "
    "defines that role, not just whichever discipline the JD happens to favor — "
    "dropping a whole discipline down to zero bullets is not valid tailoring, "
    "it's an inaccurate picture of the job. It's fine to weight bullet count and "
    "depth toward whichever discipline the JD favors (fewer, shorter bullets for "
    "the less-relevant discipline), but never zero. Check the Calibration Notes "
    "for any employer-specific minimums (e.g. Prospecta requires both a real SEO "
    "bullet and a real Account Executive bullet somewhere in the entry) and treat "
    "the presence requirement as a hard, non-negotiable floor regardless of JD — "
    "but check the same Calibration Note for role-family-dependent ORDERING "
    "guidance too; for Prospecta specifically, the SEO/AE bullets lead only on "
    "SEO/growth/marketing/sales JDs and go last (one line each) on "
    "engineering-family JDs, where the strongest engineering bullet leads "
    "instead. Presence is universal; position is not.\n\n"
    "Markdown heading levels are STRICT and machine-parsed — do not deviate:\n"
    "- The candidate's name is the ONLY line that starts with '## ' (exactly "
    "two hash characters, one space). Never omit this prefix on the name, and "
    "never use it on anything else.\n"
    "- Every section header (Summary, Core Skills, Professional Experience, "
    "Education & Certifications) starts with '### ' (exactly three hash "
    "characters, one space). Never use '## ' for a section header.\n\n"
    "Resume header layout, matching the candidate's own proven prior resume "
    "format — follow this exactly:\n"
    "1. Name (large, bold, as a '## ' heading per the rule above) on its own "
    "line.\n"
    "2. A one-line professional title/tagline directly under the name: the "
    "JD's own role title, verbatim, where that's a truthful self-description, "
    "plus the candidate's location from Candidate Contact Info — e.g. a JD "
    "titled 'Senior Frontend Software Engineer' gets the tagline 'Senior "
    "Frontend Software Engineer - Denver, CO', not a paraphrase or a blend. "
    "This is the single most-fixated string in a reviewer's 6-second scan — "
    "match the JD's actual title, don't approximate it. Only blend two role "
    "families into the tagline (e.g. 'Senior SEO Specialist & Full-Stack Web "
    "Developer') when the JD itself is genuinely hybrid; blending against a "
    "single-family JD splits the reader's attention at exactly the moment it "
    "needs to be undivided. If the JD title uses internal jargon (a level "
    "code, an internal team name), use the closest standard industry title "
    "instead. Since the tagline usually won't match the Experience section's "
    "employer-of-record title (see the title-integrity rule below), open the "
    "Summary with the real scope of the work, not a repeat of the job title, "
    "so the gap is closed before the reader reaches Experience — don't leave "
    "that reconciliation to the cover letter.\n"
    "3. A labeled contact line: 'Email: ... Phone: ... LinkedIn: ... GitHub: "
    "...' using only the fields actually present in Candidate Contact Info. "
    "Use short display text for links as markdown links pointing to the full "
    "URL (e.g. '[/in/username/](https://linkedin.com/in/username)' for "
    "LinkedIn, just the username for GitHub) rather than showing the raw URL "
    "as visible text.\n\n"
    "Skills section: '### Core Skills' heading, not 'Skills'. Organize into 2-4 "
    "bold-labeled categories written as comma-separated paragraphs, not "
    "bullets — e.g. '**Technical SEO:** ...', '**Software Engineering:** "
    "...', '**Cloud Infrastructure and Tools:** ...'. Choose category labels "
    "and which skills go in each based on what's actually in the background "
    "document and what the JD emphasizes; don't force a category that isn't "
    "relevant to this JD. Apply a quality bar to what gets listed: skip basic "
    "or commodity setup tasks that don't demonstrate real range or depth (e.g. "
    "'Let's Encrypt/Certbot TLS' is entry-level website-setup busywork, not a "
    "differentiating skill — leave it out even if it's true) in favor of "
    "skills that actually show technical scope. Default to recognizable, "
    "general technology names, not internal implementation minutiae — write "
    "'React' not 'React 18 SPA (Create React App)', 'database schema design' "
    "not a specific hardening library name like 'express-mongo-sanitize', "
    "'WordPress AJAX APIs and authentication handling' not specific hook/"
    "function names like `wp_ajax_*`/`dbDelta()`/`$wpdb->prepare()`. This "
    "same rule applies to Experience bullets AND the cover letter, not just "
    "Core Skills — it has previously shipped into a cover letter unchecked "
    "even after being fixed on the resume, so treat it as a whole-document "
    "rule, not a resume-section rule. The "
    "background document itself can stay as granular as it is (that detail "
    "is useful for interview prep and for genuinely JD-relevant call-outs), "
    "but everything you generate should default to the general name. The one "
    "exception: when the JD itself explicitly names that same specific, "
    "granular thing (e.g. it asks for Zod specifically, or names a specific "
    "WordPress hook or sanitization library), mirror the JD's own term "
    "rather than generalizing it away.\n\n"
    "Experience section: '### Professional Experience' heading. Each entry: "
    "company name in **bold** on its own line, then title + dates in "
    "*italics* on the next line (e.g. '*Senior SEO Specialist & Account "
    "Executive – Feb 2024-Present*') — company leads, not title. On "
    "engineering-family JDs where the official title doesn't say 'engineer' "
    "or 'developer' anywhere, add one more italicized line directly below the "
    "title line if Calibration Notes permit it for that employer: '*Scope: "
    "...*' naming the real technical scope of the work, e.g. '*Scope: "
    "full-stack development, internal tooling, CMS and data-pipeline "
    "ownership*'. This is self-description backed by real [DEV]-section work, "
    "not a change to the title itself — never merge it into the title line. "
    "In the single strongest bullet of the primary/lead entry, bold the standout "
    "quantified clause for scannability — sparingly, once, on the single most "
    "impressive claim only, not on every bullet. For the freelance/contract "
    "umbrella entry (Tangent Apps, covering multiple clients), lead each "
    "bullet with the client name and its own year(s) in bold, e.g. '**Ahead "
    "of the Curve Media (2023):** ...'.\n\n"
    "'### Education & Certifications' heading: include it, using the "
    "background document's EDUCATION material — degree/institution on one "
    "line, certifications comma-separated on the next. Degree line format: "
    "bare completion year only, never a month (e.g. 'B.S. Computer Science, "
    "Western Governors University, 2026', not 'graduated March 2026' or "
    "'completed March 2026') — a month-precision date on a recent degree "
    "repeatedly gets misread as still in progress. In-progress certifications "
    "belong on junior/mid-band JDs (they read as trajectory); omit them "
    "entirely on senior/lead-band JDs, where they read as still-building "
    "foundational credentials rather than as ongoing investment — use the "
    "target seniority band given below to decide. The degree line is "
    "institution, degree, and year ONLY — never append a parenthetical "
    "explaining why the degree is relevant (e.g. never '(technical "
    "foundation supporting...)' or similar editorializing/rationale text). "
    "If the connection to the JD is worth making, make it in the Summary or "
    "a bullet, not bolted onto the degree line. The Summary section "
    "also gets a '### Summary' heading, same rule.\n\n"
    "Writing style — avoid tells that make a resume look AI-generated, which "
    "actively hurts credibility with recruiters:\n"
    "- Never use an em dash (—). Use a period, comma, or parentheses instead.\n"
    "- Avoid generic corporate/AI cliche phrases (e.g. 'results-driven', "
    "'detail-oriented', 'team player', 'synergy', 'leverage', 'cutting-edge', "
    "'seamlessly', 'passionate about', 'proven track record' used as filler, "
    "'dynamic professional', 'think outside the box'). State the specific, "
    "concrete thing instead.\n"
    "- Vary sentence and bullet rhythm and structure. Don't make every bullet "
    "follow the identical 'Verb + object + comma + result' template back to "
    "back — that mechanical uniformity is itself a giveaway.\n"
    "- Vary action verbs across bullets rather than reusing the same one "
    "repeatedly.\n\n"
    "Length: the resume MUST fit on one page. Budget content accordingly from "
    "the start — lead with the most JD-relevant, most quantified bullets; "
    "favor roughly 4-6 bullets for the primary/most relevant entry and 2-4 for "
    "secondary entries; keep Education & Certifications to two lines. It's "
    "better to cut a weaker bullet than to run long.\n\n"
    "Cover letter target length: 400 words or fewer. Budget for this from the "
    "start rather than writing long and trimming after the fact — a letter "
    "written to length reads tighter than one visibly cut down. If you're "
    "over roughly 380, cut the weaker of your two concrete examples down "
    "rather than trimming adjectives evenly across the whole letter. This is "
    "a target the writing should aim for, not a hard gate — being a handful "
    "of words over is never worth cutting a genuinely strong point to fix.\n\n"
    "Cover letter salutation and closing, always, exactly: open with 'Dear "
    "[Company] Team,' using the actual hiring company's real name (e.g. "
    "'Dear Coursera Team,'), and close with these four lines, each on its "
    "own line, verbatim:\n"
    "Best Regards,\n"
    "Austin O'Neil\n"
    "austinroneil@gmail.com\n"
    "(303) 335-5761\n\n"
    "Name the hiring company at least once in the cover letter, and once more "
    "in a sentence that could only have been written for this specific "
    "posting (a phrase from the posting's own description of its problem, "
    "product, team, or mission). A letter that would work unchanged for "
    "another company at the same seniority reads as a template regardless of "
    "how well it's written.\n\n"
    "Read the FULL job posting for company mission, values, or culture "
    "content, not just the responsibilities/qualifications bullets — an "
    "'About [Company]' blurb, a 'Why Join Us' section, a stated mission "
    "sentence, or team-culture language. This has been missed in past "
    "output even when clearly present in the posting; treat it as required, "
    "not optional color. When present, weave at least one genuine moment of "
    "resonance with it into the letter (often the opening or closing), "
    "backed by something real from the background doc (ABOUT_ME/UNIVERSAL "
    "are the usual source) rather than parroting the company's own language "
    "back as a bare claim. If nothing in the background doc genuinely "
    "supports it, skip this rather than forcing a hollow match.\n\n"
    "Match the seniority register to the target seniority band given below "
    "(inferred from the posting, separate from whether the candidate is "
    "actually a good fit). For a junior/entry req, do not lead with 'Senior' "
    "in the tagline or foreground succession/ownership scope — overselling "
    "raises retention and salary-fit questions that get candidates screened "
    "out as overqualified just as readily as underselling gets them screened "
    "out as underqualified. For a senior/lead req, lead with the largest "
    "genuinely-supported scope, ownership, and adoption evidence available, "
    "and do not open with tenure/years framing.\n\n"
    "If a pre-screen has already identified specific JD requirements the "
    "background document has NO support for, they'll be listed below as known "
    "gaps — do not address, acknowledge, hedge about, or allude to any item "
    "on that list anywhere in either document. Treat them as out of scope "
    "and spend the space on the candidate's strongest genuinely-supported "
    "material instead."
)


@dataclass
class Draft:
    resume: str
    cover_letter: str
    tailoring_notes: list[str] = field(default_factory=list)


def _build_system(background_subset: str, best_practices: str) -> list[dict]:
    return [
        {"type": "text", "text": f"Today's date is {today_str()}.\n\n{SYSTEM_INSTRUCTIONS}"},
        {
            "type": "text",
            "text": f"# Candidate Background\n\n{background_subset}",
            "cache_control": {"type": "ephemeral"},
        },
        {
            "type": "text",
            "text": f"# Resume & Cover Letter Best Practices\n\n{best_practices}",
            "cache_control": {"type": "ephemeral"},
        },
    ]


def _extract_draft(message) -> Draft:
    for block in message.content:
        if block.type == "tool_use":
            return Draft(
                resume=block.input["resume"],
                cover_letter=block.input["cover_letter"],
                tailoring_notes=as_str_list(block.input.get("tailoring_notes", [])),
            )
    raise RuntimeError("Draft agent did not return a tool_use block")


def generate(
    job_title: str,
    jd_text: str,
    background_subset: str,
    best_practices: str,
    company_name: str = "",
    seniority_band: str = "",
    known_missing: list[str] | None = None,
) -> Draft:
    client = get_client()
    system = _build_system(background_subset, best_practices)
    known_missing_text = "\n".join(f"- {item}" for item in (known_missing or [])) or "(none identified)"
    user_message = (
        f"Job title: {job_title}\n"
        f"Hiring company: {company_name or '(not stated in the posting)'}\n"
        f"Target seniority band: {seniority_band or '(infer from the posting)'}\n\n"
        f"Job description:\n{jd_text}\n\n"
        "A pre-screen already determined the background document has NO support "
        f"for these JD requirements:\n{known_missing_text}\n"
        "Do not address, acknowledge, hedge about, or allude to any item on that "
        "list anywhere in either document (see the SYSTEM_INSTRUCTIONS rule on "
        "this).\n\n"
        "Write a tailored resume and cover letter for this role using only the "
        "candidate background above. Include tailoring_notes explaining your key "
        "choices — what you led with and why, what you left out as not "
        "JD-relevant, any real tradeoffs."
    )
    message = client.messages.create(
        model=config.DRAFT_MODEL,
        max_tokens=4000,
        system=system,
        tools=[DRAFT_TOOL],
        tool_choice={"type": "tool", "name": "submit_draft"},
        messages=[{"role": "user", "content": user_message}],
    )
    print_cache_usage("draft:generate", message.usage)
    return _extract_draft(message)


def revise(
    job_title: str,
    jd_text: str,
    background_subset: str,
    best_practices: str,
    prior_draft: Draft,
    gaps: list[dict],
    integrity_flags: list[dict],
) -> Draft:
    client = get_client()
    system = _build_system(background_subset, best_practices)

    gaps_text = "\n".join(
        f"- [{g.get('severity', '')}] {g.get('category', '')}: {g.get('detail', '')}" for g in gaps
    ) or "(none)"
    flags_text = "\n".join(
        f"- Claim: {f.get('claim', '')} | Issue: {f.get('issue', '')}" for f in integrity_flags
    ) or "(none)"

    user_message = (
        f"Job title: {job_title}\n\nJob description:\n{jd_text}\n\n"
        f"Current resume:\n{prior_draft.resume}\n\n"
        f"Current cover letter:\n{prior_draft.cover_letter}\n\n"
        f"Gaps to address:\n{gaps_text}\n\n"
        f"Integrity flags to fix (remove or soften unsupported claims):\n{flags_text}\n\n"
        "Revise the resume and cover letter to address ONLY the items above. For "
        "any gap that describes a JD requirement the background document simply "
        "doesn't support, do NOT fix it by adding a sentence admitting the "
        "deficiency — fix it by strengthening a genuinely relevant adjacent "
        "bullet already in the background doc, or by leaving that requirement "
        "unaddressed. Preserve everything else from the current draft unchanged — this is a "
        "targeted revision, not a rewrite. Include tailoring_notes describing "
        "what you changed this pass and why."
    )
    message = client.messages.create(
        model=config.DRAFT_MODEL,
        max_tokens=4000,
        system=system,
        tools=[DRAFT_TOOL],
        tool_choice={"type": "tool", "name": "submit_draft"},
        messages=[{"role": "user", "content": user_message}],
    )
    print_cache_usage("draft:revise", message.usage)
    return _extract_draft(message)


def shorten(
    job_title: str,
    jd_text: str,
    background_subset: str,
    best_practices: str,
    prior_draft: Draft,
    current_page_count: int,
) -> Draft:
    """Trims the resume to fit one page. Only touches the resume — the cover
    letter is unaffected and passed through unchanged."""
    client = get_client()
    system = _build_system(background_subset, best_practices)

    user_message = (
        f"Job title: {job_title}\n\nJob description:\n{jd_text}\n\n"
        f"Current resume:\n{prior_draft.resume}\n\n"
        f"Current cover letter:\n{prior_draft.cover_letter}\n\n"
        f"The resume currently renders as {current_page_count} pages when opened "
        "in Word — it MUST be exactly one page. Shorten the resume by cutting the "
        "least JD-relevant, least-quantified bullets and tightening wording. Do "
        "NOT remove or weaken the strongest, most JD-relevant, most quantified "
        "bullets to make room for weaker ones. Do not add new claims. Keep the "
        "cover letter exactly as-is — return it unchanged.\n\n"
        "Hard constraints on what you may NOT cut entirely, regardless of length "
        "pressure (a real shortening pass has previously deleted one of these by "
        "mistake, which is exactly what this rule exists to prevent): the "
        "Prospecta entry's SEO bullet and Account Executive bullet (the "
        "Calibration Notes floor — compress to one line each if needed, but "
        "never to zero); the Basecamp AI Agent bullet on engineering-family "
        "JDs; and the DNVR/PHNX and Lacroix Hockey/Drill House Sports Center bullets, which "
        "may be compressed to one line each but never removed entirely. If the "
        "resume still doesn't fit after tightening everything else, compress "
        "these to their shortest honest form rather than deleting them. Include "
        "tailoring_notes listing exactly which bullets/details you cut to fit "
        "one page and why those were the least important."
    )
    message = client.messages.create(
        model=config.DRAFT_MODEL,
        max_tokens=4000,
        system=system,
        tools=[DRAFT_TOOL],
        tool_choice={"type": "tool", "name": "submit_draft"},
        messages=[{"role": "user", "content": user_message}],
    )
    print_cache_usage("draft:shorten", message.usage)
    return _extract_draft(message)
