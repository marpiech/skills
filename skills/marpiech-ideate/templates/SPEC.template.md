# <Idea name> — specification

**Status:** draft vN · <YYYY-MM-DD> · prototype `<PROTO_ROOT>/<slug>-vN/`
**Rule zero:** this is a prototype outside the repository. No repository changes, tickets
or migrations until the user declares a version *v-ready*. Every mock has an impl-note.
<!-- Rule one, if needed: e.g. "research use only" banner on every screen. -->

## 1. Goal
- Purpose: <one paragraph — the problem and who has it>
- Differentiators: <what this does that existing tools do not>
- **Non-goals:** <explicitly out of scope>

## 2. Decisions
<!-- Copied from DECISIONS.md (current rows only). -->
| # | Area | Decision | Round | Source |
|---|------|----------|-------|--------|

Defaults I chose (open to correction):
- <default and why>

## 3. Actors & roles
| actor | what they do here | real or mocked |
|-------|-------------------|----------------|

## 4. Data sources
| source | location | privacy class | real / pseudonymised / synthetic |
|--------|----------|---------------|----------------------------------|

## 5. Data contract
<!-- Shapes the prototype consumes; doubles as the proposed future API. -->

## 6. Calculations / engine
<!-- Algorithms, formulas with sources, recompute model (sync/async, caching, gates). -->

## 7. Screens & routes
<!-- One subsection per screen: purpose, route (path segments, not query params), layout
     (ASCII), components from the project's UI library, empty/error states, wording. -->

## 8. Prototype layout
- Directory tree:
- Port: <from the adapter's port registry>
- Stack: <and why, if it differs from the product>
- Access: 127.0.0.1 only, token URL

## 9. Implementation notes index
| # | mock / precomputed piece | impl-note |
|---|--------------------------|-----------|

## 10. Milestones
1. <slice> — <what the user can see after it>

## 11. Evaluation gate
- E2E acceptance scenarios:
  1. <given / when / then>
- Numeric sanity checks: <expected values and tolerances>
- User walkthrough: <the path the user will click through>

## 12. Risks, open items, sources
- Risks:
- Open items:
- Sources: <numbered list of URLs / documents / paths>
