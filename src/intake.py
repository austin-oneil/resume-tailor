"""Interactive intake: prompt for job title + pasted job description."""

from dataclasses import dataclass


@dataclass
class JobPosting:
    title: str
    description: str
    platform: str = "Other"


def get_job_posting() -> JobPosting:
    title = input("Job title: ").strip()
    platform = input("Applying via which platform (Indeed, LinkedIn, Built In, Handshake, etc.): ").strip()
    print("Paste the job description, then type END on its own line:")
    lines = []
    while True:
        line = input()
        if line.strip() == "END":
            break
        lines.append(line)
    description = "\n".join(lines).strip()
    return JobPosting(title=title, description=description, platform=platform or "Other")
