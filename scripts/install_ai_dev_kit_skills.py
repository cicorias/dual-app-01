"""Install selected Databricks skills from databricks-solutions/ai-dev-kit.

Cross-platform replacement for the previous embedded bash task. Installs a
curated subset for github-copilot and claude-code.
"""

from __future__ import annotations

from pathlib import Path

from _tools import find_executable, run

SKILLS = (
    "databricks-genie",
    "databricks-mlflow-evaluation",
    "databricks-python-sdk",
    "databricks-synthetic-data-gen",
    "databricks-unity-catalog",
    "databricks-aibi-dashboards",
)


def main() -> None:
    npx = find_executable("npx")
    root = Path(__file__).resolve().parent.parent

    # npx skills does not create the .claude/skills root, so ensure it (and .agents) exist first
    (root / ".claude" / "skills").mkdir(parents=True, exist_ok=True)
    (root / ".agents" / "skills").mkdir(parents=True, exist_ok=True)

    # ai-dev-kit stores skills under databricks-skills/, so --full-depth is required to discover them
    cmd = [npx, "-y", "skills", "add", "databricks-solutions/ai-dev-kit", "--full-depth"]
    for skill in SKILLS:
        cmd += ["-s", skill]
    cmd += ["-a", "github-copilot", "-a", "claude-code", "-y"]
    run(cmd, cwd=str(root))

    # Verify both agent skill roots exist when done
    for path in (root / ".agents" / "skills", root / ".claude" / "skills"):
        if not path.is_dir():
            raise SystemExit(f"ERROR: {path} missing")

    print("ai-dev-kit skills installed for github-copilot and claude-code.")


if __name__ == "__main__":
    main()
