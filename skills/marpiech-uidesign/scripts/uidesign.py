#!/usr/bin/env python3
"""uidesign.py — check a UI against its own design system, the single source of truth (stdlib + git; read-only).

  uidesign.py sources
      Find the design system's sources of truth: token files (CSS custom properties defined at
      theme level), theme selectors, component directories, catalogues, galleries, formatter
      modules and decision logs. Prints a suggested .claude/uidesign.json.

  uidesign.py tokens [--config FILE]
      Token integrity: UNDEFINED (used, defined nowhere — a var() fallback then wins in every
      theme), OUTSIDE-SOURCE (a global token defined outside the token files), MULTI-SOURCE (one
      token defined in several files), LOCAL-REDEFINE (a global token redefined inside a component
      selector), THEME-GAP (a literal colour token with no dark-theme value), UNUSED.

  uidesign.py lint [PATH ...] [--diff BASE] [--config FILE] [--max-hits N] [--json]
      Drift from the source of truth in styles and markup: raw colours, primitive (palette) tokens
      used directly, literal fonts, page-local <style>, visual inline styles, !important,
      gradients, monospace, uppercase, formatting outside the shared formatters, placeholder data,
      emoji, raw elements where the library has a component. --diff BASE: changed files only,
      every hit marked NEW or PRE-EXISTING.

  uidesign.py contrast [--pair FG:BG ...] [--all] [--config FILE]
      WCAG contrast of text/surface token pairs, resolved per theme (base and dark).

  uidesign.py components [--config FILE]
      Component inventory: definitions (Jinja macros, React/Vue/Svelte components, custom
      elements), usage counts, DUPLICATE definitions, SHADOW copies of library templates,
      DEPRECATED usage, UNUSED.

  uidesign.py report PROBE.json [PROBE.json ...]
      Print and merge results of the in-browser probe (scripts/probe.js) — e.g. light + dark,
      or desktop + phone.

Config (.claude/uidesign.json, all keys optional; `sources` prints a starting point):
  {"token_files": ["static/css/tokens.css"], "dark_selectors": ["[data-theme=dark]"],
   "component_dirs": ["libs/ui/templates/components"], "formatter_files": ["app/filters.py"],
   "palette": ["--blue-*", "--slate", "--white"],      # primitive tokens components must not use
   "raw_elements": {"button": "<button\\\\b", "data_table": "<table\\\\b"},
   "deprecated": ["table"], "exclude": ["emails/", "pdf/"],
   "severity": {"MONO": "error", "UPPERCASE": "off"},
   "allow": {"GRADIENT": ["*/charts/*"]}}
Exit codes: 0 clean, 1 findings at warn/error level, 2 usage error.
"""
import argparse
import colorsys
import fnmatch
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict

CSS_EXT = (".css", ".scss", ".sass", ".less", ".pcss")
MARKUP_EXT = (".html", ".htm", ".jinja", ".jinja2", ".j2", ".njk", ".hbs", ".vue", ".svelte", ".jsx",
              ".tsx", ".astro", ".erb", ".twig", ".liquid", ".mdx")
SCRIPT_EXT = (".js", ".ts", ".mjs")
DEFAULT_EXCLUDE = ["node_modules/", "venv/", ".venv/", "__pycache__/", "dist/", "build/", "vendor/",
                   ".git/", ".claude/", "coverage/", "*.min.css", "*.min.js", "*.map", "site-packages/"]
TEST_PARTS = ("tests/", "test/", "__tests__/", ".stories.", ".spec.", ".test.", "e2e/", "fixtures/")
HUE_WORDS = ("red|blue|green|slate|gray|grey|white|black|navy|teal|amber|orange|purple|pink|yellow|cyan|"
             "indigo|violet|lime|emerald|rose|sky|stone|zinc|neutral|charcoal|obsidian|snow|pearl|cream|"
             "sand|ink|brown|gold|silver|magenta|fuchsia|mint|olive|coral|salmon|beige|ivory|ash|smoke|fog|graphite|"
             "steel|bone|chalk|onyx|jet|paper|clay|rust|plum|lavender|peach|aqua|turquoise")
PRIMITIVE_RX = re.compile(rf"^--(?:color-)?(?:{HUE_WORDS})(?:-(?:\d{{2,3}}|\d|light|lighter|dark|darker|alt|muted|verydark|"
                          rf"verylight|pale|deep|bright|soft))*$")


def is_primitive(name, cfg):
    pal = cfg.get("palette")
    if pal:
        return any(fnmatch.fnmatch(name, p) for p in pal)
    return bool(PRIMITIVE_RX.match(name))
COLOR_LIT = re.compile(r"#[0-9a-fA-F]{8}\b|#[0-9a-fA-F]{6}\b|#[0-9a-fA-F]{3,4}\b|\brgba?\([^)]*\)|\bhsla?\([^)]*\)")
VAR_USE = re.compile(r"var\(\s*(--[\w-]+)\s*(,\s*([^()]*(\([^()]*\))?[^()]*))?\)")
MONO_RX = re.compile(r"monospace|ui-monospace|\bMenlo\b|\bConsolas\b|Courier|SF Mono|SFMono|JetBrains Mono|"
                     r"Fira (Code|Mono)|Roboto Mono|Source Code Pro|IBM Plex Mono|Geist Mono|Cascadia", re.I)
EMOJI_RX = re.compile("[\U0001F300-\U0001FAFF\U00002600-\U000026FF\U00002700-\U000027BF\U0001F000-\U0001F2FF]")

SEVERITY = {  # default level per rule: error / warn / info / off
    "RAW-COLOR": "warn", "PALETTE-VAR": "warn", "FONT-LITERAL": "warn", "PAGE-STYLE": "warn",
    "INLINE-STYLE": "warn", "IMPORTANT": "info", "GRADIENT": "warn", "MONO": "info", "UPPERCASE": "info",
    "SHADOW-LITERAL": "info", "INLINE-FORMAT": "warn", "PLACEHOLDER": "warn", "EMOJI": "info",
    "RAW-ELEMENT": "warn", "DEPRECATED": "warn",
}
WHY = {
    "RAW-COLOR": "colours come from tokens; a literal is a second source that drifts and ignores the dark theme",
    "PALETTE-VAR": "components use semantic tokens (role), not primitives (hue) — a primitive has no dark value",
    "FONT-LITERAL": "the font is a token; a literal family is a second source (and form controls need inherit)",
    "PAGE-STYLE": "no per-page design: a <style> block outside the component library is a local look",
    "INLINE-STYLE": "visual inline styles bypass the system; only data-driven geometry belongs inline",
    "IMPORTANT": "!important usually papers over a cascade conflict that belongs fixed at the source",
    "GRADIENT": "gradients on grounds, buttons, cards, text are a generated-UI tell (chart area fill excepted)",
    "MONO": "monospace only for code and sequence alignments; identifiers use tabular figures in the text face",
    "UPPERCASE": "uppercase tracked labels and headers read louder than the data",
    "SHADOW-LITERAL": "elevation is a token; resting cards need a border or a tone step, not a shadow",
    "INLINE-FORMAT": "numbers and dates are formatted by the shared formatters only — one format per metric",
    "PLACEHOLDER": "placeholder people/data on a screen — replace with real or clearly synthetic sample data",
    "EMOJI": "emoji are not an icon system",
    "RAW-ELEMENT": "the library already provides this element as a component; a raw copy renders differently",
    "DEPRECATED": "a deprecated component is still used",
}


# ---------------------------------------------------------------- helpers
def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True)


def die(msg):
    print(f"uidesign: {msg}", file=sys.stderr)
    sys.exit(2)


def load_config(path):
    if path and os.path.exists(path):
        try:
            return json.load(open(path, encoding="utf-8"))
        except json.JSONDecodeError as e:
            die(f"{path}: invalid JSON ({e})")
    return {}


def match_any(path, patterns):
    for p in patterns or []:
        if p.endswith("/"):
            if path.startswith(p) or f"/{p}" in f"/{path}":
                return True
        elif fnmatch.fnmatch(path, p) or fnmatch.fnmatch(os.path.basename(path), p):
            return True
    return False


def is_test(path):
    return any(t in path for t in TEST_PARTS)


def repo_files(cfg, scopes=None, base=None):
    if base:
        r = git("diff", "--name-only", "--diff-filter=AMR", f"{base}...HEAD")
        if r.returncode != 0:
            die(f"cannot diff against {base}")
        fs = set(r.stdout.split()) | set(git("diff", "--name-only", "--diff-filter=AMR", "HEAD").stdout.split())
        fs |= set(git("ls-files", "--others", "--exclude-standard").stdout.split())
    else:
        fs = set(git("ls-files", "--cached", "--others", "--exclude-standard").stdout.split())
    if scopes:
        fs = {f for f in fs if any(f == s.rstrip("/") or f.startswith(s.rstrip("/") + "/") for s in scopes)}
    exc = DEFAULT_EXCLUDE + cfg.get("exclude", [])
    return sorted(f for f in fs if os.path.isfile(f) and not match_any(f, exc))


def read(path, cache={}):
    if path not in cache:
        try:
            cache[path] = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            cache[path] = ""
    return cache[path]


def line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def line_text(text, pos):
    a = text.rfind("\n", 0, pos) + 1
    b = text.find("\n", pos)
    return text[a:b if b >= 0 else len(text)]


def blank_comments(text, css=True):
    """Replace comments with spaces, keeping newlines (so line numbers stay right)."""
    def keep(m):
        return re.sub(r"[^\n]", " ", m.group())
    text = re.sub(r"/\*.*?\*/", keep, text, flags=re.S)
    if not css:
        text = re.sub(r"<!--.*?-->", keep, text, flags=re.S)
        text = re.sub(r"\{#.*?#\}", keep, text, flags=re.S)
    return text


def style_regions(path, text):
    """(offset, css) regions: the whole file for stylesheets, <style> blocks for markup."""
    if path.endswith(CSS_EXT):
        return [(0, text)]
    return [(m.start(1), m.group(1)) for m in re.finditer(r"<style[^>]*>(.*?)</style>", text, re.S | re.I)]


def css_decls(css):
    """Yield (offset, context, prop, value) for each declaration; context = enclosing selectors/at-rules."""
    css = blank_comments(css)
    stack, last = [], 0
    for m in re.finditer(r"[{};]", css):
        seg = css[last:m.start()]
        ch = m.group()
        if ch == "{":
            stack.append(" ".join(seg.split()))
        else:
            if ":" in seg and seg.strip():
                prop, _, value = seg.partition(":")
                p = prop.strip()
                if re.match(r"^-{0,2}[a-zA-Z][\w-]*$", p) and stack:
                    off = last + (len(seg) - len(seg.lstrip()))
                    yield off, list(stack), p, value.strip()
            if ch == "}" and stack:
                stack.pop()
        last = m.end()


ROOTISH = re.compile(r"^(:root|html|:host|body)?(\[data-[\w-]*theme[^\]]*\]|\.theme-[\w-]+|\.light|\.dark|"
                     r":root|:where\(:root\))*$")


def theme_of(stack, dark_selectors):
    """base / dark for theme-level blocks (:root, html, [data-theme=…]); local for component selectors."""
    sels = [s for s in stack if not s.startswith("@")]
    if not sels:
        return "base"
    inner = sels[-1]
    rootish = all(ROOTISH.match(s.strip().replace(" ", "")) for s in inner.split(",") if s.strip())
    if not rootish or len(sels) > 1:
        return "local"
    ctx = " ".join(stack).lower()
    if any(d.lower() in ctx for d in dark_selectors) or re.search(r"dark", ctx):
        return "dark"
    return "base"


# ---------------------------------------------------------------- token model
class Tokens:
    def __init__(self, cfg, files):
        self.cfg = cfg
        self.dark = cfg.get("dark_selectors", [])
        self.defs = defaultdict(list)   # name -> [(file, line, theme, context, value)]
        self.uses = defaultdict(list)   # name -> [(file, line, fallback)]
        for f in files:
            if not f.endswith(CSS_EXT + MARKUP_EXT + SCRIPT_EXT):
                continue
            text = read(f)
            for base, css in style_regions(f, text):
                for off, stack, prop, val in css_decls(css):
                    if prop.startswith("--"):
                        self.defs[prop].append((f, line_of(text, base + off), theme_of(stack, self.dark),
                                                " ".join(stack), val))
            body = blank_comments(text, css=f.endswith(CSS_EXT))
            for m in VAR_USE.finditer(body):
                self.uses[m.group(1)].append((f, line_of(text, m.start()), (m.group(3) or "").strip()))
            if not f.endswith(CSS_EXT):  # tokens set from markup/JS count as defined
                for m in re.finditer(r"style=[\"'][^\"']*?(--[\w-]+)\s*:", body):
                    self.defs.setdefault(m.group(1), []).append((f, line_of(text, m.start()), "inline", "style=", ""))
                for m in re.finditer(r"setProperty\(\s*['\"](--[\w-]+)", body):
                    self.defs.setdefault(m.group(1), []).append((f, line_of(text, m.start()), "inline", "js", ""))

    def token_files(self):
        tf = self.cfg.get("token_files")
        if tf:
            return tf
        counts = Counter(d[0] for ds in self.defs.values() for d in ds if d[2] in ("base", "dark"))
        return [f for f, n in counts.most_common() if n >= 8][:3]

    def resolve(self, theme):
        """name -> value for a theme (base, overridden by dark defs for 'dark')."""
        vals = {}
        for name, ds in self.defs.items():
            for d in ds:
                if d[2] == "base":
                    vals[name] = d[4]
        if theme == "dark":
            for name, ds in self.defs.items():
                for d in ds:
                    if d[2] == "dark":
                        vals[name] = d[4]
        return vals


def resolve_value(val, vals, depth=0):
    if depth > 12:
        return None
    m = VAR_USE.search(val or "")
    if not m:
        return val
    name, fb = m.group(1), m.group(3)
    inner = vals.get(name)
    rep = resolve_value(inner, vals, depth + 1) if inner is not None else (resolve_value(fb, vals, depth + 1) if fb else None)
    if rep is None:
        return None
    return resolve_value(val[:m.start()] + rep + val[m.end():], vals, depth + 1)


NAMED = {"white": (255, 255, 255, 1), "black": (0, 0, 0, 1), "transparent": (0, 0, 0, 0)}


def parse_color(v):
    if v is None:
        return None
    v = v.strip().lower()
    if v in NAMED:
        return NAMED[v]
    m = re.fullmatch(r"#([0-9a-f]{3,8})", v)
    if m:
        h = m.group(1)
        if len(h) in (3, 4):
            h = "".join(c * 2 for c in h)
        if len(h) not in (6, 8):
            return None
        a = int(h[6:8], 16) / 255 if len(h) == 8 else 1
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), a
    m = re.fullmatch(r"(rgba?|hsla?)\(([^)]*)\)", v)
    if not m:
        return None
    parts = [p for p in re.split(r"[\s,/]+", m.group(2).strip()) if p]
    if len(parts) < 3:
        return None

    def num(p, scale=1.0):
        return float(p[:-1]) / 100 * scale if p.endswith("%") else float(p.replace("deg", ""))
    try:
        a = num(parts[3], 1.0) if len(parts) > 3 else 1.0
        if m.group(1).startswith("rgb"):
            return num(parts[0], 255), num(parts[1], 255), num(parts[2], 255), a
        r, g, b = colorsys.hls_to_rgb(num(parts[0]) / 360 % 1, num(parts[2], 1.0), num(parts[1], 1.0))
        return r * 255, g * 255, b * 255, a
    except ValueError:
        return None


def over(fg, bg):
    a = fg[3]
    return tuple(fg[i] * a + bg[i] * (1 - a) for i in range(3)) + (1,)


def luminance(c):
    def ch(x):
        x /= 255
        return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    return 0.2126 * ch(c[0]) + 0.7152 * ch(c[1]) + 0.0722 * ch(c[2])


def ratio(fg, bg):
    l1, l2 = sorted((luminance(fg), luminance(bg)), reverse=True)
    return (l1 + 0.05) / (l2 + 0.05)


# ---------------------------------------------------------------- sources
def cmd_sources(a):
    cfg = load_config(a.config)
    files = repo_files(cfg)
    tok = Tokens(cfg, files)
    per_file = Counter(d[0] for ds in tok.defs.values() for d in ds if d[2] in ("base", "dark"))
    dark_ctx = Counter(d[3] for ds in tok.defs.values() for d in ds if d[2] == "dark")
    comp = component_defs(files, cfg)
    comp_dirs = Counter(os.path.dirname(f) for ds in comp.values() for f, _ in ds)
    docs = [f for f in files if re.search(r"(^|/)(COMPONENTS|DESIGN|design[-_]system|tokens|style[-_]?guide)[^/]*\.(md|mdx)$", f, re.I)]
    stories = [f for f in files if ".stories." in f]
    storybook = sorted({f.split(".storybook/")[0] + ".storybook/" for f in files if ".storybook/" in f})
    galleries = sorted({f.split("/")[0] for f in files if re.search(r"gallery|showcase|playground|styleguide", f, re.I)})
    fmt = [f for f in files if f.endswith((".py", ".js", ".ts")) and not is_test(f) and re.search(
        r"\.filters\[|@\w*\.template_filter|registerHelper|Intl\.NumberFormat|def format_(date|number|af|pvalue|percent)",
        read(f))]
    logs = [f for f in files if f.endswith(".md") and re.search(r"^#+ .*decision", read(f), re.I | re.M)]
    logs.sort(key=lambda f: (not re.search(r"design|ui|component|style|token", f, re.I), f))

    print("## Token sources (files defining theme-level custom properties)")
    for f, n in per_file.most_common(8):
        print(f"  {n:>4}  {f}")
    if not per_file:
        print("  (none — the project has no CSS-variable token layer; colours are literals or a framework config)")
    tw = [f for f in files if re.search(r"(^|/)tailwind\.config\.|(^|/)tokens?\.json$|\.tokens\.json$", f)]
    for f in tw:
        print(f"  (config) {f}")
    print("\n## Dark-theme selectors seen")
    for c, n in dark_ctx.most_common(5):
        print(f"  {n:>4}  {c}")
    print("\n## Component directories (by definitions)")
    for d, n in comp_dirs.most_common(8):
        print(f"  {n:>4}  {d or '.'}")
    print("\n## Catalogues, galleries, stories")
    for f in docs + storybook + galleries[:5]:
        print(f"  {f}")
    if stories:
        print(f"  {len(stories)} *.stories.* files")
    print("\n## Formatter modules")
    for f in fmt[:8]:
        print(f"  {f}")
    print("\n## Decision logs (markdown with a 'decision' heading)")
    for f in logs[:8]:
        print(f"  {f}")
    sugg = {
        "token_files": [f for f, n in per_file.most_common(3) if n >= 8] or [f for f, _ in per_file.most_common(1)],
        "dark_selectors": sorted({re.sub(r".*?(\[data-theme=[\"']?dark[\"']?\]|\.dark\b|\.theme-dark|prefers-color-scheme:\s*dark).*", r"\1", c)
                                  for c in dark_ctx})[:3],
        "component_dirs": [d for d, _ in comp_dirs.most_common(3)],
        "formatter_files": fmt[:3],
        "palette": sorted({n for n in tok.defs if PRIMITIVE_RX.match(n)})[:40],
        "raw_elements": {}, "deprecated": [], "exclude": [], "severity": {}, "allow": {},
    }
    print("\n## Suggested .claude/uidesign.json (review every entry; it is the config, not the truth)")
    print(json.dumps(sugg, indent=1))
    return 0


# ---------------------------------------------------------------- tokens
def cmd_tokens(a):
    cfg = load_config(a.config)
    files = repo_files(cfg)
    tok = Tokens(cfg, files)
    tfiles = tok.token_files()
    if not tfiles:
        print("(no token files configured or detected — run `sources`; OUTSIDE-SOURCE checks skipped)")
    findings = defaultdict(list)
    has_dark = any(d[2] == "dark" for ds in tok.defs.values() for d in ds)
    for name, uses in sorted(tok.uses.items()):
        if name not in tok.defs:
            fb = [u for u in uses if u[2]]
            note = f"fallback wins in every theme (e.g. {fb[0][2][:30]})" if fb else "no fallback: the property is invalid"
            findings["UNDEFINED"].append((name, f"{len(uses)} uses, {note}", uses[:3]))
    for name, ds in sorted(tok.defs.items()):
        glob = [d for d in ds if d[2] in ("base", "dark")]
        if tfiles:
            outside = [d for d in glob if not match_any(d[0], tfiles) and d[0] not in tfiles]
            if outside and not is_test(outside[0][0]):
                findings["OUTSIDE-SOURCE"].append((name, "global token defined outside the token files", outside[:3]))
        srcs = sorted({d[0] for d in glob if d[2] == "base"})
        if len(srcs) > 1:
            findings["MULTI-SOURCE"].append((name, f"defined at theme level in {len(srcs)} files", [(s, 0, "") for s in srcs[:4]]))
        if glob:
            local = [d for d in ds if d[2] == "local"]
            if local:
                findings["LOCAL-REDEFINE"].append((name, f"global token redefined in {local[0][3][:50]}", local[:3]))
        if has_dark and not is_primitive(name, tok.cfg) and any(d[2] == "base" for d in ds) and \
                not any(d[2] == "dark" for d in ds):
            v = next(d[4] for d in ds if d[2] == "base")
            if parse_color(v) and not VAR_USE.search(v):
                findings["THEME-GAP"].append((name, f"literal colour {v} has no dark value", [ds[0]]))
        if glob and name not in tok.uses:
            findings["UNUSED"].append((name, "defined, never used", glob[:1]))
    order = [("UNDEFINED", "error"), ("OUTSIDE-SOURCE", "error"), ("MULTI-SOURCE", "warn"),
             ("LOCAL-REDEFINE", "warn"), ("THEME-GAP", "warn"), ("UNUSED", "info")]
    print(f"tokens: {sum(1 for ds in tok.defs.values() if any(d[2] in ('base','dark') for d in ds))} global, "
          f"{len(tok.uses)} referenced; token files: {', '.join(tfiles) or '-'}; dark theme: {'yes' if has_dark else 'no'}\n")
    bad = 0
    for kind, level in order:
        rows = findings.get(kind, [])
        if not rows:
            continue
        if level in ("error", "warn"):
            bad += len(rows)
        print(f"## {kind} ({level}) — {len(rows)}")
        shown = rows if a.all or level != "info" else rows[:a.max_hits]
        for name, msg, where in shown[:a.max_hits if level == "info" and not a.all else None]:
            loc = ", ".join(f"{w[0]}:{w[1]}" if w[1] else w[0] for w in where)
            print(f"  {name}: {msg} — {loc}")
        if len(rows) > len(shown):
            print(f"  … {len(rows) - len(shown)} more (--all)")
        print()
    if not bad:
        print("token layer consistent.")
    return 1 if bad else 0


# ---------------------------------------------------------------- lint
def cmd_lint(a):
    cfg = load_config(a.config)
    sev = {**SEVERITY, **cfg.get("severity", {})}
    allow = cfg.get("allow", {})
    files = repo_files(cfg, a.paths, a.diff)
    tok = Tokens(cfg, repo_files(cfg)) if not cfg.get("token_files") else None
    tfiles = cfg.get("token_files") or (tok.token_files() if tok else [])
    comp_dirs = cfg.get("component_dirs", [])
    fmt_files = cfg.get("formatter_files", [])
    palette = cfg.get("palette") or []
    raw = cfg.get("raw_elements", {})
    deprecated = cfg.get("deprecated", [])

    def is_palette(name):
        return is_primitive(name, cfg)

    def in_lib(f):
        return any(f.startswith(d.rstrip("/") + "/") for d in comp_dirs)

    hits = defaultdict(list)

    def add(rule, f, text, pos, snippet):
        if sev.get(rule, "warn") == "off" or match_any(f, allow.get(rule, [])):
            return
        ln = line_of(text, pos)
        hits[rule].append({"file": f, "line": ln, "text": snippet.strip()[:140], "attr": ""})

    stats = {"colours": Counter(), "font_sizes": Counter(), "radii": Counter()}
    for f in files:
        is_css, is_markup, is_script = f.endswith(CSS_EXT), f.endswith(MARKUP_EXT), f.endswith(SCRIPT_EXT)
        if not (is_css or is_markup or is_script) or is_test(f):
            continue
        text = read(f)
        token_file = f in tfiles or match_any(f, tfiles)
        for base, css in style_regions(f, text):
            for off, ctx, prop, val in css_decls(css):
                pos = base + off
                if prop.startswith("--"):
                    continue
                for c in COLOR_LIT.findall(val):
                    stats["colours"][c.lower()] += 1
                if not token_file:
                    if COLOR_LIT.search(val) and not re.match(r"^(transparent|inherit|currentcolor)$", val, re.I):
                        add("RAW-COLOR", f, text, pos, f"{prop}: {val}")
                    if prop in ("font-family", "font") and not re.match(r"^(var\(|inherit|initial|unset)", val) and \
                            not MONO_RX.search(val) and \
                            (prop == "font-family" or re.search(r"[a-z]\s*,|serif|sans", val, re.I)):
                        add("FONT-LITERAL", f, text, pos, f"{prop}: {val}")
                    if prop == "box-shadow" and not re.match(r"^(none|0|var\(|inherit|initial|unset)", val):
                        add("SHADOW-LITERAL", f, text, pos, f"{prop}: {val}")
                    if "!important" in val:
                        add("IMPORTANT", f, text, pos, f"{prop}: {val}")
                for m in VAR_USE.finditer(val):
                    if not token_file and is_palette(m.group(1)):
                        add("PALETTE-VAR", f, text, pos, f"{prop}: {val}")
                if re.search(r"(linear|radial|conic)-gradient", val) and "mask" not in prop:
                    add("GRADIENT", f, text, pos, f"{prop}: {val}")
                if prop in ("font-family", "font") and MONO_RX.search(val):
                    add("MONO", f, text, pos, f"{prop}: {val}")
                if prop == "text-transform" and "uppercase" in val:
                    add("UPPERCASE", f, text, pos, f"{prop}: {val}")
                if prop == "font-size":
                    stats["font_sizes"][val] += 1
                if prop == "border-radius":
                    stats["radii"][val] += 1
        if is_markup:
            body = blank_comments(text, css=False)
            if not in_lib(f) and not f.endswith((".vue", ".svelte")):
                for m in re.finditer(r"<style\b", body, re.I):
                    add("PAGE-STYLE", f, text, m.start(), body[m.start():m.start() + 60].split("\n")[0])
            for m in re.finditer(r"\bstyle=(\"[^\"]*\"|'[^']*')", body):
                s = m.group(1)
                if re.search(r"(^|[;\s\"'])(color|background|font|border|box-shadow|padding|margin)[\w-]*\s*:", s):
                    add("INLINE-STYLE", f, text, m.start(), s)
                if COLOR_LIT.search(s) and not token_file:
                    add("RAW-COLOR", f, text, m.start(), s)
            for m in re.finditer(r"\b(fill|stroke|color|bgcolor)=[\"'](#[0-9a-fA-F]{3,8}|rgba?\([^)]*\))", body):
                add("RAW-COLOR", f, text, m.start(), m.group())
            if not any(f == x or match_any(f, [x]) for x in fmt_files):
                for m in re.finditer(r"strftime\(|\.toFixed\(|\.toLocaleString\(|\.toPrecision\(|\|\s*round\b|"
                                     r"\"%[-0-9.]*[dfe]\"\s*\|\s*format|\{:[,.0-9]*[dfe%]\}|new Intl\.NumberFormat", body):
                    add("INLINE-FORMAT", f, text, m.start(), line_text(body, m.start()))
            for m in re.finditer(r"lorem ipsum|\bJohn Doe\b|\bJane Doe\b|\bUser \d\b|\bfoo@|placeholder text", body, re.I):
                add("PLACEHOLDER", f, text, m.start(), m.group())
            for m in EMOJI_RX.finditer(body):
                add("EMOJI", f, text, m.start(), line_text(body, m.start()))
            if not in_lib(f):
                for comp_name, rx in raw.items():
                    for m in re.finditer(rx, body):
                        add("RAW-ELEMENT", f, text, m.start(), f"{comp_name}: {body[m.start():m.start() + 60].splitlines()[0]}")
            for d in deprecated:
                for m in re.finditer(rf"(\bimport\b[^\n]*\b{re.escape(d)}\b|\b{re.escape(d)}\(|<{re.escape(d)}[\s/>])", body):
                    add("DEPRECATED", f, text, m.start(), m.group())
        if is_script and not token_file:
            for m in re.finditer(r"['\"`](#[0-9a-fA-F]{6}|#[0-9a-fA-F]{3}|rgba?\([^)]*\))['\"`]", text):
                add("RAW-COLOR", f, text, m.start(), line_text(text, m.start()))

    if a.diff:
        mb = git("merge-base", a.diff, "HEAD").stdout.strip() or a.diff
        cache = {}
        for rule, hs in hits.items():
            for h in hs:
                if h["file"] not in cache:
                    r = git("show", f"{mb}:{h['file']}")
                    cache[h["file"]] = {ln.strip() for ln in r.stdout.splitlines()} if r.returncode == 0 else set()
                line = read(h["file"]).splitlines()[h["line"] - 1].strip() if h["line"] <= len(read(h["file"]).splitlines()) else ""
                h["attr"] = "PRE-EXISTING" if line in cache[h["file"]] else "NEW"

    if a.json:
        json.dump({"hits": hits, "stats": {k: dict(v) for k, v in stats.items()}}, sys.stdout, indent=1)
        return 1 if any(sev.get(r, "warn") in ("error", "warn") and hs for r, hs in hits.items()) else 0

    scope = (f"diff vs {a.diff}" if a.diff else "whole repo") + (f", paths {' '.join(a.paths)}" if a.paths else "")
    print(f"scope: {scope} — {len(files)} files; token files: {', '.join(tfiles) or '-'}; "
          f"component dirs: {', '.join(comp_dirs) or '- (set component_dirs)'}\n")
    levels = {"error": 0, "warn": 1, "info": 2}
    bad, pre_only = 0, []
    for rule in sorted(hits, key=lambda r: (levels.get(sev.get(r, "warn"), 1), -len(hits[r]))):
        hs = hits[rule]
        level = sev.get(rule, "warn")
        new = sum(1 for h in hs if h["attr"] == "NEW")
        if level in ("error", "warn"):
            bad += new if a.diff else len(hs)
        if a.diff and not new:
            pre_only.append(f"{rule} {len(hs)}")
            continue
        print(f"## {rule} ({level}) — {len(hs)} hits" + (f" ({new} NEW)" if a.diff else "")
              + f" in {len({h['file'] for h in hs})} files")
        shown = [h for h in hs if not a.diff or h["attr"] == "NEW"] or hs
        for h in shown[:a.max_hits]:
            print(f"  {h['file']}:{h['line']}" + (f" [{h['attr']}]" if h["attr"] else "") + f"  {h['text']}")
        if len(shown) > a.max_hits:
            top = Counter(h["file"] for h in shown).most_common(3)
            print(f"  … {len(shown) - a.max_hits} more; most in " + ", ".join(f"{f} ({n})" for f, n in top))
        print(f"  why: {WHY.get(rule, '')}\n")
    if pre_only:
        print("## Pre-existing only (in the changed files, not caused by this change): " + ", ".join(pre_only) + "\n")
    print("## Drift index (distinct literal values in styles — lower is closer to one source)")
    print(f"  colours {len(stats['colours'])}, font-size values {len(stats['font_sizes'])}, "
          f"border-radius values {len(stats['radii'])}")
    if stats["font_sizes"]:
        print("  font sizes: " + ", ".join(f"{k}×{v}" for k, v in stats["font_sizes"].most_common(12)))
    if stats["radii"]:
        print("  radii: " + ", ".join(f"{k}×{v}" for k, v in stats["radii"].most_common(8)))
    if not hits:
        print("\nno drift found.")
    return 1 if bad else 0


# ---------------------------------------------------------------- contrast
FG_RX = re.compile(r"(text|fg|ink|foreground|muted|faint|label|link|heading|caption|placeholder|^--on-|-on-)", re.I)
BG_RX = re.compile(r"(bg|background|surface|ground|panel|card|raised|canvas|frame|body|base|sheet|well|fill)", re.I)
SKIP_RX = re.compile(r"(border|rule|shadow|outline|ring|grid|divider|radius|size|space|gap|width|height|font|weight|"
                     r"duration|ease|z-)", re.I)


def cmd_contrast(a):
    cfg = load_config(a.config)
    tok = Tokens(cfg, repo_files(cfg))
    themes = ["base"] + (["dark"] if any(d[2] == "dark" for ds in tok.defs.values() for d in ds) else [])
    pairs = [tuple(p.split(":", 1)) for p in a.pair] + [tuple(p.split(":", 1)) for p in cfg.get("contrast_pairs", [])]
    names = [n for n, ds in tok.defs.items() if any(d[2] in ("base", "dark") for d in ds) and not SKIP_RX.search(n)]
    auto = not pairs
    if auto:
        sem = [n for n in names if not is_primitive(n, cfg)]
        fgs = [n for n in sem if FG_RX.search(n) and not re.search(r"on-|inverse|inverted|on_", n)]
        bgs = [n for n in sem if BG_RX.search(n) and not FG_RX.search(n) and not re.search(r"hover|active|selected|pressed|disabled", n)]
        pairs = [(f, b) for f in fgs for b in bgs]
        # status pairs: --x-bg with --x-text / --x-ink / --x-fg
        for n in names:
            m = re.match(r"^(--.+?)-(bg|background|light|tint)$", n)
            if m:
                for suf in ("text", "ink", "fg", "foreground", "dark", "strong"):
                    if f"{m.group(1)}-{suf}" in tok.defs:
                        pairs.append((f"{m.group(1)}-{suf}", n))
    if not pairs:
        print("no text/surface token pairs found — pass --pair --text-primary:--surface or set contrast_pairs")
        return 2
    fails, rows, unresolved = 0, [], set()
    for theme in themes:
        vals = tok.resolve(theme)
        ground = (255, 255, 255, 1) if theme == "base" else (0, 0, 0, 1)
        for fg, bg in pairs:
            cf, cb = parse_color(resolve_value(vals.get(fg), vals)), parse_color(resolve_value(vals.get(bg), vals))
            if not cf or not cb:
                unresolved.add(fg if not cf else bg)
                continue
            cb = over(cb, ground)
            r = ratio(over(cf, cb), cb)
            level = "FAIL" if r < 3 else "LARGE-ONLY" if r < 4.5 else "ok"
            if level != "ok":
                fails += 1
            rows.append((theme, r, level, fg, bg))
    for theme in themes:
        tr = sorted([r for r in rows if r[0] == theme], key=lambda r: r[1])
        bad = [r for r in tr if r[2] != "ok"]
        print(f"## theme: {theme} — {len(tr)} pairs, {len(bad)} below 4.5:1")
        show = tr if a.all else (bad[:15] if auto else bad)
        for _, r, level, fg, bg in show:
            print(f"  {r:5.2f}  {level:<10} {fg} on {bg}")
        if len(show) < len(bad):
            print(f"  … {len(bad) - len(show)} more (--all)")
        print()
    if unresolved:
        print(f"unresolved (not a literal colour after var() resolution): {', '.join(sorted(unresolved)[:12])}")
    print("auto-pairs are every text-like token on every surface-like token: a FAIL for a pair the design never "
          "uses is noise — pin real pairs in contrast_pairs.") if not a.pair and not cfg.get("contrast_pairs") else None
    return 1 if fails else 0


# ---------------------------------------------------------------- components
def component_defs(files, cfg):
    defs = defaultdict(list)
    for f in files:
        if is_test(f):
            continue
        if f.endswith((".html", ".jinja", ".jinja2", ".j2", ".njk", ".twig")):
            for m in re.finditer(r"\{%-?\s*macro\s+(\w+)\s*\(", read(f)):
                defs[m.group(1)].append((f, line_of(read(f), m.start())))
        elif f.endswith((".jsx", ".tsx", ".js", ".ts")) and not f.endswith(".d.ts"):
            t = read(f)
            for m in re.finditer(r"export\s+(?:default\s+)?(?:function|const|class)\s+([A-Z][A-Za-z0-9]+)", t):
                if re.search(r"return\s*\(?\s*<|=>\s*\(?\s*<|React\.|jsx", t):
                    defs[m.group(1)].append((f, line_of(t, m.start())))
            for m in re.finditer(r"customElements\.define\(\s*['\"]([\w-]+)['\"]", t):
                defs[m.group(1)].append((f, line_of(t, m.start())))
        elif f.endswith((".vue", ".svelte")):
            defs[os.path.splitext(os.path.basename(f))[0]].append((f, 1))
    return defs


def cmd_components(a):
    cfg = load_config(a.config)
    files = repo_files(cfg)
    defs = component_defs(files, cfg)
    comp_dirs = cfg.get("component_dirs", [])
    markup = [f for f in files if f.endswith(MARKUP_EXT + SCRIPT_EXT) and not is_test(f)]
    uses = Counter()
    for f in markup:
        body = blank_comments(read(f), css=False)
        for name in defs:
            if "-" in name:
                n = len(re.findall(rf"<{re.escape(name)}[\s/>]", body))
            elif name[0].isupper():
                kebab = re.sub(r"(?<!^)([A-Z])", r"-\1", name).lower()
                n = len(re.findall(rf"<{name}[\s/>]", body)) + (len(re.findall(rf"<{kebab}[\s/>]", body)) if f.endswith(".vue") else 0)
            else:
                n = len(re.findall(rf"(?<![\w.]){re.escape(name)}\(", body)) - len(re.findall(rf"macro\s+{re.escape(name)}\(", body))
            uses[name] += max(0, n)
    print(f"components: {len(defs)} defined in {len({f for ds in defs.values() for f, _ in ds})} files\n")
    bad = 0
    dup = {n: ds for n, ds in defs.items() if len({f for f, _ in ds}) > 1}
    if dup:
        print(f"## DUPLICATE (warn) — {len(dup)} names defined in more than one file (one component, one home)")
        for n, ds in sorted(dup.items()):
            print(f"  {n}: " + ", ".join(f"{f}:{ln}" for f, ln in ds[:4]))
        bad += len(dup)
        print()
    if comp_dirs:
        lib = [f for f in files if any(f.startswith(d.rstrip("/") + "/") for d in comp_dirs)]
        shadows = []
        for lf in lib:
            tail = "/".join(lf.split("/")[-2:])
            for f in files:
                if f != lf and f.endswith("/" + tail) and f not in lib and not is_test(f):
                    shadows.append((f, lf))
        if shadows:
            print(f"## SHADOW (warn) — {len(shadows)} files with a library template's path (a loader may pick the copy)")
            for f, lf in shadows[:20]:
                print(f"  {f}  shadows  {lf}")
            bad += len(shadows)
            print()
    for d in cfg.get("deprecated", []):
        if uses.get(d):
            print(f"## DEPRECATED (warn) — {d} used {uses[d]}×")
            bad += 1
    print("## Usage (most used first)")
    for n, c in sorted(uses.items(), key=lambda x: -x[1])[:a.max_hits]:
        print(f"  {c:>5}  {n}  ({defs[n][0][0]})")
    unused = sorted(n for n in defs if not uses.get(n))
    if unused:
        print(f"\n## UNUSED (info) — {len(unused)}: {', '.join(unused[:30])}" + (" …" if len(unused) > 30 else ""))
        print("  (a component used only by the gallery/stories, or only through a dynamic name, shows here too)")
    return 1 if bad else 0


# ---------------------------------------------------------------- report
def cmd_report(a):
    bad = 0
    merged = defaultdict(list)
    for p in a.files:
        try:
            data = json.load(open(p, encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as e:
            die(f"{p}: {e}")
        label = f"{data.get('viewport', '?')} {data.get('scheme', '')}".strip()
        print(f"# {p} — {data.get('url', '')} [{label}]")
        st = data.get("stats", {})
        if st:
            print("  stats: " + "; ".join(f"{k}: {v}" for k, v in st.items() if not isinstance(v, (dict, list)) or len(str(v)) < 120))
        for fd in data.get("findings", []):
            merged[fd["id"]].append((label, fd))
        print()
    lv = {"FAIL": 0, "WARN": 1, "INFO": 2}
    for fid, items in sorted(merged.items(), key=lambda x: min(lv.get(i[1]["level"], 2) for i in x[1])):
        level = min((i[1]["level"] for i in items), key=lambda l: lv.get(l, 2))
        if level in ("FAIL", "WARN"):
            bad += 1
        print(f"## {fid} ({level}) — " + ", ".join(f"{lab}: {fd.get('count', 0)}" for lab, fd in items))
        print(f"  {items[0][1].get('why', '')}")
        for lab, fd in items:
            for s in fd.get("samples", [])[:a.max_hits]:
                print(f"  [{lab}] {s.get('sel', '')}  {s.get('detail', '')}  “{s.get('text', '')[:60]}”")
        print()
    if not merged:
        print("probe: no findings.")
    return 1 if bad else 0


def main():
    p = argparse.ArgumentParser(description="Check a UI against its design system (read-only).")
    p.add_argument("--config", default=".claude/uidesign.json")
    sub = p.add_subparsers(dest="sub", required=True)
    sub.add_parser("sources")
    s = sub.add_parser("tokens"); s.add_argument("--all", action="store_true"); s.add_argument("--max-hits", type=int, default=15)
    s = sub.add_parser("lint"); s.add_argument("paths", nargs="*"); s.add_argument("--diff")
    s.add_argument("--max-hits", type=int, default=8); s.add_argument("--json", action="store_true")
    s = sub.add_parser("contrast"); s.add_argument("--pair", action="append", default=[]); s.add_argument("--all", action="store_true")
    s = sub.add_parser("components"); s.add_argument("--max-hits", type=int, default=25)
    s = sub.add_parser("report"); s.add_argument("files", nargs="+"); s.add_argument("--max-hits", type=int, default=5)
    a = p.parse_args()
    if a.sub != "report" and git("rev-parse", "--git-dir").returncode != 0:
        die("run inside a git repository")
    sys.exit({"sources": cmd_sources, "tokens": cmd_tokens, "lint": cmd_lint, "contrast": cmd_contrast,
              "components": cmd_components, "report": cmd_report}[a.sub](a))


if __name__ == "__main__":
    main()
