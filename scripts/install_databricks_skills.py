"""Install ALL Databricks agent skills (project, symlinked) for both agents.

Cross-platform replacement for the previous embedded bash task. Installs every
skill from databricks/databricks-agent-skills for github-copilot and claude-code.
"""

from __future__ import annotations

from pathlib import Path

from _tools import find_executable, run


def main() -> None:
    npx = find_executable("npx")
    root = Path(__file__).resolve().parent.parent

    # npx skills does not create the .claude/skills root, so ensure it (and .agents) exist first
    (root / ".claude" / "skills").mkdir(parents=True, exist_ok=True)
    (root / ".agents" / "skills").mkdir(parents=True, exist_ok=True)

    # Project install with symlinks (default), all skills, both agents
    run(
        [
            npx, "-y", "skills", "add", "databricks/databricks-agent-skills",
            "-s", "*",
            "-a", "github-copilot",
            "-a", "claude-code",
            "-y",
        ],
        cwd=str(root),
    )

    # Verify both agent skill roots exist when done
    for path in (root / ".agents" / "skills", root / ".claude" / "skills"):
        if not path.is_dir():
            raise SystemExit(f"ERROR: {path} missing")

    print("Databricks skills installed for github-copilot and claude-code.")


if __name__ == "__main__":
    main()
