# CSS and template traps (DEBUG mode)

Read in DEBUG mode, and in REVIEW when two "identical" elements render differently. Each trap cost a
real review round somewhere. Project-specific traps go to the adapter; generic ones are appended here
through the Self-update log.

## Method first

1. **Measure, don't guess.** In the browser: `getComputedStyle(el)` for both elements (font-family,
   font-size, weight, line-height, padding, color, background) and `el.getBoundingClientRect()`.
   The difference is usually invisible in the template.
2. **Find the winning rule** (DevTools "Computed → rule" or by bisecting classes), then fix it at
   the single source (system.md §4), not with a more specific override on the page.
3. **Verify by looking** at the rendered result at every width and theme the project ships.

## Cascade and inheritance

- **Form controls do not inherit the page font.** `button, input, select, textarea` use the browser's
  own face unless the base styles set `font: inherit` (or `font-family: inherit`). Symptom: the same
  `.btn` looks different as `<a>` and as `<button>`.
- **An undefined custom property with a fallback** (`var(--error-bg, #fff5f5)`) always uses the
  fallback — in every theme. Symptom: light colours in dark mode. Fix the token name; delete the
  literal fallback.
- **A token defined only for light** inherits its light value in dark mode. Every colour token needs
  a value per theme.
- **`!important` on a utility** beats component styles and every later fix; remove it at the source.
- **Utility classes from another framework** (`.text-xs` with no rule behind it) silently do nothing.
  Grep for the class definition before trusting it.

## Layout

- **Column widths go on the header cell** (`th`) in auto table layout; widths on `td` are ignored when
  the header disagrees. A global `th:first-child { width: … }` affects every table.
- **Flex items cannot be line-clamped** (`-webkit-line-clamp` needs a block); cap chips by count or by
  container height instead.
- **Chips and pills inside cells** need `flex: none; white-space: nowrap`, or a narrow column squeezes
  them into a box with the word spilling out.
- **Ellipsis needs three properties** on the element that holds the text: `overflow: hidden;
  white-space: nowrap; text-overflow: ellipsis` — and a block or inline-block box with a width.
- **`position: sticky` taller than its scroll container** slides away by the overhang; size it to the
  scrollport (`calc(100vh - <fixed chrome>)`), and remove trailing margins that add phantom scroll.
- **A grid row stretched to its neighbour** leaves a blank band in the shorter card; use
  `align-items: start` or a layout where the short cards stack beside the tall one.

## Templates and frameworks

- **Macro attributes must be escaped by the template engine.** Building attribute strings and
  marking them safe lets an apostrophe in data break out of the attribute.
- **An unknown variant falls back silently** in many component maps (often to the loudest variant).
  Check the variant list in the catalogue when a "ghost" button renders as primary.
- **Jinja**: macros imported with `{% from … import a %}` do not bring sibling macros that `a` calls —
  import them too; `d.values` resolves to the dict method, use `d["values"]` for colliding keys;
  custom filters are registered per application — a missing filter is an app-setup issue.
- **Same-path template overrides**: with a loader that searches the app's templates before the shared
  library, a file at the same relative path silently replaces the library's component everywhere in
  that app (`uidesign.py components` reports these as SHADOW).
- **Reactive `:style` bindings**: a string binding replaces the whole `style` attribute; an object
  binding merges with the static style.

## htmx (and other partial-swap libraries)

- **Events bubble.** A container listening for `htmx:beforeRequest` also hears every request from
  inside it (search pickers, name checks). Scope by `evt.detail.elt === this` or by target.
- **`htmx:beforeSwap` fires on the target**, not on the requesting element; bind on `document.body`
  and filter by `evt.detail.target.id`.
- **4xx/5xx bodies are not swapped by default**; a friendly error partial needs `shouldSwap = true`
  for that target (keep auth redirects excluded).
- **Out-of-band swaps only run when the library processes the response**; inserting fetched HTML with
  `innerHTML` leaves `hx-swap-oob` elements nested and inert — use the library's own request API.
- **Fragment scripts re-run on every swap**: guard listeners so they are attached once.

## Headless rendering for checks

- Serve the page from a real origin (relative URLs fail with `setContent`/`file://` for partial swaps).
- Pass `page.evaluate` a **string** when a TypeScript runner would inject helpers into a function
  body (e.g. `__name is not defined`).
- Wait for a page-specific selector, not a fixed timeout; retry flaky login redirects a bounded number
  of times and log the URL on failure.
