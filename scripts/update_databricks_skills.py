"""Update all installed Databricks agent skills (project scope) to latest.

Cross-platform replacement for the previous embedded bash task.
"""

from __future__ import annotations

from pathlib import Path

from _tools import find_executable, run


def main() -> None:
    npx = find_executable("npx")
    root = Path(__file__).resolve().parent.parent

    # Update all project-scoped skills to latest versions (non-interactive)
    run([npx, "-y", "skills", "update", "--project", "--yes"], cwd=str(root))

    print("Databricks skills updated to latest versions.")


if __name__ == "__main__":
    main()
