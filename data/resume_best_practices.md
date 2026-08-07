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
- **Placement beats frequency.** A keyword carries the most weight in the Summary and
  inside an experience bullet that proves it, and much less in a bare skills list. For
  each of the JD's top 5-8 must-have terms that the background genuinely supports, aim
  to place it in two of three locations: the Core Skills block, the tagline or Summary,
  and the bullet that demonstrates it.
- **2-3 appearances, different contexts.** Repeating a primary keyword two or three
  times in genuinely different sentences reads as depth; repeating it identically reads
  as stuffing, which current parsers penalize rather than reward.
- **Mirror the JD's exact string, then gloss it.** If the JD writes "Google Analytics
  4," write "Google Analytics 4 (GA4)" rather than "GA4" alone. Literal-match screening
  still runs before any semantic layer in most ATS stacks. This extends the acronym
  rule above in both directions.
- **Never list a technology with no supporting evidence anywhere in the background
  doc**, even if it appears in the candidate background's tech-stack inventory section.
  A skills-list entry the candidate can't defend in a technical screen is worth less
  than the keyword match it buys — check the Calibration Notes for which tech-stack
  entries are index-only (touched, not claims-ready) before listing them in Core
  Skills.

## Section Structure (resume)

This structure matches the candidate's own proven prior resume — follow it exactly
rather than defaulting to a generic resume template.

1. **Header** — three lines:
   1. Name, large and bold.
   2. **Tagline** — the JD's own role title, verbatim, where that is a truthful
      self-description, followed by location (e.g. "Senior Frontend Software
      Engineer - Denver, CO" for a JD titled exactly that). This is self-description,
      not a claim about any employer's records, and it is the single most-fixated
      element in a reviewer's 6-second scan — do not paraphrase it into a near-miss
      of the JD's actual title. If the JD title contains company-internal jargon (a
      level code, an internal team name), use the closest standard industry title
      instead. Never blend two role families into the tagline for a single-family
      JD ("Senior SEO Specialist & Full-Stack Web Developer" against a pure frontend
      engineering req splits the reader's attention at exactly the moment it needs
      to be undivided) — blend only when the JD itself is genuinely hybrid.

      When the employer-of-record title in the Experience section won't match this
      tagline (the normal case for this candidate), the Summary's *first clause*
      must close that gap before the reader reaches the Experience section — lead
      the Summary with the scope, not the title (e.g. "Builds and owns production
      systems end to end — a live serverless AWS/Python agent in daily use, custom
      CMS and plugin architecture, a shipped React/Node/Stripe application — inside
      a client-facing role at a small agency"). Do not leave the reconciliation to
      the cover letter; most reviewers decide before they open it.
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
   Also default to general, recognizable technology names over internal
   implementation specifics: "React" not "React 18 SPA (Create React App)",
   "database schema design" not a specific hardening library name like
   "express-mongo-sanitize", "WordPress AJAX APIs and authentication handling" not
   specific hook/function names. This applies to Professional Experience bullets too,
   not just Core Skills. Exception: mirror the JD's own term when it explicitly names
   that same specific, granular thing (e.g. it asks for Zod by name).
   **Baseline breadth — express it in stacks shipped, not platforms touched (revised
   per 2026-08-06 v2 system audit).** Versatility is a genuine differentiator for this
   candidate and should be visible on every resume, but research on how technical
   reviewers actually read a skills section converges on one point: a flat list of
   platform names reads as dabbling, not depth, and that reading is exactly the
   "generalist vs. specialist" framing that has independently driven a
   `narrative_coherence` or `seniority_calibration` objection on every dev-family
   application reviewed so far. Express breadth instead as production systems
   delivered in different stacks — the defensible claim is PHP/MySQL full-stack
   plugin architecture, React/Node/Express with Stripe payments, and Python/AWS
   serverless: three different production stacks, each with a real shipped artifact
   behind it. Put that breadth in the Core Skills category labels and let the
   Experience bullets prove it.
   - **WordPress/PHP always stays**, on any JD. It's backed by two from-scratch
     full-stack plugins (custom schema, REST-style AJAX API, nonce and
     prepared-statement security, admin dashboard) — that's depth, and it's
     defensible in a technical screen, not a platform-familiarity claim.
   - **Webflow, Wix, and SquareSpace are role-family gated.** Include them on SEO,
     growth, marketing, and agency JDs, where they're genuinely relevant and where
     the Honeycomb SquareSpace engagement and the Webflow CMS rebuild are real
     credentials. Omit them entirely on software-engineering-family JDs — on an
     engineering req they're the lowest-signal items on the page, reading as
     website-builder work rather than engineering.
   - The Webflow CMS rebuild for Jeff Gray, DDS is a legitimate engineering bullet on
     its own merits (architecture, ownership, coordinating with a client's senior
     developer) and may appear in Experience on any JD — that's different from
     listing "Webflow" as a platform skill. Describe the work, not the tool.
4. **Professional Experience** (not "Experience") — ordered by employer primacy (per
   any ordering guidance in the background doc's Calibration Notes), not strictly
   reverse-chronological. Each employer appears as exactly ONE entry — never split a
   single employer into multiple entries by discipline (e.g. a separate "SEO" entry
   and a separate "Developer" entry for the same company). If a role spans multiple
   disciplines, the entry MUST include at least one real bullet from EACH core
   discipline that defines the role — dropping a whole discipline to zero bullets is
   not valid tailoring. Weight bullet count toward whichever discipline the JD favors,
   but never zero; check Calibration Notes for employer-specific minimums (e.g.
   Prospecta requires both a real SEO bullet and a real Account Executive bullet
   somewhere in the entry — check the same note for role-family-dependent ordering,
   since position is not universal even though presence is) and treat the presence
   requirement as a hard floor. Each entry: **company name**
   in bold on its own line, then *title – dates* in italics on the next line (company
   leads, not title). On engineering-family JDs where the official title doesn't say
   "engineer" or "developer," an additional italicized `*Scope: ...*` line naming the
   real technical scope is permitted directly beneath the title line when Calibration
   Notes allow it for that employer — self-description backed by real documented work,
   never a change to the title itself. Then 3-6 bullets. Lead bullets with the most JD-relevant, most
   quantified achievements; bold the single standout quantified clause in the lead
   entry's top bullet only (sparingly — once, not on every bullet). For a
   freelance/contract umbrella entry (e.g. Tangent Apps) covering multiple clients,
   lead each bullet with the client name and its own year(s) in bold, e.g.
   `**Ahead of the Curve Media (2023):** ...`.
5. **Education & Certifications** — include whenever the background doc has an
   `EDUCATION` section: degree/institution on one line, certifications
   comma-separated on the next. **Degree line format (revised per 2026-08-06 v2
   audit):** `B.S. Computer Science — Western Governors University, 2026` — the bare
   completion year only, never a month. 7 of 9 independent reviewers misread a
   month-precision recent-degree date as still in progress (one even read "March
   2026" as a future date in an August 2026 run) — this is a resume-legibility
   problem, not a reviewer error, and a bare year is the standard convention that
   avoids it. **In-progress certifications** (e.g. "AWS Solutions Architect –
   Associate (in progress)") are included on junior and mid-band JDs, where they
   read as active trajectory, and **omitted entirely on senior/lead-band JDs**,
   where an unearned cert next to a recent degree has drawn an explicit
   hiring-manager objection ("reinforcing the junior-for-this-role signal") and buys
   nothing on the ATS side (an in-progress cert isn't a keyword any parser scores).
   Use the seniority_band signal passed into the draft agent to decide.

## The Top Third

Reviewers spend roughly 6-8 seconds deciding whether to keep reading, and that decision
is made almost entirely on the name, tagline, Summary, and the first bullet of the lead
entry (eye-tracking research on resume review consistently finds this: reviewers fixate
first on current title and company, then previous title, then dates, then education).
Budget the top third of the page accordingly:

- The Summary's first sentence must contain at least one hard number drawn from the
  background doc. A number in the first line is the cheapest available credibility
  signal — resumes with a quantified claim up front draw materially more attention than
  ones that open with a duty description.
- The lead entry's first bullet must be the single most impressive genuinely-supported
  claim for *this* JD, not the chronologically first fact or the most-recently-written
  one. Primacy is a real effect; the strongest bullet buried at position four is worth
  much less than the same bullet at position one.
- Nothing in the top third should be a credential still in progress. An in-progress
  certification or a not-yet-complete degree date, visible above the fold, reads as
  "still building foundational credentials" on a mid/senior req — this has been an
  actual, recurring hiring-manager objection. Keep in-progress items in the Education &
  Certifications section at the bottom, where they read as ongoing investment rather
  than as a gap.
- Name the hiring company at least once in the cover letter, and once more in a
  sentence that could only have been written for this specific posting (a phrase from
  the posting's own description of its problem, product, or mission). A letter that
  would work unchanged for another company at the same seniority reads as a template
  regardless of how well it's written — this has been an explicit, recurring
  hiring-manager complaint even on otherwise well-written letters.

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
- **Non-metric quantification.** When a bullet has no percentage or dollar figure
  available, it can still be sized. Prefer, in order: the count of things affected
  (clients, users, members, accounts, pages, endpoints, lines rewritten); the count of
  parties coordinated (teams, agencies, stakeholders); the duration or deadline pressure
  (a 48-hour window, a 10-month engagement); and the adoption fact (reused companywide,
  in daily production use, still maintained). All four of these are real, sizeable facts
  when the background doc actually states them — don't let a bullet read as an
  unverifiable adjective when a real count or adoption fact is available instead.
- **Version numbers do not count as quantification.** "React 18," "Express 4," "React
  Router v6" are ATS keyword tokens, not impact — don't let them occupy the slot where a
  scale number belongs, and don't mistake listing them for having quantified the bullet.

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

- Opens with 'Dear [Company] Team,' using the hiring company's real name, on its own
  line. Closes with a fixed 4-line sign-off, each on its own line: 'Best Regards,' /
  'Austin O'Neil' / 'austinroneil@gmail.com' / '(303) 335-5761'. Both ends are enforced
  deterministically (structure_lint checks this).
- 3-4 short paragraphs, under 400 words total (the salutation/closing lines don't count
  toward this).
- Paragraph 1 (after the salutation): an opening hook (see below), not a role announcement.
- Paragraph 2-3: two concrete, quantified examples from the background doc that map
  directly to the JD's stated requirements — not a restatement of the resume.
- Closing: brief, confident, no groveling ("I would welcome the opportunity...").
- No generic filler ("I am a hard worker who is passionate about..."). Every sentence
  should be doing work a generic applicant couldn't also claim.
- **Never volunteer a missing qualification.** Not claiming a skill you don't have is
  the integrity rule; actively announcing what you're missing is a different, separate
  choice that undermines the letter's actual job of putting the candidate's best foot
  forward. If the JD asks for something the background doc doesn't support, the answer
  is to say nothing about it and lead harder with what's actually there, not to write a
  sentence admitting the gap. Silence about something isn't dishonest; only false claims
  are. Banned patterns: "I haven't yet...", "I don't have direct experience in...",
  "While I lack...", "I can't yet point to...", "Admittedly, I...". If a reviewer flags
  a missing-qualification gap as feedback, fix it by finding genuinely relevant adjacent
  experience already in the background doc and strengthening its positioning, never by
  writing about the deficiency.
- **Target: 400 words.** This is a target to write to, not a hard gate — a small overage
  (a handful of words) is not worth cutting a genuinely strong point to fix, and isn't
  treated as a blocking issue. Still budget for it while drafting rather than writing long
  and trimming — a letter written to length reads tighter than one visibly cut down.
- **The adjacent-strength pivot.** Silence is the floor, not the ceiling. When a JD
  leans on something the background doc doesn't support, the strongest available move is
  usually not silence but a paragraph that (1) names the underlying *problem* the
  requirement exists to solve, in the JD's own words; (2) gives one specific, real
  instance of solving that class of problem with different tools; and (3) stops. Never
  name the missing tool, never characterize your level with it, never promise to pick it
  up.

  - Weak (do not write this): "I haven't worked hands-on in Conductor or Profound
    specifically; my tracked-analytics background is GA4, Search Console, SEMrush,
    Ahrefs, and SEO PowerSuite, and I'd expect to pick up a new platform quickly given
    that overlap."
  - Strong: "The part of this role I'd want to talk about is turning visibility data
    into a decision someone acts on. When one account's bounce rate moved 53.4% to
    35.0%, the useful output wasn't the number, it was tracing it to a UX lever rather
    than a keyword gap and redirecting the next month's priorities on that basis."

  Both are honest. The first tells the reader what you cannot do and then asks them to
  discount it; the second tells them what you do and lets the tooling question come up
  in the screen, where you can answer it in conversation. A reader unsure whether you're
  qualified will resolve that uncertainty against you — don't hand them the doubt in
  writing.

### Company Culture & Values Fit

- Read the full JD for company mission, stated values, culture description, or
  personality signals, not just the technical requirements section — phrases like "who
  thrives here," "what we value," team-culture blurbs, or a mission statement. When
  present, at least one moment in the letter (often the opening hook or the closing)
  should resonate with that signal.
- Never do this by parroting the company's own words back as a bare assertion (e.g.
  "I thrive in fast-paced, ambiguous environments" just because the JD says it values
  that). Pair it with a real, specific moment from the background doc (usually ABOUT_ME
  or UNIVERSAL) that actually demonstrates the trait — show it, don't claim it.
- If the JD's culture/values language doesn't map to anything genuinely true in the
  background doc, don't force a match. Same rule as a missing skill: don't fabricate an
  affinity or personality trait that isn't real. Silence beats a hollow values claim.
- Culture-fit signals add color to the letter; they don't replace the two required
  concrete, quantified achievement examples from the structure above.

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
