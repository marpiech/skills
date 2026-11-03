#!/bin/sh
# Copy to hooks/pre-push (chmod +x) and enable once per clone:  git config core.hooksPath hooks
# Refuses a push to the release branch when files that SHIP changed but the version did not
# go up, or when the new version is already tagged. A convenience, not a security boundary
# (--no-verify skips it): mirror the rule in CI / branch protection.
#
# Settings — edit these three:
RELEASE_BRANCH="main"
SHIPPED_PATHS="src pyproject.toml"          # paths whose change requires a new version
VERSION_FILE="pyproject.toml"               # file holding the version
VERSION_REGEX='^version *= *"([^"]+)"'      # first capture group = the version

REMOTE="${1:-origin}"
ZERO=0000000000000000000000000000000000000000

version_at() {  # $1 = commit-ish
    git show "$1:$VERSION_FILE" 2>/dev/null | sed -nE "s/$VERSION_REGEX/\\1/p" | head -n 1
}

greater() {     # is $1 > $2 (PEP 440-ish numeric compare)
    python3 - "$1" "$2" <<'PY'
import re, sys
def key(v):
    m = re.match(r"v?(\d+(?:\.\d+)*)(.*)", v)
    nums = [int(x) for x in m.group(1).split(".")] + [0] * 4
    return nums[:4], m.group(2) == ""      # a final release sorts after its pre-releases
sys.exit(0 if key(sys.argv[1]) > key(sys.argv[2]) else 1)
PY
}

blocked=0
while read -r _lref lsha rref _rsha; do
    [ "$rref" = "refs/heads/$RELEASE_BRANCH" ] || continue
    [ "$lsha" = "$ZERO" ] && continue
    git fetch -q "$REMOTE" "$RELEASE_BRANCH" 2>/dev/null
    base="$REMOTE/$RELEASE_BRANCH"
    if ! git rev-parse -q --verify "$base" >/dev/null; then
        echo "pre-push: no $base to compare with; CI decides."; continue
    fi
    # shellcheck disable=SC2086
    if [ -z "$(git diff --name-only "$base" "$lsha" -- $SHIPPED_PATHS)" ]; then
        echo "pre-push: nothing that ships changed; no version bump needed."; continue
    fi
    new=$(version_at "$lsha"); old=$(version_at "$base")
    if [ -z "$new" ]; then
        echo "pre-push: cannot read the version from $VERSION_FILE; refusing to guess." >&2
        blocked=1; continue
    fi
    if [ -n "$old" ] && ! greater "$new" "$old"; then
        echo "pre-push: version $new is not greater than $base's $old — bump it." >&2
        echo "          A published version can never be replaced." >&2
        blocked=1; continue
    fi
    if git rev-parse -q --verify "refs/tags/v$new" >/dev/null; then
        echo "pre-push: tag v$new exists — that version is already released." >&2
        blocked=1; continue
    fi
    echo "pre-push: version $new > ${old:-none}, not yet tagged. OK."
done
exit $blocked
