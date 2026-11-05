---
name: marpiech-audit
description: Audit a codebase — or just the current diff — against the project's own rules (CLAUDE.md, architecture conventions) and generic risk categories (security, tenant isolation, authorization, layering, single source of truth, code quality, duplication, naming, UI conventions, oversized files), score each category by Importance × Not-implementing risk ÷ Implementing risk, and report the top five with file:line evidence and a suggested fix. Runs a project-owned check catalogue through a read-only helper, reads every hit before calling it a violation, and in diff mode attributes each finding as NEW (introduced by this change) or PRE-EXISTING so a change is only held to what it caused. The check catalogue updates itself: zero-hit checks are reviewed, false-positive patterns narrowed, and new anti-patterns found by reading become new checks with the decision recorded. Use when the user says "/marpiech-audit", "audit the code", "audit this service", "audit my changes", "what are the biggest problems in this codebase?", "check for violations of CLAUDE.md", "security / isolation / RBAC review", or when another workflow (marpiech-myplan, marpiech-resolve) reaches its audit step.
---

# marpiech-audit — the five problems that matter most, with evidence

## Purpose

Codebases drift from their own rules: a route starts committing transactions, a query
loses its tenant filter, a permission is enforced only by hiding a button. Linters catch
syntax, not these. A useful audit is not a long list — it is a short, ranked list of real
violations with file:line evidence, scored by how much they matter against how risky they
are to fix, and honest about what a given change introduced versus what was already
there. This skill runs the project's check catalogue, reads the hits, scores and ranks
the categories, reports the top five, and improves the catalogue each time it runs.

`<SKILL_DIR>` = the directory holding this SKILL.md; `<AUD>` =
`python3 <SKILL_DIR>/scripts/audit.py` (stdlib + git; read-only).

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

1. Look for `.claude/adapters/marpiech-audit.md` and the catalogue
   `.claude/audit-checks.json` in the repository root.
2. IF present → read: default scope, layering rules and where they are written,
   linters and their expanded rule sets, category score overrides, the catalogue's
   recorded exemptions, the change log of earlier runs, and project learnings.
3. ELSE → read CLAUDE.md and the architecture docs it links; list the rules that can be
   checked mechanically; copy `templates/audit-checks.template.json` to
   `.claude/audit-checks.json` keeping only checks for rules this project actually has,
   and adapt names and globs. Show the user the draft catalogue before the first run and
   offer to save the adapter (`templates/adapter.template.md`).
4. IF /marpiech-memory is installed → READ: earlier audits and accepted exemptions
   are prime memory material.

---

## Algorithm

### Step 2 — Fix the scope

```
"audit my changes" / called from myplan or resolve   → DIFF scope (--diff <base>)
"audit <service / path>"                             → PATH scope (--scope <paths>)
"audit the code"                                     → WHOLE repo (adapter default scope)
```

Diff scope: base = the merge-base with the main branch, or the parent commit of the
ticket's work. Small scopes (≤ ~20 files) run inline; a whole-repository audit of a
large codebase MAY fan out to parallel subagents by category group (security +
isolation + authorization / architecture + single source / quality + duplication +
size / UI + naming) — each gets the catalogue section and the rules it encodes, and
returns hits with file:line. Fan-out costs more than it saves on small scopes.

### Step 3 — Run the mechanical checks

1. `<AUD> run [--scope …] [--diff <base>]` — catalogue checks plus built-in generic ones
   (credential literals, key material, stale TODO markers).
2. `<AUD> sizes [--scope …]` — oversized files (> 500 lines large, > 800 must-split,
   > 5000 probably generated — look before reporting).
3. The project's linters with an **expanded** rule set reported separately (a pinned
   minimal rule set reports 0 on a tidy tree and hides complexity and exception-chaining
   problems), e.g. `ruff check --isolated --select E,F,I,UP,B,SIM,C901` (ignore rules the
   adapter lists as framework noise), `eslint`, `golangci-lint`.
4. IF diff scope → for complexity and size findings, measure the base version too
   (`git show <base>:<file>`) so "worsened by this change" is a number, not an opinion.

### Step 4 — Read what grep cannot see

Some of the most expensive problems are not greppable. For the categories in scope,
read the relevant code using `references/categories.md` as the checklist — notably:
list/search queries without a tenant filter, fetch-by-id without an ownership check,
proxies that forward a client-supplied resource id to another service, authorization
that silently passes when a field is missing (fail-open), "has a project in context"
mistaken for "may access that project", permissions enforced only in templates,
twin endpoints (HTML vs API) that check different permissions, enforcement switches
left in log mode in every deployed environment. This audit checks the project's rules; for an
adversarial review (attacker model, source → sink verification, CI/agent workflows, supply
chain) IF `/marpiech-security` is installed → recommend it in the report rather than
expanding this step.

### Step 5 — Triage every hit

FOR each hit:
1. Open the line in context. Classify: **violation** / **false positive** (pattern too
   broad) / **accepted exemption** (a recorded decision in the catalogue's `decided`).
2. In diff scope keep the attribution: NEW (introduced or worsened by this change) vs
   PRE-EXISTING (`git blame` confirms when unsure).
3. Spot-check anything a subagent claims is absent ("set nowhere", "never called") —
   absence claims are the most common subagent error.

Only confirmed violations count toward the score.

### Step 6 — Score and rank

For each category with confirmed violations: start from the catalogue's defaults
(Importance, Not-implementing risk, Implementing risk; 1–10), then adjust:
- more than 10 violations → Importance + 1 (max 10);
- a violation in a production-critical path → Not-implementing risk + 1;
- the fix touches many call sites or a hot path → Implementing risk + 1.

`Priority = I × NR ÷ IR`. Sort descending; take the top five. In diff scope rank NEW
findings; list PRE-EXISTING ones separately and briefly.

### Step 7 — Report

```
## Audit — <scope> — <date>

### #1 <Category> — score XX.X — N violations (K new)
- `path/file.py:123` — <what is wrong, in one line>
- … (max 10; summarise the rest)
**Suggested fix:** <1–2 sentences; the root cause when several hits share one>

### #2 … (top five only)

### Summary
| # | Category | Score | Violations | Top file |

### Pre-existing (diff scope only)
<counts per category; not caused by this change>

### Self-update
<what changed in the catalogue, or "No changes — all checks current.">
```

Fixes are not part of the audit. IF the user asks to fix → fix the NEW findings of a diff
scope in the same change; pre-existing ones become separate work (IF /marpiech-tickets is
installed → offer to file them).

### Step 8 — Self-update the catalogue

1. **Zero-hit checks** (listed by `run`): is the pattern stale or wrong (e.g. it greps
   `session.` while routes name the session `db`), or is it a regression guard worth
   keeping? Fix the regex, or keep it and note "0 again" in the change log.
2. **False positives**: narrow the pattern or add an exclusion — and write the decision
   into `decided` so the next run does not re-litigate it.
3. **New anti-patterns** found while reading (Step 4/5) that recur → a new numbered check
   with `why`.
4. **Score calibration**: a category consistently mis-ranked → adjust its I / NR / IR.
5. Append a dated entry to the adapter's change log: added / changed / removed checks and
   why. Generic lessons (true for any project) → this skill's Self-update log.

---

## Rules & guardrails

- Read-only: the audit changes no code; the catalogue and adapter are the only files it
  edits, and only in Step 8.
- Never report a grep hit as a violation without reading it.
- Never quote secret values found during the audit; report file:line and rotate-first
  advice (IF /marpiech-secrets is installed → its leak response).
- In diff scope, do not hold a change responsible for pre-existing problems — and do not
  hide that they exist.
- Top five means five. Long lists are not read.

---

## Adapting this skill to your project

Adapter: `<project>/.claude/adapters/marpiech-audit.md` (template:
`templates/adapter.template.md`). Catalogue: `<project>/.claude/audit-checks.json`
(template: `templates/audit-checks.template.json`). Category checklist:
`references/categories.md`.

| setting | default | how to discover |
|---------|---------|-----------------|
| default scope | whole repository | service directories, `src/` |
| rules to check | CLAUDE.md + architecture docs | "must / never / always" statements with a code shape |
| catalogue | template, pruned to the project's rules | — |
| category scores | template defaults | past incidents raise NR |
| linters + expanded rules | detected config | `pyproject.toml [tool.ruff]`, `.eslintrc`, CI |
| framework noise to ignore | none | e.g. a rule that fires on idiomatic dependency injection |
| deploy overlays to check for enforcement flags | none | k8s overlays, env files per environment |

Example for a fictional project:

```markdown
# marpiech-audit — project adapter (acme-shop)

## Scope
- default: services/*/app and libs/core/src; exclude services/*/tests, migrations

## Rules the catalogue encodes
- routes → services → repositories; repositories never commit (docs/architecture.md)
- every list query is scoped by store_id from the session (docs/tenancy.md)
- permissions are checked server-side; templates only hide buttons

## Linters
- ruff (pinned E,F,I,UP); audit also runs `--isolated --select E,F,I,UP,B,SIM,C901`, ignores B008

## Change log
- 2026-03-01 — C2 regex now matches `db.` (sessions are named db in routes); was 0 for 3 runs
- 2026-02-10 — A1 exempts services/*/config.py (defaults overridden per environment)
```

---

## CLAUDE.md snippet

```markdown
## Audit (skill: marpiech-audit)
- After implementing (and before delivering) a non-trivial change: `/marpiech-audit` on the
  diff — fix what the change introduced; report pre-existing issues separately.
- Periodically: `/marpiech-audit` on the whole repo — top five by priority, with evidence;
  the check catalogue (.claude/audit-checks.json) updates itself each run.
```

---

## Self-update log

Generic learnings, newest first. Project-specific learnings go to the project's adapter.

- 2026-11-03 — initial generic version, distilled from a production monorepo's audit
  command and its change log. Lessons carried over: a check that greps the wrong variable
  name returns 0 forever (routes bound the session as `db`, not `session`); a pinned
  minimal linter rule set hides complexity — run an expanded set separately; isolation
  and authorization dominated real findings while secrets/localhost checks stayed at 0
  for months (keep them as cheap regression guards); subagents' "not set anywhere"
  claims need a spot check; for a diff scope, inline checks beat fanning out, and every
  hit must be attributed new vs pre-existing. First generic run found committed
  infrastructure state files holding key material — the built-in key-material check
  scans everything tracked, not just source code.
