---
name: marpiech-observe-ci
description: The authority on what actually shipped. Observes GitHub Actions through a read-only helper — finds the run a push triggered, watches it to completion in the background (every job state change reported, silence never mistaken for progress), explains a failure down to the job, step and error lines, and proves whether a commit has landed on a deploy branch through a successful deploy. Separates code failures from infrastructure failures (runner never picked the job up, provider outage, fail-safe steps that went green without doing the work). Use when the user asks "did it deploy?", "is staging green?", "why did CI fail?", "what's blocking the deploy?", "watch the run", "/marpiech-observe-ci", after any push that should deploy, when a deploy seems stuck or no run appeared, and before ever claiming a change is live.
---

# marpiech-observe-ci — what actually shipped

## Purpose

A commit on a deploy branch is not a deploy: a gate can block it, a scan can fail it,
a newer push can cancel it, or the CI provider can be down. Reports like "it's live"
based on a push or a green tick are the most common false claims in delivery work. This
skill makes the claim checkable: it ties every statement to a run id and a commit,
names the gate that failed, and distinguishes "your code broke" from "the platform
broke". Outcome: a precise answer — landed / not landed / in flight / blocked by
<gate> — with evidence.

`<SKILL_DIR>` = the directory holding this SKILL.md; `<CI>` =
`python3 <SKILL_DIR>/scripts/ci.py` (needs `gh`, read-only).

---

## Step 0 — Self-update (every run, takes a second)

1. Run `<SKILL_DIR>/scripts/self-update.sh`.
2. Interpret the exit code:
   - `0` → nothing to do (up to date, offline, or a copied install). Continue silently.
   - `10` → updates are available. Show the user the printed commit list and file
     summary in one short message and ASK whether to update. IF yes → run
     `<SKILL_DIR>/scripts/self-update.sh --apply`, then re-read this SKILL.md before
     continuing (it may have changed). IF no → continue with the current version.
   - `20` → the clone has local edits or diverged history. Tell the user in one line;
     do not attempt to fix it; continue with the current version.
3. Never pull, reset, or stash on your own. Never run self-update more than once per
   session.

## Step 1 — Load the project adapter

1. Look for `.claude/adapters/marpiech-observe-ci.md` in the repository root.
2. IF present → read the **pipeline map** (which push/branch triggers which workflow,
   which jobs are gates, which branch deploys to which environment), health endpoints,
   known fail-safe steps and how to assert they really ran, runner notes (self-hosted
   runner logs, ports it binds), the CI status page, project-specific traps.
3. ELSE → build a provisional map: `ls .github/workflows/`, read each workflow's `on:`
   triggers and job names, and `gh run list --limit 20`. Offer at the end to save it as
   the adapter (`templates/adapter.template.md`).
4. IF the CI is not GitHub Actions → use the adapter's commands for that provider and
   keep the same algorithm and reporting rules.

---

## Algorithm — pick the question, then follow its branch

```
"watch this push / did my push deploy?"      → A. WATCH
"why did it fail? / what's blocking?"        → B. WHY
"is <commit/change> live? / is X deployed?"  → C. LANDED
"is <branch/env> green?"                     → D. STATUS
```

### A. Watch a push to completion

1. Identify the commit: `git rev-parse HEAD` (or the pushed sha) and the branch.
2. Start a **background** watcher so the conversation can continue:
   `<CI> watch --branch <branch> --sha <sha> [--workflow <deploy workflow>]`
   (run it under the session's background-monitor tool when available, so each printed
   line arrives as an event; otherwise run it in the background and read its output).
   It waits up to 3 minutes for the run to appear, then prints every job transition.
3. Interpret the exit code: `0` success → go to C to confirm landing; `1` failed →
   B; `2` timeout → report "still running" with the run id and keep watching only if
   the user wants; `3` no run appeared → see trap "push but no run" in
   `references/traps.md`.
4. Never stop watching silently and never summarise an unfinished run as success.

### B. Explain a failure

1. Find the run: `<CI> find --branch <branch> [--sha <sha>]` → newest run for the head
   commit (older runs for the same commit are usually cancelled/superseded).
2. `<CI> why <RUN_ID>` → failed jobs, failed steps, the CI's error annotations and the
   last matching log lines.
3. Classify (the first match wins):
   - job failed with **no steps** → **infrastructure** (runner never acquired the job):
     do not look for a code error; check runner/provider status, then re-run;
   - failure at a **network / cluster-connection / registry** step after all gates
     passed → infrastructure or credentials, not the change;
   - a **gate** step (lint, unit, e2e, migrations, security scan) → name the gate; read
     the error lines; reproduce locally with the same command before fixing;
   - a **deploy/rollout** step → read the rollout error; check the environment
     (marpiech-resolve `references/production-diagnosis.md` if it is installed).
4. Attribute honestly: on a shared branch the run may carry other people's commits —
   `git log --oneline <run sha> -10` — and the failing part may not be yours.
5. IF a re-run is the right fix (infrastructure) → propose `gh run rerun <RUN_ID>
   --failed` (or re-dispatching the workflow) and run it only with the user's go-ahead.

### C. Prove a commit landed

1. `<CI> landed <SHA> --branch <deploy-branch> [--workflow <deploy workflow>]`:
   - "NOT LANDED: not on branch" → the push did not reach the deploy branch;
   - "NOT LANDED: newest completed run … concluded failure" → B on that run;
   - "NOT YET … in flight" → A on the in-flight run;
   - "LANDED: run … succeeded" → continue.
2. IF the adapter lists **fail-safe steps** (steps that exit 0 even when they did not do
   their job, e.g. scans that tolerate a download failure) → assert they really ran with
   the adapter's log check.
3. IF the adapter lists a **health endpoint** for the environment and the claim
   matters → check it (`curl -s -o /dev/null -w '%{http_code}' <url>`), and if a version
   endpoint exists, compare the reported version/commit.
4. Report (see Reporting rules).

### D. Branch / environment status

`<CI> find --branch <branch> --limit 5` → the newest completed run's conclusion is the
status; an in-flight run is reported as such. Results gathered from an environment
**while a deploy is rolling** are invalid (restarts cause transient errors) — wait for
the deploy to conclude before judging tests or error rates against it.

---

## Reporting rules

- Every claim carries **run id + commit** (short sha) so it can be checked.
- Name the **gate** that failed (unit / e2e / migrations / scan / deploy), not "CI failed".
- Say **infrastructure** when it is infrastructure, with the evidence.
- If your own change broke it, say so plainly.
- Never say "live" / "deployed" from a push, a merge or a green tick alone — only after
  C says LANDED (and health, when it matters).

## Rules & guardrails

- Read-only by default: `find`, `watch`, `why`, `landed` change nothing.
- Re-runs, cancellations and dispatches affect shared CI — only with the user's go-ahead.
- Logs can contain secrets or customer data that slipped through masking: quote only
  the lines needed, never paste whole logs, never copy secrets into the conversation.
- Never "fix" a failing gate by disabling it, skipping it, or adding an allowlist entry
  without the user's explicit decision.

---

## Adapting this skill to your project

Adapter: `<project>/.claude/adapters/marpiech-observe-ci.md`
(template: `templates/adapter.template.md`; generic traps: `references/traps.md`).

| setting | default | how to discover |
|---------|---------|-----------------|
| pipeline map | built from `.github/workflows/*` | `on:` triggers, `needs:` chains, reusable workflow calls |
| gates | jobs that block a deploy | jobs the deploy job `needs:` |
| deploy branches → environments | none | workflow triggers and their deploy targets |
| fail-safe steps + log assertion | none | steps with `continue-on-error`, `|| true`, trailing `exit 0` |
| health endpoints | none | public health/version URLs per environment |
| runner notes | none | self-hosted runner location of diagnostic logs, ports it binds |
| status page | provider's public status page | — |

Example for a fictional project:

```markdown
# marpiech-observe-ci — project adapter (acme-shop)

## Pipeline
| push to | workflow | gates | deploys to |
|---------|----------|-------|------------|
| main | deploy-staging.yml | lint, unit, e2e, migrations, image-scan | staging |
| release | deploy-prod.yml | same + manual approval | production |
| any PR | ci.yml | lint, unit | — |

## Fail-safe steps
- image-scan tolerates scanner-DB download failures; assert with
  `gh run view --job <id> --log | grep -c "scan complete:"` = number of images

## Health
- staging: https://staging.example.com/healthz (version at /version)

## Runner notes
- self-hosted runner; diagnostic logs in the runner's _diag directory; it binds 8080 —
  do not leave local services on 8080 while a deploy can run

## Learned in this project
- 2026-03-01 — the sca job is skipped on deploys by design (it runs on main pushes only)
```

---

## CLAUDE.md snippet

```markdown
## CI / deploys (skill: marpiech-observe-ci)
- After every push that should deploy: `/marpiech-observe-ci` watches the run in the
  background; never report "live" before it says LANDED (run id + commit).
- CI failed? `/marpiech-observe-ci why <run>` — name the gate; infrastructure failures
  (no steps ran, network/registry steps) are not code bugs.
```

---

## Self-update log

Generic learnings, newest first. Project-specific learnings go to the project's adapter.

- 2026-11-03 — initial generic version, distilled from a production team's CI skill and
  its trap list (see `references/traps.md`). The helper prefers the CI's own
  `##[error]` annotations over keyword matches — package names like `libfoo-error0`
  make naive "error" greps noisy.
