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
- **Q7 One filter scope per screen.** A filter in the page header applies to every block below it;
  a block that ignores it says so ("All time — not filtered"). Active filters are visible as chips
  with one "Clear all"; a filtered view never looks like the unfiltered one.

## K — Headline figures

- **K1 No tile per figure by default.** One container split by 1px dividers, or the figure inside
  the card that explains it. No icon in a coloured circle, no sparkline, no tinted tile.
- **K2 Size.** Values 16–40px (typical 24); labels 12–14px, sentence case, secondary ink, above the
  value. Nothing at 48px or over on a working screen.
- **K3 The answer figure leads**, about 1.3× its siblings; no other figure is larger.
- **K4 One figure, one place.** A figure shown in the strip is not repeated in a legend or panel.
- **K5 Deltas name their window** ("vs previous 30 days") and colour means good/bad, not up/down
  (a rising failure rate is bad). Zero or undefined change is grey; from zero write "+4 (new)".
- **K6 Every figure has its definition one step away**: a hover or info affordance that says what
  is counted, over which window, from which source. Two screens that use the same label count the
  same thing (single source: one metric definition, one query).

## C — Charts

- **C1 Form follows the question:** over time → one line (area only with a fill ≤15%); per period
  → square-cornered columns; distribution → histogram with equal bins; ranking → sorted horizontal
  bars; share → thin ring or 100% bar, ≤5 parts; to target → progress bar with both ends labelled;
  a few numbers → no chart. Size limits: fewer than 4 points → print the numbers; more than ~15
  categories → a table or top-N plus "Other"; bars sorted by value unless the axis is ordered
  (time, stage, size class).
- **C2 One series per chart**, three at most; switch metrics with a control instead of overlaying.
  Grouped or stacked charts: at most 5 values per dimension; group the rest into "Other".
- **C3 Axes.** 3–5 light horizontal gridlines, no y-axis line, a heavier baseline; round even
  ticks with the top tick above the maximum; zero baseline for bars and counts; 4–8 flat x labels
  (never rotated); time on a time scale; never a chart without a scale. No second y-axis: two
  measures on different scales get two charts sharing the x-axis (a dual axis invites false
  correlations). Small multiples and sparklines in one row share one y-scale, or say they do not.
- **C4 Marks.** Straight segments, 1–3px (smoothing invents values between data points); no point
  markers except on hover; bars square or ≤4px top radius.
- **C5 Colour.** One hue per chart, on the main data element; neutrals for the rest; one subject
  keeps one hue across the screen; status colours only for status; more than four hues on a screen
  is a warning, more than six a failure.
- **C6 Legends.** None for one series; prefer direct labels at the line end; otherwise ≤5 items,
  swatches drawn from the same style as the marks (a legend drawn separately drifts from the mark),
  in the same position on every chart of the screen. With two or three series also vary line
  style or marker so the chart still reads in greyscale. Clickable legend items toggle their
  series, and the last visible series cannot be hidden.
- **C7 Annotate what matters.** A spike or step much larger than usual gets a 1px marker and a short
  label naming the cause; thresholds are 1px dashed reference lines labelled at the end. Labels
  never collide with lines or each other.
- **C8 Honest short histories.** Draw zeros and gaps; no padded range; do not give one point the
  screen's largest plot. A forecast after "today" is dashed and its end value labelled. Missing
  periods are a break in the line (or a dashed grey bridge with no point), never interpolated.
- **C9 Charts come from the shared chart module** (single source): axis code written per chart drifts.
- **C10 The title states the finding** ("Failed runs doubled after 12 May"), the subtitle states
  the measure, unit and window ("Failed runs per day, last 30 days, UTC"). A label-only title
  ("Runs") makes every reader find the point alone.
- **C11 Every chart has a text equivalent**: an accessible name (`role="img"` + `aria-label`, or
  a `<figcaption>`) that gives the finding with the high, low and latest values, and a way to see
  the numbers as a table ("View as table" or the table beside it). ⚙ probe CHART-A11Y
- **C12 Render for the data size**: SVG up to ~1,000 marks, canvas above that, aggregate (bin,
  sample, roll up) above ~10,000 — a chart that stalls the page is a broken chart.
- **C13 Time is unambiguous**: time axes and stamps name the time zone when users or instruments
  span zones (UTC for lab and pipeline events unless the design system says otherwise); relative
  stamps ("3 h ago") have the absolute time on hover.

## N — Numbers and tables

- **N1 Numbers right-aligned in tabular figures**; headers of numeric columns right-aligned and
  flush with their values.
- **N2 Fixed decimals per metric** (one formatter per metric, used everywhere); thousands
  separators; a sign on every change; units as a smaller secondary suffix joined by a
  non-breaking space so "12 GB" never wraps. Money uses 0 or 2 decimals within one context, never
  a mix.
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
  shift when data lands. A refresh keeps old values and updates a freshness stamp. Loaders wait
  ~150–300 ms before appearing and, once shown, stay ~300–500 ms, so fast responses do not flash.
- **S3 Error** sits inside the block that failed: what failed, when data was last good, Retry.
- **S4 Stale or snapshot data** carries a freshness stamp ("Updated 09:14") or a quiet notice. The
  stamp gives the time of the data, not of the fetch. Auto-refresh no faster than the data
  changes (a daily metric does not poll every 10 s).
- **S5 Counts follow the view**: tab and badge counts recomputed for the current filter.
- **S6 Red is a signal, not a texture**: one red mark per object, on the failing fact.
- **S7 Motion means "live"**: at most two pulsing or animated indicators per screen, only on data
  that is truly real-time; none on data that polls or refreshes on load. Everything that moves
  stops under `prefers-reduced-motion`. ⚙ probe MOTION
- **S8 View state lives in the URL** (single source of view state): filters, tab, sort, page,
  expanded row and selected range survive reload, sharing and Back/Forward.

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
- **P8 Chart palettes are tokens too**: one categorical scale used in a fixed order (series 1 is
  always the same hue), one sequential and one diverging scale. Sequential: the largest value is
  the strongest step — darkest on light, lightest on dark; never a rainbow, never a gradient in
  place of steps. Grey is reserved for "Other" and "No data"; the brand accent is not one of the
  categorical colours in multi-series charts (it would read as "most important").
- **P9 Colour is never the only code**, and palettes survive colour-vision deficiency: adjacent
  categorical colours differ in lightness, not only hue; good/bad uses blue/orange or red with a
  shape or label, not red/green alone; status also carries a word or icon.
- **P10 Dark charts are re-tuned, not inverted**: each chart colour has a dark value chosen for
  the dark surface (contrast ≥3:1 for marks), and the dark theme declares `color-scheme: dark`
  so scrollbars and native controls follow. ⚙ probe COLOR-SCHEME

## L — Layout and density

- **L1 One left edge, one right edge** per screen; blocks share edges; no orphan cells or stretched
  cards with blank bands.
- **L2 Density is three settings moved together**: row pitch, padding, type size. Expert screens
  (variant review, QC) can be dense (13px body, 28–42px rows) but keep generous gutters. One
  density tier per screen (compact ~32–40px rows, standard ~44–48px, comfortable ~56–64px);
  tables of different tiers side by side read as two products. ⚙ probe ROW-DENSITY
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
