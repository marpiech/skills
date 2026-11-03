---
name: marpiech-tests
description: Write tests that prove a change works and would catch it breaking — for a change already made, tests-first before a change (TDD), a regression test that reproduces a bug, or a diagnosis of a flaky test. Discovers the repository's own test setup (frameworks, layout, fixtures and factories, markers, default deselections, run commands, CI invocations), maps changed files to existing tests, picks the cheapest test type that really exercises the change (unit, unit against a real dependency, integration, API/CLI end-to-end, UI end-to-end, performance), follows the patterns already in the repo, runs the tests, and runs the revert check — the same tests against the code without the change, in a throwaway worktree, must fail for the right reason. Reports passed / failed / skipped honestly (a test skipped for missing credentials is not a pass). Use when the user says "/marpiech-tests", "write tests", "add tests for", "cover this with tests", "test this change", "make sure this works", "tests first", "write a failing test", "reproduce this bug in a test", "this test is flaky", or when another workflow (marpiech-myplan, marpiech-resolve) reaches its test step.
---

# marpiech-tests — tests that would catch the change

## Purpose

A test suite earns its keep only when its tests fail on broken code. Tests written after
the fact often pass whatever the code does: they assert on mocks, re-state the
implementation, skip themselves when an environment variable is missing, or are
deselected by default. This skill writes tests from the repository's own patterns, at
the cheapest level that really exercises the change, and then **proves** them: they pass
on the change and fail without it, for the right reason. Outcome: a small set of tests
that would have caught the bug or the regression, a truthful run summary, and no new
flakiness.

`<SKILL_DIR>` = the directory holding this SKILL.md; `<T>` =
`python3 <SKILL_DIR>/scripts/tests.py` (stdlib + git; `discover` and `map` are read-only).

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

1. Look for `.claude/adapters/marpiech-tests.md` in the repository root.
2. IF present → read: test types and where each lives, run commands per type (unit, a
   single file, full suite, end-to-end per environment), fixtures/factories to reuse,
   markers (e.g. `mutating`, `slow`) and which environments each may run against,
   services an end-to-end run needs, how credentials are injected, known flaky tests,
   and project learnings.
3. ELSE → `<T> discover` and read its output: frameworks and config, test directories,
   shared fixtures/factories, markers, `addopts` that deselect tests by default, run
   scripts, and the exact commands CI runs. CI's command is the most reliable "how to
   run". Offer at the end to save the result as the adapter (`templates/adapter.template.md`).
4. IF /marpiech-memory is installed → READ for the area: test traps are classic
   memory entries.

---

## Algorithm — pick the mode

```
change already made, "write/add tests", "make sure this works"   → A. COVER
before implementing, "tests first", myplan 11b / resolve plan     → B. TESTS FIRST
"bug X happens", ticket describes a defect                        → C. REGRESSION
"this test is flaky / fails sometimes"                            → D. FLAKY
```

All modes end with **R. Run and report**.

### A. Cover a change

1. **Identify the change**, in order: files or a feature the user named; uncommitted work
   (`git diff`, `git diff --cached`); the branch (`git diff <base>...HEAD`). Note what
   layer changed (route/handler, service/business logic, data access, model, UI,
   CLI, configuration) and whether it is a feature, a fix or a refactor.
2. **Map to existing tests:** `<T> map [--base <base>]` → for each changed source file
   the test files that probably cover it, or NO-TEST. Read the covering tests: extend an
   existing file before creating a new one.
3. **Choose the test type** — the cheapest one that exercises the real behaviour:

   | the change is in | write | why |
   |------------------|-------|-----|
   | pure logic (rules, transforms, parsing, calculations) | unit test | fast, precise |
   | data access whose behaviour depends on the database (queries, JSON/array columns, constraints) | unit/integration test against a real database (container or test DB) | a mocked session proves nothing about SQL |
   | an HTTP endpoint's contract (status, shape, permissions) | API end-to-end test, or an in-process app client | exercises routing, auth and serialisation |
   | a CLI command | CLI end-to-end test (subprocess or the framework's runner) | flags, exit codes, output |
   | a user-visible UI flow | UI end-to-end test (Playwright, Cypress, …), one happy path + the key failure | slow: keep few |
   | performance | a threshold test on the hot path, generous margin | catches order-of-magnitude regressions |
   | a refactor with no behaviour change | usually none — existing tests must still pass; add one only where coverage is missing |

   IF in doubt → unit first; add one end-to-end test only when the risk is in the wiring
   (routing, auth, serialisation, UI), which unit tests cannot see.
4. **Write the tests following the repo's patterns** — open 2–3 neighbouring tests and copy
   their structure, fixtures, factories, naming and markers. `references/patterns.md`
   has generic shapes per type when the repo has none.
   - Names describe the scenario: `test_<what>_<condition>_<expected>`.
   - Arrange / act / assert; one behaviour per test; assert on outcomes, not on calls,
     unless the call *is* the behaviour (e.g. "sends exactly one e-mail").
   - Cover the edge the change introduced (empty, boundary, permission denied, error
     path), not only the happy path.
   - Mock only at the boundary (network, clock, external services); never mock the unit
     under test.
   - Tests that create or change data carry the project's `mutating` marker (or equivalent);
     slow ones carry `slow`.
   - Credentials for end-to-end tests are injected (IF /marpiech-secrets is installed →
     `secrets.py run --env <test env> -- <test command>`), never written into tests or files.
5. **Prove them** (the revert check):
   `<T> prove-fails --cmd '<run command> {tests}' [--base <base>] <test files> [--support <new helper>]`
   - It first runs the tests on the current tree — they must pass (else SETUP: fix first);
   - then runs the same tests against `<base>` (default `HEAD` = without uncommitted
     changes; use the merge-base or the parent commit when the change is committed) in a
     throwaway worktree — they must **fail**;
   - GOOD → read the output and confirm an assertion failed, not an import or fixture
     error; BAD (passes on base) → the test does not detect the change: strengthen the
     assertions and repeat; SETUP? → read: "the new function does not exist" is
     detection, "dependency missing in the worktree" is not — then run the base check by
     hand if needed.
   - Skip the revert check only for pure refactors (nothing to detect) and say so.
6. → R.

### B. Tests first (before implementing)

1. From the plan or ticket, list the observable behaviours that will be new or different.
2. Write tests for them, outer layer first when user-facing: UI end-to-end (if any) →
   API/CLI → unit. Follow A.3–A.4 for type and patterns.
3. Run them. They **must fail, and fail because the behaviour is missing** (not found,
   missing element, assertion on the new value) — not because of a syntax error, a broken
   fixture or a missing service. Save the failure output; it is the "before" evidence.
4. IF a new test passes before the implementation → the test is wrong; fix it first.
5. After the implementation: run exactly these tests UNTIL they pass (fix the
   implementation; fix a test only if its assertion was wrong — and say so). → R.

### C. Regression test for a bug

1. Reproduce the bug by hand first (command, request or UI steps) and note the exact
   wrong output.
2. Write the smallest test that shows the wrong output at the lowest layer where it
   appears. Run it: it must fail **with the bug's symptom**.
3. Fix the code (or hand over to the fixing workflow). The test passes.
4. Revert check (A.5) against the commit before the fix.
5. Name the test after the behaviour, not the ticket; reference the ticket in a comment
   only if the project does that.

### D. Flaky test

1. Measure: run the single test N times (`pytest -x --count` with a repeat plugin, a
   shell loop, `--repeat-each` in Playwright) and in random order if the framework
   supports it. Record the failure rate and the failure messages.
2. Classify the cause (first match wins) using `references/flakiness.md`: shared state
   between tests, order dependence, time and time zones, unawaited async work, fixed
   sleeps instead of waits, real network, resource or port collisions with other runs,
   test data left over from earlier runs, randomness without a seed.
3. Fix the cause — never add retries, longer sleeps or a skip as the fix. IF a quarantine
   is unavoidable → mark it with the project's flaky/quarantine marker, a reason and an
   owner, and tell the user.
4. Prove: N consecutive passes, including in random order.

### R. Run and report

1. Run the new and changed tests, then the scope the adapter's gate requires (the
   affected package, or the full suite). Use the command CI uses; note default
   deselections (`addopts -m "not slow"`) and run deselected tests explicitly when they
   are the ones you wrote.
2. Report **counts** — passed / failed / skipped / deselected — and for every skip, why.
   A test skipped because credentials or a service are missing has **not** passed; say
   which tests did not run and what they need.
3. Pre-existing failures: prove they fail on the base too (a worktree of the base, or
   `prove-fails` logic in reverse), report them, do not fold their fixes into this change.
4. Show the user: which tests were added, what each proves, the revert-check result,
   and the run summary.

---

## Rules & guardrails

- Never weaken, delete or skip an existing test to make the suite pass; if an existing
  test is wrong, say so and get the user's agreement first.
- Never point tests that create or change data at a shared or production environment;
  only tests marked safe (e.g. not `mutating`) may run against shared environments, and
  only when the adapter allows it.
- Never put credentials, real personal data or production identifiers in test code or
  fixtures; use generated, obviously fictional data.
- Unit tests make no real network calls.
- Never run untrusted code (e.g. a fork's tests) outside a sandbox or without approval.
- The revert check uses a temporary worktree; never stash, reset or check out over the
  user's working tree.

---

## Adapting this skill to your project

Adapter: `<project>/.claude/adapters/marpiech-tests.md` (template:
`templates/adapter.template.md`; generic patterns: `references/patterns.md`; flakiness:
`references/flakiness.md`).

| setting | default | how to discover |
|---------|---------|-----------------|
| test types → locations | from `discover` | test directories, file naming |
| run commands | what CI runs | `discover` "Run commands" (CI lines first) |
| single-file command | framework default (`pytest <file>`, `npx vitest run <file>`) | package scripts |
| full-suite / gate command | CLAUDE.md or CI | — |
| fixtures / factories | from `discover` | `conftest.py`, `factories`, `helpers` |
| markers and allowed environments | from config | `markers =`, `addopts` |
| end-to-end prerequisites | none | services to start, test users, seed scripts |
| credentials injection | none | secrets tool; IF /marpiech-secrets is installed, its `run` |
| known flaky tests | none | quarantine markers, CI re-run history |

Example for a fictional project:

```markdown
# marpiech-tests — project adapter (acme-shop)

## Types
| type | where | run |
|------|-------|-----|
| unit (mocked) | services/*/tests/ | `cd services/<svc> && pytest tests/<file> -q` |
| unit (real DB) | services/orders/tests/db/ | needs `docker compose up -d db`; factories in tests/factories.py |
| API e2e | e2e/api/ | `secrets.py run --env dev -- pytest e2e/api/<file> -q` |
| UI e2e | e2e/ui/ (Playwright) | `npx playwright test <file>` (stack must be up) |

## Markers
- mutating — creates data; dev only. slow — deselected by default (addopts); run with -m slow.
- staging may run `-m "not mutating"` only.

## Gate
- before push: `make test` (all unit suites) + the e2e files you touched

## Learned in this project
- 2026-03-01 — the test DB listens on 5433, not 5432; CI's runner binds 5432
```

---

## CLAUDE.md snippet

```markdown
## Tests (skill: marpiech-tests)
- Every behaviour change ships with tests that FAIL without it: `/marpiech-tests`
  (cover / tests-first / regression) runs the revert check in a throwaway worktree.
- Report passed / failed / skipped; a test skipped for missing credentials did not pass.
- Never weaken or skip an existing test to get green — fix the cause or ask.
```

---

## Self-update log

Generic learnings, newest first. Project-specific learnings go to the project's adapter.

- 2026-11-03 — initial generic version, distilled from a production monorepo's
  test-creator skill and its end-to-end testing notes. The revert check first runs the
  tests on the current tree: without that, a missing test runner in the environment
  ("No module named pytest") showed up as a convincing "fails on base". Discovery reads
  `git ls-files` instead of walking the disk — a repository with large untracked data
  directories made a plain walk take minutes. A pytest `addopts` with `-m 'not slow'`
  silently deselects tests; `discover` flags it.
