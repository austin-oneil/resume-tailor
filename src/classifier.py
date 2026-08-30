"""Classifies a job posting into a role family.

Cost-conscious two-tier approach: cheap keyword heuristic first, falling back
to a single short Haiku tool-call only when the heuristic finds no signal at
all. This label is now purely descriptive (used for output-folder naming and
the applications log) — it no longer gates what evidence the drafting/scoring
agents get to see (background_loader.build_subset always loads the full
document). So there's no cost to leaning toward "hybrid": a title-only exact
match used to hide real cross-discipline evidence from the model, which was
the actual bug; now it just mislabels a folder. Scans the JD body as well as
the title, not just the title, since a title alone regularly undersells how
technical a "growth"/"marketing" role actually is (and vice versa) — real
alignment can span categories, so this errs toward calling it hybrid rather
than forcing a single stringent bucket.
"""

import config
from src.client import get_client

DEV_KEYWORDS = [
    "engineer", "developer", "software", "swe", "full stack", "full-stack",
    "frontend", "front-end", "backend", "back-end", "web developer",
]
SEO_KEYWORDS = ["seo", "growth marketer", "marketing", "content strategist", "organic"]
SALES_KEYWORDS = [
    "sales", "account executive", "account manager", "solutions consultant",
    "customer success", "business development",
]
HYBRID_TITLES = [
    "solutions engineer", "web growth engineer", "sales engineer",
    "growth engineer", "technical account manager",
]

CLASSIFY_TOOL = {
    "name": "submit_classification",
    "description": "Submit the role-family classification for a job posting.",
    "input_schema": {
        "type": "object",
        "properties": {
            "role_family": {
                "type": "string",
                "enum": ["dev", "sales-technical", "seo-growth", "hybrid"],
            }
        },
        "required": ["role_family"],
    },
}


def classify_role_family(job_title: str, jd_text: str = "") -> str:
    title_lower = job_title.lower()

    for phrase in HYBRID_TITLES:
        if phrase in title_lower:
            return "hybrid"

    # Scan title + a body excerpt together, not the title alone — a title
    # like "Senior Marketing Manager" reads as pure seo-growth on its own,
    # but the body can easily be asking for hands-on dev/CMS-platform
    # fluency. Checking both before deciding means a JD that genuinely
    # blends categories gets called "hybrid" instead of being forced into
    # whichever single bucket the title happened to hit first.
    body_excerpt = " ".join(jd_text.split()[:400]).lower()
    combined = f"{title_lower} {body_excerpt}"

    has_dev = any(k in combined for k in DEV_KEYWORDS)
    has_seo = any(k in combined for k in SEO_KEYWORDS)
    has_sales = any(k in combined for k in SALES_KEYWORDS)
    matches = sum([has_dev, has_seo, has_sales])

    if matches > 1:
        return "hybrid"
    if matches == 1:
        if has_dev:
            return "dev"
        if has_seo:
            return "seo-growth"
        return "sales-technical"

    return _classify_with_haiku(job_title, jd_text)


def _classify_with_haiku(job_title: str, jd_text: str) -> str:
    client = get_client()
    excerpt = " ".join(jd_text.split()[:200])
    message = client.messages.create(
        model=config.CLASSIFIER_MODEL,
        max_tokens=100,
        tools=[CLASSIFY_TOOL],
        tool_choice={"type": "tool", "name": "submit_classification"},
        messages=[{
            "role": "user",
            "content": (
                "Classify this job posting into exactly one role family: "
                "'dev' (software/web engineering), 'sales-technical' (sales, "
                "account management, solutions consulting), 'seo-growth' (SEO, "
                "marketing, growth), or 'hybrid' (blends dev with sales or growth, "
                "e.g. sales engineer, solutions engineer, web growth engineer).\n\n"
                f"Job title: {job_title}\n\nJob description excerpt:\n{excerpt}"
            ),
        }],
    )
    for block in message.content:
        if block.type == "tool_use":
            return block.input["role_family"]
    return "hybrid"
