#!/usr/bin/env bash
# mem-lint.sh — health check for the repo-memory system; run at the end of a session.
# Reports, without changing anything:
#   MISSING-FIELD  a memory file lacks a required frontmatter field
#   ORPHAN         a memory file the root index does not link to
#   DEAD-LINK      a root-index link pointing at a file that no longer exists
#   STALE          last-verified older than the threshold
#
# Usage (run from the repository root):
#   scripts/mem-lint.sh [--stale-days N]      # default N = 90
# Env:
#   MEM_FILENAME  memory file name (default: MEMORY.md)
#   MEM_ROOT      root index path (default: ./$MEM_FILENAME)
# Exit code: 0 = clean, 1 = findings (informational — never blocks anything by itself).

set -uo pipefail

name="${MEM_FILENAME:-MEMORY.md}"
root_index="${MEM_ROOT:-$name}"
stale_days=90
[[ "${1:-}" == "--stale-days" ]] && stale_days="${2:?missing N}"

here=$(cd "$(dirname "$0")" && pwd -P)
findings=0
report() { echo "$1"; findings=1; }

to_epoch() { date -d "$1" +%s 2>/dev/null || date -j -f %Y-%m-%d "$1" +%s 2>/dev/null; }
today=$(date +%s)

files=$(MEM_FILENAME="$name" "$here/mem-search.sh" --list | sed -E 's/  \(.*$//')

for f in $files; do
  [[ "$f" == "$root_index" ]] && continue

  # Required frontmatter fields, searched only inside the first --- block.
  fm=$(awk 'NR==1 && $0=="---"{infm=1; next} infm && $0=="---"{exit} infm{print}' "$f")
  for field in summary why created last-verified; do
    grep -qE "^${field}:[[:space:]]*[^[:space:]]" <<<"$fm" || report "MISSING-FIELD $f: $field"
  done

  # Linked from the root index? (path relative to the repo root)
  if [[ -f "$root_index" ]] && ! grep -qF "]($f)" "$root_index"; then
    report "ORPHAN        $f (add a pointer line to $root_index)"
  fi

  lv=$(grep -m1 -E '^last-verified:' <<<"$fm" | sed -E 's/^last-verified:[[:space:]]*//; s/[[:space:]"]*$//')
  if [[ -n "$lv" ]] && when=$(to_epoch "$lv"); then
    days=$(( (today - when) / 86400 ))
    [[ $days -gt $stale_days ]] && report "STALE         $f (${days}d since last-verified)"
  fi
done

# Dead links in the root index.
if [[ -f "$root_index" ]]; then
  # Only pointer lines ("- [topic](path) — hook"); format examples in backticks are skipped.
  grep -E '^[[:space:]]*- \[' "$root_index" | grep -oE '\]\([^)]+\)' | sed -E 's/^\]\(//; s/\)$//; s/#.*$//' | while read -r link; do
    [[ "$link" =~ ^https?:// ]] && continue
    [[ -e "$link" ]] || echo "DEAD-LINK     $root_index → $link"
  done | grep . && findings=1
else
  report "NO-INDEX      $root_index does not exist (run the INIT mode of the skill)"
fi

[[ $findings -eq 0 ]] && echo "mem-lint: clean."
exit $findings
