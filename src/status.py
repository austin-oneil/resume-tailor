"""Consistent, scannable stage/progress output for the CLI.

Pure presentation — no pipeline logic lives here. Lets someone running
main.py directly in their own terminal see exactly where the run is (which
of the 6 stages, which agent/model is active, which iteration/attempt)
without reading source code or squinting at a flat stream of prints.

Also the single seam the GUI (gui_app.py) hooks into for its live activity
feed: every function here notifies any registered listeners with the same
structured data it prints, so the pipeline code itself (main.py, fit_gate.py,
hiring_gate.py, etc.) stays completely unaware of whether it's being driven
from a terminal or a webview window.
"""

TOTAL_STAGES = 6
_WIDTH = 78

_listeners: list = []


def add_listener(fn) -> None:
    """fn(kind: str, fields: dict) -> None. Exceptions from a listener are
    swallowed so a misbehaving UI can never take down the actual pipeline."""
    _listeners.append(fn)


def clear_listeners() -> None:
    _listeners.clear()


def _notify(kind: str, **fields) -> None:
    for fn in _listeners:
        try:
            fn(kind, fields)
        except Exception:
            pass


def classified(role_family: str) -> None:
    print(f"Classified as: {role_family}")
    _notify("classified", role_family=role_family)


def stage(number: int, title: str, model: str) -> None:
    print()
    print("=" * _WIDTH)
    print(f"STAGE {number}/{TOTAL_STAGES}: {title}  [{model}]")
    print("=" * _WIDTH)
    _notify("stage", number=number, title=title, model=model, total=TOTAL_STAGES)


def substep(text: str) -> None:
    print(f"  {text}")
    _notify("substep", text=text)


def detail(text: str) -> None:
    print(f"    {text}")
    _notify("detail", text=text)


def done(status: str, score: int, pages: int, hm_verdict: str) -> None:
    print()
    print("=" * _WIDTH)
    icon = "PASSED" if status == "accepted" else "NEEDS MANUAL REVIEW"
    print(f"RESULT: {icon}")
    print(f"  score={score}/100  pages={pages}  hiring_manager={hm_verdict}")
    print("=" * _WIDTH)
    _notify("done", status=status, score=score, pages=pages, hm_verdict=hm_verdict)
