---
name: marpiech-debug
description: Systematic root-cause debugging — never a fix before the cause is proven. Frames the symptom (expected vs actual, since when, where), checks project memory and known failures first, reproduces the bug (or, in production, observes it read-only), shrinks it by bisecting commits, inputs, configuration and layers, writes down competing hypotheses each with a prediction and the cheapest test that would refute it, proves the one root cause that explains every symptom, then fixes it at the single place it originates with a regression test that fails first, verifies with the original reproduction, hunts for the same defect elsewhere, and records the lesson. Stops after three failed fixes to question the design instead of trying a fourth. Covers application bugs, regressions, performance regressions, intermittent failures, data-pipeline and workflow-engine failures (WDL/Cromwell, Nextflow, Snakemake, schedulers), container and service start failures, and "works locally, fails in CI / staging". Use when the user says "/marpiech-debug", "debug this", "why does X fail", "find the root cause", "it broke after…", "this used to work", "it's slow since…", "the pipeline/analysis/job failed", "500 error", "works on my machine", or pastes a stack trace or a failing log.
---

# marpiech-debug — prove the cause, then fix it once

## Purpose

Most wasted debugging time comes from fixing a guess: a plausible change is made, the
symptom moves, a second guess follows, and after an hour the code has three patches and
the original cause is still there. This skill replaces guessing with a short, strict
procedure: reproduce, shrink, state hypotheses that could be wrong, prove one, fix it at
its source with a test that failed first, and record the lesson so nobody debugs it
again. The outcome is a proven root cause, one fix in the right place, a regression test,
and a note in memory — or, when the cause cannot be proven in the time box, an honest
report of what is known, what was ruled out, and what to try next.

`<SKILL_DIR>` = the directory holding this SKILL.md. The working notes of a session live
in a debug log (`templates/debug-log.template.md`) kept in the scratch area, never in the
repository unless the user asks.

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

1. Look for `.claude/adapters/marpiech-debug.md` in the repository root.
2. IF present → read it: how to run and reach each environment (local, CI, staging,
   production — and which are read-only), where logs, traces and metrics live, the
   known-failures table (symptom → cause → fix), pipeline/workflow-engine mechanics,
   rebuild vs hot-reload rules, the commands that inject credentials, and project
   learnings. Adapter settings override the defaults in this file.
3. ELSE → use the defaults: local reproduction only, logs from the process output and
   the project's log files, production treated as read-only. Do not create the adapter
   now; offer it at the end (Step 12) if this session learned anything project-specific.

---

## Algorithm

### Step 2 — Frame the symptom (write it down before touching anything)

Fill the top of the debug log:

| field | example |
|-------|---------|
| **actual** — what happens, in observable terms | "POST /orders returns 500; log shows `KeyError: 'currency'`" |
| **expected** — what should happen | "201 with the order id" |
| **since when** — first bad occurrence, last known good | "since Tuesday's deploy; Monday's build was fine" |
| **where** — environment, input, user, data, platform | "staging only; only orders with a voucher" |
| **how often** — always / sometimes (rate) / once | "every voucher order" |
| **evidence** — exact error text, ids, timestamps, screenshots | the first error line, not the last |

Rules for framing:
- Quote the **first** error, not the cascade it caused. Scroll up in the log until the
  first line that is not a consequence of an earlier one.
- Turn adjectives into facts: "slow" → "p95 went from 120 ms to 2.1 s"; "broken" → the
  status code, the wrong value, the missing element.
- IF the report is ambiguous (which page? which input? which environment?) → ask the user
  ONE question with options, then continue. Do not debug a guess of the symptom.

Choose the **mode** from the frame; it changes Steps 4–5 (details in
`references/techniques.md`):

```
always reproducible, local                → BUG
"used to work" / "since <deploy|commit>"  → REGRESSION   (bisect first)
slower than before / timeouts             → PERFORMANCE  (measure before and after)
sometimes / only in CI / only under load  → INTERMITTENT (rate first; IF it is a test → /marpiech-tests flaky mode)
a job, pipeline or workflow run failed    → PIPELINE     (references/pipelines.md)
a service will not start / 500 / 502      → SERVICE      (logs and config first)
only in production                        → PRODUCTION   (observe read-only; never experiment there)
looks wrong in the browser                → IF /marpiech-uidesign is installed → its DEBUG mode; ELSE BUG
```

### Step 3 — Check what is already known (minutes, before any experiment)

1. IF /marpiech-memory is installed → READ mode with the symptom's nouns and the first
   error line's distinctive token. Gotchas and rejected fixes are exactly what it holds.
2. Read the adapter's **known-failures** table. A match is a hypothesis to *test*, not a
   conclusion — confirm it in Step 7 like any other.
3. Look at what changed: `git log --oneline --since=<last good>` on the paths involved,
   recent dependency bumps (lock-file diff), configuration and infrastructure changes,
   data changes (a new kind of input, a new customer, a migration).
4. IF a ticket exists and /marpiech-tickets is installed → read its comments and
   attachments (screenshots often show what the text omits).

### Step 4 — Reproduce (or observe)

```
REPEAT
  try the cheapest faithful reproduction:
    unit/function call  <  local script  <  local service  <  CI job  <  staging
UNTIL the symptom appears on demand, OR the time box for reproduction (default 30 min) ends
```

- A reproduction is a **command** someone else can run, with its exact input, that shows
  the actual result. Save it in the debug log.
- PRODUCTION mode: never reproduce by experimenting on production. Observe: logs, traces,
  metrics, the stored data the request touched (read-only queries), the exact build that
  is deployed. Reproduce elsewhere with the same data shape (anonymised), never the data.
- INTERMITTENT mode: measure the rate first (run N times; IF 0/N, raise N or add the
  suspected stressor — parallelism, slow network, a full disk, a clock change). A fix for
  an intermittent bug is only proven when the rate drops from a measured value to 0 over a
  run count that would have shown it.
- IF it cannot be reproduced in the time box → do NOT fix by guessing. Add the missing
  observation (a log line with the decisive values, a metric, a trace span) behind the
  project's normal logging, ship it the normal way if the user agrees, and report.

### Step 5 — Shrink it (find *where*, before *why*)

Narrow the search space by halves, never by intuition alone. Pick the axis that fits:

| axis | method |
|------|--------|
| **commits** (REGRESSION) | `git bisect start <bad> <good>`; `git bisect run <repro command>` when the repro is a script whose exit code says good/bad. Mark untestable commits `git bisect skip`. |
| **input** | halve the input (rows, file, request body, list of samples) until the smallest input that still fails; keep each step's result |
| **configuration** | diff working vs failing environment (env var NAMES and fingerprints, never values — IF /marpiech-secrets is installed use its compare); flip one difference at a time |
| **layers** | check the value at each boundary (client → API → service → storage → back) and find the first boundary where it is already wrong |
| **dependencies** | lock-file diff between good and bad; pin one changed package back at a time |
| **time** | for PERFORMANCE: profile both versions on the same input; compare the top frames, not totals |

Gate: Step 5 ends when you can name **the smallest unit** (one commit, one input record,
one config key, one function, one boundary) where good turns into bad. Write it down.

### Step 6 — State competing hypotheses (in writing, at least two)

For the narrowed location, write each hypothesis as a row in the debug log:

| # | hypothesis | if true, we will see… | cheapest test that could refute it | result |
|---|------------|-----------------------|------------------------------------|--------|
| H1 | the voucher path drops `currency` when the cart total is 0 | the dict lacks the key only for total 0 | call `build_order` with total 0 and 1 | |
| H2 | the new serializer renames the field | the key exists as `currency_code` | print the keys at the boundary | |

Rules:
- Always at least **two** hypotheses; the second one keeps you honest about the first.
- A hypothesis must make a **prediction that could be false**. "Something with caching"
  is not a hypothesis; "the cached value is from before the migration, so its `version`
  is 3" is.
- Run the cheapest refutation first. Change **one** thing per experiment. Record every
  result, including "refuted" — refuted hypotheses are findings.

### Step 7 — Prove the root cause (the gate before any fix)

The cause is proven only when ALL of these hold:
1. **It explains every symptom** in the frame (including "only on staging", "only
   vouchers", "since Tuesday"). A cause that explains most of them is a contributing
   factor; keep looking for the rest.
2. **You can switch it**: undoing or forcing the cause makes the symptom disappear or
   appear on demand (revert one line, feed the bad input, set the config key).
3. **You know why it happens**, one level below the surface: not "the value is null" but
   "the value is null because the importer treats an empty cell as missing since commit
   abc123, which changed `read_csv`'s default".

IF the gate fails → back to Step 6 with what you learned. IF two cycles of Steps 6–7
produce nothing → widen Step 5 (a different axis) before inventing more hypotheses.

### Step 8 — Fix it at the source, test first

1. **Name the one place** the fix belongs: the function, formatter, token, config key or
   contract where the defect originates — not every caller that shows it. IF the defect
   originates outside the codebase (a dependency, an upstream service, infrastructure) →
   fix or pin there, or apply a clearly labelled workaround and record the upstream
   issue.
2. **Regression test first.** IF /marpiech-tests is installed → use it (regression mode):
   a test that reproduces the bug through the narrowest real path, run it, confirm it
   fails for the right reason. ELSE write that test yourself and run it.
3. Make the smallest change that removes the cause. No unrelated refactors, renames or
   formatting in the same change.
4. A **mitigation** (retry, guard, feature flag off) is allowed when the user needs relief
   now — label it "mitigation, root cause still open" in code comment, commit message and
   report, and keep the root-cause work open.

**Three-strikes rule.** IF three fixes in a row did not remove the symptom (or each
moved it somewhere else) → STOP fixing. The model of the system is wrong. Go back to
Step 2 with the user: re-frame, question the design or the assumption everything rests
on, and say plainly that three attempts failed and why.

### Step 9 — Verify

All must pass before the bug is called fixed:
1. The regression test now passes; the original reproduction command (Step 4) now shows
   the expected result.
2. The neighbouring tests (the module's suite; for a shared function, its callers'
   suites) pass.
3. INTERMITTENT: the measured failure rate is 0 over a run count that would have shown
   the old rate. PERFORMANCE: the same measurement as in the frame, on the same input,
   is back within the target.
4. IF the symptom was seen in an environment (CI, staging) → verify there after delivery;
   IF /marpiech-observe-ci is installed → use it to prove the fix landed and deployed.
   Until then the status is "fixed locally, not yet verified in <env>".

### Step 10 — Hunt for the same defect elsewhere (variant analysis)

The pattern that produced this bug usually exists more than once.
1. Describe the defect as a code shape ("dict access on optional serializer field",
   "date parsed without timezone", "query without tenant filter").
2. Grep for that shape across the repository; read each hit.
3. Fix the true variants in the same change when they are small and certain; list the
   rest for the user. IF the shape is mechanical and /marpiech-audit is installed →
   propose it as a new catalogue check so it cannot come back silently.

### Step 11 — Report

```
## Debug — <symptom in one line> — <date>
Mode: <BUG|REGRESSION|…>  ·  Reproduction: `<command>`
Root cause: <one sentence, one level below the surface>  (introduced in <commit/PR/date> if known)
Proof: <how the cause was switched on and off>
Fix: <file:line> — <what changed>  ·  Regression test: <test id> (failed before, passes now)
Verified: <local / CI / env>  ·  Still to verify: <env, or "nothing">
Variants: <fixed N, listed M>
Ruled out: <H2 — why>, <H3 — why>
```

IF the time box ended without a proven cause → the same shape with "Root cause:
NOT PROVEN", the best remaining hypotheses with their next test, and the observation that
would settle it.

### Step 12 — Record the lesson

1. IF /marpiech-memory is installed → UPDATE mode: the cause, the misleading symptom,
   the rejected hypotheses and why (the next person will think of them too).
2. A failure that will recur in this project (an environment quirk, a pipeline failure
   mode) → add a row to the adapter's known-failures table (symptom → cause → fix).
3. A generic lesson about debugging → this skill's Self-update log (Step B of the
   self-update protocol). Never project paths, hosts or ticket keys there.

---

## Rules & guardrails

- **No fix before Step 7.** A change made before the cause is proven is an experiment:
  revert it unless it is a labelled mitigation.
- **One change per experiment**; record every result, including refutations.
- **Production is read-only.** No experiments, restarts, data edits or config flips on
  production unless the user explicitly asks for that specific action. Read-only queries
  only, and only the rows needed.
- **Credentials:** inject them into the command (the project's secrets tool; IF
  /marpiech-secrets is installed use it); never print them, never write them to files in
  `/tmp` or the repository, never paste them into the debug log. Refer to them by
  variable name.
- **Customer data:** never copy production data into tests, fixtures, the debug log or
  memory. Reproduce with synthetic or anonymised data of the same shape.
- Do not disable a check, test, TLS verification or a security control to make the
  symptom go away. If that is the only relief, ask the user and label it a mitigation.
- Keep the user informed: after the frame, after the reproduction, after the proof — one
  line each. Never report "fixed" before Step 9.
- Three-strikes rule (Step 8) is not optional.

---

## Adapting this skill to your project

**1. Placeholders and their defaults**

| setting | default | how to discover the right value |
|---------|---------|----------------------------------|
| environments and access | local only; production read-only | CI config, deploy docs, CLAUDE.md |
| how to run one service / job locally | from README / build file | `Makefile`, `docker-compose*.yml`, `package.json` scripts |
| rebuild vs hot-reload | rebuild everything | compose volumes / dev-server config |
| logs, traces, metrics | process output | logging config, observability docs |
| secrets injection command | none | `.infisical.json`, `.sops.yaml`, `.envrc`, CI env |
| known failures | empty | memory files, incident notes, recurring tickets |
| pipeline / workflow engine | none | `*.wdl`, `main.nf`, `Snakefile`, scheduler configs |
| time boxes | 30 min reproduce, 2 h total | team habit |

**2. Where the adapter lives:** `<project>/.claude/adapters/marpiech-debug.md`,
committed with the project. Template: `templates/adapter.template.md`.

**3. Example adapter for a fictional project**

```markdown
# marpiech-debug — project adapter (acme-shop)

## Environments
- local: `make up` (compose); api hot-reloads, worker needs `make rebuild worker`
- CI: GitHub Actions `test.yml`; staging: read/write for the team; production: READ-ONLY
- logs: `make logs svc=<name>`; traces: the tracing UI linked in docs/observability.md

## Secrets
- `infisical run --env=dev -- <command>` — variables named in .env.example

## Known failures (symptom → cause → fix)
| 502 on every page after a deploy | worker crashed on a missing env var | add it to the env config; restart |
| job "failed" after ~20 s | workflow file passed as a local path, relative imports unresolved | pass the URL |

## Time boxes
- reproduce 30 min · total 2 h, then report

## Learned in this project
- 2026-03-02 — voucher orders with total 0 skip the currency field (fixed in pricing.build_order)
```

---

## CLAUDE.md snippet

```markdown
## Debugging (skill: marpiech-debug)
- Any bug, regression, failed job or "why does X fail": `/marpiech-debug` — frame,
  reproduce, shrink, prove the root cause, THEN fix at the source with a failing test first.
- No fix before the cause is proven; three failed fixes → stop and re-frame with the user.
- Production is read-only while debugging; credentials are injected, never printed.
```

---

## Self-update log

Generic learnings, newest first. Project-specific learnings go to the project's adapter.

- 2026-11-05 — initial generic version. Procedure distilled from widely used systematic-
  debugging practice (reproduce → isolate → hypothesise → prove → fix → verify, the
  three-failed-fixes stop rule) and from a production genomics platform's workflow-engine
  debugging notes: time-to-failure is a strong first signal for pipeline runs (seconds →
  import/config resolution, minutes → input mapping, long → a task's own error), and
  credentials must be injected rather than extracted to temporary files.
