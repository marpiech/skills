#!/usr/bin/env python3
"""audit.py — run a project's check catalogue over the code and score the findings (stdlib + git).

  audit.py run [--checks FILE] [--scope PATH ...] [--diff BASE] [--only CAT,...] [--max-hits N] [--json]
      Run every grep-style check in the catalogue (default .claude/audit-checks.json; the
      skill's templates/audit-checks.template.json is a starting point) plus the built-in
      generic checks. With --diff BASE only files changed since BASE are scanned and every
      hit is ATTRIBUTED: NEW (the line is not in BASE's version of the file) or PRE-EXISTING.
      Output: hits per check, category totals, priority score, and checks with zero hits
      (candidates for the self-update review). Read-only.

  audit.py sizes [--scope PATH ...] [--warn 500] [--must 800] [--ext .py,.ts,...]
      Oversized source files ("god files"); results above 5000 lines are flagged as
      probably generated or vendored.

Catalogue format (JSON):
  {"categories": {"A": {"name": "Security", "I": 10, "NR": 9, "IR": 2}, ...},
   "exclude": ["tests/", "migrations/", "node_modules/"],          # applied to every check
   "checks": [{"id": "A1", "cat": "A", "title": "...", "regex": "...",
               "include": ["*.py"], "exclude": ["*/config.py"], "flags": "i",
               "why": "...", "decided": "exemptions and the decision they came from",
               "per_file": false}]}          # true = one hit per matching file (naming checks)

Priority = Importance x Not-implementing risk / Implementing risk  (I, NR, IR in 1..10).
Category adjustments: >10 hits → I+1 (max 10). Checks are hints; every hit is read
before it is reported as a violation.
"""
import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys

DEFAULT_EXCLUDE = ["node_modules/", "venv/", ".venv/", "__pycache__/", "dist/", "build/", "vendor/",
                   "external/", ".git/", "*.min.js", "*.lock", "package-lock.json"]
BUILTIN = {
    "categories": {
        "S": {"name": "Secrets in code", "I": 10, "NR": 9, "IR": 2},
        "Q": {"name": "Stale markers", "I": 3, "NR": 2, "IR": 1},
    },
    "checks": [
        {"id": "S1", "cat": "S", "title": "literal credential assignment",
         "regex": r"(?i)(password|passwd|secret|api[_-]?key|token)\w*\s*[:=]\s*['\"][A-Za-z0-9+/_\-]{12,}['\"]",
         "include": ["*.py", "*.js", "*.ts", "*.go", "*.rb", "*.java", "*.kt", "*.cs", "*.php", "*.yml", "*.yaml", "*.json", "*.toml"],
         "exclude": ["tests/", "test/", "*.example*", "*.sample*", "*.template*"],
         "why": "credentials belong in the secrets backend"},
        {"id": "S2", "cat": "S", "title": "private key or cloud key material",
         "regex": r"-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,}",
         "include": ["*"], "exclude": [], "why": "never commit key material"},
        {"id": "Q1", "cat": "Q", "title": "TODO / FIXME / HACK / XXX markers",
         "regex": r"(#|//|/\*|<!--)\s*(TODO|FIXME|HACK|XXX)\b",
         "include": ["*.py", "*.js", "*.ts", "*.tsx", "*.go", "*.rs", "*.rb", "*.java", "*.kt", "*.html", "*.css"],
         "exclude": [], "why": "stale intentions; each one is either a ticket or a deletion"},
    ],
}


def git(*a):
    return subprocess.run(["git", *a], capture_output=True, text=True)


def files_in(scopes, base):
    if base:
        r = git("diff", "--name-only", "--diff-filter=AMR", f"{base}...HEAD")
        if r.returncode != 0:
            sys.exit(f"audit: cannot diff against {base}")
        fs = set(r.stdout.split()) | set(git("diff", "--name-only", "--diff-filter=AMR", "HEAD").stdout.split())
        fs |= set(git("ls-files", "--others", "--exclude-standard").stdout.split())
    else:
        fs = set(git("ls-files", "--cached", "--others", "--exclude-standard").stdout.split())
    if scopes:
        fs = {f for f in fs if any(f == s.rstrip("/") or f.startswith(s.rstrip("/") + "/") for s in scopes)}
    return sorted(f for f in fs if os.path.isfile(f))


def match_any(path, patterns):
    for p in patterns:
        if p.endswith("/"):
            if path.startswith(p) or f"/{p}" in f"/{path}":
                return True
        elif fnmatch.fnmatch(path, p) or fnmatch.fnmatch(os.path.basename(path), p):
            return True
    return False


def base_lines(base, path, cache={}):
    key = (base, path)
    if key not in cache:
        mb = git("merge-base", base, "HEAD").stdout.strip() or base
        r = git("show", f"{mb}:{path}")
        cache[key] = set(ln.strip() for ln in r.stdout.splitlines()) if r.returncode == 0 else set()
    return cache[key]


def load_catalogue(path):
    cat = {"categories": dict(BUILTIN["categories"]), "checks": list(BUILTIN["checks"]), "exclude": list(DEFAULT_EXCLUDE)}
    if path and os.path.exists(path):
        user = json.load(open(path, encoding="utf-8"))
        cat["categories"].update(user.get("categories", {}))
        ids = {c["id"] for c in user.get("checks", [])}
        cat["checks"] = [c for c in cat["checks"] if c["id"] not in ids] + user.get("checks", [])
        cat["exclude"] += user.get("exclude", [])
        for b in user.get("disable_builtin", []):
            cat["checks"] = [c for c in cat["checks"] if c["id"] != b]
    elif path:
        print(f"(no catalogue at {path} — built-in generic checks only; start from templates/audit-checks.template.json)",
              file=sys.stderr)
    return cat


def cmd_run(a):
    cat = load_catalogue(a.checks)
    files = files_in(a.scope, a.diff)
    only = set(a.only.split(",")) if a.only else None
    texts, results = {}, []
    for chk in cat["checks"]:
        if only and chk["cat"] not in only and chk["id"] not in only:
            continue
        try:
            rx = re.compile(chk["regex"], re.I if "i" in chk.get("flags", "") else 0)
        except re.error as e:
            print(f"BAD-REGEX {chk['id']}: {e}")
            continue
        inc, exc = chk.get("include", ["*"]), cat["exclude"] + chk.get("exclude", [])
        hits = []
        for f in files:
            if not match_any(f, inc) or match_any(f, exc):
                continue
            if f not in texts:
                try:
                    texts[f] = open(f, encoding="utf-8", errors="replace").read().splitlines()
                except OSError:
                    texts[f] = []
            if chk.get("per_file"):  # the file itself is the finding (naming, presence)
                if rx.search("\n".join(texts[f])):
                    hits.append({"file": f, "line": 1, "text": "(file)", "attr": ""})
                continue
            for i, ln in enumerate(texts[f], 1):
                if rx.search(ln):
                    tag = ""
                    if a.diff:
                        tag = "PRE-EXISTING" if ln.strip() in base_lines(a.diff, f) else "NEW"
                    hits.append({"file": f, "line": i, "text": ln.strip()[:160], "attr": tag})
        results.append({**chk, "hits": hits})

    if a.json:
        json.dump(results, sys.stdout, indent=1)
        return 0
    scope = (f"diff vs {a.diff}" if a.diff else "whole repo") + (f", paths {', '.join(a.scope)}" if a.scope else "")
    print(f"scope: {scope} — {len(files)} files, {len(results)} checks\n")
    per_cat = {}
    for r in results:
        n = len(r["hits"])
        new = sum(1 for h in r["hits"] if h["attr"] == "NEW")
        per_cat.setdefault(r["cat"], [0, 0])
        per_cat[r["cat"]][0] += n
        per_cat[r["cat"]][1] += new
        if not n:
            continue
        print(f"## {r['id']} [{r['cat']}] {r['title']} — {n} hits" + (f" ({new} NEW)" if a.diff else ""))
        shown = [h for h in r["hits"] if not a.diff or h["attr"] == "NEW"] or r["hits"]
        for h in shown[:a.max_hits]:
            print(f"  {h['file']}:{h['line']}" + (f" [{h['attr']}]" if h["attr"] else "") + f"  {h['text']}")
        if len(shown) > a.max_hits:
            print(f"  … {len(shown) - a.max_hits} more")
        if r.get("why"):
            print(f"  why: {r['why']}")
    print("\n## Category scores (before reading the hits — adjust after triage)")
    rows = []
    for c, (n, new) in per_cat.items():
        if not n:
            continue
        meta = cat["categories"].get(c, {"name": c, "I": 5, "NR": 5, "IR": 5})
        imp = min(10, meta["I"] + (1 if n > 10 else 0))
        score = imp * meta["NR"] / max(1, meta["IR"])
        rows.append((score, c, meta["name"], n, new))
    for score, c, name, n, new in sorted(rows, reverse=True):
        print(f"  {score:5.1f}  {c} {name}: {n} hits" + (f", {new} NEW" if a.diff else ""))
    zero = [r["id"] for r in results if not r["hits"]]
    if zero:
        note = " in this diff (only a whole-repo run says a check is stale)" if a.diff else \
            " — regression guards, or stale patterns? (self-update review)"
        print(f"\nzero-hit checks ({len(zero)}): {', '.join(zero)}{note}")
    return 1 if any(r["hits"] for r in results) else 0


def cmd_sizes(a):
    exts = tuple(a.ext.split(","))
    rows = []
    for f in files_in(a.scope, None):
        if not f.endswith(exts) or match_any(f, DEFAULT_EXCLUDE + ["tests/", "test/", "migrations/"]):
            continue
        try:
            n = sum(1 for _ in open(f, encoding="utf-8", errors="replace"))
        except OSError:
            continue
        if n > a.warn:
            rows.append((n, f))
    for n, f in sorted(rows, reverse=True):
        flag = "CHECK (generated/vendored?)" if n > 5000 else "MUST-SPLIT" if n > a.must else "large"
        print(f"{n:>6}  {flag:<27} {f}")
    print(f"{len(rows)} files over {a.warn} lines")
    return 1 if rows else 0


def main():
    p = argparse.ArgumentParser(description="Run a project's audit catalogue (read-only).")
    sub = p.add_subparsers(dest="sub", required=True)
    s = sub.add_parser("run"); s.add_argument("--checks", default=".claude/audit-checks.json")
    s.add_argument("--scope", nargs="*", default=[]); s.add_argument("--diff")
    s.add_argument("--only"); s.add_argument("--max-hits", type=int, default=10); s.add_argument("--json", action="store_true")
    s = sub.add_parser("sizes"); s.add_argument("--scope", nargs="*", default=[])
    s.add_argument("--warn", type=int, default=500); s.add_argument("--must", type=int, default=800)
    s.add_argument("--ext", default=".py,.ts,.tsx,.js,.go,.rs,.java,.kt,.rb,.cs,.php")
    a = p.parse_args()
    if git("rev-parse", "--git-dir").returncode != 0:
        sys.exit("audit: run inside a git repository")
    sys.exit({"run": cmd_run, "sizes": cmd_sizes}[a.sub](a))


if __name__ == "__main__":
    main()
