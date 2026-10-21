#!/usr/bin/env bash
# claudemd-check.sh — audit a project's CLAUDE.md (and its deep-docs directory) against
# the marpiech-init conventions. Read-only; prints findings, exit 1 if any.
#
#   SIZE         file over the character budget (CLAUDE.md and each deep doc)
#   NO-BLOCK     the managed skills block markers are missing or unbalanced
#   DEAD-LINK    relative markdown link to a file that does not exist
#   PLACEHOLDER  an unfilled <TEMPLATE_VALUE> left from the template
#   SECRET?      a line that looks like it contains a credential (inspect by hand)
#   UNKNOWN-SKILL  /marpiech-* referenced but not installed (see list-skills.sh)
#
# Usage (from the project root):
#   scripts/claudemd-check.sh [--file CLAUDE.md] [--limit 20000] [--docs-dir claude-docs]

set -uo pipefail

file=CLAUDE.md; limit=20000; docs_dir=""
while [[ $# -gt 0 ]]; do
  case "$1" in
    --file) file="$2"; shift 2 ;;
    --limit) limit="$2"; shift 2 ;;
    --docs-dir) docs_dir="$2"; shift 2 ;;
    *) echo "unknown argument: $1" >&2; exit 2 ;;
  esac
done
[[ -f "$file" ]] || { echo "NO-FILE       $file does not exist (run INIT mode)"; exit 1; }

findings=0
report() { echo "$1"; findings=1; }
here=$(cd "$(dirname "$0")" && pwd -P)

check_size() {
  local f="$1" n
  n=$(wc -c < "$f" | tr -d ' ')
  [[ "$n" -gt "$limit" ]] && report "SIZE          $f is $n chars (budget $limit) — move detail to the deep-docs dir"
}

check_links() {
  local f="$1" d
  d=$(dirname "$f")
  # [text](target) where target is relative (no scheme, no leading #). Fenced blocks and
  # `inline code` are stripped first — regexes like `[a-z]([-a-z0-9]*)` are not links.
  awk '/^[[:space:]]*(```|~~~)/ { fence = !fence; next } !fence' "$f" | sed -E 's/`[^`]*`//g' \
    | grep -oE '\]\([^)#][^)]*\)' | sed -E 's/^\]\(//; s/\)$//; s/#.*$//; s/[[:space:]].*$//' \
    | grep -vE '^[a-z]+:' | sort -u | while read -r link; do
      [[ -z "$link" ]] && continue
      [[ -e "$d/$link" ]] || echo "DEAD-LINK     $f → $link"
    done
}

check_size "$file"
out=$(check_links "$file"); [[ -n "$out" ]] && report "$out"

starts=$(grep -c '<!-- marpiech-init:skills:start -->' "$file")
ends=$(grep -c '<!-- marpiech-init:skills:end -->' "$file")
if [[ "$starts" -ne 1 || "$ends" -ne 1 ]]; then
  report "NO-BLOCK      managed skills block markers: start=$starts end=$ends (expected 1/1)"
fi

grep -nE '<[A-Z][A-Z0-9_]{2,}>' "$file" \
  | while read -r hit; do echo "PLACEHOLDER   $file:${hit%%:*} unfilled template value"; done | grep . && findings=1

grep -nEi '(password|passwd|secret|token|api[_-]?key)[[:space:]]*[:=][[:space:]]*["'"'"']?[A-Za-z0-9/+_-]{8,}|BEGIN .*PRIVATE KEY|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,}|xox[bap]-|sk-[A-Za-z0-9]{20,}' "$file" \
  | while read -r hit; do echo "SECRET?       $file:${hit%%:*}"; done | grep . && findings=1

installed=$("$here/list-skills.sh" | awk 'NR>1 && $2!="AVAILABLE" {print $1}')
for ref in $(grep -oE '/marpiech-[a-z0-9-]+' "$file" | sort -u | sed 's#^/##'); do
  grep -qx "$ref" <<<"$installed" || report "UNKNOWN-SKILL $ref is referenced but not installed"
done

if [[ -n "$docs_dir" && -d "$docs_dir" ]]; then
  while IFS= read -r f; do
    check_size "$f"
    out=$(check_links "$f"); [[ -n "$out" ]] && report "$out"
  done < <(find "$docs_dir" -name '*.md' -not -path '*/archive/*')
fi

[[ $findings -eq 0 ]] && echo "claudemd-check: clean ($(wc -c < "$file" | tr -d ' ')/$limit chars)."
exit $findings
