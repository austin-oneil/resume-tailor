"""Consistent, scannable stage/progress output for the CLI.

Pure presentation — no pipeline logic lives here. Lets someone running
main.py directly in their own terminal see exactly where the run is (which
of the 6 stages, which agent/model is active, which iteration/attempt)
without reading source code or squinting at a flat stream of prints.
"""

TOTAL_STAGES = 6
_WIDTH = 78


def stage(number: int, title: str, model: str) -> None:
    print()
    print("=" * _WIDTH)
    print(f"STAGE {number}/{TOTAL_STAGES}: {title}  [{model}]")
    print("=" * _WIDTH)


def substep(text: str) -> None:
    print(f"  {text}")


def detail(text: str) -> None:
    print(f"    {text}")


def done(status: str, score: int, pages: int, hm_verdict: str) -> None:
    print()
    print("=" * _WIDTH)
    icon = "PASSED" if status == "accepted" else "NEEDS MANUAL REVIEW"
    print(f"RESULT: {icon}")
    print(f"  score={score}/100  pages={pages}  hiring_manager={hm_verdict}")
    print("=" * _WIDTH)
