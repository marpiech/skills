#!/usr/bin/env bash
# list-skills.sh — find marpiech-* skills available to a project and show how each is
# wired. Read-only.
#
# Looks in, in this order (first hit per name wins, as in Claude Code):
#   <repo>/.claude/skills/marpiech-*      project install
#   ~/.claude/skills/marpiech-*           user install
#   <clone>/skills/marpiech-*             skills shipped in the same clone as this
#                                         script but not installed anywhere (AVAILABLE)
#
# Usage (from the project root):
#   scripts/list-skills.sh              # table: name, status, adapter, path
#   scripts/list-skills.sh --snippets   # also print each INSTALLED skill's CLAUDE.md snippet

set -uo pipefail

show_snippets=false; [[ "${1:-}" == "--snippets" ]] && show_snippets=true
clone_skills=$(cd "$(dirname "$0")/../.." && pwd -P)   # .../skills (sibling skill dirs)
declare -A seen

# Print the fenced block that follows the "## CLAUDE.md snippet" heading.
snippet() {
  awk '
    /^## CLAUDE\.md snippet/ { insec = 1; next }
    insec && /^```/          { if (infence) exit; infence = 1; next }
    insec && infence         { print; next }
    insec && /^## /          { exit }   # next section reached without a fenced block
  ' "$1/SKILL.md"
}

row() {  # name status path
  local adapter="-"
  [[ -f ".claude/adapters/$1.md" ]] && adapter="yes"
  printf '%-22s %-10s %-8s %s\n' "$1" "$2" "$adapter" "$3"
}

printf '%-22s %-10s %-8s %s\n' SKILL STATUS ADAPTER PATH
installed=()
for base in ".claude/skills:project" "$HOME/.claude/skills:user"; do
  dir=${base%%:*}; kind=${base##*:}
  for s in "$dir"/marpiech-*; do
    [[ -f "$s/SKILL.md" ]] || continue
    name=$(basename "$s")
    [[ -n "${seen[$name]:-}" ]] && continue
    seen[$name]=1; installed+=("$s")
    row "$name" "$kind" "$(cd "$s" && pwd -P)"
  done
done
for s in "$clone_skills"/marpiech-*; do
  [[ -f "$s/SKILL.md" ]] || continue
  name=$(basename "$s")
  [[ -n "${seen[$name]:-}" ]] && continue
  row "$name" "AVAILABLE" "$s"
done

if $show_snippets; then
  for s in "${installed[@]}"; do
    echo
    echo "### $(basename "$s")"
    snippet "$s"
  done
fi
