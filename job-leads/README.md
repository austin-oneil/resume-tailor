# Job Leads

Written by the nightly job-scanning routine (see the `/schedule` cloud routine configured
for this repo). Each night it searches for new postings, screens them against
`data/background.md` and `src/hiring_manager.py`'s hiring-manager rubric, and only writes
a dated report here (`YYYY-MM-DD.md`) for postings that get a genuine "advance" verdict.

Rejected postings are never written up — they're just recorded by ID/URL in `_seen.json`
so the same listing isn't re-evaluated on a later run, with zero further effort spent on
them.

This directory is screening output only. It does not generate tailored resumes or cover
letters — for anything listed here worth pursuing, run `main.py` locally as usual.
