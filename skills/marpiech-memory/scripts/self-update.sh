#!/usr/bin/env bash
# self-update.sh — Step 0 of every marpiech-* skill.
# Checks whether the git clone this skill was installed from has upstream changes.
# It NEVER applies changes silently: without --apply it only reports; Claude shows the
# report to the user and re-runs with --apply only after the user agrees.
#
# Usage:
#   scripts/self-update.sh            # check (fetches at most once per 24h)
#   scripts/self-update.sh --force    # check, fetching even if fetched recently
#   scripts/self-update.sh --apply    # fast-forward the clone (after user approval)
#
# Exit codes: 0 = nothing to do / skipped / applied, 10 = updates available,
#             20 = cannot update automatically (local edits or diverged history).

set -uo pipefail

mode="${1:-check}"
skill_dir=$(cd "$(dirname "$0")/.." && pwd -P)   # -P resolves the install symlink

if ! root=$(git -C "$skill_dir" rev-parse --show-toplevel 2>/dev/null); then
  echo "self-update: skill is not inside a git clone (copied install) — skipping."
  exit 0
fi

git_dir=$(git -C "$root" rev-parse --absolute-git-dir)
stamp="$git_dir/marpiech-skills-last-fetch"   # lives in .git/, never committed
upstream=$(git -C "$root" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null || echo origin/main)
remote=${upstream%%/*}

if [[ "$mode" == "--apply" ]]; then
  if [[ -n $(git -C "$root" status --porcelain) ]]; then
    echo "self-update: clone has local modifications — refusing to pull. Commit or stash them first."
    exit 20
  fi
  git -C "$root" pull --ff-only --quiet "$remote" "${upstream#*/}" \
    && { echo "self-update: updated to $(git -C "$root" rev-parse --short HEAD)."; exit 0; } \
    || { echo "self-update: fast-forward failed (diverged history) — resolve manually."; exit 20; }
fi

# Fetch at most once per day unless forced; offline is not an error.
now=$(date +%s)
last=$(cat "$stamp" 2>/dev/null || echo 0)
if [[ "$mode" == "--force" || $(( now - last )) -ge 86400 ]]; then
  if git -C "$root" fetch --quiet "$remote" 2>/dev/null; then
    echo "$now" > "$stamp"
  else
    echo "self-update: fetch from '$remote' failed (offline?) — using last known state."
  fi
fi

behind=$(git -C "$root" rev-list --count "HEAD..$upstream" 2>/dev/null || echo 0)
ahead=$(git -C "$root" rev-list --count "$upstream..HEAD" 2>/dev/null || echo 0)

if [[ "$behind" -eq 0 ]]; then
  echo "self-update: up to date with $upstream ($(git -C "$root" remote get-url "$remote" 2>/dev/null))."
  exit 0
fi

echo "self-update: $behind new commit(s) on $upstream from $(git -C "$root" remote get-url "$remote" 2>/dev/null):"
git -C "$root" log --oneline "HEAD..$upstream" | head -20
echo "--- files changed:"
git -C "$root" diff --stat "HEAD...$upstream" | tail -15

if [[ "$ahead" -gt 0 || -n $(git -C "$root" status --porcelain) ]]; then
  echo "self-update: clone also has local commits or edits — cannot fast-forward automatically."
  exit 20
fi
echo "self-update: ask the user, then run: $0 --apply"
exit 10
