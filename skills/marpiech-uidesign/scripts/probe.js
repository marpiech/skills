/* probe.js — rendered-page design probe for marpiech-uidesign.
 *
 * Runs INSIDE the page (browser side). No dependencies, no network, reads only; returns JSON.
 * The file is one expression: pass its text to page.evaluate(src) (Playwright), to a browser
 * tool's "run JavaScript" action, or paste it into the DevTools console. Save the returned object
 * as <name>.json and print it with `uidesign.py report <name>.json [...]`.
 *
 * Optional config: set window.__UIDESIGN = {mono: "warn"|"fail"|"info", maxSamples: 6,
 * numericCells: "td,th,[role=cell],[role=gridcell]", floating: ".menu,.popover"} before evaluating.
 */
(() => {
  const CFG = Object.assign({ mono: "info", maxSamples: 6, numericCells: "td,th,[role=cell],[role=gridcell]",
    floating: "[role=dialog],[role=menu],[role=tooltip],[role=listbox],dialog,.dropdown,.popover,.tooltip,.menu,.modal" },
    window.__UIDESIGN || {});
  const findings = {};
  const add = (id, level, why, el, detail) => {
    const f = findings[id] || (findings[id] = { id, level, why, count: 0, samples: [] });
    f.count++;
    if (f.samples.length < CFG.maxSamples) f.samples.push({ sel: sel(el), text: txt(el), detail: detail || "" });
  };
  const sel = (el) => {
    if (!el || !el.tagName) return "";
    const parts = [];
    for (let e = el, i = 0; e && e.tagName && i < 3; e = e.parentElement, i++) {
      let s = e.tagName.toLowerCase();
      if (e.id) { s += "#" + e.id; parts.unshift(s); break; }
      const cls = [...e.classList].slice(0, 2);
      if (cls.length) s += "." + cls.join(".");
      parts.unshift(s);
    }
    return parts.join(" > ");
  };
  const txt = (el) => ((el && (el.innerText || el.textContent)) || "").trim().replace(/\s+/g, " ").slice(0, 60);
  const visible = (el) => {
    const r = el.getBoundingClientRect();
    if (r.width < 1 || r.height < 1) return false;
    const cs = getComputedStyle(el);
    return cs.visibility !== "hidden" && cs.display !== "none" && parseFloat(cs.opacity) > 0.05;
  };
  const ownText = (el) => [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim().length > 0);
  const parse = (c) => {
    const m = c && c.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(/[\s,\/]+/).filter(Boolean).map(Number);
    return [p[0], p[1], p[2], p.length > 3 ? p[3] : 1];
  };
  const lum = (c) => {
    const f = (x) => { x /= 255; return x <= 0.04045 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2]);
  };
  const blend = (fg, bg) => [0, 1, 2].map((i) => fg[i] * fg[3] + bg[i] * (1 - fg[3])).concat(1);
  const contrast = (a, b) => { const [x, y] = [lum(a), lum(b)].sort((p, q) => q - p); return (x + 0.05) / (y + 0.05); };
  const bgOf = (el) => {
    const layers = [];
    for (let e = el; e; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if (cs.backgroundImage && cs.backgroundImage !== "none") return null; // image/gradient: unknown
      const c = parse(cs.backgroundColor);
      if (c && c[3] > 0) { layers.push(c); if (c[3] >= 1) break; }
    }
    let bg = [255, 255, 255, 1];
    for (let i = layers.length - 1; i >= 0; i--) bg = blend(layers[i], bg);
    return bg;
  };
  const hue = (c) => {
    const [r, g, b] = c.slice(0, 3).map((x) => x / 255);
    const mx = Math.max(r, g, b), mn = Math.min(r, g, b), d = mx - mn;
    const l = (mx + mn) / 2, s = d === 0 ? 0 : d / (1 - Math.abs(2 * l - 1));
    if (s < 0.18 || l < 0.08 || l > 0.96) return null; // grey, near-black, near-white
    let h = mx === r ? ((g - b) / d) % 6 : mx === g ? (b - r) / d + 2 : (r - g) / d + 4;
    return Math.round(((h * 60) + 360) % 360 / 30) * 30 % 360; // 12 hue buckets
  };
  const MONO = /monospace|menlo|consolas|courier|sf mono|sfmono|jetbrains|fira (code|mono)|roboto mono|source code pro|plex mono|geist mono|cascadia/i;
  const NUM = /^[+\-−±~≈<>]?\s?[$€£]?\s?\d[\d,.\s  ]*(e[+\-−]?\d+|×\s?10[⁻\-−]?[⁰¹²³⁴⁵⁶⁷⁸⁹\d]+)?\s?(%|x|×|kb|mb|gb|bp|kbp|mbp|ms|s|min|h|d|k|m|bn)?$/i;
  const EMOJI = /[\u{1F300}-\u{1FAFF}\u{2600}-\u{27BF}]/u;
  const PLACEHOLDER = /lorem ipsum|\bjohn doe\b|\bjane doe\b|\buser \d\b|\bacme\b|placeholder/i;

  const all = [...document.body.querySelectorAll("*")].filter((e) => !["SCRIPT", "STYLE", "NOSCRIPT", "TEMPLATE"].includes(e.tagName));
  const sizes = {}, families = {}, radii = {}, weights = {};
  const hues = new Set();
  const first = (f) => f.split(",")[0].replace(/["']/g, "").trim().toLowerCase();
  const bodyFamily = first(getComputedStyle(document.body).fontFamily);

  for (const el of all) {
    if (!visible(el)) continue;
    const cs = getComputedStyle(el);
    const fs = parseFloat(cs.fontSize);
    if (ownText(el)) {
      sizes[cs.fontSize] = (sizes[cs.fontSize] || 0) + 1;
      weights[cs.fontWeight] = (weights[cs.fontWeight] || 0) + 1;
      const fam = cs.fontFamily.split(",")[0].replace(/["']/g, "").trim();
      families[fam] = (families[fam] || 0) + 1;
      if (fs < 11) add("TINY-TEXT", "FAIL", "text under 11px is unreadable; meta and axis text start at 11-12px", el, cs.fontSize);
      const fg = parse(cs.color), bg = bgOf(el);
      if (fg && bg) {
        const r = contrast(blend(fg, bg), bg);
        const large = fs >= 24 || (fs >= 18.66 && parseInt(cs.fontWeight, 10) >= 700);
        if (r < (large ? 3 : 4.5)) add("CONTRAST", r < 3 ? "FAIL" : "WARN", "text below WCAG AA (4.5:1, large text 3:1)", el, r.toFixed(2) + ":1");
      }
      if (MONO.test(cs.fontFamily) && !el.closest("pre,code,kbd,samp,.sequence,[data-sequence]"))
        add("MONO", CFG.mono.toUpperCase(), "monospace outside code/sequences — identifiers use tabular figures in the text face", el, cs.fontFamily.split(",")[0]);
      if (EMOJI.test(txt(el))) add("EMOJI", "WARN", "emoji are not an icon system", el);
      if (PLACEHOLDER.test(txt(el)) && !el.closest("input,textarea")) add("PLACEHOLDER", "FAIL", "placeholder people or text on the screen", el);
    }
    if (cs.backgroundImage.includes("gradient") && el.tagName !== "svg")
      add("GRADIENT", "WARN", "gradient on a ground, card, button or text (chart area fills excepted)", el, cs.backgroundImage.slice(0, 50));
    if (cs.boxShadow !== "none" && !el.matches(CFG.floating) && !["fixed", "absolute", "sticky"].includes(cs.position) &&
        !el.matches("button,input,select,textarea,a,[role=button]"))
      add("RESTING-SHADOW", "INFO", "a shadow on a resting panel; elevation is for what floats", el, cs.boxShadow.slice(0, 40));
    if ((cs.backgroundColor !== "rgba(0, 0, 0, 0)" || cs.borderTopWidth !== "0px") && cs.borderTopLeftRadius !== "0px" &&
        el.getBoundingClientRect().width > 120)
      radii[cs.borderTopLeftRadius] = (radii[cs.borderTopLeftRadius] || 0) + 1;
    if (el.matches("button,input,select,textarea") && first(cs.fontFamily) !== bodyFamily && !MONO.test(cs.fontFamily))
      add("CONTROL-FONT", "WARN", "a form control does not inherit the page font (button/input default to the UA face)", el, cs.fontFamily.split(",")[0]);
    if (el.matches("a[href],button,[role=button],input:not([type=hidden]),select,[tabindex]:not([tabindex='-1'])")) {
      const r = el.getBoundingClientRect();
      if ((r.width < 24 || r.height < 24) && !el.closest("p,li,td") && cs.display !== "inline")
        add("SMALL-TARGET", "WARN", "interactive target under 24x24px (WCAG 2.5.8)", el, `${Math.round(r.width)}x${Math.round(r.height)}`);
    }
    if (el.closest("svg") && ["path", "rect", "circle", "line", "polyline", "polygon", "ellipse"].includes(el.tagName.toLowerCase())) {
      for (const c of [cs.fill, cs.stroke]) { const p = parse(c); if (p && p[3] > 0.2) { const h = hue(p); if (h !== null) hues.add(h); } }
    }
  }

  // numbers in tables: right-aligned, tabular figures
  const cells = [...document.querySelectorAll(CFG.numericCells)].filter(visible);
  let numericCells = 0;
  for (const c of cells) {
    const t = txt(c);
    if (!t || !NUM.test(t) || t.length > 24) continue;
    numericCells++;
    const cs = getComputedStyle(c);
    if (!["right", "end"].includes(cs.textAlign) && !(c.firstElementChild && ["right", "end"].includes(getComputedStyle(c.firstElementChild).textAlign)))
      add("NUM-ALIGN", "WARN", "numbers in a column are right-aligned so digits line up", c, cs.textAlign);
    if (!/tabular-nums/.test(cs.fontVariantNumeric) && !MONO.test(cs.fontFamily))
      add("NUM-TABULAR", "WARN", "numbers in tables use tabular figures (font-variant-numeric: tabular-nums)", c, cs.fontVariantNumeric);
  }
  for (const th of document.querySelectorAll("th,[role=columnheader]")) {
    if (!visible(th)) continue;
    const cs = getComputedStyle(th);
    if (cs.textTransform === "uppercase" || parseFloat(cs.letterSpacing) > 0.5)
      add("HEADER-CAPS", "WARN", "uppercase or tracked table headers read louder than the data", th, cs.textTransform);
  }
  for (const tb of document.querySelectorAll("tbody")) {
    const rows = [...tb.rows].slice(0, 6).map((r) => getComputedStyle(r).backgroundColor);
    if (rows.length >= 4 && rows[0] === rows[2] && rows[1] === rows[3] && rows[0] !== rows[1])
      add("ZEBRA", "INFO", "zebra striping — rules or spacing separate rows", tb);
  }

  // page-level checks
  const h1 = [...document.querySelectorAll("h1")].filter(visible);
  if (!h1.length) add("NO-H1", "WARN", "the screen has no h1 naming what it is", document.body);
  for (const h of h1) if (parseFloat(getComputedStyle(h).fontSize) > 32)
    add("TITLE-SIZE", "WARN", "an app-screen title above 32px reads as a landing page", h, getComputedStyle(h).fontSize);
  if (document.documentElement.scrollWidth > document.documentElement.clientWidth + 1)
    add("H-SCROLL", "FAIL", "the page scrolls sideways at this width", document.body,
      `${document.documentElement.scrollWidth}px > ${document.documentElement.clientWidth}px`);
  const nSizes = Object.keys(sizes).length;
  if (nSizes > 9) add("TYPE-SCALE", "WARN", "more than 9 font sizes on one screen — the scale has drifted", document.body, Object.keys(sizes).join(" "));
  const nFam = Object.keys(families).filter((f) => families[f] > 2).length;
  if (nFam > 2) add("FONT-FAMILIES", "WARN", "more than two typefaces in use", document.body, Object.keys(families).join(", "));
  const nRadii = Object.keys(radii).length;
  if (nRadii > 3) add("RADII", "WARN", "more than three panel radii — radius is chosen once", document.body, Object.keys(radii).join(" "));
  if (hues.size > 6) add("CHART-HUES", "FAIL", "more than six hues in charts — one hue per chart, status colours for status", document.body, hues.size + " hue buckets");
  else if (hues.size > 4) add("CHART-HUES", "WARN", "more than four hues in charts", document.body, hues.size + " hue buckets");

  // motion: endless animations mean "live"; they must stop under reduced motion
  const endless = [...document.querySelectorAll("body *")].filter((el) => {
    const cs = getComputedStyle(el);
    return cs.animationName !== "none" && cs.animationIterationCount === "infinite" && visible(el) &&
      !el.closest("[aria-busy=true],[role=progressbar],.spinner,.loading");
  });
  if (endless.length && matchMedia("(prefers-reduced-motion: reduce)").matches)
    add("MOTION", "FAIL", "endless animation still running under prefers-reduced-motion", endless[0], endless.length + " elements");
  else if (endless.length > 2)
    add("MOTION", "WARN", "more than two endlessly animated indicators — motion should mark only truly live data", endless[0], endless.length + " elements");

  // charts need a text equivalent (accessible name / caption / table view)
  for (const ch of document.querySelectorAll("svg, canvas")) {
    if (!visible(ch) || ch.parentElement.closest("svg")) continue;
    const r = ch.getBoundingClientRect();
    const marks = ch.tagName.toLowerCase() === "svg" ? ch.querySelectorAll("path,rect,circle,line,polyline,polygon").length : 99;
    if (r.width < 120 || r.height < 60 || marks < 6) continue; // icons and decorations
    const fig = ch.closest("figure");
    const named = ch.getAttribute("aria-label") || ch.getAttribute("aria-labelledby") || ch.getAttribute("aria-describedby") ||
      (ch.querySelector && ch.querySelector(":scope > title")) || (fig && fig.querySelector("figcaption")) ||
      ch.getAttribute("aria-hidden") === "true";
    if (!named) add("CHART-A11Y", "WARN", "a chart without a text equivalent (aria-label / figcaption with the finding, or a table view)", ch,
      `${Math.round(r.width)}x${Math.round(r.height)}`);
  }

  // a dark-looking page must declare color-scheme: dark (native controls, scrollbars)
  const pageBg = bgOf(document.body);
  if (pageBg && lum(pageBg) < 0.2 && !/dark/.test(getComputedStyle(document.documentElement).colorScheme || ""))
    add("COLOR-SCHEME", "WARN", "dark page without `color-scheme: dark` — scrollbars and native controls stay light", document.documentElement,
      getComputedStyle(document.documentElement).colorScheme || "normal");

  // one density tier per screen
  const tiers = {};
  for (const t of document.querySelectorAll("table")) {
    if (!visible(t) || !t.tBodies.length) continue;
    const hs = [...t.tBodies[0].rows].slice(0, 12).filter(visible).map((rw) => rw.getBoundingClientRect().height).sort((a, b) => a - b);
    if (hs.length < 3) continue;
    const med = hs[Math.floor(hs.length / 2)];
    const tier = med <= 40 ? "compact" : med <= 52 ? "standard" : "comfortable";
    (tiers[tier] = tiers[tier] || []).push(`${sel(t)}:${Math.round(med)}px`);
  }
  if (Object.keys(tiers).length > 1)
    add("ROW-DENSITY", "INFO", "tables on this screen use different density tiers — one tier per screen", document.body,
      Object.entries(tiers).map(([k, v]) => `${k}(${v.length})`).join(" "));

  // CSS variables referenced in same-origin stylesheets but unresolved at :root
  const rootCS = getComputedStyle(document.documentElement);
  const unresolved = new Set();
  for (const sh of document.styleSheets) {
    let rules;
    try { rules = sh.cssRules; } catch (e) { continue; } // cross-origin
    const walk = (rs) => { for (const r of rs) {
      if (r.cssRules) walk(r.cssRules);
      if (!r.style) continue;
      const m = r.cssText.match(/var\(\s*--[\w-]+/g) || [];
      for (const v of m) { const n = v.replace(/var\(\s*/, ""); if (!rootCS.getPropertyValue(n).trim()) unresolved.add(n); }
    } };
    walk(rules);
  }
  if (unresolved.size) findings["UNRESOLVED-VAR"] = { id: "UNRESOLVED-VAR", level: "INFO",
    why: "var() names with no value at :root in this theme (may be scoped locally — confirm with `uidesign.py tokens`)",
    count: unresolved.size, samples: [...unresolved].slice(0, CFG.maxSamples).map((n) => ({ sel: ":root", text: n, detail: "" })) };

  return {
    url: location.href, viewport: `${innerWidth}x${innerHeight}`,
    scheme: (matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light") +
      (document.documentElement.dataset.theme ? `/data-theme=${document.documentElement.dataset.theme}` : ""),
    stats: { fontSizes: nSizes, sizes: Object.entries(sizes).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${k}×${v}`).join(" "),
      typefaces: Object.keys(families).join(", "), weights: Object.keys(weights).join(" "), panelRadii: Object.keys(radii).join(" "),
      chartHueBuckets: hues.size, numericCells },
    findings: Object.values(findings),
  };
})()
