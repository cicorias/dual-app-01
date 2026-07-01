"""Shared cross-platform helpers for mise task scripts.

These helpers keep task logic in version-controlled Python (per the mise task
conventions) and behave identically on Windows, Linux, and macOS.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from collections.abc import Sequence


def find_executable(name: str) -> str:
    """Resolve an executable by name across platforms.

    On Windows, npm-installed CLIs like ``npx`` are exposed as ``npx.cmd``;
    ``shutil.which`` handles the ``PATHEXT`` resolution for us.
    """
    resolved = shutil.which(name)
    if resolved is None:
        sys.stderr.write(f"ERROR: required executable '{name}' not found on PATH\n")
        sys.exit(1)
    return resolved


def run(cmd: Sequence[str], *, cwd: str | None = None) -> None:
    """Run a command, echoing it, and exit non-zero if it fails."""
    printable = " ".join(cmd)
    location = f" (in {cwd})" if cwd else ""
    print(f"==> {printable}{location}", flush=True)
    result = subprocess.run(list(cmd), cwd=cwd)  # noqa: S603
    if result.returncode != 0:
        sys.exit(result.returncode)
