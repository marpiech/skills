---
name: marpiech-docs
description: Keep a project's documentation true — both the agent-facing layer (CLAUDE.md, deep-dive docs for agents, skills, component catalogues) and the user-facing layer (product docs, possibly in a separate repository or a hosted docs platform edited by humans). Four modes — MAINTAIN (mine recent sessions for ground truth, delete what no longer exists, enforce size budgets, one home per fact), IMPACT (which docs does this change or PR affect, via a decision matrix and a code-path → doc-page map; works when the docs live in another repo), AUTHOR (write or fix a user page from verified sources only, in plain controlled English, in the product's exact words, with co-editing rules when humans edit the same docs), CHECK (dead links, pages missing from the nav, size budgets, prose lint). Use when the user says "/marpiech-docs", "update the docs", "review / prune CLAUDE.md or the agent docs", "does this change need docs?", "docs impact", "write the docs page for X", "fill in this stub", "apply this docs review", "check the docs for dead links", or at the docs step of a delivery workflow.
---

# marpiech-docs — documentation that tells the truth

## Purpose

Documentation fails in two quiet ways: agent-facing docs keep describing a world that no
longer exists (moved paths, retired services, commands that stopped working), so every
future session starts from a lie; and user-facing docs drift from the product — or worse,
describe what the code *could* do rather than what the deployed product *does*. Neither
failure has a build error. This skill gives each layer an owner and a procedure: prune
and correct the agent layer from real session evidence, detect which user pages a change
makes stale, author pages only from verified sources, and run mechanical checks that
the docs platform itself will not. Outcome: fewer, shorter, correct docs, and a clear
list of what still needs a human.

`<SKILL_DIR>` = the directory holding this SKILL.md; `<DC>` =
`python3 <SKILL_DIR>/scripts/docs-check.py` (read-only; `git`, optional `gh`).

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

1. Look for `.claude/adapters/marpiech-docs.md` in the repository root.
2. IF present → read the **documentation map** (each layer: audience, location, format,
   platform, owner), the **decision matrix** (change type → docs to update), the
   impact-map path, size budgets, nav file, terminology table (canonical term ← rejected
   forms), audience definition, sources of truth, page template, co-editing rules, and
   project learnings.
3. ELSE → build a provisional map:
   - agent layer: `CLAUDE.md`, `AGENTS.md`, `.claude/skills/*/SKILL.md`,
     `.claude/commands/*.md`, a deep-docs directory referenced from CLAUDE.md;
   - user layer: `docs/`, `mkdocs.yml`, `SUMMARY.md`, `docusaurus.config.*`,
     `conf.py` (Sphinx), a README that points at an external docs site or repo;
   - generated docs (API schema pages) — note them, never hand-edit them.
   Offer at the end to save the map as the adapter (`templates/adapter.template.md`).
4. IF /marpiech-memory is installed → run its READ mode for the area first; recorded
   decisions often explain why a doc says what it says.

---

## Algorithm — pick the mode

```
"prune / review / update CLAUDE.md or agent docs"        → A. MAINTAIN
"does this change / PR need docs?", delivery docs step  → B. IMPACT
"write / fix / fill in the page for X", review feedback → C. AUTHOR
"check the docs", before committing any docs change     → D. CHECK
```

Several modes often chain: B finds stale pages → C fixes them → D verifies.

### A. MAINTAIN the agent-facing layer

Targets: the always-loaded file (CLAUDE.md), deep-dive docs, skills, commands,
component catalogues. Readers: an agent, on every session — every line costs tokens.

1. **Measure.** `<DC> size CLAUDE.md <deep-docs>/*.md --limit <budget>` (default 20000
   characters per file). Note each OVER file.
2. **Collect ground truth.** What did recent sessions learn that the docs contradict or
   omit? Sources, in order: the current conversation; recent commits and their messages
   (`git log --since=<date> --stat`); project memory entries; error messages that sent
   an agent down a wrong path. Highest-signal items: commands that failed as written,
   moved paths, renamed services, missing parameters, shell-quoting traps.
3. **Verify each candidate** against the repo (path exists? command runs? flag is
   accepted?) before writing it. A doc fix that is itself wrong is worse than none.
4. **Apply, in this priority order:**
   1. *Delete* what no longer exists (paths, ports, services, procedures). The
      highest-value edit is usually a deletion.
   2. *Correct* wrong commands, endpoints, parameters and examples.
   3. *De-duplicate*: one home per fact — keep it where it belongs (always-loaded rules
      in CLAUDE.md, rationale and detail in deep docs) and link from the other.
   4. *Add* working patterns and pitfall warnings at the point of use; inline computed
      values (IDs, encoded URLs) where command substitution invites quoting bugs.
   5. *Compress*: cut prose that does not change what an agent does.
5. **Bring OVER files under budget** by moving detail into deep docs (with a link),
   never by deleting rules that still hold. Archive obsolete deep docs to an
   `archive/` subdirectory instead of leaving them in the main tree.
6. **Gate:** D (links + size) passes for the touched files; IF /marpiech-init is
   installed → its AUDIT mode is the fuller CLAUDE.md check.
7. Show the user a summary — deleted / corrected / moved / added — before committing.

### B. IMPACT — which docs does this change affect?

1. **Walk the decision matrix** (adapter; default below) against the change and list
   every row that applies:

   | change | update |
   |--------|--------|
   | CLI command added / changed | CLI reference page(s) |
   | UI added / changed | the user guide page for that screen; screenshots |
   | API endpoint added / changed | API reference (unless generated) |
   | new service / module | user guide (if user-visible) + architecture doc + agent overview |
   | architecture changed (auth, data model, service communication) | architecture doc + matching deep doc |
   | deployment changed | deployment doc + matching deep doc |
   | new pattern / convention | matching deep doc; CLAUDE.md if broadly applicable |
   | UI component added / changed | component catalogue |
   | config key / env var added | configuration reference + example env file |

2. **Run the map:** `<DC> impact --base <base branch or commit>` (map default
   `.claude/doc-impact-map.json`, template `templates/doc-impact-map.template.json`).
   - Docs in **this** repo → a rule is OPEN when its code changed and none of its
     pages did.
   - Docs in **another** repo (`docs_repo`: `owner/name` via `gh`, or a local checkout
     path) → OPEN when a page is older than the newest matching code change. Pull the
     local docs checkout first, or the dates lie.
   - For a pull request: IF /marpiech-merge-pr is installed → its `pr-facts.py` reads
     the same map against the PR; ELSE use `--base <PR base branch>` on the PR branch.
3. **Judge each OPEN rule** — date and path checks give false positives (a typo fix makes
   a page "fresh"; an internal refactor touches a mapped path without changing behaviour).
   Keep only rules where users would now see something the page does not describe.
4. **Act:**
   - same repo → update the pages in the same change (C for user pages);
   - other repo → a separate change against the docs repo, or IF the user prefers a
     follow-up ticket (IF /marpiech-tickets is installed → draft it there) listing the
     code change and the stale pages;
   - posting a PR comment about docs impact is an outward action — ask first.
5. This is a **prompt, not a gate**: never block a merge or deploy on it.

### C. AUTHOR a user-facing page

Read `references/writing-standard.md` before writing — it holds the review lessons and
the plain-language rules this mode enforces.

1. **Co-editing pre-flight** (when the adapter says humans edit the docs too — e.g. a
   hosted editor syncing to git):
   1. `git -C <docs repo> status` — IF stray uncommitted edits exist → stop and ask;
      they may overwrite a human's newer work. Then `git pull --ff-only`.
   2. Read the **current** nav file; adapt to its structure — never assume a cached
      tree.
   3. Identify who owns each page you might touch: `git log -5 --format='%an %s' -- <page>`.
      IF the recent commits are not from agent sessions (no agent trailer) → **add, do
      not rewrite**: new pages and inserted nav lines only; content fixes to a human's
      page go to its author as a ticket or comment, not as an edit.
   4. After adding pages, tell the owner (ticket or message, with the user's approval)
      what was added and where, so they can fold it into their structure.
2. **Find the source of truth**, in this order: the existing CLI/API reference (lift
   commands verbatim); the code — route handler, template, model, enum; the *deployed*
   product (ask the user when unsure whether a feature is enabled); adjacent authored
   pages for structure and tone. IF none of these covers it → write an honest stub
   (`templates/stub.template.md`), never invented content.
3. **Write** from `templates/page.template.md` (or the adapter's page template), matching
   2–3 authored pages in the same section (`head -30` them first). Apply the rules in
   `references/writing-standard.md`: document only what is live, every claim traceable,
   the UI's exact labels, the reader's altitude (no internals on user pages), the
   required role for each action, one instruction per numbered step, a short "See also".
4. **Keep channels separate**: UI pages describe clicks; CLI pages describe commands;
   API pages describe requests. Do not paste a CLI flow into a UI page because the UI is
   missing — say "in development" and link to the CLI page.
5. **Verify every factual claim** (route, flag, role, status name, limit, file path)
   with a grep in the code before keeping it. A short page of verified facts beats a
   long page of plausible fiction.
6. **Self-review** against the checklist at the end of `references/writing-standard.md`,
   then run D on the touched pages.
7. **Commit** with explicit paths only (`git add <page> <nav file>`), never `git add -A`
   in a co-edited docs repo. IF a commit clobbered someone's change → `git revert` it at
   once; never rewrite shared history.

### D. CHECK (before every docs commit)

1. `<DC> links <docs dirs>` — every DEAD-LINK is fixed or explained.
2. `<DC> nav <nav file> [--root <docs dir>] [--exclude <unpublished dir>]` — DEAD-NAV
   entries are fixed; each UNLISTED page is either added to the nav or deliberately
   unpublished (then excluded in the adapter). On platforms that hide unlisted pages
   this is the only warning there is.
3. `<DC> size <agent docs> --limit <budget>` for the agent layer.
4. `<DC> style <pages> [--reject 'bad=good' …] [--british] [--max-words 25]` with the
   adapter's terminology table — advisory: read each hit and judge it.
5. The platform's own build, when it has one (`mkdocs build --strict`, `npm run build`,
   `sphinx-build -W`, …) — `references/platforms.md` lists platform quirks.

---

## Rules & guardrails

- Never document what you cannot point at in code or in the deployed product.
- Never edit generated docs by hand; change their source.
- Never rewrite or delete a page a human owns in a co-edited docs repo; propose instead.
- Never paste secrets, internal hostnames, bucket paths, customer data or real personal
  names into docs or screenshots; user docs show a fictional persona.
- Commits to a separate docs repository, PR comments and tickets are outward actions —
  ask first. Never force-push a docs branch.
- Docs impact is advisory; it never blocks a merge or a deploy.

---

## Adapting this skill to your project

Adapter: `<project>/.claude/adapters/marpiech-docs.md` (template:
`templates/adapter.template.md`). Impact map: `templates/doc-impact-map.template.json`.

| setting | default | how to discover |
|---------|---------|-----------------|
| documentation map | built in Step 1 | docs dirs, nav files, docs links in README / CLAUDE.md |
| decision matrix | the table in B | the project's "docs checklist" in CLAUDE.md, if any |
| impact map | `.claude/doc-impact-map.json` | user-visible code paths → the pages describing them |
| agent-doc budget | 20000 characters per file | CLAUDE.md "docs rules" section |
| nav file + excluded dirs | `SUMMARY.md` / `mkdocs.yml` | docs platform config |
| terminology table | none | UI labels in templates; past review comments |
| audience | "a user of the product, not its developer" | who reads the docs; roles they hold |
| sources of truth | CLI reference, code, deployed product | where commands, routes, enums live |
| co-editing | none | non-agent authors in `git log` of the docs repo; hosted editor sync |
| spelling variant | none | the product UI's language |

Example for a fictional project:

```markdown
# marpiech-docs — project adapter (acme-shop)

## Documentation map
| layer | audience | where | platform | owner |
|-------|----------|-------|----------|-------|
| agent | Claude | CLAUDE.md, docs/agents/ | markdown | dev team |
| user  | shop admins | acme/acme-docs repo → docs.example.com | hosted editor, git sync | docs editor (humans) + agents add-only |
| API   | integrators | /openapi.json | generated | — |

## Settings
- impact-map: .claude/doc-impact-map.json (docs_repo: acme/acme-docs)
- agent-budget: 20000
- nav: SUMMARY.md; exclude: drafts/, internal/
- spelling: American (--british flags)
- audience: store admins (roles Owner / Manager / Staff); never document the internal support role

## Terminology (canonical ← never write)
- Order History ← order log, orders browser
- archive ← bundle
- Manager ← Editor   (there is no Editor role)

## Decision matrix additions
- checkout flow changed → docs: checkout/*.md + screenshots in images/checkout/

## Co-editing
- humans edit in the hosted editor; agents: pull --ff-only first, add-only on human pages,
  file a ticket to the page author for fixes

## Learned in this project
- 2026-03-01 — the hosted editor rewrites `-` bullets to `*` on sync; ignore that diff noise
```

---

## CLAUDE.md snippet

```markdown
## Documentation (skill: marpiech-docs)
- After a change users or agents will notice: `/marpiech-docs impact` — update every
  doc the decision matrix names (user docs elsewhere → separate change or follow-up).
- Agent docs (CLAUDE.md + deep docs) stay under budget and true: `/marpiech-docs`
  maintain mode after significant work; delete what no longer exists.
- User pages: `/marpiech-docs` author mode — verified facts only, the UI's exact words.
```

---

## Self-update log

Generic learnings, newest first. Project-specific learnings go to the project's adapter.

- 2026-11-03 — initial generic version, distilled from a production team's internal-docs
  skill and its customer-docs authoring skill (review lessons from many reviewed pages).
  The checker skips agent files (CLAUDE.md, MEMORY.md) in impact and nav results, and
  un-escapes markdown escapes (`a\_b`) in link targets — both were false positives on
  real repositories. `analyses` is a plural, not a British spelling.
