"""Desktop GUI entry point.

Wraps the exact same orchestration main.py uses (src/pipeline.py) in a
native window via pywebview, so intake, live stage-by-stage progress, and
the final report + file links don't require a terminal. Launched by
ResumeTailor.app (see build_app.sh) so it shows up with its own Dock icon.
"""

import json
import subprocess
import threading
from pathlib import Path

import webview

from src import pipeline, status
from src.intake import JobPosting

GUI_DIR = Path(__file__).resolve().parent / "gui"


class Api:
    def __init__(self):
        self.window = None
        self._context = None
        self._lock = threading.Lock()

    def _push(self, kind: str, fields: dict) -> None:
        if not self.window:
            return
        try:
            self.window.evaluate_js(f"onPipelineEvent({json.dumps(kind)}, {json.dumps(fields)})")
        except Exception:
            pass

    # --- called from the frontend ---

    def submit_job(self, title, platform, description):
        title = (title or "").strip()
        description = (description or "").strip()
        platform = (platform or "Other").strip() or "Other"
        if not title or not description:
            self._push("error", {"message": "Job title and description are both required."})
            return
        threading.Thread(target=self._run_gate, args=(title, platform, description), daemon=True).start()

    def confirm_continue(self, proceed):
        with self._lock:
            context = self._context
            self._context = None
        if not context:
            return
        if not proceed:
            self._push("cancelled", {})
            return
        threading.Thread(target=self._run_rest, args=(context,), daemon=True).start()

    def open_path(self, path):
        if path and Path(path).exists():
            subprocess.run(["open", path])

    def reveal_path(self, path):
        if path and Path(path).exists():
            subprocess.run(["open", "-R", path])

    # --- background work ---

    def _run_gate(self, title, platform, description):
        posting = JobPosting(title=title, description=description, platform=platform)
        try:
            context = pipeline.run_fit_gate(posting)
        except Exception as exc:
            self._push("error", {"message": str(exc)})
            return

        if pipeline.gate_requires_confirmation(context.gate):
            with self._lock:
                self._context = context
            gate = context.gate
            self._push("gate_confirm", {
                "match_estimate": gate.match_estimate,
                "missing_requirements": gate.missing_requirements,
                "red_flags": gate.red_flags,
                "disqualifying_requirements": gate.disqualifying_requirements,
                "seniority_band": gate.seniority_band,
            })
        else:
            self._run_rest(context)

    def _run_rest(self, context):
        try:
            result = pipeline.run_from_gate(context)
        except Exception as exc:
            self._push("error", {"message": str(exc)})
            return
        self._push("result", self._serialize(result))

    def _serialize(self, result) -> dict:
        hm = result.hiring_gate_result.hm_result
        return {
            "final_status": result.final_status,
            "score": result.score,
            "pages": result.pages,
            "hm_verdict": result.hm_verdict,
            "job_title": result.job_title,
            "company_name": result.company_name,
            "folder": str(result.folder),
            "resume_docx": str(result.resume_docx),
            "cover_letter_docx": str(result.cover_letter_docx),
            "report_path": str(result.report_path),
            "report_markdown": result.report_text,
            "hm_overall_impression": hm.overall_impression,
            "hm_concerns": hm.concerns,
            "hm_positive_signals": hm.positive_signals,
            "stopped_reason": result.hiring_gate_result.stopped_reason,
        }


def _customize_macos_app_identity():
    """The venv's python3 is a symlink into the python.org framework build,
    which re-execs itself through Python.framework's own Python.app stub to
    get a WindowServer connection for any Cocoa GUI (pywebview included) —
    so by the time pywebview creates a window, macOS has already associated
    this process with that framework's bundle, not ResumeTailor.app. That
    shows up as the Dock icon/menu-bar name reading "Python" instead of
    "Resume Tailor". Overriding NSBundle's in-memory CFBundleName and
    setting the app icon directly fixes both, regardless of which bundle
    macOS thinks launched the process. Best-effort: never block startup
    over cosmetics if pyobjc isn't available for some reason."""
    try:
        from AppKit import NSApplication, NSImage
        from Foundation import NSBundle

        bundle = NSBundle.mainBundle()
        info = bundle.localizedInfoDictionary() or bundle.infoDictionary()
        if info is not None:
            info["CFBundleName"] = "Resume Tailor"

        icon_path = Path(__file__).resolve().parent / "ResumeTailor.app" / "Contents" / "Resources" / "AppIcon.icns"
        if icon_path.exists():
            icon = NSImage.alloc().initByReferencingFile_(str(icon_path))
            NSApplication.sharedApplication().setApplicationIconImage_(icon)
    except Exception:
        pass


def main():
    api = Api()
    window = webview.create_window(
        "Resume Tailor",
        str(GUI_DIR / "index.html"),
        js_api=api,
        width=1040,
        height=780,
        min_size=(820, 600),
    )
    api.window = window
    status.add_listener(api._push)
    _customize_macos_app_identity()
    webview.start()


if __name__ == "__main__":
    main()
