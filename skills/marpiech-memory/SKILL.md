---
name: marpiech-memory
description: Grep-based, markdown-only project memory — plain MEMORY.md files committed next to the code they describe (no RAG, no embeddings, no vector DB), holding decisions, rationale, gotchas and rejected alternatives that live nowhere else. Use it at the START of almost every session (read mode) and at the END of any non-trivial work (update mode). Also trigger — even when the word "memory" is never said — when the user asks "why is X like this", "did we decide…", "do we have notes on…", resumes earlier work, asks to set up project memory, or before any non-trivial change that could repeat a settled mistake. Trigger on "/marpiech-memory", "check memory", "update memory", "remember this for the repo", "init memory".
---

# marpiech-memory — grep-based repo memory

## Purpose

Code says *what*; git says *when*; almost nothing says *why*. This skill maintains a
lightweight memory of the *why*: small `MEMORY.md` files committed next to the code they
describe, discovered with plain grep, read hierarchically (index → hits → full file →
links), and updated at the end of every piece of non-trivial work. The outcome: a new
session (or a new teammate) can recover past decisions, gotchas and dead ends in a few
seconds instead of re-deriving them — or worse, repeating them.

The skill has three **modes**. Pick the mode in Step 2.

| mode | when | cost |
|------|------|------|
| **READ** | session start; before any non-trivial change; "why is X like this?" | seconds |
| **UPDATE** | end of non-trivial work; user says "remember this" | 2 minutes |
| **INIT** | the project has no memory system yet | 5–10 minutes, once |

Throughout, `<SKILL_DIR>` means the directory containing this SKILL.md, and
`<MEM>` means the memory file name (default `MEMORY.md`). Run scripts from the
repository root.

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

1. Look for `.claude/adapters/marpiech-memory.md` in the repository root.
2. IF present → read it and apply its settings (file name, root index path, stale
   threshold, ticket prefix, commit policy, other knowledge stores, project-specific
   rules, learned items). Adapter settings override the defaults in this file.
3. ELSE → use the defaults: `<MEM>` = `MEMORY.md`, root index = `./MEMORY.md`,
   stale threshold = 90 days, commit policy = same commit as the code change.
   Do not create the adapter now; INIT mode offers it.
4. IF the adapter sets a different file name → export `MEM_FILENAME=<name>` (and
   `MEM_ROOT=<path>` for a non-default index) for every script call below.

## Step 2 — Choose the mode

```
IF the root index does not exist AND no <MEM> files exist anywhere
   → INIT mode (ask the user first: "This repo has no memory system — set one up?")
     IF the user declines → stop the skill; mention it once, never again this session.
ELSE IF the session is ending, a task just finished, or the user said
        "update memory" / "remember this"
   → UPDATE mode
ELSE
   → READ mode
```

A single session normally runs READ at the start and UPDATE at the end.

---

## READ mode

Goal: get the context the current task needs at minimum cost, and never present a stale
note as fact.

1. **Level 0 — read the root index** (the whole file; it is short by design).
   - Note every pointer line whose hook overlaps the task's nouns.
   - IF there is no task yet (plain session start) → stop here. Tell the user in one or
     two lines what areas have memory and their ages are visible via
     `<SKILL_DIR>/scripts/mem-search.sh --list`. Do not read further.
2. **Level 1 — search.** Derive 2–4 search terms from the task: module/directory names,
   domain nouns, the external system involved, a distinctive token from an error
   message, the ticket key. For each term run:
   `<SKILL_DIR>/scripts/mem-search.sh '<term>'`
   (use `-i` as an extra argument for case-insensitive search). Collect the distinct files.
3. For each candidate file, read **only the frontmatter and the `## Durable` section**.
   Rank files: nearest to the code being changed first; then by relevance of `summary`.
4. **Level 2 — full read** only for files that (a) sit in or above the directory being
   changed, or (b) whose summary/Durable says they matter. Read the Log newest-first and
   stop when entries are clearly older than the relevant decisions.
5. **Level 3 — follow `relations`** (docs, ADRs, other memory files, PRs) only when a
   Level-2 read explicitly says the detail lives there.
6. **Tip-not-truth check** for everything you are about to rely on:
   - Reasoning (why, rejected, invariants) → trust, cite the file.
   - Mechanical claims (paths, names, behaviour) → verify against current code first.
     IF verification fails → do not use the claim; tell the user; remember to fix the
     file in UPDATE mode (bump `last-verified`, correct Durable, or mark
     `status: deprecated`).
   - IF `last-verified` is older than the stale threshold OR a `revisit-when` event has
     already happened → say so when citing it ("note from 140 days ago — verified
     still true" / "…no longer true").
7. **Report** to the user in a compact block before starting the actual work:
   ```
   Memory: 3 relevant notes
   - services/payments/MEMORY.md (12d) — idempotency key must be created before retries
   - services/orders/MEMORY.md (140d, re-verified) — order totals are server-side only
   - rejected before: client-side totals (drift on coupon expiry)
   ```
   IF nothing relevant was found → say "Memory: nothing relevant" in one line and go on.
8. Keep a mental list of **memory debts** discovered while reading (stale claims, missing
   index lines, files with no `why`). UPDATE mode settles them.

Rules for READ: never read every memory file "to be safe"; never build or assume an
embedding index; stop the moment you have enough.

---

## UPDATE mode

Goal: leave the memory more useful than you found it, in about two minutes, without
copying anything that has a canonical home.

1. **Collect candidate learnings** from the session. Walk this list and write down every
   item that applies:
   - a decision was made, and its reason;
   - an alternative was tried or considered and rejected — and why;
   - something behaved unexpectedly (a gotcha, a misleading error, a hidden coupling);
   - something was hard (a time sink and what finally worked);
   - an invariant was discovered ("never do X because Y");
   - a memory note was found stale or wrong during READ (memory debt);
   - a `revisit-when` event happened.
2. **Filter.** Drop every candidate that:
   - is derivable from the code, git log, or an existing doc (link it instead);
   - is a general rule for the whole repo → propose a CLAUDE.md line instead and ask;
   - is in-flight work → belongs in the task tracker, not memory;
   - contains secrets, credentials, internal hostnames, customer data or personal
     data — memory is committed to git. Rephrase without them or drop it.
   IF nothing survives → tell the user "Memory: nothing worth recording" and stop.
3. **Locate the target file** for each learning:
   - the nearest existing `<MEM>` in or above the directory the learning is about
     (`<SKILL_DIR>/scripts/mem-search.sh --list` shows them);
   - IF none exists AND the context is non-obvious → create `<dir>/<MEM>` from
     `<SKILL_DIR>/templates/MEMORY.template.md` (fill `summary`, `why`, dates).
   - One file = one subject. Do not append unrelated topics to a convenient file.
4. **Write the Log entry** at the top of `## Log`, following the checklist in
   `references/conventions.md` §9: dated heading, 2–5 bullets, the *why*, prefixes
   (`unexpected:`, `rejected:`, `invariants:`, `hard:`, `revisit-when:`), provenance
   (ticket/PR/commit) when it exists.
5. **Promote** — IF the learning settles something → also edit `## Durable` (add or
   correct a bullet) and, when relevant, the frontmatter (`rejected`, `invariants`,
   `revisit-when`, `status`).
6. **Settle memory debts** from READ: correct or deprecate stale claims.
7. **Stamp** every file you touched or re-verified:
   `<SKILL_DIR>/scripts/mem-stamp.sh <file> [file...]`
8. **Index** — for every newly created file add one pointer line to the root index:
   `- [topic](path/to/MEMORY.md) — <the surprise that makes you open it>`.
   For an existing file whose content changed meaningfully, update its hook.
9. **Lint** — run `<SKILL_DIR>/scripts/mem-lint.sh --stale-days <N>`. Fix every
   `MISSING-FIELD`, `ORPHAN` and `DEAD-LINK` caused by this session. Report remaining
   `STALE` items to the user as a list; do not "re-verify" files you did not check.
10. **Commit according to the policy** (adapter `commit-policy`, default
    `same-commit-as-code`): stage memory changes together with the code they describe.
    Only commit when the user's workflow says to commit; otherwise leave them staged or
    modified and mention them in the summary.
11. **Report** in two to four lines: files created/updated, index lines added, debts
    settled, stale items remaining.

---

## INIT mode

Goal: give a repository a working memory system and wire it into its CLAUDE.md.

1. **Inspect the repo** (read-only): top-level layout, existing CLAUDE.md / AGENTS.md,
   docs directory, task/todo files, existing notes files with "notes", "decisions" or
   "adr" in the name. Identify the 3–8 areas (services, packages, top-level modules)
   where non-obvious context is most likely.
2. **Ask the user** only what you cannot infer, in one message:
   - file name (default `MEMORY.md`) — IF a `MEMORY.md` with a different purpose already
     exists, propose another name (e.g. `NOTES.md`);
   - ticket prefix for provenance lines (if any);
   - commit policy.
3. **Create the root index** from `<SKILL_DIR>/templates/ROOT-INDEX.template.md`,
   replacing `<skill-dir>` with how this project reaches the skill (usually
   `~/.claude/skills/marpiech-memory` or `.claude/skills/marpiech-memory`).
4. **Seed memory files — only with real content.** For each area from step 1 where the
   current session, existing docs, or the user can supply a genuine *why* (a decision,
   gotcha or rejected alternative), create `<area>/<MEM>` from the template and add an
   index line. Do NOT create empty placeholder files; an empty memory is noise.
5. **Create the adapter** `.claude/adapters/marpiech-memory.md` from
   `<SKILL_DIR>/templates/adapter.template.md`, filled with the answers from step 2 and
   the knowledge stores found in step 1. Delete template lines that do not apply.
6. **Wire CLAUDE.md** — append the snippet from "CLAUDE.md snippet" below to the
   project's CLAUDE.md (create the file if missing; ask first if the file is
   generated by another tool). IF the project uses `marpiech-init`, let it place the
   snippet in its "Skills workflow" section instead.
7. **Lint** with `mem-lint.sh` and report what was created.

---

## Rules & guardrails

- Memory is **committed and shared**. Never write secrets, tokens, passwords,
  connection strings, private hostnames/IPs, customer data or personal data into it.
  Use the *name* of an env var or secret, never its value.
- **Owns only what has no other home**: link to code, docs and CLAUDE.md; never copy.
- **Capabilities, not paths**: describe behaviour and reasons; paths are hints.
- **Tip, not truth**: verify mechanical claims before asserting them.
- Discovery is **lexical only** — no embeddings, no vector stores, no whole-tree reads.
- The root index stays **thin**: one line per file, never content.
- Do not rewrite or delete other people's Log entries; append corrections as new
  dated entries and fix Durable.
- This repo memory is not Claude Code's personal auto-memory; when both exist, team
  knowledge goes here, personal preferences go there.

---

## Adapting this skill to your project

The skill works with zero configuration. Adapt it when the defaults do not fit.

**1. Placeholders and their defaults**

| placeholder / setting | default | how to discover the right value |
|-----------------------|---------|----------------------------------|
| `memory-filename` | `MEMORY.md` | keep unless the name is already taken by something else |
| `root-index` | `./MEMORY.md` | keep at the repo root unless the root is generated/owned elsewhere |
| `stale-days` | `90` | shorten (30–60) for fast-moving code, lengthen for stable libraries |
| `ticket-prefix` | none | look at recent commit messages: `git log --oneline -50` |
| `commit-policy` | `same-commit-as-code` | `separate-commit` if reviewers want memory diffs isolated; `never-commit` only for private experiments |
| `extra-exclude-dirs` | common build/vendor dirs | add generated or vendored trees that may contain stray `MEMORY.md` |
| other knowledge stores | CLAUDE.md | list your docs/ADR/todo locations so memory links rather than copies |

**2. Where the adapter lives:** `<project>/.claude/adapters/marpiech-memory.md`,
committed with the project. Template: `templates/adapter.template.md`.

**3. Example adapter for a fictional project**

```markdown
# marpiech-memory — project adapter (acme-shop)

## Settings
- memory-filename: MEMORY.md
- root-index: MEMORY.md
- stale-days: 60
- ticket-prefix: ACME
- commit-policy: same-commit-as-code
- extra-exclude-dirs: frontend/node_modules, infra/.terraform

## Other knowledge stores in this repo
- rules: CLAUDE.md
- formal docs: docs/adr/
- active work: todo/

## Project-specific memory rules
- every service under services/ owns a MEMORY.md once it has one non-obvious decision
- incident learnings go to memory only after the post-mortem is merged

## Learned in this project
- 2026-02-11 — payments and orders share an invariant; cross-link both memory files
```

**4. Installing the skill** (once per machine or per project):
`git clone <this skills repo>` then symlink `skills/marpiech-memory` into
`~/.claude/skills/` (all projects) or `<project>/.claude/skills/` (one project). Use a
symlink rather than a copy so Step 0 can keep it updated.

---

## CLAUDE.md snippet

Paste into the project's CLAUDE.md (or let `marpiech-init` place it):

```markdown
## Project memory (skill: marpiech-memory)
- SESSION START: run `/marpiech-memory` (read mode) before any non-trivial work —
  read the root MEMORY.md index, grep for the task's nouns, verify before trusting.
- BEFORE CHANGING code in a directory: check the nearest MEMORY.md for invariants
  and rejected alternatives.
- SESSION END / TASK DONE: run `/marpiech-memory` (update mode) — record decisions,
  gotchas, rejected paths; stamp; add index lines; commit with the code change.
- Memory holds only what has no other home. Never secrets or personal data.
```

---

## Self-update log

Generic learnings about this skill, newest first. Project-specific learnings go to the
project's adapter, never here. When a learning changes a step, edit the step too.

- 2026-10-20 — initial generic version, distilled from a production repo that ran
  this protocol across ~30 memory files; the thin index + hooks-name-the-surprise rule
  was what kept the index useful as it grew.
