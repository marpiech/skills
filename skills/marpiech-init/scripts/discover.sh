#!/usr/bin/env bash
# discover.sh — read-only fingerprint of a repository, used by marpiech-init to draft
# CLAUDE.md without guessing. Prints a markdown report to stdout; writes nothing.
#
# It only reports FILE NAMES and command names. It never prints the contents of env
# files, secret files, or config values — those are exactly what must not leak into a
# CLAUDE.md.
#
# Usage (from the repository root): scripts/discover.sh [repo-dir]

set -uo pipefail

repo="${1:-.}"
cd "$repo" || { echo "no such directory: $repo" >&2; exit 1; }

have() { command -v "$1" >/dev/null 2>&1; }
in_git=false; git rev-parse --is-inside-work-tree >/dev/null 2>&1 && in_git=true

# Tracked files only when in git (respects .gitignore); otherwise a pruned find.
files() {
  if $in_git; then git ls-files
  else find . \( -name node_modules -o -name .git -o -name venv -o -name .venv \) -prune \
         -o -type f -print | sed 's#^\./##'
  fi
}
exists() { files | grep -qE "$1"; }

echo "# Repository fingerprint: $(basename "$(pwd -P)")"
echo

echo "## Agent instruction files"
for f in CLAUDE.md CLAUDE.local.md AGENTS.md .claude/settings.json .claude/settings.local.json; do
  [[ -e "$f" ]] && printf -- '- %s (%s chars)\n' "$f" "$(wc -c < "$f" | tr -d ' ')"
done
[[ -d .claude/skills ]]   && echo "- .claude/skills/: $(ls .claude/skills | tr '\n' ' ')"
[[ -d .claude/commands ]] && echo "- .claude/commands/: $(ls .claude/commands | tr '\n' ' ')"
[[ -d .claude/adapters ]] && echo "- .claude/adapters/: $(ls .claude/adapters | tr '\n' ' ')"
echo

echo "## Languages & build files"
for pat in 'package\.json$' 'pyproject\.toml$' 'requirements.*\.txt$' 'setup\.py$' 'go\.mod$' \
           'Cargo\.toml$' 'pom\.xml$' 'build\.gradle(\.kts)?$' 'Gemfile$' 'composer\.json$' \
           '\.csproj$' 'Makefile$' 'justfile$' 'Taskfile\.ya?ml$' 'Dockerfile' \
           'docker-compose.*\.ya?ml$' '\.tf$' 'Chart\.yaml$' 'kustomization\.ya?ml$'; do
  n=$(files | grep -cE "(^|/)$pat")
  [[ "$n" -gt 0 ]] && printf -- '- %-28s %s file(s), e.g. %s\n' "$pat" "$n" "$(files | grep -E "(^|/)$pat" | head -1)"
done
echo

echo "## Candidate commands (names only — verify before documenting)"
if [[ -f package.json ]] && have python3; then
  python3 -I -c 'import json,sys; s=json.load(open("package.json")).get("scripts",{}); [print(f"- npm run {k}") for k in s]' 2>/dev/null
fi
if [[ -f Makefile ]]; then
  grep -E '^[A-Za-z0-9_.-]+:([^=]|$)' Makefile | cut -d: -f1 | grep -v '^\.' | sort -u | sed 's/^/- make /' | head -30
fi
if [[ -f pyproject.toml ]]; then
  grep -qE '^\[tool\.pytest' pyproject.toml && echo "- pytest (configured in pyproject.toml)"
  grep -qE '^\[tool\.ruff' pyproject.toml   && echo "- ruff (configured in pyproject.toml)"
  grep -qE '^\[tool\.mypy' pyproject.toml   && echo "- mypy (configured in pyproject.toml)"
  grep -qE '^\[project\.scripts\]' pyproject.toml && echo "- console scripts declared in [project.scripts]"
fi
[[ -f ruff.toml ]] && echo "- ruff (ruff.toml)"
[[ -f go.mod ]] && echo "- go test ./..."
[[ -f Cargo.toml ]] && echo "- cargo test"
echo

echo "## CI / automation"
files | grep -E '^\.github/workflows/|^\.gitlab-ci\.yml$|^\.circleci/|^Jenkinsfile$|^azure-pipelines\.yml$|^bitbucket-pipelines\.yml$|^\.pre-commit-config\.yaml$' | sed 's/^/- /'
echo

echo "## Secrets management hints (presence only, contents never read)"
for f in .infisical.json .sops.yaml .vault-token .envrc .env.example .env.template; do
  [[ -e "$f" ]] && echo "- $f present"
done
n_env=$(files | grep -cE '(^|/)\.env($|\.)' )
[[ "$n_env" -gt 0 ]] && echo "- WARNING: $n_env tracked .env-like file(s) — check they hold no real values"
echo

echo "## Documentation & knowledge stores"
for d in docs doc documentation claude-docs dev-docs adr docs/adr spec todo todos claude-todos; do
  [[ -d "$d" ]] && printf -- '- %s/ (%s files)\n' "$d" "$(find "$d" -type f | wc -l | tr -d ' ')"
done
n_mem=$(files | grep -cE '(^|/)MEMORY\.md$')
[[ "$n_mem" -gt 0 ]] && echo "- MEMORY.md files: $n_mem"
for f in README.md CONTRIBUTING.md ARCHITECTURE.md; do [[ -f "$f" ]] && echo "- $f"; done
echo

echo "## Top-level layout"
ls -1p | grep -vE '^(node_modules|venv|\.venv|__pycache__)/$' | head -40 | sed 's/^/- /'
echo

if $in_git; then
  echo "## Git"
  echo "- current branch: $(git branch --show-current)"
  def=$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null || echo "unknown")
  echo "- default remote branch: $def"
  echo "- local branches: $(git branch --format='%(refname:short)' | head -15 | tr '\n' ' ')"
  echo "- commits: $(git rev-list --count HEAD 2>/dev/null || echo 0)"
  echo "- ticket-like keys in last 200 commit subjects (most frequent prefix first):"
  git log -200 --format=%s 2>/dev/null | grep -oE '\b[A-Z][A-Z0-9]{1,9}-[0-9]+\b' \
    | sed -E 's/-[0-9]+$//' | sort | uniq -c | sort -rn | head -5 | sed 's/^/  /'
  echo "- commit subject style (last 5):"
  git log -5 --format='  %s' 2>/dev/null
fi
