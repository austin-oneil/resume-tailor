"""True page-count verification via Microsoft Word automation (AppleScript).

python-docx has no concept of page breaks — pagination only exists once a
real layout engine renders the document. This shells out to the actually-
installed Microsoft Word (headless-ish: opens, reads its own computed
statistic, closes without saving) to get the same page count the user would
see if they opened the file themselves.
"""

import subprocess
import tempfile
from pathlib import Path

from docx import Document

_APPLESCRIPT = """
on run argv
    set filePath to POSIX file (item 1 of argv)
    tell application "Microsoft Word"
        set theDoc to open file name filePath
        delay 1
        set pageCount to compute statistics theDoc statistic statistic pages
        close theDoc saving no
    end tell
    return pageCount as string
end run
"""


def get_page_count_for_file(path: Path) -> int:
    # AppleScript's `POSIX file` needs an absolute path — resolve defensively
    # so a relative path doesn't fail with a confusing "variable not defined"
    # error from inside the AppleScript instead of a clear Python error.
    abs_path = Path(path).resolve()
    result = subprocess.run(
        ["osascript", "-e", _APPLESCRIPT, str(abs_path)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    if result.returncode != 0:
        raise RuntimeError(f"Word page-count check failed: {result.stderr.strip()}")
    return int(result.stdout.strip())


def get_page_count(document: Document) -> int:
    with tempfile.NamedTemporaryFile(suffix=".docx", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    document.save(tmp_path)
    try:
        return get_page_count_for_file(tmp_path)
    finally:
        tmp_path.unlink(missing_ok=True)
