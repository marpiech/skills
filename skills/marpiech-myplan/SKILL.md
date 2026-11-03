---
name: marpiech-myplan
description: Heavy-planning and TDD delivery workflow for a substantial change that has no ticket yet. Enters plan mode, researches the code and the web, runs three rounds of a/b/c/d alignment questions (scope, UX/constraints, edges/risks), a solutions round with exactly three approaches, writes a preliminary plan and gets it independently reviewed, asks a final clarification round, and — after the user approves — creates the ticket, writes failing tests first, implements, simplifies and audits the change, proves the failing tests now pass, runs the full suite, delivers, and closes the ticket with a resolution comment. Use when the user says "/marpiech-myplan", "myplan", "plan this thoroughly", "deep plan X", "align with me before coding", or describes a non-trivial feature/change with no ticket. Prefer marpiech-resolve when a ticket already exists, marpiech-ideate while the design itself is still open, and neither for one-line fixes.
---

# marpiech-myplan — deep planning, then test-first delivery

## Purpose

Substantial changes go wrong when the first plausible plan is implemented: requirements
were assumed, edge cases surface in review, and the ticket describes something other
than what shipped. This skill front-loads alignment — each question round builds on the
previous answers and on fresh research — and only then commits to a plan that an
independent reviewer has attacked. Delivery is test-first: tests that fail for the
right reason exist before the code that makes them pass. Outcome: an approved plan, a
ticket whose description *is* that plan, failing-then-passing tests, a clean
implementation, a delivered change and a closed ticket.

`<SKILL_DIR>` = the directory holding this SKILL.md. `$ARGUMENTS` = the user's
free-form description of the change; IF empty → ask what to plan.

| situation | use |
|-----------|-----|
| a ticket already exists | `/marpiech-resolve <TICKET>` |
| idea with no ticket, design settled enough to plan, wants rigorous alignment | **`/marpiech-myplan`** |
| new product area, design still open, prototype first | `/marpiech-ideate` |
| trivial fix | neither — just do it |

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

1. Look for `.claude/adapters/marpiech-myplan.md` in the repository root.
2. IF present → read it: plan directory, ticket system and where new tickets go, branch
   policy, test locations and commands, run/rebuild command, full-suite command, review
   tool, delivery target, time-logging policy, project rules to enforce.
3. ELSE → defaults: plans in the todos directory named by the marpiech-init adapter
   (else `claude-todos/`); ticket creation asks the user; branch policy and test
   commands come from CLAUDE.md; review by a fresh subagent; no time logging. Offer to
   create the adapter at the end from `<SKILL_DIR>/templates/adapter.template.md`.
4. IF `/marpiech-memory` is installed → run it in READ mode with the change's nouns.

---

## Overview

```
PLAN MODE (no edits, no side effects)
  1. ENTER PLAN MODE      restate the request in one sentence
  2. RESEARCH 1           code (1–3 read-only subagents) ∥ web if needed
  3. ALIGN R1             3 questions × a/b/c/d — scope / intent
  4. ALIGN R2             3 questions × a/b/c/d — UX / constraints
  5. RESEARCH 2           targeted, informed by R1+R2
  6. ALIGN R3             3 questions × a/b/c/d — edges / risks
  7. SOLUTIONS            exactly 3 approaches A/B/C; user picks one
  8. PRELIMINARY PLAN     plan file + independent review; ACCEPT/REJECT/DEFER
  9. ALIGN R4             1–3 questions — residual unknowns and deferred findings
 10. EXIT PLAN MODE       user approves the final plan
ROLLOUT
 11a ticket   11b failing tests   11c implement   11d simplify   11e audit
 11f prove the failing tests pass   11g full suite   11h deliver + close   11i report
```

Track each phase as a task: `in_progress` on entry, `completed` on exit.

---

## Phase 1 — Enter plan mode

Enter plan mode immediately. Phases 1–10 may read, search and browse, but must not
edit files, write files, or run commands with side effects. State the request back in
one sentence and let the user correct it.

## Phase 2 — Research, round 1

Spawn 1–3 read-only exploration subagents in parallel, each with a narrow brief and a
word cap:
- **current implementation** of the affected area;
- **related patterns** — how similar features were built elsewhere in the repo (reuse
  beats reinvention);
- **data model and entry points** — models, schemas, routes/handlers, CLI commands that
  will be touched;
- **dependencies** — cross-module/service calls, shared components and libraries.

IF the task involves an external API, library or standard you are unsure about → web
search in parallel. Summarise; never paste raw dumps into the conversation.

## Phases 3, 4, 6 — Alignment rounds R1–R3

Each round is **one question call with exactly 3 questions, each with 4 options
(a/b/c/d), single-select**, grounded in what research found. Recommendation first,
marked "(Recommended)"; each option's description states its consequence.

| round | focus | typical questions |
|-------|-------|-------------------|
| R1 (Phase 3) | **what** — scope / intent | primary user goal; in vs out of scope; where it lives (module / service / page) |
| R2 (Phase 4) | **how it behaves** — UX / constraints | interaction model; who may use it (roles); persistence / state |
| R3 (Phase 6) | **what breaks late** — edges / risks | empty / denied / partial-failure states; migration or backfill of existing data; dependency-down behaviour |

Rules: never re-ask what a previous round settled; one question per dimension (do not
fold scope + UX + access into one); no abstract "pick an approach" questions before
Phase 7. IF the user answers with "Other" → treat the free text as authoritative and
echo your understanding at the start of the next round.

## Phase 5 — Research, round 2

Now that the shape is known: read the specific files that will change; check model /
migration conventions; find existing components that match the chosen UX; list the
CLAUDE.md rules that apply to this change (they become checks in 11c and 11e).

## Phase 7 — Solutions round

One question with **exactly 3 approaches**, single-select:
- option label = what the approach does (short name / core idea);
- option description = its core trade-off (complexity · performance · blast radius ·
  reuse);
- optional preview with a code sketch or ASCII diagram.

Recommended approach first. IF only two real approaches exist → make C an explicit
"minimal" or hybrid option, never a throwaway. **Do not write the plan until the user
picks.**

## Phase 8 — Preliminary plan + independent review

1. Write `<PLAN_DIR>/myplan-<slug>.md` from `templates/plan.template.md`: context;
   acceptance criteria (testable bullets); TDD strategy (which tests, at which level,
   asserting what); implementation outline (files in order, one line each); migration
   plan if data changes; risks / open questions; verification end to end.
   (Plan mode may restrict writes to its own plan file — IF so, keep the plan in the
   plan-mode file and copy it to `<PLAN_DIR>` as the first rollout action.)
2. Review it independently:
   - IF the adapter names a review tool (e.g. a second-model plan-review plugin) → run
     it on the plan file and follow its response protocol;
   - ELSE → spawn a fresh general-purpose subagent given **only the plan file** and the
     instruction "find the most serious problems: wrong assumptions, missing cases,
     untestable criteria, simpler alternatives; for each: evidence, impact, fix".
3. For each finding record **ACCEPT** (with the concrete plan change), **REJECT** (with
   the reason) or **DEFER** (needs the user — goes to R4). Never skip the review because
   the plan "looks fine".

## Phase 9 — Alignment round 4

1–3 questions, only about: deferred review findings, open questions in the plan,
ambiguities that would block implementation. Do not pad.

## Phase 10 — Exit plan mode

Present the final plan for approval. WAIT. IF the user requests changes → apply them
and present again. No rollout without explicit approval.

---

## Phase 11 — Rollout

### 11a. Create the ticket

1. IF `/marpiech-tickets` is installed → use it; ELSE use the ticket system named in the
   adapter; ELSE ask the user whether and where to create one (skip if they say no).
2. Where it goes: apply the adapter's `ticket-parent-rule` (e.g. "latest active epic
   whose name matches `Release X.Y` with the highest version"). IF the rule matches
   nothing or several candidates tie → ask; never invent a parent.
3. Content: summary = concise title; description = the approved plan; labels from the
   adapter (e.g. `myplan`); assignee per adapter.
4. Record the ticket key; use it in the branch name (if the branch policy creates
   branches) and in every commit subject.

### 11b. Write failing tests first

1. Follow the branch policy (adapter / CLAUDE.md). IF the policy is trunk-only → stay on
   the trunk; never create a branch the policy forbids.
2. Write tests in this order, following existing patterns in the repo:
   end-to-end UI test (if user-facing) → API/CLI test (if backend-facing) → unit tests
   next to the code being changed.
3. Run them. They **must fail**, and fail *because the feature is missing* (a
   not-found, a missing element, an assertion on new behaviour) — not because of an
   import error or broken fixture. Save the failure output.
4. IF a new test passes before implementation → the test is wrong; fix the test first.

### 11c. Implement

1. Execute the implementation outline in order.
2. Apply every CLAUDE.md rule listed in Phase 5 as you go.
3. After each logical step: rebuild/restart what the adapter's `run-command` names and
   check its logs for startup errors before moving on.

### 11d. Simplify the fresh code

Run `/simplify` (built-in) on the change. Apply unambiguous improvements; skip any that
would undo a deliberate choice from the plan; raise judgment calls that change
behaviour with the user.

### 11e. Audit the wider impact

IF `/marpiech-audit` is installed → run it scoped to the touched files; ELSE run
`/code-review` on the diff. Fix findings caused by this change. Note pre-existing
issues in the final report; do not fold their fixes into this change.

### 11f. Prove the failing tests now pass

Run **exactly** the tests from 11b. REPEAT diagnose → fix (usually the implementation;
the test only if its assertion is wrong) → re-run UNTIL all pass. Do not continue
while any is red.

### 11g. Full suite

Run the adapter's `full-suite-command` (or the commands in CLAUDE.md). Fix failures
caused by this change. Pre-existing unrelated failures: record them with evidence that
they also fail without the change; they do not block.

### 11h. Deliver and close

1. Commit **only this change's files** with explicit `git add <paths>`; commit subject
   starts with the ticket key; body = what + why.
2. Push / open a PR **only as the delivery policy says and when the user asked for
   delivery**. Never force-push.
3. IF the push should deploy → IF `/marpiech-observe-ci` is installed → watch the run to
   completion; ELSE watch it with the CI's CLI. A push is not a deploy; do not close the
   ticket on an unshipped change. Cite the run and commit in the ticket comment.
4. Close / transition the ticket per the adapter: resolution comment (what shipped, the
   commit, the run), and time logging only if the adapter's policy asks for it.

### 11i. Report

One short summary: ticket key, commit, what shipped, ticket state, anything deferred.
IF `/marpiech-memory` is installed → run it in UPDATE mode with the decisions, rejected
approaches (from Phase 7) and surprises of this change.

---

## Rules & guardrails

- Plan mode is non-negotiable for Phases 1–10; wanting to edit a file before Phase 11
  means alignment is being skipped.
- Every alignment question has 4 concrete, mutually exclusive options grounded in
  research; rounds build on each other and are never merged into one big batch.
- The ticket is created during rollout, not before — its description is the approved
  plan.
- Tests fail before implementation, for the right reason.
- Commit only files from this change; never force-push; push/deploy only when asked.
- Never print or paste secrets while creating tickets or running tests; inject them as
  environment variables via the project's secrets tool.

---

## Adapting this skill to your project

Adapter: `<project>/.claude/adapters/marpiech-myplan.md` (template:
`templates/adapter.template.md`).

| setting | default | how to discover |
|---------|---------|-----------------|
| `plan-dir` | marpiech-init todos dir, else `claude-todos/` | existing plans/todo directory |
| `ticket-system` | ask | tracker named in CLAUDE.md; key prefix in `git log` |
| `ticket-parent-rule` | ask | how the team groups work (epics per release, milestones, projects) |
| `ticket-labels` / `assignee` | none / current user | team convention |
| `branch-policy` | from CLAUDE.md | trunk-only vs branch-per-ticket; naming pattern |
| `tests` | from CLAUDE.md | per level: location, pattern file to copy, command |
| `run-command` | none | how to rebuild/restart the affected component locally |
| `full-suite-command` | from CLAUDE.md | the command CI runs |
| `review-tool` | fresh subagent | second-model plan-review plugin command, if any |
| `delivery` | ask | where a finished change goes (PR to main, push to a deploy branch) |
| `time-logging` | none | e.g. "log 80 % of the AI-hours estimate" if the team logs time |

Example for a fictional project:

```markdown
# marpiech-myplan — project adapter (acme-shop)

## Settings
- plan-dir: plans/
- ticket-system: Jira, project ACME (via /marpiech-tickets)
- ticket-parent-rule: latest open epic named "Shop X.Y" with the highest X.Y
- ticket-labels: myplan
- branch-policy: branch-per-ticket, `ACME-<n>-<slug>` from main
- tests:
  - ui-e2e: e2e/tests/<area>.spec.ts (copy e2e/tests/cart.spec.ts) — `npm run e2e -- <file>`
  - api: tests/api/test_<area>.py — `pytest tests/api/test_<area>.py`
  - unit: next to the module — `pytest <path>`
- run-command: docker compose up --build -d <service> && docker compose logs --tail 50 <service>
- full-suite-command: make test-all
- review-tool: fresh subagent
- delivery: PR to main; deploy happens on merge (watch with /marpiech-observe-ci)
- time-logging: none

## Project rules to check in 11c / 11e
- prices are integers in cents; never floats
- every new endpoint has an authorization test
```

---

## CLAUDE.md snippet

```markdown
## Planning (skill: marpiech-myplan)
- Substantial change with no ticket → `/marpiech-myplan <description>`: plan mode,
  3 alignment rounds, 3 approaches, reviewed plan, then ticket + failing tests first.
- Existing ticket → /marpiech-resolve. Open design → /marpiech-ideate first.
```

---

## Self-update log

Generic learnings, newest first. Project-specific learnings go to the project's adapter.

- 2026-11-03 — initial generic version, distilled from a production workflow. Kept: the
  round structure (scope → UX → edges → approaches), "ticket during rollout so its
  description is the approved plan", and "prove the failing tests now pass before the
  full suite". Generalised: the tracker, parent-epic rule, test layout, delivery target
  and time logging moved to the adapter; branch creation now follows the project's
  branch policy instead of always branching.
