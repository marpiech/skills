#!/usr/bin/env bash
# mem-stamp.sh — set created:/last-verified: frontmatter on a memory file.
#   - If the file has no YAML frontmatter, prepend a minimal block.
#   - `created:` is added only if missing (the original date is preserved).
#   - `last-verified:` is always bumped to today — run this after re-checking a file.
# Only the FIRST frontmatter block is touched, so dated entries in the body that
# happen to mention these keys are left alone.
# Why: freshness is the backbone of tip-not-truth (references/conventions.md).
#
# Usage: scripts/mem-stamp.sh <path/to/MEMORY.md> [more files...]

set -euo pipefail

[[ $# -ge 1 ]] || { echo "usage: mem-stamp.sh <file> [file...]" >&2; exit 1; }
today=$(date +%F)

for f in "$@"; do
  [[ -f "$f" ]] || { echo "no such file: $f" >&2; exit 1; }
  tmp=$(mktemp)

  if ! head -1 "$f" | grep -qx -- '---'; then
    {
      printf -- '---\nsummary: \nwhy: \ncreated: %s\nlast-verified: %s\n---\n\n' "$today" "$today"
      cat "$f"
    } > "$tmp"
    mv "$tmp" "$f"
    echo "added frontmatter (created/last-verified = $today) → $f"
    continue
  fi

  awk -v today="$today" '
    BEGIN { infm = 0; seen_created = 0; done_lv = 0 }
    NR == 1 && $0 == "---" { infm = 1; print; next }
    infm && $0 == "---" {
      if (!seen_created) print "created: " today
      if (!done_lv)      print "last-verified: " today
      infm = 0; print; next
    }
    infm && /^created:/        { seen_created = 1; print; next }
    infm && /^last-verified:/  { print "last-verified: " today; done_lv = 1; next }
    { print }
  ' "$f" > "$tmp"
  mv "$tmp" "$f"
  echo "stamped last-verified=$today (created preserved) → $f"
done
