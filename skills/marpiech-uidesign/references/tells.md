# Tells of a generated (template) dashboard

Read in REVIEW Step R4. A tell is a device that marks a screen as assembled from defaults rather than
designed for its data. None is wrong in itself; each is a sign that no decision was made. The
project's design system may adopt any of them on purpose — then it is a decision (cite it), not a tell.
The probe (`scripts/probe.js`) and `uidesign.py lint` detect the ones marked ⚙.

| Tell | Instead |
|---|---|
| A greeting with an emoji ("Welcome back, Alex 👋") as the title ⚙ | A noun title naming the screen, 18–32px |
| Four KPI cards, each with an icon in a tinted circle | One container divided by rules; label over value |
| A green "+12.5%" pill on every KPI; a sparkline on every KPI | A delta only where it informs, with its window; grey for zero |
| KPI values at 36–48px, bold, in the brand colour ⚙ (title size) | 24–30px in primary ink |
| Gradient area chart, smoothed curve, a dot on every point ⚙ (gradient) | A straight 2px line, no or faint fill, no markers |
| A rainbow: a hue per bar or per chart ⚙ | One hue per chart, status colours for status |
| Dense gridlines, axis lines on both sides, a legend for one series | 3–5 faint lines, no y-axis line, no single-series legend |
| A fat donut with labels on slices | A thin ring, or a sorted bar list with values |
| Large radius + 1px border + large soft shadow on every card ⚙ | A border or a tone step; one radius family |
| Zebra rows under uppercase tracked headers ⚙ | Sentence-case grey headers; rules or spacing |
| Left-aligned numbers in proportional digits ⚙ | Right-aligned tabular figures, fixed decimals per metric |
| Saturated status chips with white text | Pale tint with dark text of the same hue |
| The accent on every button, tab and link | Accent on data and one primary action |
| A dark or saturated sidebar with a coloured active pill and left bar | Sidebar on the page ground; a neutral active state |
| A top bar with search, bell and avatar whatever the screen needs | Only controls the screen uses |
| Export / Share / date picker clustered by the title by habit | Actions that are real; a freshness stamp |
| Placeholder people, round vanity totals ("10,000+"), sums that do not add up ⚙ (placeholders) | Real or clearly synthetic data; totals computed from the rows |
| Pagination under a five-row overview | Capped rows, "View all", the total |
| An equal four-up grid whatever the data, orphan cells, stretched cards | Column count chosen by item count; shared edges |
| Neon on dark, glowing borders, glass, backdrop blur ⚙ (gradient/shadow) | True neutral darks, lightness steps, colour on data |
| An illustration plus "No data yet" in an empty chart | The zero line drawn and one sentence in the frame |
| Monospace as a "technical" costume for IDs and labels ⚙ | Text face with tabular figures; mono for code/sequences |

**Removal is not enough.** A screen with every tell removed and nothing in their place is a tidy
template. What fills the space is the product: its own data at real size, the screen's one question
answered by its biggest block, and figures whose sums close.
