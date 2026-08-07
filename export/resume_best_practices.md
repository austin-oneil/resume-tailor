# Resume & Cover Letter Best Practices Reference

Use this as the house style for every resume and cover letter generated. Edit freely —
this file is loaded as-is and cached alongside the background doc.

## ATS Formatting

- Plain markdown structure only: `#`/`##` headings, `-` bullets, no tables, no columns,
  no text boxes, no images, no icons. ATS parsers frequently mangle multi-column layouts.
- Standard section headers ATS parsers recognize: `Summary`, `Professional Experience`,
  `Core Skills`, `Education & Certifications`. These are this candidate's proven house
  headers (see Section Structure below) — don't drift back to generic "Experience" /
  "Skills" naming.
- Use the exact job title and key skill terms from the JD somewhere in the resume
  (naturally, not stuffed) — many ATS systems do literal keyword matching before a human
  ever sees the resume.
- Use the exact dates given in the background doc for a role, at whatever precision it
  actually provides (full month, or just a year, or a year range). Never invent a
  plausible-looking date range to fill a gap — if a specific entry genuinely has no
  dates anywhere in the background doc, an honest `[dates not in background doc]`
  placeholder for that entry beats a fabricated one.
- No headers/footers — some ATS parsers drop content placed there.
- Spell out acronyms at least once if they appear in the JD's required-skills list.

## Section Structure (resume)

This structure matches the candidate's own proven prior resume — follow it exactly
rather than defaulting to a generic resume template.

1. **Header** — three lines:
   1. Name, large and bold.
   2. A one-line professional title/tagline tailored to this JD, plus location
      (e.g. "Senior SEO Specialist & Full-Stack Web Developer - Denver, CO").
   3. A labeled contact line: `Email: ... Phone: ... LinkedIn: ... GitHub: ...`,
      using only fields actually present in Candidate Contact Info. Links use short
      display text (e.g. `/in/username/`, or just the GitHub username) as a markdown
      link to the full URL — never show the raw URL as visible text.
2. **Summary** — 2-3 lines, role-specific, naming the target role and the single
   strongest matching qualification. Not a generic objective statement.
3. **Core Skills** (not "Skills") — 2-4 bold-labeled categories written as
   comma-separated paragraphs, not bullets (e.g. `**Technical SEO:** ...`,
   `**Software Engineering:** ...`, `**Cloud Infrastructure and Tools:** ...`).
   Choose categories and contents based on what's in the background doc and what the
   JD emphasizes — don't force an irrelevant category in. Apply a quality bar: leave
   out basic/commodity setup tasks that don't show real range or depth (e.g. "Let's
   Encrypt/Certbot TLS" is entry-level website-setup busywork, not a differentiating
   skill, even though it's true) in favor of skills that actually demonstrate scope.
4. **Professional Experience** (not "Experience") — ordered by employer primacy (per
   any ordering guidance in the background doc's Calibration Notes), not strictly
   reverse-chronological. Each employer appears as exactly ONE entry — never split a
   single employer into multiple entries by discipline (e.g. a separate "SEO" entry
   and a separate "Developer" entry for the same company). If a role spans multiple
   disciplines, the entry MUST include at least one real bullet from EACH core
   discipline that defines the role — dropping a whole discipline to zero bullets is
   not valid tailoring. Weight bullet count toward whichever discipline the JD favors,
   but never zero; check Calibration Notes for employer-specific minimums (e.g.
   Prospecta requires both a real SEO bullet and a real Account Executive bullet,
   ahead of the dev bullets) and treat them as a hard floor. Each entry: **company name**
   in bold on its own line, then *title – dates* in italics on the next line (company
   leads, not title), then 3-6 bullets. Lead bullets with the most JD-relevant, most
   quantified achievements; bold the single standout quantified clause in the lead
   entry's top bullet only (sparingly — once, not on every bullet). For a
   freelance/contract umbrella entry (e.g. Tangent Apps) covering multiple clients,
   lead each bullet with the client name and its own year(s) in bold, e.g.
   `**Ahead of the Curve Media (2023):** ...`.
5. **Education & Certifications** — include whenever the background doc has an
   `EDUCATION` section: degree/institution on one line, certifications
   comma-separated on the next.

## Bullet Writing

- Start with a strong past-tense action verb (Built, Migrated, Diagnosed, Managed,
  Closed, Reduced) — never "Responsible for."
- Quantify wherever the background doc has a number: %, $, time saved, count of
  clients/users, before/after metrics. Don't invent a number that isn't in the source
  material — an unquantified but true bullet beats a fabricated metric.
- One idea per bullet. Avoid stacking three achievements into one run-on line.
- Mirror the JD's terminology where the background doc genuinely supports it (e.g. if
  the JD says "stakeholder management" and the background doc describes exactly that,
  use the JD's phrase — don't force it where the underlying experience doesn't match).
- Vary action verbs across bullets instead of reusing the same one repeatedly. Rotate
  through categories rather than defaulting to "spearheaded" or "leveraged" for
  everything:
  - Leadership: Led, Directed, Coordinated, Mentored, Championed
  - Building: Built, Developed, Designed, Architected, Launched
  - Improving: Streamlined, Optimized, Reduced, Automated, Modernized
  - Communicating: Presented, Negotiated, Translated, Facilitated, Advised
  - Problem-solving: Diagnosed, Resolved, Debugged, Troubleshot, Untangled
- **Technical bullet formula** (for dev-heavy roles, when the underlying facts support
  it): `[Action verb] + [what was built/fixed] + [scale or impact, if the background doc
  actually states one] + [technology used]`. Example shape: "Rebuilt a WordPress CMS for
  reliability and content delivery using custom PHP, resolving recurring client-reported
  outages." Only include a scale/impact clause when the background doc gives you one —
  see Quantification below.

## Quantification — Real Numbers Only

- Every number in the output must trace back to an actual figure in the background doc.
  **Never estimate, round up, or invent a plausible-sounding metric that isn't there** —
  this includes phrasing like "~40%" or "100+" when the background doc gives no basis for
  it. An unquantified but true bullet always beats a fabricated or guessed metric.
  (Some generic resume-writing guides recommend "conservative estimation" for missing
  numbers — that approach is intentionally rejected here because it's indistinguishable
  from fabrication once it lands on a resume, and directly conflicts with the integrity
  requirement this tool is built around.)
- If a genuinely strong bullet has no number behind it, it's fine to leave it unquantified
  rather than force a metric that doesn't exist.

## Avoiding AI-Written Tells

Recruiters and ATS vendors are increasingly screening for AI-generated resumes, and being
flagged as AI-written can hurt a candidate's credibility even when every claim is true.
Concrete things to avoid:

- **Em dashes.** The single most common tell — AI drafting tools overuse them
  constantly, while human writers use them sparingly. Never use one; use a comma,
  period, or parentheses instead.
- **Generic corporate/AI cliches with nothing behind them**: "results-driven,"
  "detail-oriented," "team player," "synergy," "leverage" (as a filler verb),
  "cutting-edge," "seamlessly," "passionate about," "dynamic professional," "proven
  track record" used without a concrete claim attached, "think outside the box." State
  the specific thing instead of the label for it.
- **Mechanical uniformity.** Don't write every bullet in the identical
  verb-object-comma-result template back to back — that metronomic rhythm is itself a
  giveaway. Vary sentence length and structure.
- **Inflated or unexplainable metrics.** A number the candidate couldn't defend in an
  interview is a red flag independent of the AI question — see Quantification above.
- **Voice mismatch.** Keep the tone grounded and specific to this candidate's actual
  background doc content, not a generic "impressive-sounding professional" register that
  could describe anyone.

## Cover Letter

- 3-4 short paragraphs, under 350 words total.
- Paragraph 1: an opening hook (see below), not a role announcement.
- Paragraph 2-3: two concrete, quantified examples from the background doc that map
  directly to the JD's stated requirements — not a restatement of the resume.
- Closing: brief, confident, no groveling ("I would welcome the opportunity...").
- No generic filler ("I am a hard worker who is passionate about..."). Every sentence
  should be doing work a generic applicant couldn't also claim.

### Opening Hooks

Only use hook types this tool can actually back up with real material — the JD text and
the candidate background doc. Don't fabricate outside knowledge (a recent company
launch, a mutual connection, funding news) that isn't given to you.

- **Achievement-led**: open with the single strongest, most specific, quantified
  achievement from the background doc that maps to the JD's top requirement, then
  connect it to the role. ("Grew organic traffic 40%+ within two months for a 30-client
  book, entirely through technical SEO — the same discipline this Growth Engineer role
  needs applied to your funnel.")
- **Problem-solver**: open by naming a specific challenge the JD itself describes (in
  its own words, e.g. "aligning technical and business stakeholders," "scoping
  integrations under deadline pressure"), then immediately show a real background-doc
  example of navigating exactly that. Grounded in the JD's actual language, not assumed
  company context.
- Do not use a "specific company knowledge" or "mutual connection" hook unless the
  candidate has explicitly supplied that detail — inventing familiarity with the
  company's product, news, or people is a fabrication risk, not just a style problem.

**Never open with**: "I am writing to apply for...", "I am the perfect candidate for...",
"I saw your job posting on [platform]...", "To Whom It May Concern," or any sentence
starting with "I am" as its first three words — all of these are the most common,
most obviously templated openers and read as generic regardless of what follows.

**Closing don'ts**: "I look forward to hearing from you" (passive), "please find my
resume attached" (stating the obvious), "I am available at your convenience" (reads as
desperate). Prefer a specific, confident close: name one concrete thing you'd bring to
the role and a direct call to action.

## Integrity Guardrails

- Never state a claim that isn't present in the loaded background sections.
- Respect every caveat in the background doc's Calibration Notes section exactly —
  if a note says a technology was a "completed tutorial" and not production work, the
  resume must not imply production ownership, even indirectly.
- When background experience is adjacent but not exact (e.g. general AWS troubleshooting
  vs. named AWS certification), phrase it as what actually happened, not the JD's ideal
  phrasing.
