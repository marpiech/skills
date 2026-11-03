#!/usr/bin/env python3
"""release.py — pre-release checks for a Python package (python3 stdlib + git).

  release.py version
      Every place the version is declared (pyproject, setup.py, setup.cfg, __init__,
      version.py/_version.py) and whether they agree; flags dynamic versioning.

  release.py check [--base REF] [--name DIST] [--index URL] [--changelog FILE] [--min-python 3.X]
      Preflight: versions agree; version > the latest v* tag (and > REF's version if given);
      tag v<version> not taken locally or on the remote; version not yet on the index;
      the changelog has a section for it (or an Unreleased section to rename); released
      changelog sections unchanged since their tag; package sources parse under the
      oldest supported Python. Exit 0 = ready, 1 = blockers.

  release.py audit DIST_DIR [--deny REGEX] [--allow REGEX] [--max-kb N] [--previous DIR]
      Read the built wheel(s) and sdist(s) WITHOUT installing: file lists, sizes, files that
      should not ship (tests, notebooks, env files, keys, VCS dirs, large data), secret-looking
      strings, project-specific denied terms (customer names, hostnames) minus an allow-list
      of accepted occurrences, wheel-vs-sdist differences, metadata Name/Version, and new
      files compared with a previous release's artifacts. Exit 0 = clean, 1 = findings.

  release.py published --name DIST --version V [--index URL] [--dist DIR]
      Is the version on the index, and do the published files' sha256 match the local
      build? (read-only HTTPS GET of the index's JSON API.)

Network: only `check` (version lookup) and `published` contact the index, default
https://pypi.org (override with --index or RELEASE_INDEX_URL). Nothing is ever uploaded.
"""
import argparse
import ast
import glob
import hashlib
import json
import os
import re
import subprocess
import sys
import tarfile
import urllib.error
import urllib.request
import zipfile

INDEX = os.environ.get("RELEASE_INDEX_URL", "https://pypi.org")
SECRET_RX = re.compile(r"(-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,}|"
                       r"pypi-AgE[A-Za-z0-9_-]{20,}|xox[abpr]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9_-]{20,}|"
                       r"(?i:(?:password|secret|token|api[_-]?key)\w*['\"]?\s*[:=]\s*['\"][^\s'\"$<{]{12,}['\"]))")
UNWANTED = re.compile(r"(^|/)(tests?|testing|\.git|\.github|\.venv|venv|__pycache__|\.pytest_cache|\.ipynb_checkpoints)/|"
                      r"\.ipynb$|(^|/)\.env(\.|$)|\.pem$|\.key$|\.pyc$|(^|/)\.DS_Store$|credentials.*\.json$|"
                      r"service[-_]?account.*\.json$|\.sqlite3?$|\.db$")
TEXT_EXT = (".py", ".txt", ".md", ".rst", ".cfg", ".toml", ".ini", ".json", ".yml", ".yaml", ".html",
            ".js", ".css", ".csv", ".tsv", "PKG-INFO", "METADATA", ".sh", ".j2", ".xml")


def run(*cmd):
    return subprocess.run(cmd, capture_output=True, text=True)


def read(p):
    try:
        return open(p, encoding="utf-8", errors="replace").read()
    except OSError:
        return ""


def vkey(v):
    """Comparable key for PEP 440-ish versions: 1.2.10 > 1.2.9; pre-releases sort before."""
    m = re.match(r"^v?(\d+(?:\.\d+)*)(?:[-_.]?(a|b|rc|alpha|beta|c|pre|preview)[-_.]?(\d*))?"
                 r"(?:[-_.]?(post|rev|r)[-_.]?(\d*))?(?:[-_.]?dev[-_.]?(\d*))?", v.strip(), re.I)
    if not m:
        return (0,)
    nums = [int(x) for x in m.group(1).split(".")] + [0] * 3
    pre = {"a": 0, "alpha": 0, "b": 1, "beta": 1, "c": 2, "rc": 2, "pre": 2, "preview": 2}
    pre_k = (pre[m.group(2).lower()], int(m.group(3) or 0)) if m.group(2) else (9, 0)
    post_k = int(m.group(5) or 0) if m.group(4) else -1
    dev_k = int(m.group(6) or 0) if m.group(6) is not None else 10**9
    return tuple(nums[:6]) + pre_k + (post_k, dev_k)


# ------------------------------------------------------------------ version sources
PATTERNS = [
    ("pyproject.toml", r"(?ms)^\[project\][^\[]*?^version\s*=\s*[\"']([^\"']+)[\"']"),
    ("pyproject.toml", r"(?ms)^\[tool\.poetry\][^\[]*?^version\s*=\s*[\"']([^\"']+)[\"']"),
    ("setup.cfg", r"(?m)^version\s*=\s*([^\s#]+)"),
    ("setup.py", r"(?:\bversion\s*=\s*|PACKAGE_VERSION\s*=\s*|__version__\s*=\s*)[\"']([^\"']+)[\"']"),
]
INLINE = r"(?m)^__version__\s*=\s*[\"']([^\"']+)[\"']"


def version_sources():
    found = []
    for f, rx in PATTERNS:
        m = re.search(rx, read(f))
        if m and "attr:" not in m.group(1) and "file:" not in m.group(1):
            found.append((f, m.group(1)))
    cands = set(glob.glob("src/*/__init__.py") + glob.glob("*/__init__.py") + glob.glob("src/*/*version.py")
                + glob.glob("*/*version.py") + glob.glob("*/__about__.py") + glob.glob("src/*/__about__.py"))
    for f in sorted(cands):
        if "/tests" in f or f.startswith(("tests/", "test/", "docs/")):
            continue
        m = re.search(INLINE, read(f)) or re.search(r"(?m)^(?:VERSION|version)\s*=\s*[\"']([^\"']+)[\"']", read(f))
        if m:
            found.append((f, m.group(1)))
    dynamic = bool(re.search(r"(?m)^dynamic\s*=.*version", read("pyproject.toml"))) or \
        any(k in read("pyproject.toml") + read("setup.py") for k in ("setuptools_scm", "hatch-vcs", "use_scm_version", "versioneer"))
    return found, dynamic


def dist_name():
    for f, rx in (("pyproject.toml", r"(?ms)^\[(?:project|tool\.poetry)\][^\[]*?^name\s*=\s*[\"']([^\"']+)"),
                  ("setup.cfg", r"(?m)^name\s*=\s*(\S+)"), ("setup.py", r"\bname\s*=\s*[\"']([^\"']+)")):
        m = re.search(rx, read(f))
        if m:
            return m.group(1)
    return None


def cmd_version(a):
    found, dynamic = version_sources()
    for f, v in found:
        print(f"{v:<14} {f}")
    if dynamic:
        print("dynamic versioning detected (setuptools_scm / hatch-vcs / attr:) — the TAG is the version")
    vals = {v for _, v in found}
    if not found:
        print("no static version found")
        return 1
    if len(vals) > 1:
        print("DISAGREE: the declarations differ — a build would report a version it was not built as")
        return 1
    print(f"agree: {vals.pop()}")
    return 0


# ------------------------------------------------------------------ check
def tags():
    return [t for t in run("git", "tag", "--list", "v*").stdout.split() if re.match(r"^v\d", t)]


def on_index(name, version, index):
    url = f"{index.rstrip('/')}/pypi/{name}/{version}/json"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "release-check"}), timeout=15) as r:
            return json.load(r)
    except urllib.error.HTTPError as e:
        return None if e.code == 404 else {"_error": f"HTTP {e.code}"}
    except (urllib.error.URLError, OSError) as e:
        return {"_error": str(e)[:100]}


def sections(text):
    """{heading: body} for '## 1.2.3' / '### v1.2.3 (date)' / '## [1.2.3]' style changelogs."""
    out, cur, buf = {}, None, []
    for ln in text.splitlines():
        m = re.match(r"^#{1,4}\s*\[?v?(\d+\.\d+[^\]\s]*|Unreleased)\]?", ln, re.I)
        if m:
            if cur:
                out[cur] = "\n".join(buf).strip()
            cur, buf = m.group(1).lower() if m.group(1).lower() == "unreleased" else m.group(1), []
        elif cur:
            buf.append(ln)
    if cur:
        out[cur] = "\n".join(buf).strip()
    return out


def cmd_check(a):
    block, warn = [], []
    found, dynamic = version_sources()
    vals = sorted({v for _, v in found})
    if len(vals) > 1:
        block.append("version declarations disagree: " + ", ".join(f"{f}={v}" for f, v in found))
    version = found[0][1] if found else None  # the build backend's source (pyproject/setup) comes first
    if dynamic and not version:
        warn.append("dynamic versioning: the tag you push IS the version; checks use the tag you plan")
        version = a.version
    if a.version:
        if version and a.version != version:
            block.append(f"planned version {a.version} != declared {version}")
        version = a.version
    if not version:
        print("BLOCK no version to check (give --version for dynamic versioning)")
        return 1
    print(f"version {version}  ({dist_name() or 'name?'})")

    ts = tags()
    latest = max(ts, key=vkey) if ts else None
    if latest and vkey(version) <= vkey(latest):
        block.append(f"version {version} is not greater than the latest tag {latest}")
    if f"v{version}" in ts:
        block.append(f"tag v{version} already exists locally — that version is (being) released")
    rr = run("git", "ls-remote", "--tags", a.remote, f"refs/tags/v{version}")
    if rr.returncode == 0 and rr.stdout.strip():
        block.append(f"tag v{version} already exists on {a.remote}")
    if a.base:
        base_src = {}
        for f, _ in found:
            r = run("git", "show", f"{a.base}:{f}")
            if r.returncode == 0:
                m = re.search(dict(PATTERNS).get(f, INLINE), r.stdout) or re.search(INLINE, r.stdout)
                if m:
                    base_src[f] = m.group(1)
        bv = next(iter(base_src.values()), None)
        if bv and vkey(version) <= vkey(bv):
            block.append(f"version {version} is not greater than {a.base}'s {bv} — bump it")

    name = a.name or dist_name()
    if name and not a.offline:
        info = on_index(name, version, a.index)
        if info is None:
            print(f"ok    {version} is not on {a.index} yet")
        elif "_error" in info:
            warn.append(f"could not ask {a.index}: {info['_error']}")
        else:
            block.append(f"{name} {version} is ALREADY on {a.index} — versions are immutable; bump")

    cl = a.changelog or next((f for f in ("CHANGELOG.md", "CHANGES.md", "HISTORY.md", "CHANGELOG.rst", "NEWS.md") if os.path.exists(f)), None)
    if cl:
        now = sections(read(cl))
        if version not in now and "unreleased" not in now:
            warn.append(f"{cl} has no section for {version} and no Unreleased section")
        elif version not in now:
            warn.append(f"{cl}: rename 'Unreleased' to {version} as part of the bump")
        for head, body in now.items():  # section X must still read as it did when vX shipped
            if head == "unreleased" or f"v{head}" not in ts:
                continue
            old = run("git", "show", f"v{head}:{cl}")
            if old.returncode == 0 and head in sections(old.stdout) and sections(old.stdout)[head] != body:
                block.append(f"{cl}: released section {head} differs from what shipped in v{head} — released"
                             " notes are as immutable as the release; put new notes under Unreleased")
    else:
        warn.append("no changelog file found")

    if a.min_python:
        major, minor = (int(x) for x in a.min_python.split(".")[:2])
        bad = []
        files = [f for f in run("git", "ls-files", "*.py").stdout.split()
                 if not re.search(r"(^|/)(tests?|docs|examples|scripts)/", f)]
        for f in files:
            try:
                ast.parse(read(f), filename=f, feature_version=(major, minor))
            except SyntaxError as e:
                bad.append(f"{f}:{e.lineno}")
        if bad:
            block.append(f"{len(bad)} files do not parse as Python {a.min_python}: {', '.join(bad[:5])}"
                         " (syntax only — also run the tests on that interpreter)")
        else:
            print(f"ok    {len(files)} files parse as Python {a.min_python} (syntax only)")

    if run("git", "status", "--porcelain", "--untracked-files=no").stdout.strip():
        warn.append("working tree has uncommitted changes — release from a clean, pushed commit")
    for w in warn:
        print(f"WARN  {w}")
    for b in block:
        print(f"BLOCK {b}")
    print("READY" if not block else f"NOT READY ({len(block)} blockers)")
    return 1 if block else 0


# ------------------------------------------------------------------ audit
def members(path):
    """[(name, size, bytes-or-None)] for a wheel or sdist."""
    out = []
    if path.endswith(".whl") or path.endswith(".zip"):
        with zipfile.ZipFile(path) as z:
            for i in z.infolist():
                if not i.is_dir():
                    out.append((i.filename, i.file_size, z.read(i) if i.file_size < 5_000_000 else None))
    else:
        with tarfile.open(path) as t:
            for m in t.getmembers():
                if m.isfile():
                    name = m.name.split("/", 1)[1] if "/" in m.name else m.name  # strip <name>-<ver>/
                    f = t.extractfile(m)
                    out.append((name, m.size, f.read() if f and m.size < 5_000_000 else None))
    return out


def payload(ms):
    """File names minus per-build metadata, so two builds can be compared."""
    return {n for n, _, _ in ms if not n.endswith(("RECORD", "PKG-INFO", "METADATA", "WHEEL"))}


def cmd_audit(a):
    arts = sorted(glob.glob(os.path.join(a.dist, "*.whl")) + glob.glob(os.path.join(a.dist, "*.tar.gz")))
    if not arts:
        print(f"no wheel or sdist in {a.dist} — build first (python -m build)")
        return 2
    deny = re.compile(a.deny, re.I) if a.deny else None
    allow = re.compile(a.allow, re.I) if a.allow else None
    findings, lists = 0, {}
    for art in arts:
        ms = members(art)
        kind = "wheel" if art.endswith(".whl") else "sdist"
        lists[kind] = payload(ms)
        total = sum(s for _, s, _ in ms)
        print(f"\n## {os.path.basename(art)}  ({len(ms)} files, {total // 1024} KiB)")
        for n, s, data in ms:
            if UNWANTED.search(n):
                print(f"UNWANTED  {n}")
                findings += 1
            if s > a.max_kb * 1024:
                print(f"LARGE     {n}  {s // 1024} KiB")
                findings += 1
            if data is None or not (n.endswith(TEXT_EXT) or b"\0" not in data[:1024]):
                continue
            text = data.decode("utf-8", errors="replace")
            if n.endswith(("METADATA", "PKG-INFO")):
                nm = re.search(r"(?m)^Name:\s*(.+)$", text)
                vv = re.search(r"(?m)^Version:\s*(.+)$", text)
                rp = re.search(r"(?m)^Requires-Python:\s*(.+)$", text)
                print(f"metadata  Name={nm.group(1).strip() if nm else '?'} Version={vv.group(1).strip() if vv else '?'}"
                      f" Requires-Python={rp.group(1).strip() if rp else 'UNSET'}")
            for i, ln in enumerate(text.splitlines(), 1):
                if SECRET_RX.search(ln):
                    print(f"SECRET?   {n}:{i} (value not shown)")
                    findings += 1
                if deny:
                    for m in deny.finditer(ln):
                        if allow and allow.search(ln):
                            continue
                        print(f"DENIED    {n}:{i}: '{m.group(0)}'")
                        findings += 1
    if "wheel" in lists and "sdist" in lists:
        extra = sorted(lists["sdist"] - lists["wheel"] - {"setup.py", "setup.cfg", "pyproject.toml", "MANIFEST.in"})
        extra = [e for e in extra if not e.endswith((".egg-info", "SOURCES.txt", "top_level.txt", "dependency_links.txt",
                                                    "requires.txt", "entry_points.txt", "not-zip-safe"))
                 and ".egg-info/" not in e]
        print(f"\nsdist-only files ({len(extra)}) — these ship too, check them: " + ", ".join(extra[:15])
              + (" …" if len(extra) > 15 else ""))
    if a.previous:
        prev = set()
        for art in glob.glob(os.path.join(a.previous, "*.whl")):
            prev |= payload(members(art))
        now = lists.get("wheel", set())
        strip = lambda s: {re.sub(r"^[^/]+-[\d.]+[^/]*\.dist-info/", "dist-info/", x) for x in s}
        new, gone = sorted(strip(now) - strip(prev)), sorted(strip(prev) - strip(now))
        print(f"\nvs previous wheel: {len(new)} new files, {len(gone)} removed")
        for n in new[:30]:
            print(f"NEW       {n}")
        for n in gone[:30]:
            print(f"REMOVED   {n}")
    print(f"\n{findings} findings — every one is read before publishing; a version cannot be replaced")
    return 1 if findings else 0


# ------------------------------------------------------------------ published
def cmd_published(a):
    info = on_index(a.name, a.version, a.index)
    if info is None:
        print(f"NOT PUBLISHED: {a.name} {a.version} is not on {a.index}")
        return 1
    if "_error" in info:
        print(f"could not ask {a.index}: {info['_error']}")
        return 2
    files = info.get("urls", [])
    print(f"PUBLISHED: {a.name} {a.version} on {a.index} ({len(files)} files)")
    local = {os.path.basename(p): hashlib.sha256(open(p, "rb").read()).hexdigest()
             for p in glob.glob(os.path.join(a.dist, "*"))} if a.dist else {}
    bad = 0
    for f in files:
        remote = f.get("digests", {}).get("sha256", "")
        mark = ""
        if local:
            if f["filename"] not in local:
                mark = "  (no local copy)"
            elif local[f["filename"]] == remote:
                mark = "  sha256 matches local build"
            else:
                mark = "  SHA256 DIFFERS from local build"
                bad += 1
        print(f"- {f['filename']}  {f.get('size', '?')} B{' YANKED' if f.get('yanked') else ''}{mark}")
    return 1 if bad else 0


def main():
    p = argparse.ArgumentParser(description="Pre-release checks for a Python package.")
    sub = p.add_subparsers(dest="sub", required=True)
    sub.add_parser("version")
    s = sub.add_parser("check")
    s.add_argument("--base"); s.add_argument("--name"); s.add_argument("--version")
    s.add_argument("--index", default=INDEX); s.add_argument("--changelog"); s.add_argument("--min-python")
    s.add_argument("--remote", default="origin"); s.add_argument("--offline", action="store_true")
    s = sub.add_parser("audit"); s.add_argument("dist")
    s.add_argument("--deny", help="regex of terms that must not ship (customer names, hosts, ids)")
    s.add_argument("--allow", help="regex matching LINES where a denied term is accepted (recorded decision)")
    s.add_argument("--max-kb", type=int, default=1024); s.add_argument("--previous")
    s = sub.add_parser("published"); s.add_argument("--name", required=True); s.add_argument("--version", required=True)
    s.add_argument("--index", default=INDEX); s.add_argument("--dist")
    a = p.parse_args()
    sys.exit({"version": cmd_version, "check": cmd_check, "audit": cmd_audit, "published": cmd_published}[a.sub](a))


if __name__ == "__main__":
    main()
