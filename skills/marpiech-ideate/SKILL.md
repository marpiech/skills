---
name: marpiech-ideate
description: Idea → specification → throwaway prototype workflow for a NEW product area, module or UI whose design is still open. Mines internal sources first (the repo, sibling repos, connected document stores, container images, project memory), runs parallel web research on domain best practice, competitors and UI patterns, drives many a/b/c/d alignment rounds, keeps a numbered decision log, writes SPEC.md plus one implementation note per mocked piece, gets a blind limited-context review and a second-opinion review, then builds a standalone prototype OUTSIDE the repository — with no repository changes until the user declares a version "v-ready". Use when the user says "/marpiech-ideate", "ideate", "brainstorm / design a new module", "we will not code now", "ask me questions about X", "write a spec", "mockup", "prototype", "v1/v2 prototype", or explores a feature with no ticket and no settled design, even without the word "ideate". Prefer it over marpiech-myplan while the design itself is open; hand off to marpiech-myplan or marpiech-resolve once a version is v-ready.
---

# marpiech-ideate — from idea to a v-ready prototype

## Purpose

New product areas fail in two predictable ways: code gets written before the design is
agreed (and is thrown away), or the design is agreed in chat and then forgotten. This
skill runs a deliberate loop — **think wide, ask a lot, decide explicitly, write the
spec, review it adversarially, prototype it outside the repo, iterate v1 → v2 → … until
the user says "v-ready"**. Your job is to make the user's decisions cheap and
well-informed, never to make them for the user. Outcome: a SPEC.md, a decision log, one
implementation note per mocked piece, and a running prototype the user has walked
through — ready to be planned into the real codebase.

`<SKILL_DIR>` = the directory holding this SKILL.md. `<PROTO_ROOT>` = where prototypes
live (adapter `prototype-root`; default: the session scratchpad directory if the
environment provides one, else `/tmp/scratch`). `<slug>` = short kebab-case name of the
idea.

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

1. Look for `.claude/adapters/marpiech-ideate.md` in the repository root.
2. IF present → read it and apply: prototype root, port registry, sibling repositories
   and other internal sources, UI component library to imitate, preferred prototype
   stack, data privacy rules, second-opinion review tool, project-specific lessons.
3. ELSE → use the defaults stated in each step and offer at the end of the session to
   create the adapter from `<SKILL_DIR>/templates/adapter.template.md`.
4. IF `/marpiech-memory` is installed → run it in READ mode with the idea's nouns as
   search terms before Phase 0. Earlier decisions about this area are binding until the
   user says otherwise.

---

## Rule zero — the prototype gate

- Prototypes live in `<PROTO_ROOT>/<slug>[-vN]/`, standalone, outside the repository.
- **No changes in the repository** (code, migrations, docs, tickets) until the user says
  a version is *v-ready*. Exceptions: memory notes (marpiech-memory) and this skill's
  own self-update log.
- Mocks are allowed, but **every mocked or precomputed piece gets an
  `impl-notes/NN-<topic>.md`** (template: `templates/impl-note.template.md`) saying how to
  build it for real in the product: component/service, data model, API, data source,
  risks. This keeps the prototype honest and makes the later port plannable.
- Ask in round 1 whether the gate differs for this idea (location, iteration naming).
  Users who are not asked tend to impose the gate mid-way, forcing rework.

Track the phases as tasks. **The user decides how many question rounds there are**
("10 more", "one more round" — eight rounds is normal). Never declare alignment
finished on your own.

```
0. FRAME          restate intent; round-1 basics (gate, primary user, real data, privacy)
1. DISCOVER       internal sources (one read-only subagent) ∥ web research bursts
2. SYNTHESISE     need→evidence table, requirement catalogue ✅🟡❌, screens, open questions
3. ALIGN ×N       question rounds; DECISIONS.md updated every round; facts checked between
4. SPEC           SPEC.md + impl-notes/
5. BLIND REVIEW   limited-context reviewer subagent(s) on the spec only
6. SECOND OPINION independent review of the bundled spec; ACCEPT / DEFER-to-user
7. PROTOTYPE      only when the user says "build"; run scripts, local-only, e2e, walkthrough
8. ITERATE        user review → vN+1; on "v-ready" hand off to myplan / resolve
```

---

## Phase 0 — Frame

1. Restate the idea in one or two sentences and ask the user to confirm or correct it.
2. Create `<PROTO_ROOT>/<slug>/` and `DECISIONS.md` from
   `templates/DECISIONS.template.md` now — the log exists from round 1.
3. Put these questions in the **first** round (they otherwise surface late and force
   rework):
   - **Where and how is the prototype built?** Offer rule zero as "(Recommended)".
   - **Who is the primary user?** (role, expertise, customer tier).
   - **Which real data can the prototype run on?** Ask what the user has. Real data
     often turns a simulated feature into a convincing one; scope also tends to narrow
     late to "only data source X" — ask early.
   - **What is the privacy class of that data?** (public / synthetic / internal /
     customer / personal). Personal or customer data stays local-only, never goes into
     screenshots, external tools, or prompts to external models.

## Phase 1 — Discover: internal first, then the web

Rule: **do not ask the user anything an internal source can answer.**

**Internal sources** — spawn ONE read-only exploration subagent ("very thorough"), in
parallel with the web searches, so file dumps stay out of your context. Brief it with:
goal; directories and repositories to read; what to return (key paths, concrete schema
excerpts, what the product shows today vs what its data holds, gaps); a cap of ~1200
words. Sources to include:
- this repository: existing modes, entities, templates, what the UI exposes vs what the
  stored outputs contain;
- sibling repositories listed in the adapter (legacy UIs to match, related libraries);
- pipeline/job outputs and intermediates on disk; container images of the relevant
  tools (list their files read-only, e.g. `docker run --rm --entrypoint ls <image> <dir>`);
- connected document stores (drive/wiki/notes connectors) — full-text and title search;
- project memory files for the area.

**Web research** — bursts of 2–5 parallel searches. Cover three angles explicitly:
1. **Domain best practice / standards** — guidelines, reporting standards, regulation.
2. **Competitors and reference tools** — commercial products, open-source equivalents.
3. **Optimal UI/interaction patterns** for the task — review flows, evidence display,
   comparison views, usability findings. This angle is the one most often skipped.

Results on UI specifics are often thin: still extract the *principle* and cite it.
Keep a **Sources** list — it goes into the synthesis and the spec. Run a new burst
whenever an answer opens a new area.

## Phase 2 — Synthesise (one message, before asking)

Write one message the user can react to:
- **Need → evidence** table: what users/guidelines require, each with its source.
- **Requirement catalogue**, grouped into areas A, B, C…, each item marked
  ✅ exists in current outputs · 🟡 only in intermediates · ❌ new work.
- Proposed screens/modes, entities, prerequisites, MVP slices.
- The open questions that will drive the first alignment rounds.

## Phase 3 — Alignment rounds (repeat until the user stops)

**Mechanics (question tool):**
- At most **4 questions per call**; 10 questions = 3 calls (4 + 3 + 3).
- 3–4 options per question, labelled "a) …", "b) …"; recommendation first with
  "(Recommended)"; each description states the *consequence* in one line.
- Multi-select for scope/data/technology picks.
- For **layout** questions attach an ASCII mockup preview to each option; free-text
  layout answers are much harder to act on.

**Content rules:**
1. **Expect "Other".** The most design-shaping answers arrive as free text ("a and d
   plus a special flag"). Treat it as the real answer, echo back how you understood
   it, and phrase options so they can be combined.
2. **Architecture / storage / placement questions:** show a pros/cons table *before*
   the options.
3. **Methodology questions early, with warnings.** IF an option has a known statistical,
   scientific, legal or safety problem → say so in its description. Validity problems
   found only after the spec are expensive.
4. **Check facts before asking a question that depends on them.** Do the lookup
   between rounds; never ask "is X available in Y?" when you can check.
5. **Reconcile after every round:** compare new answers with earlier decisions; raise
   any conflict immediately, before the next round.
6. Skip low-value meta questions ("more questions or done?").
7. Where you choose a default yourself, list it under "Defaults I chose (open to
   correction)".

**Decision log** — after every round update `DECISIONS.md`: numbered rows
`# | Area | Decision | Round | Source (user / default / research)`. Supersede rows
explicitly (`~~#12~~ → #31`), never delete. IF marpiech-memory is installed → also add
a short memory entry pointing at the prototype directory so a later session can resume.

## Phase 4 — Spec (when the user says so)

Write `<PROTO_ROOT>/<slug>/SPEC.md` from `templates/SPEC.template.md`. Required
sections: status + rule zero; goal, differentiators, **non-goals**; decisions table
(from DECISIONS.md) + defaults chosen; actors/roles (mocked roles noted); data sources
with privacy class; data contract (doubles as the proposed future API); calculations /
engine / recompute model; screens & routes (in the style of the project's UI library,
see adapter); prototype layout (tree, port, stack); impl-notes index; milestones;
**evaluation gate** (e2e acceptance scenarios, numeric sanity checks, user walkthrough);
risks, open items, sources.

Write one `impl-notes/NN-<topic>.md` per mocked or precomputed piece.

## Phase 5 — Blind review (limited context)

Spawn 1–2 general-purpose subagents that receive **only SPEC.md + impl-notes and a
reviewer persona** — never the conversation or your recommendations (a reviewer handed
your reasoning tends to confirm it). Personas that pay off (`references/review-personas.md`):
*domain methods reviewer*, *primary end user doing the real task*, *security & privacy
reviewer*. Ask for ranked findings with "what breaks, for whom". Never include personal
or customer data in the brief. Fold accepted findings into the spec before Phase 6.

## Phase 6 — Second-opinion review

1. Bundle: `cat SPEC.md impl-notes/*.md > review/spec-bundle.md` (review tools take one
   file).
2. Choose the reviewer:
   - IF the adapter names a review tool (e.g. a second-model plan-review plugin) → use it
     with the bundle as the plan file; follow its own response protocol.
   - ELSE → spawn one fresh general-purpose subagent with the bundle only and the
     instruction "find the 10 most serious problems; for each: evidence, impact, fix".
3. Respond per finding: **ACCEPT** with a concrete spec change, or **DEFER** when it
   would overturn an explicit user decision → present it to the user with options;
   never silently override a user decision.
4. REPEAT a round after substantive spec changes UNTIL a round yields no HIGH findings
   or the user stops it.

## Phase 7 — Prototype (only when the user says "build")

Start from `templates/prototype/` (copy into `<PROTO_ROOT>/<slug>[-vN]/`):
- `restart.sh` starts the app in the background on `$PORT`, killing only the process
  that listens on that port (never `pkill -f <pattern>`: the pattern matches your own
  shell and kills it), and waits until the app answers.
- **Bind `127.0.0.1` only**; generate a one-time access token into `.token`
  (permissions 600) and require it in the URL; the README shows the run, SSH-tunnel
  and cleanup lines.
- Pick a port from the adapter's **port registry** (next free one) and record it there.
- `e2e/`: headless scenarios matching the spec's acceptance list; keep them green.
- Real data where agreed, pseudonymised; no personal data in screenshots.
- Deliverable for review: local URL + a markdown walkthrough with screenshots.

## Phase 8 — Iterate → v-ready

1. Each user review produces vN+1 (new directory, or a tag line in README).
2. Outright rejection is possible ("I don't like any of it") — that is why the spec
   comes before code. On rejection: go back to Phase 3 with the reasons, then Phase 4.
3. WHEN the user declares **v-ready**:
   - write `PORT-PLAN.md` from the impl-notes (what to build where, in what order);
   - hand off: IF no ticket exists → `/marpiech-myplan` with the port plan; IF a ticket
     exists → `/marpiech-resolve <TICKET>`; ELSE plan with the user directly;
   - only now may repository changes, tickets and the normal workflow begin.
4. Run the self-update protocol below.

---

## Rules & guardrails

- No repository changes before v-ready (rule zero). No tickets before v-ready.
- Prototypes bind to localhost only and require a token; never expose them publicly.
- Personal, customer or otherwise sensitive data never leaves the machine: not into web
  searches, external review tools, subagent briefs, screenshots, or the spec.
- Never invent facts in the spec: each external claim has a source; each internal claim
  has a path or was confirmed by the user.
- Never override an explicit user decision because a reviewer disagreed — DEFER it.

---

## Adapting this skill to your project

Adapter: `<project>/.claude/adapters/marpiech-ideate.md` (template:
`templates/adapter.template.md`).

| setting | default | how to choose |
|---------|---------|---------------|
| `prototype-root` | session scratchpad, else `/tmp/scratch` | any directory outside the repository that survives the session |
| `port-registry` | empty | one row per prototype: port, slug, date; start above your dev-stack ports |
| `internal-sources` | this repo + memory | sibling repos (legacy UI, shared libraries), output directories, container images, document-store folders |
| `ui-library` | none | the component library / design system the prototype should imitate, and its key components |
| `prototype-stack` | whatever the product uses | e.g. "same web framework + templates, read-only mount of the component library" |
| `privacy-rules` | personal/customer data local-only | the project's data classes and where each may go |
| `review-tool` | fresh subagent | a second-model plan-review plugin and its command, if the team uses one |

Example for a fictional project:

```markdown
# marpiech-ideate — project adapter (acme-shop)

## Settings
- prototype-root: ~/scratch/acme
- internal-sources: ../acme-legacy-admin (legacy UI to match), ../acme-pricing (library), docs/research/
- ui-library: acme-ui (Button, DataTable, Card, Tag, InfoGrid); prototypes import its CSS read-only
- prototype-stack: FastAPI + Jinja2 + HTMX, server-side SVG charts
- privacy-rules: order data = customer → pseudonymise; never in screenshots or external prompts
- review-tool: /codex-review:plan --plan review/spec-bundle.md

## Port registry
| port | prototype | since |
|------|-----------|-------|
| 8101 | checkout-redesign | 2026-02-01 |

## Learned in this project
- 2026-02-03 — marketing decks in the shared drive hold the persona research; search them in Phase 1
```

---

## CLAUDE.md snippet

```markdown
## Ideation (skill: marpiech-ideate)
- New product area / module / UI with an open design → `/marpiech-ideate` before any code.
- Prototypes live outside the repo; NO repo changes, tickets or migrations until the user
  declares a version "v-ready". Then hand off to /marpiech-myplan or /marpiech-resolve.
```

---

## Self-update log

Generic learnings, newest first. Project-specific learnings go to the project's adapter.
When a learning changes a phase, edit the phase too.

- 2026-11-03 — initial generic version, distilled from three ideation sessions in a
  production product team. What they taught:
  - a v1 built from loose ideas was rejected wholesale; a v2 built from a written spec
    was accepted for review → spec before code;
  - the user imposed the prototype gate mid-way → ask about it in round 1;
  - a methodology the user chose was found invalid only by the post-spec review →
    methodology questions early, with warnings, and a blind methods reviewer;
  - the decision log lived only in memory and was hard to resume → DECISIONS.md from
    round 1;
  - a question depended on a fact nobody had checked → fact-check between rounds;
  - a later answer contradicted an earlier decision → reconcile after every round;
  - UI-pattern research was skipped → it is now an explicit third research angle;
  - one read-only exploration subagent over existing outputs found evidence the product
    never exposed → always run it;
  - a question call with 5 questions failed validation → max 4 per call.
