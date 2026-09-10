# Wide-Crawl Job Screening — 2026-09-10

Supplemental, wider-than-usual crawl run per explicit request, with a specific focus on
surfacing postings actually posted TODAY (2026-09-10) or YESTERDAY (2026-09-09), verified
via each platform's real date fields (not visible "reposted X days ago" badges).

## Advanced

None this run. Despite a wide sweep (~36 distinct companies/orgs across Greenhouse, Ashby,
Lever, RemoteOK, and Built In city editions — Seattle, Denver, Chicago, Atlanta), no posting
that cleared the geography and compensation filters also cleared the skeptical
hiring-manager screen on role-family fit. The large-tech-company boards swept this run
(GitLab, Coinbase, Reddit, Figma, Samsara, Twilio, MongoDB, Notion, Ramp, Cohere,
Perplexity, Palantir, etc.) skew almost entirely toward senior/staff engineering roles
requiring elite CS-fundamentals/distributed-systems backgrounds, or hard stack mismatches
(Go, Scala, Ruby, deep ML infra, blockchain) — a real, not manufactured, gap against
Austin's WordPress/PHP/Webflow/freelance-SEO-hybrid background at 2-5 YOE. See judgment
calls at the bottom.

## Flagged for review

### Senior Associate SEO/AEO (Answer Engine Optimization) Strategist — JPMorganChase
**FRESH — posted today (2026-09-10), age 0 days.**

- URL: https://builtin.com/job/senior-associate-seo-aeo-answer-engine-optimization-strategist/10584706
- Location/comp: Chicago, IL (eligible geo — priority 5). In-office 5 days/week. No comp
  range listed on the posting ("salary determined based on role, experience, skill set and
  location... additional details provided during hiring process") — proceeding per the
  no-comp-listed rule rather than auto-rejecting.
- Post date verified via Built In JSON-LD: `datePosted: 2026-09-10`, `validThrough:
  2026-10-10` (not expired).
- Role family: seo-growth (hybrid AEO/AI-discovery lean).

**Why flagged, both sides:** This is an unusually precise subject-matter match — the JD
wants someone who can "bring a clear point of view on AI-powered discovery, optimizing
content to be surfaced and cited in AI answers/overviews," which is close to verbatim what
background.md documents as Austin's actual, hands-on work at Prospecta Marketing: he
created the company's AEO/AIO strategy, including entity-based/knowledge-graph optimization
and optimizing for Google AI Overviews, ChatGPT, and Perplexity, with measurable early
results. That's a genuinely rare, specific skill overlap, not a generic SEO-keyword match.

Against that: the posting requires "4+ years of SEO and/or digital marketing experience"
with a demonstrated track record of measurable results at that tenure, and Austin's SEO
tenure (Feb 2024–present, ~2.5 years, with promotions to Account Executive at 1 year and
Senior SEO Specialist at 2 years) falls short of the stated floor. The role also expects
executive-level narrative-building for a large regulated financial-services organization in
a highly matrixed org — a real scale/environment jump from managing 30+ dental-practice
accounts at an agency, even though the underlying skill (translating technical work for
skeptical, non-technical stakeholders) is genuinely present in his background. A skeptical
hiring manager could reasonably reject on the years-of-experience floor alone; equally, the
AEO specialty match is strong enough that it's a real judgment call rather than a clean
reject.

## Rejected — summary (not written up individually per rejection-logging rules)

- **NinjaHoldings — Data Engineer** (Chicago, Built In, FRESH — posted 2026-09-10). Hard
  reject on scope/seniority: role supervises junior data engineers, owns ML-platform
  extension and end-to-end pipeline architecture — genuinely senior/staff-level ownership
  Austin's background doesn't support (his data work is VBA/Python scripting and a single
  serverless Lambda agent, not production ML-platform ownership).
- **Figma — Marketing Engineer, AI Deployment** (Remote US, non-senior title but requires
  5+ years building GTM/RevOps systems plus hands-on production experience with agent
  orchestration platforms — Gumloop, n8n, Workato — none of which are in Austin's
  background; his one AI agent (Basecamp) doesn't rise to the "portfolio of shipped agents
  across a marketing org" bar this JD wants). Reject on hard experience/tooling mismatch.
- **Hex — Product Engineer Intern** (San Francisco). Internship targeting current students;
  not a fit for a candidate with a completed degree and 5+ years of work experience, and
  unlikely to clear the $100k comp floor.
- **91 additional postings** (GitLab, Coinbase, Reddit, Samsara, Twilio, MongoDB, Instacart,
  Airtable, Smartsheet, Sproutsocial, Seatgeek, Godaddy, Ramp, Notion, Cohere, Attio,
  Perplexity, Runway, Zapier, Palantir) cleared an initial non-senior-title + eligible-geo
  filter but were rejected on sight without a full JD pull: titles/companies signal hard
  stack requirements (Go, Scala, Ruby, ML infrastructure, blockchain, deep distributed
  systems) or elite competitive-engineering bars that are a genuine mismatch for Austin's
  real background, not a borderline call worth spending full review effort on. All logged
  to `_seen.json` under 2026-09-10.
- **Fusion92 (Denver, SEO Specialist, 1-2 YOE)** — surfaced via search as a strong
  on-paper geo/experience fit, but the only URL found (a Built In listing) 404'd by the
  time it was checked directly — not logged to `_seen.json` since no stable URL could be
  confirmed; worth a manual look by Austin directly on Fusion92's careers page.
- **Blacksmith Agency — SEO Specialist** (fully remote): requires 10+ years of SEO
  experience — clear seniority mismatch, rejected without logging a specific URL (found via
  search aggregators with inconsistent job-board URLs across mirrors).
