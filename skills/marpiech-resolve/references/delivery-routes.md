# Delivery routes

A **route** fixes, for one ticket: the branch, how to sync it, whether the local stack
is used, the test gate, the push target, the deploy to watch, and obligations after
delivery. Every resolve run is on exactly one route, chosen in Phase 2 and stated in
Phase 2.5. Routes are defined in the project adapter; this file describes the common
patterns and the rules every route obeys.

## Rules for every route

1. Never force-push (`--force` and `--force-with-lease` included: the lease check uses a
   possibly stale local view of the remote and can silently overwrite parallel work).
   If history must be rewritten, stop and ask the user to push themselves.
2. Never create a branch the project policy or the user did not name. If a branch seems
   needed, propose a name and wait for an explicit yes.
3. Fetch before pushing; never deliver against a stale view of the remote.
4. Absorb commits that exist only on the target branch (reverts, hotfixes) **deliberately**:
   on conflict read both sides, keep both behaviours unless one truly supersedes the other,
   never blanket `--ours`/`--theirs`; run the cheapest check on resolved files before
   committing the merge.
5. Push only the refs the route names, in one push when the route pushes several.
6. A rejected push means someone else pushed or the target has commits you lack —
   fetch and investigate; never force.
7. Watch the deploy to completion; cite run id + commit; never report "live" from a push.
8. Post-delivery obligations (merge-back, version bumps) are part of the ticket.

## Pattern A — trunk route (common default)

| aspect | value |
|--------|-------|
| branch | the trunk (e.g. `main` or `dev`) — no new branch |
| sync | `git pull --ff-only origin <trunk>`; merge `origin/<deploy-branch>` if it can hold extra commits |
| local stack | rebuild affected components; verify in the browser / with API calls |
| test gate | the full suite (unit + API + UI end-to-end) |
| push | `git push origin <trunk>` or `<trunk>:<trunk> <trunk>:<deploy-branch>` when two refs mirror each other |
| watch | the deploy workflow for that branch |

**Mirrored refs invariant** (when the trunk and a deploy branch must point at the same
commit): check before delivering —
`[ "$(git rev-parse origin/A)" = "$(git rev-parse origin/B)" ] && echo in-sync || echo DRIFT`.
IF B is ahead and A has nothing extra → fast-forward A to B (`git push origin origin/B:A`).
IF both have unique commits → stop and ask.

## Pattern B — branch-per-ticket route

| aspect | value |
|--------|-------|
| branch | `<KEY>-<slug>` from the trunk, per policy |
| sync | rebase or merge the trunk before opening the PR (merge if the branch was pushed) |
| test gate | the full suite locally, then CI on the PR |
| push | `git push -u origin <branch>`; open a PR; merging is the reviewer's step (or /marpiech-merge-pr) |
| watch | the PR checks; after merge, the deploy |

## Pattern C — hotfix route (release branch + merge-back)

For a defect that must reach an environment fed by a release branch before the next
regular release.

| aspect | value |
|--------|-------|
| branch | a **user-named** branch cut from `origin/<release-branch>`; reuse one the user points at |
| sync | `git fetch origin <release-branch>`; start from / fast-forward to its tip |
| local stack | often **not** usable: the release tree may be behind the trunk (migrations, config) — check the adapter |
| test gate | unit tests + lint of touched components (project config), template parse; no local e2e unless the adapter says so; compare failures against the branch tip |
| push | `git push origin <branch>:<release-branch>` (fast-forward only) |
| watch | the release environment's deploy; then verify **on that environment** (read-only inspection or UI as a test user) |
| after | **merge-back**: `git cherry-pick -x <shas>` onto the trunk; resolve semantically (the trunk's structure wins, keep both behaviours); run the trunk's gates; deliver on the trunk route and watch that deploy too |

Merge-back trap: anything versioned per tree (cache/parser/schema version stamps) must
stay **strictly ordered** — the trunk's number above the hotfix tree's — or an artifact
stamped by one tree makes the other skip its backfill.

## Writing a route in the adapter

```markdown
- <name> (keywords: …): branch …; sync …; local stack …; gate …; push …; watch …; after …
```
