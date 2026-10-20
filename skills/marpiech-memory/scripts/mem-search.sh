#!/usr/bin/env bash
# mem-search.sh — lexical discovery for the repo-memory system.
# Searches every committed memory file for a pattern and prints, per match:
#   <path>:<line>: <matched text>   (<N>d <source>)
# Age is days since the file's `last-verified:` frontmatter (falls back to mtime),
# so staleness is visible at a glance (see references/conventions.md, tip-not-truth).
#
# Usage (run from the repository root):
#   scripts/mem-search.sh <pattern> [extra args...]   # extra args passed to rg/grep
#   scripts/mem-search.sh --list                      # enumerate all memory files + age
#
# Env:
#   MEM_FILENAME  memory file name to look for (default: MEMORY.md)
#
# Discovery is purely lexical — there is NO index or embedding. Uses ripgrep when a
# real `rg` binary is on PATH, otherwise find + grep.

set -euo pipefail

name="${MEM_FILENAME:-MEMORY.md}"
today=$(date +%s)
RG=$(type -P rg || true)   # type -P ignores shell functions/aliases — real binary only

# Portable "YYYY-MM-DD → epoch" (GNU date, then BSD/macOS date).
to_epoch() {
  date -d "$1" +%s 2>/dev/null || date -j -f %Y-%m-%d "$1" +%s 2>/dev/null
}

# Age in days, preferring last-verified: frontmatter over filesystem mtime.
age() {
  local f="$1" lv when src
  lv=$(grep -m1 -E '^last-verified:' "$f" 2>/dev/null \
       | sed -E 's/^last-verified:[[:space:]]*//; s/[[:space:]"]*$//' || true)
  if [[ -n "$lv" ]] && when=$(to_epoch "$lv"); then
    src="since last-verified"
  else
    when=$(stat -c %Y "$f" 2>/dev/null || stat -f %m "$f" 2>/dev/null || echo "$today")
    src="mtime, no last-verified"
  fi
  printf '%dd %s' "$(( (today - when) / 86400 ))" "$src"
}

# List every memory file, skipping the usual heavy / vendored directories.
list_files() {
  if [[ -n "$RG" ]]; then
    "$RG" --files -g "$name"
  else
    find . \( -name node_modules -o -name .git -o -name venv -o -name .venv \
              -o -name dist -o -name build -o -name target \) -prune \
      -o -name "$name" -print | sed 's#^\./##'
  fi
}

if [[ "${1:-}" == "--list" ]]; then
  list_files | sort | while read -r f; do
    printf '%s  (%s)\n' "$f" "$(age "$f")"
  done
  exit 0
fi

pattern="${1:?usage: mem-search.sh <pattern> [args...]  |  --list}"
shift || true

# Produce file:line:text, then annotate each line with the file's age.
if [[ -n "$RG" ]]; then
  "$RG" --line-number --no-heading --color=never -g "$name" "$pattern" "$@" || true
else
  list_files | tr '\n' '\0' | xargs -0 grep -nH -E "$@" -- "$pattern" 2>/dev/null || true
fi | while IFS= read -r hit; do
  file=${hit%%:*}; rest=${hit#*:}
  line=${rest%%:*}; text=${rest#*:}
  printf '%s:%s: %s  (%s)\n' "$file" "$line" "$text" "$(age "$file")"
done
