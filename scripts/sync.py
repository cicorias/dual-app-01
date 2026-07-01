"""Install both apps' dependencies with uv (from each app's pyproject.toml).

Cross-platform replacement for the previous embedded bash loop.
"""

from __future__ import annotations

from pathlib import Path

from _tools import find_executable, run

APP_DIRS = ("app-a-frontend", "app-b-backend")


def main() -> None:
    uv = find_executable("uv")
    root = Path(__file__).resolve().parent.parent
    for name in APP_DIRS:
        app_dir = root / name
        if not app_dir.is_dir():
            raise SystemExit(f"ERROR: app directory not found: {app_dir}")
        run([uv, "sync"], cwd=str(app_dir))


if __name__ == "__main__":
    main()
