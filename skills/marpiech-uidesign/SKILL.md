---
name: marpiech-uidesign
description: Check whether a UI is designed well — dashboards, data-dense app screens, and the component library and CSS tokens they are built from — against the project's own design system as the single source of truth, with researched dashboard rules (hierarchy, headline figures, charts, tables and number formatting, empty/loading/error states, type, colour, density, phone) and optional genomic/clinical data rules filling only the gaps the system leaves. Runs read-only static checks (tokens used but undefined, tokens defined in a second place, literal colours/fonts outside the token files, page-local styles, copied or shadowed components, inline formatting, contrast of token pairs per theme), a rendered probe in a real browser at several widths and themes, and a written look at the screenshots; scores five dimensions, ranks findings P0–P3, and names for every fix the one place it must be made. Also builds new screens and components from the library, maintains tokens/components/decision log, and debugs "looks different than on page X". Use when the user says "/marpiech-uidesign", "is our design ok?", "review / check the design", "review this dashboard / screen / component", "check the UI", "design audit", "does this follow the design system?", "make this dashboard look designed", "it looks generic / AI-made", "inconsistent", "looks different than on page X", "not aligned", "cut off", "add a component / token", or before merging a change that touches templates, components or CSS.
---

# marpiech-uidesign — one design, checked against its one source

## Purpose

A product's screens drift: a page gets its own colour, a component is copied and tweaked, a
number is formatted inline, a figure is computed twice and the copies disagree. Each drift is small;
together they make the product look assembled and make data harder to trust. Generated UI adds its
own drift — the template look (tinted icon tiles, gradient charts, rainbow palettes, uppercase
headers). This skill answers **"is our design ok?"** by checking screens and the component library
against the project's **design system as the single source of truth** — tokens, components,
formatters, decisions — and, where the system is silent, against researched defaults for dashboards
and data-dense screens (and genomic data when relevant). Outcome: a scored, ranked review with
evidence, where every fix names the one place to change; plus, on request, screens and components
built or repaired the same way.

`<SKILL_DIR>` = the directory holding this SKILL.md; `<UI>` =
`python3 <SKILL_DIR>/scripts/uidesign.py` (stdlib + git; read-only). `<SKILL_DIR>/scripts/probe.js`
runs inside a browser page (no dependencies, no network) and returns JSON.

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

1. Look for `.claude/adapters/marpiech-uidesign.md` and the checker config
   `.claude/uidesign.json` in the repository root.
2. IF present → read: where the sources of truth are (token files, theme selectors, component
   library, catalogue, gallery, formatters, decision log), the domain (`genomics` or not), house
   overrides of the skill defaults, accepted exceptions, how to render screens (dev URL variable,
   login through the secrets tool, widths, theme switch), and project learnings.
3. ELSE → run `<UI> sources`; it lists token files, dark-theme selectors, component directories,
   catalogues, galleries, formatter modules and decision logs, and prints a suggested
   `.claude/uidesign.json`. Show the user the draft config and adapter
   (`templates/adapter.template.md`, `templates/uidesign.template.json`) and ask only what the repo
   cannot answer (usually: which file is the decision log, and which deviations are deliberate).
4. IF /marpiech-memory is installed → READ: earlier design decisions and rejected options are
   prime memory material.

---

## Algorithm

### Step 2 — Establish the source of truth (every mode)

1. Open the design system's own documents, in this order: decision log → token files →
   component catalogue → gallery or stories. Note each decision's ID; reviews cite them.
2. Precedence when anything disagrees (references/system.md §2): the user's decision now →
   the decision log → tokens and components as built → adapter overrides → this skill's defaults.
3. IF the decision log and the built system disagree → that is a finding (P1, "the system
   contradicts its own decision"), not something to resolve silently.
4. IF the project has no design system at all (no tokens, no shared components) → say so first;
   the review still runs, and its top recommendation is to create the single sources
   (SYSTEM mode) before polishing pages.

### Step 3 — Pick the mode

```
"is our design ok?", "review/check the design/screen/dashboard/component",
 a UI change before merge, "looks generic / AI-made"                    → REVIEW (R)
"build/design a new screen or dashboard", "make this look designed"    → BUILD  (B)
"add a component / token", "clean up the tokens", "design system"      → SYSTEM (S)
"looks different than on page X", "cut off", "not aligned", CSS bug     → DEBUG  (D)
```

### REVIEW

**R1 — Scope.** A diff (`--diff <base>`, the merge-base with the main branch), paths, named screens
(URLs), or the whole UI. For each screen write its **one question** and **one finding** (Q1–Q2 in
references/dashboards.md) before looking at details — they are the yardstick.

**R2 — Static checks** (cheap, run all four):
1. `<UI> tokens` — UNDEFINED and OUTSIDE-SOURCE are errors (a fallback is silently winning; a token
   has a second home); MULTI-SOURCE, LOCAL-REDEFINE, THEME-GAP are warnings; UNUSED is information.
2. `<UI> lint [paths] [--diff <base>]` — literal colours/fonts/shadows outside the token files,
   primitives used by components, page-local `<style>`, visual inline styles, inline formatting,
   placeholders, raw elements where the library has a component. In diff scope only NEW hits are
   held against the change.
3. `<UI> components` — DUPLICATE (one component defined twice), SHADOW (a same-path copy a template
   loader may pick instead of the library), DEPRECATED usage, usage counts.
4. `<UI> contrast` — text/surface token pairs per theme; pin the real pairs in `contrast_pairs` so
   impossible pairs do not drown the real ones.

**R3 — Render check** (references/render-check.md): every screen at 1440 / 768 / 390 × every
theme; full-page screenshots plus `probe.js` results; `<UI> report <dir>/*.json`. IF no browser
automation is available → ask the user to run the probe in DevTools, or continue statically and
state in the report that the render check did not run.

**R4 — Look** (references/review.md §1): Read every screenshot and answer the ten passes in writing,
per screen. Check against, in order: the design system's decisions → references/dashboards.md →
references/genomics.md (IF the domain applies) → references/tells.md.

**R5 — Triage every hit and observation:**
- *violates the design system* (cite the decision/token/component) — strongest;
- *violates a default rule* (cite its ID) — only where the system is silent;
- *false positive* — narrow the check in `.claude/uidesign.json` (`allow`, `severity`) and say why;
- *accepted exception* — already recorded in the decision log or adapter; list, do not re-litigate.
Absence claims ("defined nowhere", "used nowhere") from the scripts are spot-checked with a grep
before being reported.

**R6 — Score and rank** (review.md §2–3): five dimensions 0–4, caps applied, findings P0–P3.

**R7 — Report** (review.md §4). Every finding names **the single place the fix belongs** (a token,
a component, a formatter, a query, a decision) — never "adjust this page's CSS" when the cause is
shared. Top findings first; at most about ten.

**R8 — Fix only when asked.** Then fix at the source in the order of review.md §5, re-run R2–R4,
at most three rounds. Pre-existing problems outside a diff scope become separate work
(IF /marpiech-tickets is installed → offer to file them).

### BUILD

**B1 — Inventory** the data (every field, its type, its states: present / zero / missing / error /
stale) and the jobs the user does on the screen.
**B2 — Name** the one question, the one finding, and the most frequent job (Q1, Q2, Q5).
**B3 — List the blocks** as answers to the next questions (Q3); delete any block without one.
**B4 — Reuse first:** `<UI> components` and the catalogue — compose from existing components and
tokens. A missing piece goes through SYSTEM mode (defined once, documented, decided), not into the
page.
**B5 — Build** the shell, then the data with real or clearly synthetic sample values, through the
shared formatters (one formatter per metric) and one data source per figure (N11).
**B6 — Build every state** (S1–S6): empty, zero, loading, error, stale, phone.
**B7 — Review it:** run REVIEW R2–R7 on what you built; fix and repeat, three rounds at most.
Report the screen's question, the components used, anything added to the system, and the sample
data that must be replaced.

### SYSTEM

Follow references/system.md §4: search first → define once at the right tier (with its dark value)
→ catalogue + gallery entry → decision log entry → migrate callers in the same change (no
compatibility alias without an end date) → re-run `tokens`, `lint`, `components`, and the probe on a
screen that uses it. For a token clean-up: fix UNDEFINED first (silent fallbacks), then
OUTSIDE-SOURCE / MULTI-SOURCE (move to the token file), then primitives in components (introduce
or reuse a semantic token), then THEME-GAP.

### DEBUG

Follow references/css-traps.md: measure computed styles of the two elements that "look different",
find the winning rule, fix it at the single source, verify at every width and theme, and append the
trap (generic → this skill's log; project-specific → the adapter).

### Step 9 — Record what was learned (every mode)

1. **Design decisions** made or confirmed in this session (a component choice, a variant
   convention, a rejected design) → the **design system's decision log** — its one home — in the
   same change as the code (format in references/system.md §5). Not into the adapter, not into
   CLAUDE.md (they link to the log).
2. **Checker tuning** (exceptions, severities, contrast pairs, raw-element patterns) →
   `.claude/uidesign.json`, with the reason in the adapter's change log.
3. **Project mechanics** (render commands, URLs as variable names, theme switch, flaky login
   recipe) → the adapter.
4. **Generic lessons** (true for any project) → this skill's Self-update log, folded into the
   references when they change a rule.

---

## Rules & guardrails

- **The design system is the authority.** The skill's defaults never override a recorded decision;
  a page never gets its own look; a shared bug is fixed in the shared source.
- **One home per fact** — values in tokens, looks in components, formats in formatters, figures in
  one query, decisions in the decision log. Never copy design-system content into the adapter, a
  skill, or CLAUDE.md; link to it.
- Read-only by default: REVIEW changes nothing unless the user asks for fixes.
- Judge the render, not the code; never report a script hit without reading it in context.
- Never print or store credentials for logging in to a screen; take them from environment variables
  injected by the project's secrets tool. Screenshots stay out of the repository and out of public
  places, and never show personal or patient data — use synthetic samples.
- Never install packages or browsers on your own; use what the project has, or say the render check
  did not run.
- Top findings first; a long tail of P3s buries what matters.

---

## Adapting this skill to your project

Adapter: `<project>/.claude/adapters/marpiech-uidesign.md` (template:
`templates/adapter.template.md`). Checker config: `<project>/.claude/uidesign.json` (template:
`templates/uidesign.template.json`; `<UI> sources` prints a filled draft).

| setting | default | how to discover |
|---------|---------|-----------------|
| token files | files defining ≥8 theme-level custom properties | `<UI> sources` |
| dark-theme selectors | any selector or media query containing "dark" | `<UI> sources` |
| primitive (palette) tokens | names that are hue words (`--blue-500`, `--slate`) | token file sections |
| component library dirs | directories with the most component definitions | `<UI> sources` |
| catalogue / gallery | COMPONENTS.md, DESIGN.md, stories, a gallery app | `<UI> sources` |
| decision log | markdown with a "decision" heading | `<UI> sources`; ask |
| formatter modules | filter registrations, `Intl.NumberFormat`, `format_*` helpers | `<UI> sources` |
| raw elements to flag | none | library components that wrap a native element (`button`, `table`) |
| domain rules | off | `genomics` when screens show variants, samples, QC, PGx |
| render widths / themes | 1440, 768, 390 × light, dark | the app's breakpoints and theme switch |
| render access | none | dev/staging URL **variable names**, login via the secrets tool |
| house overrides | none | decisions that replace a default (e.g. "no monospace anywhere") |

Example for a fictional project:

```markdown
# marpiech-uidesign — project adapter (acme-shop)

## Sources of truth (link, never copy)
- tokens: libs/ui/static/tokens.css (light :root, dark [data-theme="dark"])
- components: libs/ui/templates/components/ — catalogue libs/ui/COMPONENTS.md, gallery app `gallery/`
- formatters: libs/ui/filters.py (format_money, format_date, format_count)
- decisions: docs/design-system.md → "Decision log" (D1…)

## Domain
- none (retail); genomics rules off

## House overrides of skill defaults
- headline figures sit in tiles (D4); K1 does not apply
- one filled primary per screen is the brand green, not near-black (D2)

## Render
- URL: $ACME_DEV_URL; login with $ACME_E2E_USER / $ACME_E2E_PASSWORD via `<secrets tool> run --`
- theme: set `data-theme` on <html>; widths 1440, 768, 390

## Change log (newest first)
- 2026-03-02 — GRADIENT allowed in libs/ui/static/charts.css (area fill under the revenue line, D7)
- 2026-02-11 — contrast_pairs pinned to the 9 pairs the components use
```

---

## CLAUDE.md snippet

```markdown
## UI design (skill: marpiech-uidesign)
- Sources of truth: tokens, components, formatters and the decision log named in
  .claude/adapters/marpiech-uidesign.md. Pages never get their own look; shared bugs are fixed
  in the shared component; new decisions go to the decision log in the same change.
- Before merging a change that touches templates, components or CSS: `/marpiech-uidesign` review
  on the diff (static checks + render check) — fix what the change introduced.
- "Looks different than on page X", "cut off", "inconsistent": `/marpiech-uidesign` debug mode.
```

---

## Self-update log

Generic learnings, newest first. Project-specific learnings go to the project's adapter; design
decisions go to the project's design-system decision log.

- 2026-11-05 — initial generic version. Review rules distilled (rewritten, not copied) from
  taste-skill v2.1's study of real app screens (Leonxlnx/taste-skill, MIT) and the Operate-mode /
  audit structure of Impeccable (pbakaus/impeccable, Apache-2.0); single-source-of-truth method and
  traps from a production monorepo's UI rulebook and debugging notes. Lessons carried over: most
  "minor UI bugs" are one component rendered two ways (a raw element beside the component, an
  `<a>` vs a `<button>`, a page-local style) — the fix is always to converge on the shared part;
  an undefined token with a literal fallback leaks light colours into dark mode and is invisible in
  review of the template; form controls not inheriting the font make identical buttons differ;
  numbers must be right-aligned tabular figures with one formatter per metric; missing and zero
  must look different (in genomic data: not-tested / not-covered / no-call / reference); a review
  is judged on screenshots, and a clean probe only proves nothing banned was measured.
