#!/usr/bin/env python3
"""docs-check.py — read-only documentation checks (python3 stdlib; `git`, optional `gh`).

  docs-check.py impact [--base REF] [--map FILE]
      Which documentation pages does the current change probably affect?
      Changed files = `git diff --name-only <base>...HEAD` + uncommitted changes.
      Map format: see templates/doc-impact-map.template.json. With "docs_repo":
        "owner/name"   → page dates come from the GitHub API (`gh api`);
        "../path"      → page dates come from that local checkout (`git log`).
      Same repository → a rule is OPEN when none of its pages changed too.
      Other repository → a rule is OPEN when a page is older than the newest
      matching code change. A prompt, not a gate (date checks give false positives).

  docs-check.py links  DIR...
      Relative links/images in *.md that point at missing files (code fences and
      inline code are ignored; http(s)/mailto and pure #anchors are skipped).

  docs-check.py nav    NAV_FILE [--root DIR] [--exclude PATH ...]
      NAV_FILE is SUMMARY.md-style markdown links or an mkdocs.yml `nav:`.
      DEAD-NAV = entry pointing at a missing page; UNLISTED = page not in the nav
      (on many platforms an unlisted page is silently invisible).

  docs-check.py size   FILE... [--limit CHARS]
      Character budget per file (default 20000) — for always-loaded agent docs.

  docs-check.py style  DIR... [--max-words N] [--reject 'bad=good' ...] [--british]
      Advisory prose lint: inflated words, sentences longer than N words (default 25),
      rejected terms from the project's terminology table, British spellings.

Exit codes: 0 = nothing found, 1 = findings, 2 = usage / environment problem.
"""
import argparse
import glob
import json
import os
import re
import subprocess
import sys

FENCE = re.compile(r"(^|\n)(```|~~~).*?\n\2[^\n]*", re.S)
INLINE = re.compile(r"`[^`\n]*`")
LINK = re.compile(r"!?\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
INFLATED = re.compile(
    r"\b(utili[sz]e[sd]?|utili[sz]ing|facilitate[sd]?|leverage[sd]?|commence[sd]?|terminate[sd]?|"
    r"endeavou?r|ascertain|numerous|aforementioned|herein|therein|whilst|amongst|prior to|"
    r"subsequent to|in order to|approximately|a number of|seamless(ly)?|powerful|robust|"
    r"intuitive|enterprise-grade)\b", re.I)
BRITISH = re.compile(
    r"\b(analys(e|ed|ing)|organis\w*|summaris\w*|optimis\w*|customis\w*|behaviour|colour|"
    r"licence|centre|catalogue|labelled|fulfil|enrol|tumour)\b", re.I)


AGENT_FILES = {"CLAUDE.md", "CLAUDE.local.md", "MEMORY.md", "AGENTS.md"}


def run(*cmd, cwd=None):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)


def strip_code(text):
    return INLINE.sub("", FENCE.sub("\n", text))


def md_files(dirs):
    out = []
    for d in dirs:
        if os.path.isfile(d):
            out.append(d)
        else:
            out += sorted(glob.glob(os.path.join(d, "**", "*.md"), recursive=True))
    return [f for f in out if "/node_modules/" not in f and "/.git/" not in f]


# ---------------------------------------------------------------- impact
def resolve_base(base):
    for cand in [base] + (["origin/main", "origin/master", "main", "master"] if base == "origin/HEAD" else []):
        if run("git", "rev-parse", "--verify", "--quiet", cand).returncode == 0:
            return cand
    print(f"docs-check: base {base} not found — pass --base <branch or commit>", file=sys.stderr)
    sys.exit(2)


def changed_files(base):
    files = set()
    r = run("git", "diff", "--name-only", f"{base}...HEAD")
    if r.returncode != 0:
        print(f"docs-check: cannot diff against {base}: {r.stderr.strip()[:200]}", file=sys.stderr)
        sys.exit(2)
    files.update(r.stdout.split())
    files.update(run("git", "diff", "--name-only", "HEAD").stdout.split())
    for ln in run("git", "status", "--porcelain", "--untracked-files=all").stdout.splitlines():
        files.add(ln[3:].split(" -> ")[-1])
    return sorted(f for f in files if f)


def last_change(path, cwd=None):
    return run("git", "log", "-1", "--format=%cI", "--", path, cwd=cwd).stdout.strip()


def page_date(docs_repo, page):
    if docs_repo.startswith((".", "/", "~")):
        return last_change(page, cwd=os.path.expanduser(docs_repo))
    r = run("gh", "api", f"repos/{docs_repo}/commits?path={page}&per_page=1",
            "--jq", ".[0].commit.committer.date")
    return r.stdout.strip()


def cmd_impact(a):
    if not os.path.isfile(a.map):
        print(f"no map at {a.map} — judge by hand: new commands, endpoints, UI, config keys, "
              "behaviour users can see? (template: templates/doc-impact-map.template.json)")
        return 2
    m = json.load(open(a.map, encoding="utf-8"))
    a.base = resolve_base(a.base)
    files, docs_repo, opened = changed_files(a.base), m.get("docs_repo"), 0
    print(f"{len(files)} changed files vs {a.base}" + (f"; docs live in {docs_repo}" if docs_repo else ""))
    for rule in m.get("rules", []):
        hits = [f for f in files if f.startswith(rule["match"])
                and os.path.basename(f) not in AGENT_FILES]  # agent notes are not product surface
        pages = rule.get("doc_pages", [])
        if not hits or not pages:
            continue
        if not docs_repo:
            stale = [p for p in pages if p not in files]
            is_open = len(stale) == len(pages)
        else:
            code_date = max((last_change(f) for f in hits), default="") or "9999"  # uncommitted = now
            stale = []
            for p in pages:
                d = page_date(docs_repo, p)
                if not d or d < code_date:
                    stale.append(f"{p} (last change {d[:10] or 'never'})")
            is_open = bool(stale)
        if is_open:
            opened += 1
            print(f"OPEN  {rule['match']}  ({len(hits)} files: {', '.join(hits[:3])}"
                  f"{'…' if len(hits) > 3 else ''})\n      → {', '.join(stale)}"
                  + (f"\n      note: {rule['note']}" if rule.get("note") else ""))
    if not opened:
        print("no open documentation impact")
    return 1 if opened else 0


# ---------------------------------------------------------------- links
def local_target(src, href):
    if re.match(r"^[a-z][a-z0-9+.-]*:", href, re.I) or href.startswith(("#", "/")) or "{" in href:
        return None
    path = href.split("#")[0].split("?")[0].replace("\\", "")  # markdown escapes: a\_b
    return os.path.normpath(os.path.join(os.path.dirname(src), path)) if path else None


def cmd_links(a):
    bad = 0
    for f in md_files(a.dirs):
        text = strip_code(open(f, encoding="utf-8", errors="replace").read())
        for href in LINK.findall(text):
            t = local_target(f, href)
            if t and not os.path.exists(t):
                print(f"DEAD-LINK {f}: {href}")
                bad += 1
    print(f"{bad} dead links")
    return 1 if bad else 0


# ---------------------------------------------------------------- nav
def nav_entries(nav):
    text = open(nav, encoding="utf-8").read()
    if nav.endswith((".yml", ".yaml")):
        part = text.split("\nnav:", 1)[-1] if "\nnav:" in text else text
        return re.findall(r"^\s*-\s*(?:[^:\n]+:\s*)?['\"]?([^\s:'\"]+\.md)['\"]?\s*$", part, re.M)
    return [h for h in LINK.findall(strip_code(text)) if local_target(nav, h)]


def cmd_nav(a):
    root = a.root or os.path.dirname(a.nav) or "."
    entries = nav_entries(a.nav)
    base = root if a.nav.endswith((".yml", ".yaml")) else os.path.dirname(a.nav) or "."
    listed = {os.path.normpath(os.path.join(base, e.split("#")[0].strip())) for e in entries}
    bad = 0
    for p in sorted(listed):
        if not os.path.exists(p):
            print(f"DEAD-NAV {p}")
            bad += 1
    skip = {os.path.normpath(a.nav)}
    excl = [os.path.normpath(os.path.join(root, e)) for e in a.exclude or []]
    for p in md_files([root]):
        n = os.path.normpath(p)
        name = os.path.basename(n)
        if n in listed or n in skip or name in AGENT_FILES or name.startswith(("_", ".")):
            continue
        if any(n == e or n.startswith(e + os.sep) for e in excl):
            continue  # not published (legacy, internal, another space)
        print(f"UNLISTED {n}")
        bad += 1
    print(f"{len(listed)} nav entries, {bad} findings")
    return 1 if bad else 0


# ---------------------------------------------------------------- size
def cmd_size(a):
    bad = 0
    for f in a.files:
        n = len(open(f, encoding="utf-8", errors="replace").read())
        flag = "OVER" if n > a.limit else "ok  "
        bad += n > a.limit
        print(f"{flag} {n:>7}  {f}")
    return 1 if bad else 0


# ---------------------------------------------------------------- style
def prose_paragraphs(text):
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", strip_code(text))
    text = re.sub(r"\{[%{][^}\n]*[%}]\}|\{[^}\n]*\}", "", text)  # template tags, attr lists
    text = re.sub(r"^---\n.*?\n---\n", "", text, flags=re.S)       # front matter
    for block in re.split(r"\n\s*\n", text):
        b = block.strip()
        if b and b[0] not in "#|>-*!<" and not re.match(r"^\d+\.\s", b):
            yield " ".join(b.split())


def cmd_style(a):
    rejects = []
    for r in a.reject or []:
        bad_term, _, good = r.partition("=")
        rejects.append((re.compile(r"\b" + re.escape(bad_term.strip()) + r"\b", re.I), good.strip()))
    hits = 0
    for f in md_files(a.dirs):
        raw = open(f, encoding="utf-8", errors="replace").read()
        plain = strip_code(raw)
        for i, line in enumerate(plain.splitlines(), 1):
            for m in INFLATED.finditer(line):
                print(f"WORD   {f}:{i}: '{m.group(0)}' — use the plain word")
                hits += 1
            if a.british:
                for m in BRITISH.finditer(line):
                    print(f"SPELL  {f}:{i}: '{m.group(0)}' — American spelling")
                    hits += 1
            for rx, good in rejects:
                for m in rx.finditer(line):
                    print(f"TERM   {f}:{i}: '{m.group(0)}' → '{good}'")
                    hits += 1
        for para in prose_paragraphs(raw):
            for s in re.split(r"(?<=[.!?])\s+", para):
                n = len(s.split())
                if n > a.max_words:
                    print(f"LONG   {f}: {n} words :: {s[:90]}")
                    hits += 1
    print(f"{hits} advisory findings — read each one; none is a build gate")
    return 1 if hits else 0


def main():
    p = argparse.ArgumentParser(description="Read-only documentation checks.")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("impact"); s.add_argument("--base", default="origin/HEAD")
    s.add_argument("--map", default=".claude/doc-impact-map.json")
    s = sub.add_parser("links"); s.add_argument("dirs", nargs="+")
    s = sub.add_parser("nav"); s.add_argument("nav"); s.add_argument("--root")
    s.add_argument("--exclude", action="append", help="dir or file (relative to root) that is not published")
    s = sub.add_parser("size"); s.add_argument("files", nargs="+"); s.add_argument("--limit", type=int, default=20000)
    s = sub.add_parser("style"); s.add_argument("dirs", nargs="+")
    s.add_argument("--max-words", type=int, default=25); s.add_argument("--reject", action="append")
    s.add_argument("--british", action="store_true")
    a = p.parse_args()
    sys.exit({"impact": cmd_impact, "links": cmd_links, "nav": cmd_nav,
              "size": cmd_size, "style": cmd_style}[a.cmd](a))


if __name__ == "__main__":
    main()
