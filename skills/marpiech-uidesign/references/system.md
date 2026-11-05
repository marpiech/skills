# One source of truth — how a design system is kept single

Read in SYSTEM mode, in Step 2 (precedence), and whenever a review finding says "second source".

## 1. One home per kind of fact

| Fact | Its one home | Everything else |
|---|---|---|
| A value (colour, size, radius, shadow, font, spacing, z-index, duration) | the **token file(s)** | references it with `var(--…)` / the token import |
| How an element looks and behaves | the **component** in the library (macro, component, custom element) | calls the component; never re-creates its markup or CSS |
| What a component accepts | the component's **catalogue entry** (COMPONENTS.md, stories, docstring) | links to it; never copies its API |
| How it looks in every variant and state | the **gallery / stories** rendered from the real component | — |
| Why it is that way, and what was rejected | the **decision log** of the design system | adapters and CLAUDE.md link to it, never restate it |
| How a number, date, frequency or identifier is formatted | the **formatter** (filter, helper) | templates call it; no inline `strftime`, `toFixed`, f-strings |
| A figure shown on a screen | **one query / selector** | every place that shows the figure reads that one result |
| The current view (filters, sort, page) | **one state** (usually the URL) | counts, badges and exports derive from it |

The skill's own rules (references/*.md) are defaults that fill gaps; they never become a second copy
of the project's rules. The adapter holds pointers and project-specific facts, not design content.

## 2. Precedence when sources disagree

1. What the user decides now (then record it — step 4).
2. The design system's decision log.
3. The design system's tokens and components as built (the code is the truth of what *is*; the log
   is the truth of what was *decided* — if they disagree, that is a finding, not a choice to make
   silently).
4. The project adapter's house overrides.
5. This skill's defaults (dashboards.md, genomics.md, tells.md).

Never resolve a conflict by tuning one page. Either the page converges on the system, or the user
decides the system should change — and then it changes in its one home, for every page.

## 3. Token tiers

- **Primitive** (palette) tokens name a value: `--blue-600`, `--grey-100`. They live in the token
  file and are referenced only by semantic tokens.
- **Semantic** tokens name a role: `--surface`, `--surface-alt`, `--text-primary`, `--text-muted`,
  `--border`, `--positive`, `--negative`, `--status-vus-bg`. Components use only these. Each theme
  (light, dark, high-contrast) re-points the semantic tokens; components never branch on the theme.
- **Component** tokens (optional) are scoped inside a component (`.chip { --chip-pad: 4px }`) and never
  reuse a global token's name.

Consequences the checker enforces: a token used but defined nowhere (its fallback silently wins in
every theme); a global token defined outside the token files or in several files; a global token
redefined inside a component; a literal colour token with no dark value; primitives used by
components; literal colours, fonts and shadows outside the token files.

## 4. Changing the system (the order of work)

1. **Search first**: `uidesign.py components` and the catalogue. A new component or token needs a
   reason no existing one covers.
2. **Define once** at the right tier; add the dark value at the same time.
3. **Document once**: catalogue entry + gallery/story with every variant and state.
4. **Record the decision** in the design system's decision log (template below): rule, why,
   rejected alternatives, date, ticket.
5. **Migrate callers** in the same change, or file the migration; remove the old path — no alias
   left "for compatibility" without an end date.
6. **Re-run** `tokens`, `lint`, `components` and the probe on a screen that uses it.

A visual bug in a shared component is fixed in the component, once — never patched on the page
where it was reported.

## 5. Decision log entry (in the design system, not in this skill)

```markdown
### D<n> — <rule in one line> (<ticket>, <YYYY-MM-DD>)
<The rule, precisely enough to check.>
**Why:** <the problem it solved; who decided; evidence>
**Rejected:** <alternatives and why>
**Enforced by:** <check id / test / lint rule, or "review only">
```

Append; never silently rewrite. Correct a wrong entry in place with a dated note rather than adding a
contradicting one.

## 6. Signs the single source is breaking (and the check that finds it)

| Sign | Check |
|---|---|
| "Looks different than on page X" | `components` (DUPLICATE/SHADOW), `lint` RAW-ELEMENT, probe CONTROL-FONT |
| Light colours leaking into dark mode | `tokens` UNDEFINED (fallback wins) and THEME-GAP |
| A colour tweak "didn't apply everywhere" | `tokens` MULTI-SOURCE / OUTSIDE-SOURCE, `lint` RAW-COLOR |
| Two date or number formats for one metric | `lint` INLINE-FORMAT |
| A KPI disagrees with the table below it | review look 6 (two queries for one figure) |
| Badge counts that ignore the filter | review look 6 / S5 (counts not derived from the view state) |
