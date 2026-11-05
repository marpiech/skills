# Review rubric — "is our design ok?"

Read in REVIEW Steps R4–R7. Judge from **screenshots and probe results, not from the code**: the
code shows intentions, the render shows what is there.

## 1. The look (answer each in writing, per screen)

Open every screenshot (each width, each theme). Make each pass on its own.

1. **One second.** Glance and look away: what did you see? There should be one answer — the
   screen's question (Q1). If the answer is "a dashboard", nothing leads.
2. **Squint.** Text becomes grey bars: two or three masses with clear size differences, the largest
   carrying the answer. Many similar masses = everything medium.
3. **Cover the name.** Could this be any product's screen? If yes, the data is not leading (Q1–Q3).
4. **Edges.** Count the distinct left edges of text blocks; a composed screen reuses two or three
   (L1). Cards in one row end on one line.
5. **Colour.** Where is the accent? On data and one action (P3, C5)? Status colours only for status?
6. **Numbers.** Do they line up digit for digit (N1)? Does every figure shown twice agree, and do
   totals recompute from the displayed rows (N11)? Is every relative figure against something named?
7. **Zero and missing.** Does every zero look like a zero and every missing value like a dash
   (N3)? In genomic screens: are not-tested / not-covered / no-call / reference distinct (G9)?
8. **States.** Empty, loading, error, stale — seen or simulated (S1–S4)?
9. **Phone.** Navigation folded, no sideways scroll, tables as two-line rows (M1–M2)?
10. **System fidelity (single source of truth).** Does every element on the screen come from the
    component library, in the variant its role demands? Would the same element on another screen
    look identical? Any local look (page style, inline style, raw element, copied component)?

## 2. Score (five dimensions, 0–4 each, /20)

| Dimension | 4 | 2 | 0 |
|---|---|---|---|
| **Question & hierarchy** | the answer is the biggest, first-read thing; the finding is beside its action | answer present but not leading | no discernible question |
| **Data integrity** | figures agree, sums close, formats fixed per metric, zero/missing distinct, provenance shown | minor format drift | numbers contradict each other or states are confusable |
| **System fidelity** | every value from a token, every element from the library, no local looks; static checks clean | some literals / page styles | the screen has its own look |
| **Legibility & access** | contrast ≥4.5:1 in every theme, nothing <11px, targets ≥24px, keyboard focus visible | isolated failures | systematic failures |
| **Restraint** | no tells; accent on data; one radius family | a few tells | template look |

Bands: 18–20 ship · 14–17 fix the weak dimension · 10–13 significant work · <10 rework.

**Caps (override the arithmetic):**
- Any probe or lint **FAIL/error** left unexplained → total ≤ 13.
- A figure that contradicts another, or a missing/no-call state that renders like a normal result →
  Data integrity = 0 and total ≤ 9 (this is a correctness bug, not a design note).
- Tokens UNDEFINED or OUTSIDE-SOURCE in the reviewed scope → System fidelity ≤ 2.
- A duplicated or shadowed component in scope → System fidelity ≤ 2.
- Page scrolls sideways on the phone → Legibility ≤ 2.

Calibrate: score your own work as a reviewer who did not build it; an honest 18 is rare.

## 3. Severity of each finding

- **P0** — wrong or unsafe information (contradicting figures, a no-call shown as normal, a status
  colour that says the opposite). Blocks release.
- **P1** — WCAG AA failure, broken state, a second source of truth (token outside the source, copied
  component, local look on a shared element). Fix before release.
- **P2** — drift from the design system or a default rule, with a workaround.
- **P3** — polish. Keep P3s few: a long tail buries what matters.

## 4. Report shape (keep rounds comparable)

```
## UI review — <scope> — <date> — round n
Screens: <name — its one question — its one finding>
Sources of truth: tokens <files> · components <dirs> · decisions <log>
Score: question _ · data _ · fidelity _ · legibility _ · restraint _ → _/20  (caps: …)

### Findings (P0 first; max ~10)
- [P1] <what is wrong, as a designer would say it> — <file:line or screen@width/theme> —
  rule <DS decision id | Q/K/C/N/S/T/P/L/M/F/G id> — fix at <the single source to change>
- …

### Fixed at the source vs on the page
<every fix names the ONE place it is made: token, component, formatter, decision>

### Static checks
tokens: … · lint: … (NEW in diff: …) · components: … · contrast: …

### Accepted exceptions (recorded where)
### Decisions to record
<new decisions for the design system's decision log>
```

Name problems precisely ("the AF column is left-aligned in proportional digits",
"the Orders header uses a plain button where every other header uses the header-action component"), never
"could be more polished".

## 5. Fix order and rounds

Fix in this order; later items cannot rescue earlier ones: correctness of data (P0) → second sources
of truth (move to the source) → hierarchy → layout edges → type → colour → detail and states.
At most three rounds of fix → re-check → re-look; stop when a round finds nothing a stranger would
notice. If round three still scores under 14, say so with the remaining findings; do not round up.
