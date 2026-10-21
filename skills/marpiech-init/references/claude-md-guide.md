# Writing a good CLAUDE.md — guide for marpiech-init

Read this before drafting or restructuring a project's CLAUDE.md. Contents:

1. What CLAUDE.md is for (and what it is not)
2. The three-tier documentation model
3. Section-by-section guidance
4. How to phrase a rule
5. The managed skills block
6. Budget and pruning
7. Things that must never be in CLAUDE.md
8. Worked example (fictional project)

---

## 1. What CLAUDE.md is for

CLAUDE.md is loaded into **every** session. Every line costs context in every
conversation, so it holds only what Claude needs *often* or *must never get wrong*:

- rules that, if broken, cause real damage (secrets, force-push, data loss);
- the mandatory workflow and its gates;
- commands Claude would otherwise guess;
- a map of where deeper knowledge lives.

It is **not** a design document, a changelog, a tutorial or a ticket tracker. Anything
read only occasionally belongs one link away.

`CLAUDE.local.md` (gitignored) holds one person's private preferences; CLAUDE.md is
committed and shared — write it for the whole team.

## 2. The three-tier documentation model

| tier | where | budget | holds |
|------|-------|--------|-------|
| always-loaded | `CLAUDE.md` | ~20k chars | rules, workflow, commands, map |
| on-demand | deep-docs dir (default `claude-docs/`) | ~20k chars/file | architecture dives, rationale, runbooks |
| in-flight | todos dir (default `claude-todos/`) | none | plans and checklists for active work |
| next to code | `MEMORY.md` files (marpiech-memory) | small | decisions, gotchas, rejected paths |
| procedural | skills (`.claude/skills/`, `~/.claude/skills/`) | per skill | multi-step workflows |

Rule of thumb: IF Claude needs it in > 50 % of sessions → CLAUDE.md. IF it is a
procedure with steps → a skill. IF it is the *why* of one area → MEMORY.md. ELSE → deep docs.

IF the repository already has a docs directory used for the same purpose, reuse it
instead of creating `claude-docs/`.

## 3. Section-by-section guidance

| section | include when | content |
|---------|--------------|---------|
| Behavioral Rules | always | 5–12 rules in the §4 shape; generic safety rules + project-specific ones |
| Skills workflow | any marpiech skill installed | the managed block (§5) |
| Development Workflow | team works ticket-driven, or any CI gates exist | Light/Heavy table, numbered steps, gates, docs checklist |
| Documentation Self-Update Rules | always | the tier model with this project's dirs and budgets |
| Project Overview | always | 2–4 sentences |
| Technology Stack | always | short bullets from discovery |
| Commands | always | only verified commands, in one fenced block, each with a short comment |
| Architecture | > 1 component/service | table: component, responsibility, port/entry point |
| Code Conventions | conventions a linter does not enforce | bullets |
| Environments & CI/CD | deploys exist | branch → environment mapping, how to watch a deploy |
| Detailed Documentation | deep docs exist | one line per file: link — *when to read it* |

Ordering principle: what prevents damage first (rules), then how to work (workflow),
then reference material.

## 4. How to phrase a rule

```markdown
**NEVER hardcode URLs, hosts or ports.**

- All external URLs come from configuration/environment
- Why: the same build runs in four environments; a hardcoded host broke staging twice
- Violation check: grep the diff for `localhost`, `127.0.0.1`, `:80[0-9][0-9]`
```

- **Bold imperative headline**, `NEVER`/`ALWAYS` only when truly absolute.
- 2–5 bullets: *how to comply*, *why* (one line), *how to check*.
- A rule without a check is a wish; add a grep, test, or command where possible.
- Exceptions spelled out explicitly ("The ONLY exception is …"), never implied.
- Incident references stay generic ("a force-push once overwrote parallel commits"),
  no names, dates of private incidents, or internal identifiers in public repos.

## 5. The managed skills block

Everything between

```
<!-- marpiech-init:skills:start -->
<!-- marpiech-init:skills:end -->
```

is owned by marpiech-init and rebuilt by SYNC mode. Humans edit outside it. Inside, the
block contains:

1. A **phase table** — the session lifecycle with the skill to use in each phase:

   ```
   | phase | skill | when |
   |-------|-------|------|
   | SESSION START | /marpiech-memory (read) | always, before non-trivial work |
   | PLAN | /marpiech-myplan | new features, cross-cutting changes |
   | IMPLEMENT | /marpiech-resolve <TICKET> | ticket-driven work, end to end |
   | REVIEW / MERGE | /marpiech-merge-pr <PR> | before anything reaches a deploy branch |
   | OBSERVE | /marpiech-observe-ci | after every push that should deploy |
   | SESSION END | /marpiech-memory (update) | always, after non-trivial work |
   ```

   Only installed skills appear. Phases without a skill are omitted.

2. **Each installed skill's own snippet**, verbatim from its SKILL.md
   "CLAUDE.md snippet" section (collected by `list-skills.sh --snippets`), one after
   another, in phase order.

3. A last line: `Skills self-update (Step 0) and ask before pulling. Adapters: .claude/adapters/.`

## 6. Budget and pruning

When CLAUDE.md exceeds the budget, apply in order until under:

1. Move code examples longer than ~10 lines to a deep doc; leave a link.
2. Move any section read in < 50 % of sessions to a deep doc; leave a one-line pointer.
3. Merge rules that say the same thing.
4. Delete history ("we used to…") — it belongs in MEMORY.md or git.
5. Shorten "Detailed Documentation" hooks to one clause each.

Never delete a Behavioral Rule to save space without asking the user.

## 7. Never in CLAUDE.md

- Credentials, tokens, connection strings, even "example" ones that look real.
- Private hostnames, IP addresses, cloud project/account IDs, bucket names — unless the
  repository itself is private AND the user explicitly wants them there; even then,
  prefer referencing the config file that holds them.
- Personal data (names + emails of colleagues, customers).
- Commands that print secrets (`cat .env`, `env | grep`).
- Unverified commands. A wrong command in CLAUDE.md is executed with confidence.

## 8. Worked example (fictional `acme-shop`)

~~~markdown
# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.
Always-loaded quick reference (budget 20000 chars). Deep dives: `claude-docs/`.
Active work: `claude-todos/`.

## Behavioral Rules

**NEVER hardcode secrets.**

- Secrets come from the environment only; run tools with `direnv exec . <cmd>`
- Reference variables by name (`$PAYMENT_API_KEY`), never paste values

**One branch per ticket.**

- `ACME-<n>-short-slug` from `main`; merge via PR only
- Never commit directly to `main`

## Skills workflow

<!-- marpiech-init:skills:start -->
| phase | skill | when |
|-------|-------|------|
| SESSION START | /marpiech-memory (read) | always, before non-trivial work |
| SESSION END | /marpiech-memory (update) | always, after non-trivial work |

## Project memory (skill: marpiech-memory)
- SESSION START: run `/marpiech-memory` (read mode) …
<!-- marpiech-init:skills:end -->

## Commands

```bash
make install   # deps + pre-commit hooks
make dev       # app on the port from .env.example
make test      # unit tests (pytest)
make lint      # ruff + mypy
```
~~~
