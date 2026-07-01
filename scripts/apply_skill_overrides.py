"""Re-apply project-local overrides to vendored Databricks agent skills.

The skills under ``.agents/skills`` are vendored copies pulled from GitHub and
tracked in ``skills-lock.json``. Running ``npx skills update`` overwrites those
files, discarding any local edits. This script re-applies our project standard
(Databricks serverless **environment version 5** — Python 3.12.3, Ubuntu 24.04,
Databricks Connect 18, Scala 2.13.16, JDK 17) on top of the freshly-pulled
skills, idempotently, so it is safe to run after every update.

It is wired into the ``update-databricks-skills`` mise task and can also be run
standalone:

    uv run --no-project scripts/apply_skill_overrides.py

Each override is a literal ``find``/``replace`` pair. ``done_marker`` (defaults
to ``replace``) is a token whose presence means the override is already applied
so the run is idempotent. If neither ``find`` nor ``done_marker`` is present the
anchor has drifted upstream and a WARNING is emitted so the override can be
refreshed. Only ``.agents/skills`` is edited; the ``.claude/skills`` entries are
symlinks into it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Override:
    """A single literal substitution applied to a vendored skill file."""

    find: str
    replace: str
    done_marker: str | None = None

    def marker(self) -> str:
        return self.done_marker if self.done_marker is not None else self.replace


@dataclass
class FileOverrides:
    """All overrides that target one skill file (relative to .agents/skills)."""

    relpath: str
    overrides: list[Override] = field(default_factory=list)


# Bump example serverless environment specs from the older env-2 (Python 3.11)
# default to our project standard, env-5 (Python 3.12). The JSON form appears in
# several files; the Python-kwarg form only in the configuration guide.
_CLIENT_BUMP_JSON = Override('"client": "2"', '"client": "5"')
_CLIENT_BUMP_KWARG = Override('client="2"', 'client="5"')

# Additive row for the DBR -> spec.client mapping tables: keep the factual
# historical rows, append our recommended default (env 5, also Python 3.12).
_MAPPING_ROW = Override(
    find='| 16.x+ | `"3"` | 3.12 |',
    replace='| 16.x+ | `"3"` | 3.12 |\n| 16.x+ (recommended) | `"5"` | 3.12 (env 5, Connect 18) |',
    done_marker='| 16.x+ (recommended) | `"5"` | 3.12 (env 5, Connect 18) |',
)

OVERRIDES: list[FileOverrides] = [
    FileOverrides(
        "databricks-apps-python/SKILL.md",
        [
            Override(
                "Python 3.11, Ubuntu 22.04, 2 vCPU, 6 GB RAM",
                "Python 3.12, Ubuntu 24.04, 2 vCPU, 6 GB RAM",
            ),
            Override(
                "Python 3.11, Ubuntu 22.04 LTS",
                "Python 3.12, Ubuntu 24.04 LTS",
            ),
        ],
    ),
    FileOverrides(
        "databricks-serverless-migration/SKILL.md",
        [_CLIENT_BUMP_JSON, _MAPPING_ROW],
    ),
    FileOverrides(
        "databricks-serverless-migration/references/configuration-guide.md",
        [_CLIENT_BUMP_JSON, _CLIENT_BUMP_KWARG, _MAPPING_ROW],
    ),
    FileOverrides(
        "databricks-serverless-migration/references/mlflow-uc-patterns.md",
        [_CLIENT_BUMP_JSON],
    ),
    FileOverrides(
        "databricks-serverless-migration/references/code-patterns.md",
        [_CLIENT_BUMP_JSON],
    ),
]


def _skills_dir() -> Path:
    return Path(__file__).resolve().parent.parent / ".agents" / "skills"


def apply_file(base: Path, spec: FileOverrides) -> tuple[int, int, int]:
    """Apply all overrides for one file. Returns (applied, skipped, missing)."""
    path = base / spec.relpath
    if not path.is_file():
        print(f"WARN  missing skill file (not installed?): {spec.relpath}")
        return (0, 0, len(spec.overrides))

    text = path.read_text(encoding="utf-8")
    original = text
    applied = skipped = missing = 0

    for ov in spec.overrides:
        # Append-style overrides (explicit done_marker) embed `find` inside
        # `replace`, so check the marker first to stay idempotent.
        if ov.done_marker is not None and ov.done_marker in text:
            skipped += 1
        elif ov.find in text:
            text = text.replace(ov.find, ov.replace)
            applied += 1
        elif ov.marker() in text:
            skipped += 1
        else:
            missing += 1
            print(
                f"WARN  anchor drifted in {spec.relpath!r}; refresh override for: "
                f"{ov.find!r}"
            )

    if text != original:
        path.write_text(text, encoding="utf-8")
        print(f"OK    {spec.relpath}: {applied} applied, {skipped} already current")
    elif missing == 0:
        print(f"--    {spec.relpath}: already current ({skipped} overrides)")

    return (applied, skipped, missing)


def main() -> None:
    base = _skills_dir()
    if not base.is_dir():
        raise SystemExit(f"ERROR: skills dir not found: {base}")

    total_applied = total_skipped = total_missing = 0
    for spec in OVERRIDES:
        a, s, m = apply_file(base, spec)
        total_applied += a
        total_skipped += s
        total_missing += m

    print(
        f"\nSkill overrides: {total_applied} applied, {total_skipped} already current, "
        f"{total_missing} drifted anchors."
    )
    if total_missing:
        print(
            "One or more anchors drifted upstream — review the WARN lines and "
            "update scripts/apply_skill_overrides.py."
        )


if __name__ == "__main__":
    main()
