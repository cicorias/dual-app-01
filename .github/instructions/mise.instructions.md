---
description: Mise toolchain conventions and Python-based task automation
applyTo: "mise.toml,**/*.py"
---

# Mise Task Automation

## Run Commands Must Use Python Files

**All `run` commands in `mise.toml` must execute Python scripts (or other language files), not embedded shell scripts.**

### Rationale
- **Maintainability:** Logic stays in dedicated, version-controlled files rather than embedded in TOML
- **Testability:** Python scripts can be unit tested independently
- **Cross-platform:** Python is more portable than bash scripts (Windows, Linux, macOS)
- **Readability:** Complex logic is clearer in a full programming language than shell syntax

### Pattern

**❌ AVOID** embedded shell scripts:
```toml
[tasks.my-task]
run = """
set -euo pipefail
for dir in app-a app-b; do
  (cd "$dir" && uv sync)
done
"""
```

**✅ DO** call Python files:
```toml
[tasks.my-task]
description = "Brief description"
run = "uv run scripts/my_task.py"
```

Then create `scripts/my_task.py` with the logic.

### Guidelines
- Store task scripts in `scripts/` directory (or a dedicated subdirectory if organizing by purpose)
- Use `uv run scripts/script_name.py` to invoke scripts (ensures correct Python environment)
- Scripts should handle errors gracefully (exit non-zero on failure)
- Document script purpose and usage in docstrings
- Add `sys.exit(1)` on error conditions so mise tasks fail appropriately

## Task Arguments - Usage Spec Reference

**REMINDER:** Always use the `usage` field. Never use `$1`, `$@`, or shell-native argument handling.

The `usage` field uses [KDL-inspired syntax](https://usage.jdx.dev/) to define arguments, flags, and completions.

### Positional Arguments (`arg`)

| Attribute | Type | Default | Description |
|-----------|------|---------|-------------|
| `(name)` | string | *required* | `"<name>"` = required, `"[name]"` = optional. `"<file>"` triggers file completion, `"<dir>"` triggers dir completion. |
| `help` | string | none | Short help text shown with `-h` |
| `long_help` | string | none | Extended help text shown with `--help` |
| `default` | string | none | Default value if not provided. `default=""` sets to empty string (different from unset). |
| `env` | string | none | Environment variable that can provide this arg's value. Priority: CLI > env > default. |
| `var` | boolean | `false` | Variadic mode (accept multiple values). `"<name>"` requires 1+, `"[name]"` accepts 0+. Shorthand: `"<name>..."` |
| `var_min` | integer | none | Minimum values when variadic |
| `var_max` | integer | none | Maximum values when variadic |
| `choices` | values | none | Restrict to enumerated set. Env-backed via `choices env="VAR_NAME"` (split on commas/whitespace, resolved at parse/completion time); literal + env can be **combined**: `choices "local" env="VAR"` (deduped) |
| `double_dash` | string | none | `"required"`, `"optional"`, `"automatic"`, `"preserve"` |
| `hide` | boolean | `false` | Exclude from help output |
| `parse` | string | none | Parse arg value with external command (template: `"mycli parse {}"`) |

## Best Practices

### DO ✅

- **Always use `usage` field** for task arguments
- Use `${var?}` for required args to fail early
- Set `description` for discoverability
- Use `sources`/`outputs` for cacheable tasks
- Use `depends` for task ordering; structured `depends` to pass args/env
- Use `confirm` for destructive operations
- Use `choices` for stable enums, `complete` for dynamic/filesystem-derived values
- Group related tasks with namespaces (e.g., `test:unit`, `test:e2e`)
- Use `mise.local.toml` for personal overrides (gitignored)
- Prefer aqua backend for security (cosign/SLSA/attestation verification)
- Migrate from `ubi:` backend to `github:` (ubi deprecated)
- Use `env._.file`/`env._.path` instead of the deprecated top-level `env_file`/`dotenv`/`env_path` (removed 2027.4.0)
- Redact sensitive values with `redact = true`; use SOPS or direct-age for secrets
- Use templates for dynamic values instead of hardcoding paths
- Use `extends` to share config between similar tasks
- Use shims in `.zprofile`/`.bash_profile` and PATH activation in `.zshrc`/`.bashrc`
- Use `[tool_alias]` (not deprecated `[alias]`)
- Pin tool versions with `mise.lock` + `locked = true` in CI; use `minimum_release_age` for supply-chain delay
- Use `jdx/mise-action@v4` in GitHub Actions — it handles masking automatically
- Use `mise bootstrap` with `[bootstrap]`/`[dotfiles]` to onboard new developers and provision fresh machines in one command

### DON'T ❌

- Use `$1`, `$2`, `$@`, `$*` for arguments
- Use `$args` in PowerShell
- Use inline template functions `{{arg()}}`/`{{option()}}`/`{{flag()}}` in run scripts (deprecated, removed 2027.5.0)
- Forget to quote glob patterns in sources
- Set env vars in `env` that deps need (they don't inherit — use structured `depends` with `env`)
- Use `raw = true` unless interactive input needed (forces single-threaded, bypasses redactions)
- Set `MISE_ENV` in `mise.toml` (it determines which files to load — use `.miserc.toml`)
- Manually add executables to shims directory (`mise reshim` deletes them)
- Use `MISE_RAW=1` without knowing it sets `MISE_JOBS=1`
- Install new `asdf:` or `vfox:` plugins when aqua/github alternatives exist

### Complete Task Example

```toml
[tasks.deploy]
description = "Deploy application to environment"
alias = "d"
depends = ["build", "test"]
usage = '''
arg "<env>" choices "dev" "staging" "prod" help="Target environment"
flag "-f --force" help="Skip confirmation"
flag "--dry-run" help="Preview only"
'''
env = { DEPLOY_TIMESTAMP = "{{now()}}" }
tools = { node = "22" }
sources = ["dist/**/*"]
timeout = "5m"
confirm = "Deploy to {{usage.env}}?"
run = '''
#!/usr/bin/env bash
set -euo pipefail

if [ -n "${usage_dry_run:-}" ]; then
  echo "DRY RUN: Would deploy to ${usage_env?}"
  exit 0
fi

./scripts/deploy.sh "${usage_env?}"
'''
```

### Complete File Task Example

```bash
#!/usr/bin/env bash
#MISE description="Run database migrations"
#MISE alias="migrate"
#MISE depends=["db:check"]
#MISE tools={postgresql="16"}
#USAGE arg "<direction>" choices "up" "down" help="Migration direction"
#USAGE flag "-n --count <n>" default="1" help="Number of migrations"
#USAGE flag "--dry-run" help="Preview SQL only"

set -euo pipefail

direction="${usage_direction?}"
count="${usage_count:-1}"

if [ -n "${usage_dry_run:-}" ]; then
  echo "Would run $count migration(s) $direction"
  exit 0
fi

migrate "$direction" -n "$count"
```

### Complete Dev Tools + Env Example

```toml
min_version = "2024.11.1"

[settings]
jobs = 8
task.output = "interleave"
task.timings = true
env_shell_expand = true

[tools]
node = "22"
python = { version = "3.12", postinstall = "pip install -r requirements.txt" }
"aqua:BurntSushi/ripgrep" = "latest"
"npm:prettier" = "latest"

[env]
NODE_ENV = "development"
DATABASE_URL = { required = "Set postgres connection string" }
API_KEY = { value = "{{env.API_KEY}}", redact = true }
_.path = ["./node_modules/.bin", "{{config_root}}/scripts"]
_.file = [".env", ".env.local"]

[hooks]
enter = "echo 'Welcome to {{vars.project_name}}'"

[vars]
project_name = "myapp"

[tasks.dev]
description = "Start development server"
depends = ["build"]
tools = { node = "22" }
run = "npm run dev"

[tasks.build]
description = "Build project"
sources = ["src/**/*.ts", "tsconfig.json"]
outputs = ["dist/**/*"]
run = "tsc --build"

[tasks.test]
description = "Run tests"
depends = ["build"]
run = "vitest run"
```