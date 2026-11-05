# Dashboard and app-screen rules (defaults)

Read in REVIEW (Step R4) and BUILD (Step B3–B6). These are **defaults**: they apply only where the
project's design system is silent. A decision in the design system always wins; when it does, the
review cites the decision, not this file. Each rule has an ID so a finding can cite it ("N3").

The numbers are medians and ranges from a study of real, well-regarded product screens (see the
Self-update log in SKILL.md for the source); treat them as a starting point, not a standard.

## Q — Question and hierarchy

- **Q1 One question.** Every screen answers one question first ("Which samples failed QC today?").
  Write it down before judging the screen. The biggest block carries the answer; the largest figure
  answers the question the title implies.
- **Q2 One finding.** Name the fact in today's data that most needs attention and put it where it
  is read first (the line under the title, or beside the headline figure), next to the action it
  drives. A finding hidden in a caption at the foot of a card makes the screen read flat.
- **Q3 Every block answers a next question.** List the blocks; a block with no question is deleted.
  This is what replaces the stock layout "KPI row, big chart, two small charts, table".
- **Q4 First screen holds the brief.** At about 1440×900 every block the user asked for shows its
  header and its first rows or figure. Cap overview lists at 4–6 rows with "View all".
- **Q5 The frequent job is one click away.** The control for the screen's main job sits where the
  answer shows (title row, the row that needs it). A screen with no control for its job is a report.
- **Q6 Evidence beside the answer.** An annotated event ("dropped after run 2026-05-12, reagent lot
  changed") beats a second chart.

## K — Headline figures

- **K1 No tile per figure by default.** One container split by 1px dividers, or the figure inside
  the card that explains it. No icon in a coloured circle, no sparkline, no tinted tile.
- **K2 Size.** Values 16–40px (typical 24); labels 12–14px, sentence case, secondary ink, above the
  value. Nothing at 48px or over on a working screen.
- **K3 The answer figure leads**, about 1.3× its siblings; no other figure is larger.
- **K4 One figure, one place.** A figure shown in the strip is not repeated in a legend or panel.
- **K5 Deltas name their window** ("vs previous 30 days") and colour means good/bad, not up/down
  (a rising failure rate is bad). Zero or undefined change is grey; from zero write "+4 (new)".

## C — Charts

- **C1 Form follows the question:** over time → one line (area only with a fill ≤15%); per period
  → square-cornered columns; distribution → histogram with equal bins; ranking → sorted horizontal
  bars; share → thin ring or 100% bar, ≤5 parts; to target → progress bar with both ends labelled;
  a few numbers → no chart.
- **C2 One series per chart**, three at most; switch metrics with a control instead of overlaying.
- **C3 Axes.** 3–5 light horizontal gridlines, no y-axis line, a heavier baseline; round even
  ticks with the top tick above the maximum; zero baseline for bars and counts; 4–8 flat x labels
  (never rotated); time on a time scale; never a chart without a scale.
- **C4 Marks.** Straight segments, 1–3px (smoothing invents values between data points); no point
  markers except on hover; bars square or ≤4px top radius.
- **C5 Colour.** One hue per chart, on the main data element; neutrals for the rest; one subject
  keeps one hue across the screen; status colours only for status; more than four hues on a screen
  is a warning, more than six a failure.
- **C6 Legends.** None for one series; otherwise ≤5 items, swatches drawn from the same style as the
  marks (a legend drawn separately drifts from the mark).
- **C7 Annotate what matters.** A spike or step much larger than usual gets a 1px marker and a short
  label naming the cause; thresholds are 1px dashed reference lines labelled at the end. Labels
  never collide with lines or each other.
- **C8 Honest short histories.** Draw zeros and gaps; no padded range; do not give one point the
  screen's largest plot. A forecast after "today" is dashed and its end value labelled.
- **C9 Charts come from the shared chart module** (single source): axis code written per chart drifts.

## N — Numbers and tables

- **N1 Numbers right-aligned in tabular figures**; headers of numeric columns right-aligned and
  flush with their values.
- **N2 Fixed decimals per metric** (one formatter per metric, used everywhere); thousands
  separators; a sign on every change; units as a smaller secondary suffix.
- **N3 Missing ≠ zero.** Missing / not applicable is a small grey dash; a real zero is printed.
  A dash at value size reads as "loading".
- **N4 Identity column gets the most width** (a third to a half) and is never the one cut off;
  shorten editorially before truncating; truncate to one line with an ellipsis, never mid-word —
  except clinical or domain terms, which wrap (see genomics.md).
- **N5 Headers** 12–14px, regular weight, secondary ink, sentence case; no fill band; a sort glyph on
  the active column only.
- **N6 Rows** 36–53px single-line, 56–92px with media; no zebra striping; row rules 1px and 3–7%
  darker than the surface, or none.
- **N7 Ink.** Only the identity and the key number in primary ink; the rest secondary.
- **N8 Status pills** pale tint with dark text of the same hue, 16–24px tall, text ≥11px; one status
  mark per row; chips never squeezed (`flex: none; white-space: nowrap`).
- **N9 Two measures stack in one cell** (count over percentage) instead of two columns.
- **N10 Full lists** state the total, keep the header visible while scrolling, and show the range
  ("1–50 of 1,284"); overviews do not paginate — they cap and link.
- **N11 Every figure shown twice agrees**, and totals are recomputed from the displayed rows
  (single source of data: one query/selector feeds both).

## S — States

- **S1 Empty** keeps the frame and header and adds one sentence (and the first action where data
  will appear). An empty chart draws its zero line, not an illustration.
- **S2 Loading** shows the final layout with flat grey bars at the real sizes; no shimmer, no layout
  shift when data lands. A refresh keeps old values and updates a freshness stamp.
- **S3 Error** sits inside the block that failed: what failed, when data was last good, Retry.
- **S4 Stale or snapshot data** carries a freshness stamp ("Updated 09:14") or a quiet notice.
- **S5 Counts follow the view**: tab and badge counts recomputed for the current filter.
- **S6 Red is a signal, not a texture**: one red mark per object, on the failing fact.

## T — Type

- **T1 One text family** (a second only with one job: code or sequences). Form controls inherit it.
- **T2 App type is not display type**: title 18–32px; 4–9 sizes per screen (typical 6), e.g.
  12/14/16/24; ≤3 weights; 700 does one job.
- **T3 Tabular figures** on every number that is compared or updates — and check the face really has
  them (digit widths must change).
- **T4 Sentence case**, tracking 0; nothing under 11px; line height ~1.4 for 14px text.

## P — Palette and surfaces

- **P1 Semantic tokens only** in components: surfaces, text tiers, borders, status. Primitives
  (hues) live in the token file only.
- **P2 Text tiers reach 4.5:1** on the surface they sit on — placeholders included, in every theme.
- **P3 Accent on data and at most one control**; no accent on chrome (nav pills, tab fills).
- **P4 Borders in three steps** (card edge, row rule lighter, control border darker); a border or a
  shadow, never both; shadows for what floats only.
- **P5 Radius chosen once** — tight (4–8px) or soft (16–24px); nested radii step down; ≤3 panel radii.
- **P6 Dark theme is its own ramp** (true neutrals, lightness steps), not the light theme inverted;
  every colour token has a dark value.
- **P7 Status pairs** (pale background + dark same-hue text) are defined once and reused.

## L — Layout and density

- **L1 One left edge, one right edge** per screen; blocks share edges; no orphan cells or stretched
  cards with blank bands.
- **L2 Density is three settings moved together**: row pitch, padding, type size. Expert screens
  (variant review, QC) can be dense (13px body, 28–42px rows) but keep generous gutters.
- **L3 Placed space reads calm; leftover space reads unfinished** (a column empty in every row, a
  card stretched to its neighbour's height).
- **L4 Spacing on a 4px base**: card gap ~16, card padding 12–32, section gap 24–64, controls 28–40px.
- **L5 Group, don't box**: one card divided by rules beats a grid of tiny cards; cards in cards never.

## M — Phone and narrow widths

- **M1 Navigation folds** (top bar + sheet, or bottom bar); the page never scrolls sideways.
- **M2 Tables become two-line rows below ~640px** (identity + key number, then secondary fields);
  a table that must stay a table scrolls inside its own frame with a frozen first column.
- **M3 Touch targets ≥44px tall** on phones (≥24×24 everywhere, WCAG 2.5.8).
- **M4 One row of controls above a chart**; blocks that carry an action move up.

## F — Forms and controls

- **F1 Label above the field**; no placeholder as label; one control height per context.
- **F2 Disabled controls stay legible and say why.**
- **F3 One filled primary per screen**; secondary outlined; tertiary text.
- **F4 Destructive actions last**, in the negative colour, with the consequence in words and a
  confirmation that names the object.
- **F5 One save model per view** (autosave with a quiet "Saved", or one Save per panel).
