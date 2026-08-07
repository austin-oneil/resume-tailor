"""Draft -> score -> revise loop. Caps at MAX_ITERATIONS; below-threshold or
unresolved integrity flags after the cap get flagged for manual review instead
of looping indefinitely.

Tracks the best-scoring draft across all iterations rather than just returning
whatever the loop's final pass produced — free-running revision with nothing
actionable left to fix has been observed to make drafts worse, not better, so
the loop also stops early once no fixable issue remains rather than grinding
to MAX_ITERATIONS on a JD-coverage gap no rewrite can close."""

import re
from dataclasses import dataclass

import config
from src import draft_agent, score_agent, status as status_display, structure_lint, style_lint
from src.draft_agent import Draft
from src.score_agent import ScoreResult


def _lint(draft: Draft, background_subset: str) -> list[dict]:
    return style_lint.lint_draft(draft) + structure_lint.lint_draft(draft, background_subset)


# Sentence-initial and common capitalized words that would otherwise
# pollute the capitalized-token extraction below (e.g. the "No" in "No
# experience with...", or "Candidate"/"Demonstrated" starting a sentence).
_CAPITALIZED_STOPWORDS = {
    "no", "not", "none", "nor", "the", "this", "that", "these", "those", "a", "an",
    "candidate", "candidates", "demonstrated", "demonstrable", "background",
    "experience", "experienced", "missing", "lacks", "lacking", "limited", "required",
    "preferred", "basic", "qualifications", "role", "position", "job", "jd",
    # Real, shipped false positive (2026-08-07, Trivelta re-run): "JD" (the
    # abbreviation itself) and sentence-generic words matched as if they were
    # real technical terms, producing a meaningless "high severity" flag
    # citing "these terms (JD, Nothing) do appear". Both were 2-letter/
    # sentence-initial noise, not signal.
    "nothing", "something", "everything", "anything", "someone", "everyone",
    "anyone", "here", "there", "while", "given", "note", "check",
}
# Proper-noun/technology-name-shaped tokens: a capitalized word, or an
# all-caps acronym, of 2+ characters. Score-agent gap descriptions reliably
# capitalize technology/skill names ("AWS Lambda", "SQL", "Tableau") while
# generic connective words in the same sentence stay lowercase — this is a
# much stronger signal than matching any lowercase word, which false-
# positived twice during testing (see below).
_PROPER_NOUN_RE = re.compile(r"\b[A-Z][A-Za-z0-9+.#]{1,}\b")


def jd_coverage_backstop(gaps: list[dict]) -> list[dict]:
    """Deterministic check, no API call (audit v3 §2.4). score_agent only
    ever receives background_subset — a role-family-filtered slice of
    background.md (background_loader.build_subset()) — but presents a
    jd_coverage classification to Austin as "the candidate genuinely does
    not have this," which asserts knowledge of the full document the agent
    was never given. For an seo-growth classification, for example, the
    entire DEV section is absent from what the agent saw; real experience
    living only in DEV can get misclassified jd_coverage, silently dropped
    from revision, and reported as a genuine career limitation.

    Cross-checks each jd_coverage gap's capitalized/technology-shaped terms
    against the FULL background.md — deliberately NOT a generic lowercase
    word match: an earlier version matched on any 4+ letter lowercase word
    and false-positived twice in testing ("never"/"scale"/"used" against a
    Kubernetes gap; "data"/"demonstrated" against a SQL/Tableau/Looker gap),
    both filler words with zero actual signal. Real gap descriptions reliably
    capitalize the actual technology/skill name, so that's the signal to key
    on. Surfaced as its own meta-issue rather than silently reclassified to
    draft_defect — a heuristic token match is good enough to flag "check
    this by hand," not good enough to unilaterally decide the gap is fixable
    and feed it back into a revision pass."""
    full_background = config.BACKGROUND_PATH.read_text().lower()
    meta_issues = []
    for gap in gaps:
        if gap.get("kind") != "jd_coverage":
            continue
        detail = gap.get("detail", "")
        candidates = {
            t for t in _PROPER_NOUN_RE.findall(detail)
            if t.lower() not in _CAPITALIZED_STOPWORDS
        }
        matches = sorted({t for t in candidates if t.lower() in full_background}, key=str.lower)
        if matches:
            meta_issues.append({
                "category": "jd_coverage_subset_mismatch",
                "detail": (
                    f"Score agent classified this as a gap the candidate genuinely "
                    f"lacks: \"{detail}\" — but it only ever saw a role-family-filtered "
                    f"subset of background.md, not the full document, and these terms "
                    f"({', '.join(matches[:5])}) do appear somewhere in the full file. "
                    "The loaded role-family subset may be wrong for this JD, or this "
                    "may be a genuine coincidental word overlap — check background.md "
                    "directly before treating this as a real capability gap."
                ),
                "severity": "high",
                "kind": "draft_defect",
            })
    return meta_issues


@dataclass
class SupervisorResult:
    draft: Draft
    score_result: ScoreResult
    style_issues: list[dict]
    iterations: int
    shipped_iteration: int
    status: str  # "accepted" | "manual_review"
    iteration_history: list[dict]
    tailoring_notes: list[str]


def _record(history: list[dict], iteration: int, result: ScoreResult, lint_issues: list[dict]) -> None:
    history.append(
        {
            "iteration": iteration,
            "score": result.score,
            "gaps": len(result.gaps),
            "integrity_flags": len(result.integrity_flags),
            "style_issues": len(lint_issues),
        }
    )


def _blocking(lint_issues: list[dict]) -> list[dict]:
    """low severity is advisory everywhere else in this system (main.py's
    blocking_style_issues filters it out of acceptance too) — it shouldn't
    be able to consume one of the capped MAX_ITERATIONS revise() calls on
    its own either (audit v3 §3 Mechanism 3)."""
    return [i for i in lint_issues if i.get("severity") in ("critical", "high", "medium")]


def _fixable_gaps(result: ScoreResult) -> list[dict]:
    """jd_coverage gaps are informational only — the candidate genuinely lacks
    that qualification and no revision of these two documents changes that.
    Only draft_defect gaps (and legacy/malformed gaps missing a kind, treated
    as fixable so nothing silently vanishes) are ever fed to revise()."""
    return [g for g in result.gaps if g.get("kind") != "jd_coverage"]


_SEVERITY_WEIGHT = {"critical": 100, "high": 10, "medium": 3, "low": 0}


def quality_key(result: ScoreResult, lint_issues: list[dict]) -> tuple:
    """Higher is better: fewest/lightest blockers (integrity flags + style
    issues, weighted by severity) first, then fewest remaining gaps, then
    highest score. Used to pick the best draft seen across the whole loop
    rather than whatever the last iteration happened to produce.

    Severity-weighted (audit v3 §3 Mechanism 3) — previously every
    integrity flag and every lint issue contributed exactly 1 to the first
    term regardless of severity, so a fabricating draft (1 integrity flag)
    and a merely-long draft (1 low-severity length advisory) tied on this
    term and the tiebreak fell to gap count/score, which could pick the
    fabricating draft. A `low` advisory is explicitly non-blocking
    everywhere else in this system (main.py's blocking_style_issues); it
    should not carry equal weight here either.

    Gap count is a real tiebreaker, not decoration — caught live on a real
    run where iteration 1 (4 unresolved gaps) and iteration 3 (0 gaps, same
    score, same blocker count) tied on the first two terms alone, and the
    earlier, objectively worse draft won the tie by insertion order."""
    blockers = 25 * len(result.integrity_flags) + sum(
        _SEVERITY_WEIGHT.get(i.get("severity", "medium"), 3) for i in lint_issues
    )
    return (-blockers, -len(result.gaps), result.score)


def run(
    job_title: str,
    jd_text: str,
    background_subset: str,
    best_practices: str,
    company_name: str = "",
    seniority_band: str = "",
    known_missing: list[str] | None = None,
) -> SupervisorResult:
    status_display.substep(f"Generating initial draft for '{job_title}'...")
    draft = draft_agent.generate(
        job_title, jd_text, background_subset, best_practices,
        company_name=company_name, seniority_band=seniority_band, known_missing=known_missing,
    )
    tailoring_notes = [f"[iteration 1] {note}" for note in draft.tailoring_notes]

    status_display.substep("Scoring draft...")
    result = score_agent.score(job_title, jd_text, background_subset, best_practices, draft)
    lint_issues = _lint(draft, background_subset)
    iteration = 1
    history: list[dict] = []
    _record(history, iteration, result, lint_issues)
    status_display.detail(
        f"iteration {iteration}/{config.MAX_ITERATIONS}: score={result.score} gaps={len(result.gaps)} "
        f"integrity_flags={len(result.integrity_flags)} style_issues={len(lint_issues)}"
    )

    best = (draft, result, lint_issues, iteration)

    fixable = _fixable_gaps(result)
    while (
        (result.score < config.SCORE_THRESHOLD or result.integrity_flags or _blocking(lint_issues) or fixable)
        and iteration < config.MAX_ITERATIONS
    ):
        if not fixable and not result.integrity_flags and not _blocking(lint_issues):
            # Nothing actionable left even though score is under threshold —
            # the gap is JD-coverage, not anything a rewrite can change.
            # Stop rather than let the drafter free-run with nothing real to
            # fix, which has been observed to degrade an already-clean draft.
            status_display.detail(
                "no fixable issues remain (remaining score gap is JD-coverage, not a draft defect) — stopping early"
            )
            break

        status_display.substep(f"Revising draft (iteration {iteration + 1}/{config.MAX_ITERATIONS})...")
        draft = draft_agent.revise(
            job_title,
            jd_text,
            background_subset,
            best_practices,
            draft,
            fixable + lint_issues,
            result.integrity_flags,
        )
        tailoring_notes += [f"[iteration {iteration + 1}] {note}" for note in draft.tailoring_notes]
        result = score_agent.score(job_title, jd_text, background_subset, best_practices, draft)
        lint_issues = _lint(draft, background_subset)
        iteration += 1
        _record(history, iteration, result, lint_issues)
        status_display.detail(
            f"iteration {iteration}/{config.MAX_ITERATIONS}: score={result.score} gaps={len(result.gaps)} "
            f"integrity_flags={len(result.integrity_flags)} style_issues={len(lint_issues)}"
        )

        if quality_key(result, lint_issues) > quality_key(best[1], best[2]):
            best = (draft, result, lint_issues, iteration)

        fixable = _fixable_gaps(result)

    best_draft, best_result, best_lint, best_iteration = best
    if best_iteration != iteration:
        status_display.detail(
            f"shipping iteration {best_iteration} (score={best_result.score}) over the later "
            f"iteration {iteration} (score={result.score}), which scored worse"
        )

    subset_mismatch_issues = jd_coverage_backstop(best_result.gaps)
    if subset_mismatch_issues:
        status_display.detail(
            f"{len(subset_mismatch_issues)} jd_coverage gap(s) may be a role-family "
            "subset issue, not a real limitation — flagged for review"
        )
        best_result.gaps = best_result.gaps + subset_mismatch_issues

    # Reconciled with main.py's blocking_style_issues rule (audit v3 §3
    # Mechanism 3 note): low severity is advisory, not blocking, everywhere
    # else in this system — this field is currently unread downstream, but
    # it shouldn't silently disagree with that rule if something starts
    # reading it later.
    outcome_status = (
        "accepted"
        if best_result.score >= config.SCORE_THRESHOLD
        and not best_result.integrity_flags
        and not _blocking(best_lint)
        else "manual_review"
    )

    return SupervisorResult(
        draft=best_draft,
        score_result=best_result,
        style_issues=best_lint,
        iterations=iteration,
        shipped_iteration=best_iteration,
        status=outcome_status,
        iteration_history=history,
        tailoring_notes=tailoring_notes,
    )
