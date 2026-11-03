#!/usr/bin/env python3
"""tests.py — find a repository's test setup, map changes to tests, prove tests catch a change.

  tests.py discover
      Test frameworks, config files, test directories, shared fixtures/factories,
      markers, and run commands found in package/build files. Read-only.

  tests.py map [--base REF] [FILE...]
      For each changed source file (default: diff vs --base plus uncommitted changes),
      list the existing test files that probably cover it, or NO-TEST. Read-only.

  tests.py prove-fails --cmd 'COMMAND {tests}' [--base REF] TEST_FILE...
      The revert check. Checks out REF (default HEAD = the code WITHOUT your uncommitted
      change) into a temporary git worktree, copies the given test files in, and runs
      COMMAND there ({tests} is replaced by the test paths). A good regression test
      FAILS on the old code. Exit 0 = failed on base (good), 1 = passed on base (the test
      does not detect the change), 2 = setup problem. The temporary worktree is removed;
      your working tree is never touched.

python3 stdlib + git. Never installs anything, never runs tests except in prove-fails.
"""
import argparse
import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import tempfile

SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", "target", "__pycache__",
             ".tox", ".mypy_cache", ".pytest_cache", "vendor", ".next", "coverage"}
TEST_FILE = re.compile(r"(^test_.*\.py$|.*_test\.(py|go)$|.*\.(test|spec)\.[cm]?[jt]sx?$|.*Test\.(java|kt)$|"
                       r".*_spec\.rb$|.*Tests?\.cs$)")
SOURCE_EXT = (".py", ".js", ".jsx", ".ts", ".tsx", ".mjs", ".go", ".rs", ".rb", ".java", ".kt", ".cs", ".php")


def run(*cmd, cwd=None):
    return subprocess.run(cmd, capture_output=True, text=True, cwd=cwd)


def walk(root="."):
    """Tracked + untracked-but-not-ignored files (fast; skips data dirs); os.walk outside git."""
    r = run("git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", cwd=root)
    if r.returncode == 0:
        for f in dict.fromkeys(r.stdout.split("\0")):
            if f and not any(part in SKIP_DIRS for part in f.split("/")) and os.path.isfile(os.path.join(root, f)):
                yield f
        return
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x not in SKIP_DIRS and not x.startswith(".")]
        for f in files:
            yield os.path.relpath(os.path.join(d, f), root)


def read(path):
    try:
        return open(path, encoding="utf-8", errors="replace").read()
    except OSError:
        return ""


# ------------------------------------------------------------------ discover
def cmd_discover(a):
    files = list(walk())
    tests = [f for f in files if TEST_FILE.match(os.path.basename(f))]
    print(f"{len(tests)} test files in {len({os.path.dirname(t) for t in tests})} directories")

    print("\n## Frameworks / config")
    hints = {
        "pytest": ["pytest.ini", "conftest.py", "pyproject.toml:[tool.pytest", "setup.cfg:[tool:pytest", "tox.ini:[pytest"],
        "jest": ["jest.config.js", "jest.config.ts", "package.json:\"jest\""],
        "vitest": ["vitest.config.ts", "vitest.config.js", "vite.config.ts:test:"],
        "playwright": ["playwright.config.ts", "playwright.config.js"],
        "cypress": ["cypress.config.ts", "cypress.config.js"],
        "go test": ["go.mod"],
        "cargo test": ["Cargo.toml"],
        "rspec": [".rspec", "spec/spec_helper.rb"],
        "junit (maven/gradle)": ["pom.xml", "build.gradle", "build.gradle.kts"],
    }
    for fw, marks in hints.items():
        where = []
        for m in marks:
            name, _, needle = m.partition(":")
            for f in files:
                if (f == name or f.endswith("/" + name)) and (not needle or needle in read(f)):
                    where.append(f)
        if where:
            print(f"- {fw}: {', '.join(sorted(set(where))[:6])}{' …' if len(set(where)) > 6 else ''}")

    print("\n## Test directories (files)")
    dirs = {}
    for t in tests:
        top = "/".join(os.path.dirname(t).split("/")[:2]) or "."
        dirs[top] = dirs.get(top, 0) + 1
    for d, n in sorted(dirs.items(), key=lambda x: -x[1])[:20]:
        print(f"- {d}/ ({n})")

    print("\n## Shared fixtures / factories / helpers")
    shared = [f for f in files if os.path.basename(f) in ("conftest.py", "setupTests.ts", "setupTests.js",
              "test_helper.rb", "spec_helper.rb", "testutil.go") or re.search(r"(^|/)(factories|fixtures|helpers|testutils?)(/|\.py$)", f)]
    collapsed = {}
    for f in shared:  # a fixtures/ directory full of data files is one entry
        m = re.search(r"^(.*?(?:^|/)(?:factories|fixtures|helpers|testutils?))/", f)
        key = m.group(1) + "/" if m else f
        collapsed[key] = collapsed.get(key, 0) + 1
    for f, n in sorted(collapsed.items())[:25]:
        print(f"- {f}" + (f" ({n} files)" if n > 1 else ""))

    print("\n## Markers / tags")
    for f in files:
        if os.path.basename(f) in ("pytest.ini", "pyproject.toml", "setup.cfg", "tox.ini"):
            m = re.search(r"markers\s*=\s*(\[.*?\]|(?:\n\s+.+)+)", read(f), re.S)
            if m:
                names = re.findall(r"[\"']?\s*([A-Za-z_][\w-]*)\s*:", m.group(1))
                print(f"- {f}: {', '.join(dict.fromkeys(names))}")
            ad = re.search(r"addopts\s*=\s*(.+)", read(f))
            if ad:
                opts = ad.group(1).strip()
                warn = re.search(r"(^|[\s\"'])(-m|-k|--ignore|--deselect)\b", opts)
                print(f"- {f}: addopts {opts[:120]}" + ("  ← DESELECTS tests by default" if warn else ""))

    print("\n## Run commands")
    for f in files:
        b = os.path.basename(f)
        if b == "package.json":
            try:
                scripts = json.loads(read(f)).get("scripts", {})
            except json.JSONDecodeError:
                continue
            for k, v in scripts.items():
                if "test" in k or "e2e" in k:
                    print(f"- {f}: npm run {k}  → {v[:100]}")
        elif b in ("Makefile", "justfile"):
            for t in re.findall(r"^([\w.-]*test[\w.-]*)\s*:", read(f), re.M):
                print(f"- {f}: {'make' if b == 'Makefile' else 'just'} {t}")
    for wf in glob.glob(".github/workflows/*.y*ml"):
        for ln in read(wf).splitlines():
            if re.search(r"\b(pytest|npm (run )?test|npx (jest|vitest|playwright)|go test|cargo test|rspec|mvn test|gradle test)\b", ln):
                print(f"- CI {wf}: {ln.strip()[:120]}")
    return 0


# ------------------------------------------------------------------ map
def changed(base):
    out = set()
    if base:
        r = run("git", "diff", "--name-only", f"{base}...HEAD")
        if r.returncode != 0:
            print(f"tests: cannot diff against {base}", file=sys.stderr)
            sys.exit(2)
        out.update(r.stdout.split())
    out.update(run("git", "diff", "--name-only", "HEAD").stdout.split())
    for ln in run("git", "status", "--porcelain", "--untracked-files=all").stdout.splitlines():
        out.add(ln[3:].split(" -> ")[-1])
    return sorted(f for f in out if f)


def stem_of(path):
    b = os.path.basename(path)
    for rx in (r"^test_(.+)\.py$", r"^(.+)_test\.(py|go)$", r"^(.+)\.(test|spec)\.[cm]?[jt]sx?$",
               r"^(.+)Tests?\.(java|kt|cs)$", r"^(.+)_spec\.rb$"):
        m = re.match(rx, b)
        if m:
            return m.group(1).lower()
    return os.path.splitext(b)[0].lower()


def cmd_map(a):
    files = a.files or changed(a.base)
    all_tests = [f for f in walk() if TEST_FILE.match(os.path.basename(f))]
    by_stem = {}
    for t in all_tests:
        by_stem.setdefault(stem_of(t), []).append(t)
    sources = [f for f in files if f.endswith(SOURCE_EXT) and not TEST_FILE.match(os.path.basename(f))
               and not f.startswith(".")]  # tool config (.claude/, .github/) is not product code
    changed_tests = [f for f in files if TEST_FILE.match(os.path.basename(f))]
    missing = 0
    for s in sources:
        stem = stem_of(s)
        cands = list(by_stem.get(stem, []))
        if not cands:  # weaker: a test file whose name contains the stem, or that imports the module
            mod = os.path.splitext(s)[0].replace("/", ".")
            cands = [t for t in all_tests if stem in os.path.basename(t).lower() and len(stem) > 3]
            cands += [t for t in all_tests if t not in cands and (mod.split(".")[-1] in read(t)) and stem in read(t) and len(stem) > 5][:3]
        cands.sort(key=lambda t: len(os.path.commonprefix([t, s])), reverse=True)
        if cands:
            print(f"{s}\n    → {', '.join(cands[:4])}")
        else:
            print(f"{s}\n    → NO-TEST")
            missing += 1
    if changed_tests:
        print("\ntests changed in this diff: " + ", ".join(changed_tests))
    print(f"\n{len(sources)} changed source files, {missing} without an obvious test")
    return 1 if missing else 0


# ------------------------------------------------------------------ prove-fails
SETUP_ERR = re.compile(r"No module named|ModuleNotFoundError|ImportError|Cannot find module|command not found|"
                       r"errors? during collection|SyntaxError|ERR_MODULE_NOT_FOUND|cannot import name|undefined: ")


def show(res, n):
    out = (res.stdout + res.stderr).strip()
    for ln in out.splitlines()[-n:]:
        print("   | " + ln[:200])
    return out


def cmd_prove_fails(a):
    root = run("git", "rev-parse", "--show-toplevel").stdout.strip()
    if not root:
        print("tests: not a git repository", file=sys.stderr)
        return 2
    for t in a.tests:
        if not os.path.isfile(t):
            print(f"tests: no such test file {t}", file=sys.stderr)
            return 2
    rel = [os.path.relpath(os.path.abspath(t), root) for t in a.tests + (a.support or [])]
    tmp = tempfile.mkdtemp(prefix="prove-fails-")
    wt = os.path.join(tmp, "wt")
    r = run("git", "-C", root, "worktree", "add", "--detach", "--quiet", wt, a.base)
    if r.returncode != 0:
        print(f"tests: cannot create worktree at {a.base}: {r.stderr.strip()[:200]}", file=sys.stderr)
        shutil.rmtree(tmp, ignore_errors=True)
        return 2
    try:
        for p in rel:
            os.makedirs(os.path.dirname(os.path.join(wt, p)) or wt, exist_ok=True)
            shutil.copy2(os.path.join(root, p), os.path.join(wt, p))
        for dep in ("node_modules", ".venv", "venv"):  # reuse installed dependencies, read-only use
            for src in glob.glob(os.path.join(root, "**", dep), recursive=False) + glob.glob(os.path.join(root, dep)):
                dst = os.path.join(wt, os.path.relpath(src, root))
                if os.path.isdir(src) and not os.path.exists(dst):
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    os.symlink(src, dst)
        test_paths = " ".join(shlex.quote(p) for p in rel[:len(a.tests)])
        cmd = a.cmd.replace("{tests}", test_paths) if "{tests}" in a.cmd else f"{a.cmd} {test_paths}"
        sub = os.path.relpath(os.getcwd(), root)

        # 1. sanity: the tests must PASS on the current tree, or the comparison means nothing
        print(f"current tree: {cmd}", flush=True)
        cur = subprocess.run(cmd, shell=True, cwd=os.path.join(root, sub), capture_output=True, text=True, timeout=a.timeout)
        if cur.returncode != 0:
            show(cur, a.lines)
            print("SETUP: the tests do not pass on the CURRENT tree — fix them (or the command) first.")
            return 2
        # 2. the revert check: same tests against the old code
        print(f"base {a.base} (worktree): {cmd}", flush=True)
        res = subprocess.run(cmd, shell=True, cwd=os.path.join(wt, sub), capture_output=True, text=True, timeout=a.timeout)
        out = show(res, a.lines)
        if res.returncode != 0:
            if SETUP_ERR.search(out):
                print(f"SETUP?: the tests fail on {a.base}, but with what looks like a setup/import error,"
                      " not an assertion. Read the output: if the failure is 'the new function does not"
                      " exist', that IS detection; if a dependency is missing in the worktree, it is not.")
                return 2
            print(f"GOOD: the tests pass on the current tree and FAIL on {a.base} (exit {res.returncode})"
                  " — they detect the change. Confirm above that an assertion failed.")
            return 0
        print(f"BAD: the tests PASS on {a.base} — they do not detect the change. Strengthen the assertions.")
        return 1
    except subprocess.TimeoutExpired:
        print(f"tests: timed out after {a.timeout}s", file=sys.stderr)
        return 2
    finally:
        run("git", "-C", root, "worktree", "remove", "--force", wt)
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    p = argparse.ArgumentParser(description="Test discovery, mapping and the revert check.")
    sub = p.add_subparsers(dest="sub", required=True)
    sub.add_parser("discover")
    s = sub.add_parser("map"); s.add_argument("files", nargs="*"); s.add_argument("--base")
    s = sub.add_parser("prove-fails"); s.add_argument("tests", nargs="+"); s.add_argument("--cmd", required=True)
    s.add_argument("--base", default="HEAD"); s.add_argument("--support", action="append",
                   help="extra new non-test file the tests need (fixture, factory)")
    s.add_argument("--timeout", type=int, default=900); s.add_argument("--lines", type=int, default=15)
    a = p.parse_args()
    if run("git", "rev-parse", "--git-dir").returncode != 0 and a.sub != "discover":
        print("tests: run inside a git repository", file=sys.stderr)
        sys.exit(2)
    sys.exit({"discover": cmd_discover, "map": cmd_map, "prove-fails": cmd_prove_fails}[a.sub](a))


if __name__ == "__main__":
    main()
