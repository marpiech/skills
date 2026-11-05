# Render check — screenshots and the probe

Read in REVIEW Step R3 and BUILD Step B7. The static checks see the code; this sees what users see.

## What to capture

For each screen in scope: widths **1440, 768, 390** (adapter may change them) × **each theme the
project ships** (light, dark). Per combination: one full-page screenshot and one probe result
(`scripts/probe.js` → JSON). Name files `<screen>-<width>-<theme>.{png,json}` in the scratchpad or the
project's ignored test-output directory — never commit them, never put them in a public place.

Use realistic data: an empty account and a busy one if the screen changes with volume (S1, L3).

## Running it — pick what the project already has

**Playwright (Node) already installed in the project** — a minimal runner (keep it outside the repo or
in the project's e2e folder if module resolution needs it):

```js
// node render-check.js <url> <outdir> <path/to/probe.js>
const { chromium } = require("playwright");
const fs = require("fs");
const [url, out, probePath] = process.argv.slice(2);
(async () => {
  const browser = await chromium.launch();
  for (const width of [1440, 768, 390]) for (const scheme of ["light", "dark"]) {
    const page = await browser.newPage({ viewport: { width, height: 900 }, colorScheme: scheme });
    await page.goto(url, { waitUntil: "networkidle" });
    // if the theme is a class/attribute, set it here per the adapter (e.g. data-theme)
    await page.screenshot({ path: `${out}/screen-${width}-${scheme}.png`, fullPage: true });
    const result = await page.evaluate(fs.readFileSync(probePath, "utf8")); // a string: no helper injection
    fs.writeFileSync(`${out}/screen-${width}-${scheme}.json`, JSON.stringify(result, null, 1));
    await page.close();
  }
  await browser.close();
})();
```

**Playwright (Python) installed** — the same with `page.evaluate(open(probe).read())`.

**A browser tool in the session** (built-in browser, a Chrome extension tool) — open the page, run
the probe text with its "execute JavaScript" action, save the returned JSON; take screenshots with
the tool. Switch the theme the way the app does (setting, attribute, OS preference emulation).

**Nothing available** — ask the user to paste the probe into the DevTools console on the page and
share the JSON and screenshots; review statically meanwhile and say the render check did not run.

Then: `python3 <SKILL_DIR>/scripts/uidesign.py report <dir>/*.json` and **Read every screenshot**.

## Authentication

Screens behind a login use the project's test account through the project's secrets tool: the
adapter names the **environment variable names** (never values) and the command that injects them
(IF /marpiech-secrets is installed → its `run` injection). Never print credentials, never write them
into the runner, never screenshot a page showing a token or a real person's data.

## What the probe measures (and its limits)

Measured: text contrast against the composited background (skips text over images/gradients),
text under 11px, font sizes/typefaces/weights in use, monospace outside code/sequences, numeric
table cells not right-aligned or not tabular, uppercase/tracked headers, zebra rows, gradients,
shadows on resting panels, panel radii, form controls not inheriting the font, targets under 24px,
chart hues (SVG marks only — canvas charts are not read), missing or oversized h1, sideways scroll,
emoji and placeholder text, `var()` names unresolved at `:root` in this theme.

Not measured: whether the hierarchy answers the screen's question, whether numbers agree, whether
states are distinct, the phone composition — those are the written look in review.md §1. A clean
probe says nothing banned was measured; it does not say the screen is good.
