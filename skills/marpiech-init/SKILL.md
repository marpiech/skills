---
name: marpiech-init
description: Bootstrap and maintain a project's CLAUDE.md and its wiring to the marpiech-* skills — discovers the repo (languages, commands, CI, branches, docs, ticket prefix), drafts a CLAUDE.md with behavioral rules, a mandatory development workflow, quality gates, docs self-update rules and a managed "Skills workflow" block that says which skill to use when (memory at session start and end), creates per-skill adapter files, and audits CLAUDE.md size, links and secrets. Use when the user says "/marpiech-init", "init this project for Claude", "create/write/improve CLAUDE.md", "set up skills in this repo", "which skills should this project use", "sync CLAUDE.md with skills", "audit CLAUDE.md", or after installing or updating a marpiech skill.
---

# marpiech-init — project CLAUDE.md and skills wiring

## Purpose

A project gets the most from Claude when its CLAUDE.md states the non-negotiable rules,
the workflow with its gates, the verified commands, and *which skill to use at which
moment*. Writing that by hand drifts: commands change, skills get added, the file
bloats. This skill drafts CLAUDE.md from facts discovered in the repo, wires the
installed marpiech-* skills into a managed block that is regenerated on demand, creates
the per-skill adapter files that bind generic skills to this project, and audits the
result. Outcome: any new session in the project starts with `/marpiech-memory`, follows
the same workflow, and ends with a memory update — without anyone remembering to say so.

Three **modes**, chosen in Step 2:

| mode | when | writes |
|------|------|--------|
| **INIT** | no CLAUDE.md, or CLAUDE.md without the managed skills block | CLAUDE.md, adapters, optional dirs |
| **SYNC** | a skill was installed/updated/removed; commands or layout changed | managed block, adapters, small fixes |
| **AUDIT** | "check/audit CLAUDE.md"; periodically | nothing — report only |

`<SKILL_DIR>` = the directory holding this SKILL.md. Run scripts from the project root.

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

1. Look for `.claude/adapters/marpiech-init.md` in the project root.
2. IF present → read it; its settings (file name, character budget, deep-docs dir,
   todos dir, ticket system, branch policy, secrets source, verified commands,
   intentionally omitted sections, learned items) override the defaults here.
3. ELSE → defaults: `CLAUDE.md`, budget 20000 characters, deep docs `claude-docs/`
   (or an existing docs dir), todos `claude-todos/`, no ticket system, trunk = default
   remote branch. INIT mode creates the adapter.

## Step 2 — Choose the mode

```
IF the user asked for an audit/check only                       → AUDIT
ELSE IF CLAUDE.md is missing
     OR it lacks the <!-- marpiech-init:skills:start --> marker  → INIT
ELSE                                                            → SYNC
```

IF CLAUDE.md exists but was not written with this skill, INIT **merges** into it — it
never replaces a human-written file wholesale (see INIT step 6).

---

## INIT mode

Goal: a complete, verified CLAUDE.md plus adapters, with the user confirming every
fact that could not be discovered.

1. **Memory first.** IF `/marpiech-memory` is installed → run it in READ mode (or INIT
   mode if the repo has no memory yet — it will ask). Past decisions may change what
   the CLAUDE.md should say.
2. **Discover.** Run `<SKILL_DIR>/scripts/discover.sh` and read the whole report. Also
   read: existing CLAUDE.md / AGENTS.md / CLAUDE.local.md (whole), README.md (first
   ~150 lines), CONTRIBUTING.md, the CI workflow files (to learn the real lint/test
   commands and branch → environment mapping), and the build file's script section.
   Never open `.env`, secret, key or credential files.
3. **Inventory skills.** Run `<SKILL_DIR>/scripts/list-skills.sh`. Note which marpiech
   skills are installed (project or user) and which are AVAILABLE in the clone but not
   installed.
4. **Verify commands.** For every command you intend to document:
   - IF it is cheap and side-effect free (`--help`, `--version`, a lint run, a dry-run)
     → run it and confirm it works.
   - ELSE (installs, migrations, deploys, anything touching shared state) → do NOT run;
     mark it "from CI config, not executed" when asking the user.
   A command that fails or cannot be confirmed is left out or listed as a question.
5. **Ask the user — one message, only what discovery could not answer.** Typical
   questions (skip any already answered by facts):
   - branch policy: trunk-only or branch-per-ticket? which branches deploy where?
   - ticket system and prefix (suggest the most frequent prefix from discovery);
   - secrets source (suggest from discovery hints: an `.infisical.json`, `.sops.yaml`,
     `.envrc`… → the matching run command);
   - deep-docs and todos directories (suggest existing ones);
   - which Behavioral Rules from the template to keep; any project rule to add;
   - which AVAILABLE skills to install (list each with its one-line purpose), and
     where: user-level (`~/.claude/skills/`, recommended — works for every project
     and is never committed) or project-level (`.claude/skills/`; a symlink to a path
     in one person's home directory breaks for teammates, so add it to the project's
     `.gitignore` or have every teammate install user-level).
   Provide a recommended default for every question so the user can answer "defaults".
6. **Draft CLAUDE.md** from `<SKILL_DIR>/templates/CLAUDE.template.md`, following
   `<SKILL_DIR>/references/claude-md-guide.md` (read it now):
   - Replace every `<PLACEHOLDER>` with a discovered or confirmed value. IF no value →
     delete the line or the section; never leave a placeholder in the output.
   - IF a CLAUDE.md already exists → keep all of its content. Map its sections onto the
     template's order; keep human wording; only *add* missing sections, the managed
     block, and rules the user approved. Show the user a summary of what moved where.
   - Delete all HTML instruction comments except the two managed-block markers.
7. **Install skills** the user chose in step 5: create the symlinks
   (`ln -s <clone>/skills/<name> <target>/<name>`). Never copy (copies cannot
   self-update). Never overwrite an existing directory of the same name — report it.
8. **Fill the managed block** — run SYNC steps 2–4 below.
9. **Create adapters:**
   - `.claude/adapters/marpiech-init.md` from `templates/adapter.template.md` with the
     settings and verified commands from steps 2–5;
   - for every other installed marpiech skill whose adapter is missing: read that
     skill's "Adapting this skill to your project" section and create its adapter from
     its template, filling only values you discovered or the user confirmed.
10. **Create directories** the CLAUDE.md now references (deep-docs, todos) only if the
    user agreed; put a 3-line README.md in each saying what belongs there.
11. **Audit** — run the AUDIT mode checks; fix everything this run caused.
12. **Report:** files created/changed, skills installed, questions still open, and the
    one-line instruction "start every session with `/marpiech-memory`".
    Do not commit unless the user asks; when they do, CLAUDE.md, adapters and new dirs
    go into one commit.

---

## SYNC mode

Goal: bring the managed block, adapters and commands back in line with reality, with
the smallest possible diff.

1. Run `<SKILL_DIR>/scripts/list-skills.sh --snippets`.
2. **Build the phase table** (format in `references/claude-md-guide.md` §5). For each
   installed skill decide its phase(s) from its snippet and description:
   SESSION START · PLAN · IMPLEMENT · REVIEW / MERGE · OBSERVE / DELIVER · SESSION END ·
   ANYTIME. Include only installed skills; drop phases with no skill.
3. **Compose the block:** phase table, then each skill's snippet verbatim in phase
   order, then the line
   `Skills self-update (Step 0) and ask before pulling. Adapters: .claude/adapters/.`
4. **Replace** everything strictly between `<!-- marpiech-init:skills:start -->` and
   `<!-- marpiech-init:skills:end -->` with the composed block. Touch nothing outside
   the markers in this step. IF the markers are missing or duplicated → stop and ask
   (INIT re-creates them).
5. **Adapters:** for each installed skill without an adapter → offer to create it
   (INIT step 9). For each adapter whose skill is no longer installed → report it; do
   not delete without asking.
6. **Commands drift:** re-run `discover.sh`; compare its candidate commands and the
   adapter's "Verified commands" with the Commands section. Report additions/removals;
   apply only after the user confirms.
7. **Workflow drift:** IF the Development Workflow references a skill that is not
   installed, or omits an installed skill that has a workflow role → propose the edit.
8. Run AUDIT; report the diff summary (`git diff --stat` plus one line per change).

---

## AUDIT mode

Read-only. Run, then report findings grouped by severity:

1. `<SKILL_DIR>/scripts/claudemd-check.sh --limit <budget> --docs-dir <deep-docs-dir>`
   — size, managed-block markers, dead links, credential-looking lines, references to
   uninstalled skills.
2. Manual checks the script cannot do — read CLAUDE.md once, top to bottom, and check:
   - every command in Commands still exists (cheap verification as in INIT step 4);
   - every Behavioral Rule has a *how to check*;
   - no section duplicates a deep doc or a MEMORY.md (link instead);
   - no private hostnames, IPs, personal data, or secret values;
   - the session lifecycle is explicit: memory read at start, memory update at end.
3. Report as:
   ```
   CLAUDE.md audit — 14 312 / 20 000 chars
   MUST FIX   SECRET? line 88 · DEAD-LINK claude-docs/old-auth.md
   SHOULD     rule "Use path segments" has no check · Commands: `make e2e` no longer exists
   OK         managed block in sync · memory start/end present
   ```
4. Offer to fix; IF the user agrees → apply as in SYNC (smallest diff) and re-audit.

---

## Rules & guardrails

- Never write a secret value, private hostname, IP, account ID or personal data into
  CLAUDE.md or an adapter; reference env var *names* and config *files* instead.
- Never open or print `.env`, key, credential or secret files — discovery reports their
  presence only.
- Never document a command you have not verified or the user has not confirmed.
- Never replace a human-written CLAUDE.md wholesale; merge and show what moved.
- Only the managed block is regenerated automatically; everything else changes only
  with the user's confirmation.
- Never commit, push, or install skills without the user's go-ahead.
- Keep CLAUDE.md under budget; move detail to deep docs rather than deleting rules.

---

## Adapting this skill to your project

The defaults suit most repositories. Adapt via `.claude/adapters/marpiech-init.md`
(template: `templates/adapter.template.md`).

**1. Settings and defaults**

| setting | default | how to choose |
|---------|---------|---------------|
| `claude-md` | `CLAUDE.md` | keep; use `AGENTS.md` only if the team standardised on it (then symlink CLAUDE.md to it) |
| `claude-md-limit` | `20000` | lower (10–15k) for small repos; never above ~40k |
| `deep-docs-dir` | `claude-docs` | reuse an existing `docs/` if it is agent-oriented |
| `todos-dir` | `claude-todos` | reuse an existing plans/todo directory |
| `ticket-system` | none | the tracker and prefix seen in commit subjects |
| `trunk-branch` | default remote branch | where daily work lands |
| `branch-policy` | ask | `trunk-only` (all work on trunk, deploy branches fed by push) or `branch-per-ticket` (PR flow) |
| `secrets-source` | environment variables | the tool the team uses to inject secrets; its *run* command, never a value |
| verified commands | none | filled by INIT after verification |

**2. Template customisation.** To change the default CLAUDE.md shape for all your
projects, edit `templates/CLAUDE.template.md` in your clone of the skills repo (it
self-updates from there). For one project only, record deviations under "Sections
intentionally omitted" in the adapter so SYNC/AUDIT do not re-propose them.

**3. Example adapter for a fictional project**

```markdown
# marpiech-init — project adapter (acme-shop)

## Settings
- claude-md: CLAUDE.md
- claude-md-limit: 15000
- deep-docs-dir: docs/agents
- todos-dir: plans
- ticket-system: Jira, prefix ACME
- trunk-branch: main
- branch-policy: branch-per-ticket
- secrets-source: environment via `direnv exec . <cmd>`

## Verified commands
- install: make install
- run-local: make dev
- unit-tests: make test
- lint: make lint

## Sections intentionally omitted from CLAUDE.md
- Environments & CI/CD — single environment, deploy is manual and out of scope

## Learned in this project
- 2026-03-01 — `make test` needs the DB container up; documented in docs/agents/testing.md
```

---

## CLAUDE.md snippet

```markdown
## Project setup (skill: marpiech-init)
- After installing, updating or removing any marpiech-* skill: run `/marpiech-init sync`
  to rebuild the Skills workflow block and create missing adapters.
- Before large CLAUDE.md edits, and when it nears its size budget: `/marpiech-init audit`.
- Text between the marpiech-init:skills markers is generated — edit outside it.
```

---

## Self-update log

Generic learnings about this skill, newest first. Project-specific learnings go to the
project's adapter, never here. When a learning changes a step, edit the step too.

- 2026-10-21 — first real audit: deep docs quote regexes such as `[a-z]([-a-z0-9]*)` that
  look like markdown links; the link checker now strips fenced blocks and inline code
  before extracting links. Treat any DEAD-LINK whose target is not a path as a checker bug.
- 2026-10-20 — initial generic version, modelled on a production CLAUDE.md that kept
  rules in the bold-imperative + bullets + check shape and split knowledge into
  always-loaded / deep-docs / todos / memory tiers with per-file character budgets.
