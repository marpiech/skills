#!/usr/bin/env python3
"""security.py — read-only security candidate finder for marpiech-security (stdlib + git).

Every hit is a CANDIDATE. The skill reads each one in context and verifies it (source →
sink, preconditions, impact) before calling it a finding. Nothing here talks to the
network, executes project code, or prints file contents beyond the matching line.

  Common flags: --include-tests (test files are skipped by default), --max-hits N.

  security.py surface [--diff BASE] [--scope PATH ...]
      Security-sensitive areas touched by the scope: auth, sessions, crypto, deserialisation,
      shell/subprocess, SQL, file paths, templates/HTML sinks, redirects, CORS/cookies/headers,
      new routes. With --diff only files changed since BASE, and only ADDED lines.

  security.py defaults [--scope PATH ...] [--diff BASE]
      Fail-open and insecure defaults: TLS verification off, debug on, wildcard CORS,
      permissive fallbacks for secrets, unsafe deserialisation, shell=True, weak hashes for
      passwords, JWT signature checks off, non-crypto randomness for tokens, broad excepts
      around auth, world-writable modes, autoescape off.

  security.py actions [--root DIR]
      CI workflows (.github/workflows/*.yml): pull_request_target / workflow_run with a
      checkout of untrusted code, untrusted event fields interpolated into run: scripts,
      missing or write-all permissions, third-party actions not pinned to a commit SHA,
      self-hosted runners, AI-agent actions triggered by comments/issues without an
      author check, secrets passed to steps on untrusted triggers.

  security.py deps [--root DIR]
      Dependency manifests and supply-chain hygiene: lock files present, unpinned or
      open ranges, direct URL/git dependencies, install-time scripts, extra index URLs.
      (Advisory lookups need the network — run pip-audit / npm audit / osv-scanner only
      when the user agrees; this command never does.)

Config (optional) .claude/security.json:
  {"exclude": ["tests/fixtures/"], "allow": {"D-TLS-OFF": ["scripts/dev_only.py"]}}
Exit code: 1 if any candidate was printed, else 0.
"""
import argparse
import fnmatch
import json
import os
import re
import subprocess
import sys

DEFAULT_EXCLUDE = ["node_modules/", "venv/", ".venv/", "__pycache__/", "dist/", "build/", "vendor/",
                   ".git/", "*.min.js", "*.lock", "package-lock.json", "*.map"]
TEST_EXCLUDE = ["tests/", "test/", "__tests__/", "e2e/", "test_*.py", "*_test.py", "*_test.go", "*.test.*", "*.spec.*"]
CODE = ["*.py", "*.js", "*.mjs", "*.cjs", "*.ts", "*.tsx", "*.jsx", "*.go", "*.rb", "*.java",
        "*.kt", "*.cs", "*.php", "*.rs", "*.sh"]
CONF = ["*.yml", "*.yaml", "*.toml", "*.ini", "*.cfg", "*.conf", "*.json", "*.env.example", "Dockerfile*"]
TPL = ["*.html", "*.jinja", "*.jinja2", "*.j2", "*.vue", "*.svelte", "*.tsx", "*.jsx", "*.erb", "*.hbs"]

# id, title, file globs, regex
SURFACE = [
    ("S-AUTH", "authentication / authorisation / session logic", CODE,
     r"(?i)\b(login|logout|authenticat\w*|authori[sz]\w*|permission\w*|is_admin|role[s]?\b|session|"
     r"jwt|oauth|oidc|csrf|api[_-]?key|bearer)\b"),
    ("S-CRYPTO", "cryptography / hashing / randomness", CODE,
     r"(?i)\b(hashlib|bcrypt|argon2|scrypt|pbkdf2|hmac|cipher|encrypt|decrypt|crypto\.|secrets\.|"
     r"random\.|Math\.random|nonce|salt)\b"),
    ("S-DESER", "deserialisation of data", CODE,
     r"\b(pickle\.loads?|yaml\.(unsafe_)?load|marshal\.loads|jsonpickle|ObjectInputStream|"
     r"unserialize\(|torch\.load|joblib\.load)\b"),
    ("S-EXEC", "process execution / dynamic code", CODE,
     r"\b(subprocess\.|os\.system|os\.popen|exec\(|eval\(|child_process|execSync|spawn\(|"
     r"Runtime\.getRuntime|new Function\()"),
    ("S-SQL", "SQL built in code", CODE,
     r"(?i)(\.execute\(|\.raw\(|text\(|cursor\.|query\()\s*f?['\"].*\b(select|insert|update|delete)\b"),
    ("S-PATH", "file system paths from data", CODE,
     r"\b(open\(|os\.path\.join|Path\(|send_file|FileResponse|readFile|createReadStream|"
     r"shutil\.|unlink|rmtree|extractall)\b"),
    ("S-HTML", "HTML sinks that bypass escaping", TPL + CODE,
     r"(\|\s*safe\b|Markup\(|mark_safe|autoescape\s+false|dangerouslySetInnerHTML|v-html|"
     r"innerHTML\s*=|outerHTML\s*=|document\.write|insertAdjacentHTML|\{\{\{)"),
    ("S-REDIRECT", "redirects / outbound requests to data-chosen targets", CODE,
     r"\b(redirect\(|RedirectResponse|res\.redirect|location\.href\s*=|requests\.(get|post)|"
     r"httpx\.|urllib\.request|fetch\(|axios\.)"),
    ("S-HEADERS", "CORS, cookies, security headers", CODE + CONF,
     r"(?i)(allow_origins|Access-Control-Allow|cors|set_cookie|samesite|httponly|secure\s*=|"
     r"Content-Security-Policy|X-Frame-Options|Strict-Transport-Security)"),
    ("S-ROUTE", "new or changed routes / endpoints", CODE,
     r"(@(app|router|bp|api)\.(get|post|put|patch|delete|route)\b|\b(app|router)\.(get|post|put|patch|delete)\(|"
     r"@(Get|Post|Put|Delete|Patch|Request)Mapping)"),
]

DEFAULTS = [
    ("D-TLS-OFF", "TLS / certificate verification disabled", CODE + CONF,
     r"(verify\s*=\s*False|rejectUnauthorized\s*:\s*false|InsecureSkipVerify\s*:\s*true|"
     r"_create_unverified_context|CERT_NONE|NODE_TLS_REJECT_UNAUTHORIZED\s*=\s*['\"]?0|--insecure\b|curl\s+-k\b)"),
    ("D-DEBUG", "debug mode on by default", CODE + CONF,
     r"(?i)(\bDEBUG\s*[:=]\s*(True|1|['\"]true['\"])|app\.run\(.*debug\s*=\s*True|FLASK_DEBUG\s*=\s*1)"),
    ("D-CORS-ANY", "wildcard CORS (worse with credentials)", CODE + CONF,
     r"(allow_origins\s*=\s*\[\s*['\"]\*['\"]|Access-Control-Allow-Origin['\"]?\s*[:,]\s*['\"]\*|origin\s*:\s*['\"]\*['\"]|"
     r"CORS_ALLOW_ALL_ORIGINS\s*=\s*True)"),
    ("D-SECRET-FALLBACK", "secret with a hard-coded fallback (fails open when unset)", CODE,
     r"(?i)(getenv|environ\.get|process\.env\.\w+\s*\|\||os\.Getenv)\W*['\"]?\w*(secret|token|key|password|passwd)\w*['\"]?"
     r"\s*(,\s*['\"][^'\"]{3,}['\"]|\|\|\s*['\"][^'\"]{3,}['\"])"),
    ("D-DESER", "unsafe deserialisation", CODE,
     r"(pickle\.loads?\(|yaml\.load\((?!.*(SafeLoader|CSafeLoader|BaseLoader))|yaml\.unsafe_load|marshal\.loads|torch\.load\((?!.*weights_only\s*=\s*True))"),
    ("D-SHELL", "shell=True / shell string execution", CODE,
     r"(shell\s*=\s*True|os\.system\(|os\.popen\(|execSync\(\s*`|exec\(\s*`)"),
    ("D-EVAL", "eval / exec of strings", CODE,
     r"(?<![\w.])(?<!def )(eval|exec)\(\s*(?!['\"])"),
    ("D-WEAK-HASH", "weak hash where a password or token may be hashed", CODE,
     r"(?i)(md5|sha1)\s*\(.*(pass|pwd|token|secret)|(pass|pwd|token|secret)\w*\s*=.*\b(md5|sha1)\("),
    ("D-JWT-NOVERIFY", "JWT signature or expiry not verified", CODE,
     r"(verify_signature['\"]?\s*:\s*False|verify\s*=\s*False.*jwt|jwt\.decode\([^)]*algorithms\s*=\s*\[\s*['\"]none|"
     r"ignoreExpiration\s*:\s*true|verify_exp['\"]?\s*:\s*False)"),
    ("D-RANDOM-TOKEN", "non-cryptographic randomness for tokens/ids", CODE,
     r"(?i)(token|secret|password|nonce|otp|reset|invite)\w*\s*=.*\b(random\.(random|randint|choice|choices)|Math\.random)\("),
    ("D-SWALLOW", "broad except that swallows the error (fails open near auth)", ["*.py"],
     r"except\s*(\(?\s*(Base)?Exception\s*\)?)?\s*(as\s+\w+\s*)?:\s*(#[^\n]*)?\n?\s*(pass|return\s+True|continue)\b"),
    ("D-PERMS", "world-writable file modes", CODE + CONF,
     r"(chmod\s+(-R\s+)?0?777|os\.chmod\([^)]*0o?777|umask\(0+\))"),
    ("D-AUTOESCAPE", "template autoescape disabled", CODE + TPL,
     r"(autoescape\s*=\s*False|\{%\s*autoescape\s+false)"),
    ("D-BIND-ALL", "service bound to all interfaces by default", CODE,
     r"(host\s*=\s*['\"]0\.0\.0\.0['\"]|listen\(\s*['\"]0\.0\.0\.0)"),
    ("D-SQL-FSTRING", "SQL built with f-string / concatenation / format", CODE,
     r"(?i)((\.execute|\.executemany|\.raw)\(\s*f['\"]|(?<![\w.])(text|query)\(\s*f['\"][^'\"]*\b(select|insert|update|delete|where)\b|"
     r"(execute|raw|text|query)\(\s*['\"][^'\"]*\b(select|insert|update|delete|where)\b[^'\"]*['\"]\s*(%|\+|\.format))"),
]


def sh(*a, cwd=None):
    r = subprocess.run(a, capture_output=True, text=True, cwd=cwd)
    return r.stdout if r.returncode == 0 else ""


def load_cfg():
    p = ".claude/security.json"
    if os.path.exists(p):
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    return {}


def match_any(path, globs):
    base = os.path.basename(path)
    for g in globs:
        if g.endswith("/"):
            if path.startswith(g) or ("/" + g) in ("/" + path):
                return True
        elif fnmatch.fnmatch(path, g) or fnmatch.fnmatch(base, g):
            return True
    return False


def tracked(scope):
    files = sh("git", "ls-files", *scope).splitlines()
    if not files:  # not a git repo: walk
        for root in scope or ["."]:
            for d, dirs, fs in os.walk(root):
                dirs[:] = [x for x in dirs if x not in (".git", "node_modules", ".venv", "venv")]
                files += [os.path.relpath(os.path.join(d, f)) for f in fs]
    return files


def added_lines(base, path):
    """Line numbers added in the working tree relative to BASE (unified=0 hunks)."""
    out = sh("git", "diff", "-U0", base, "--", path)
    lines = set()
    for m in re.finditer(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@", out, re.M):
        start, n = int(m.group(1)), int(m.group(2) or 1)
        lines.update(range(start, start + n))
    return lines


def scan(rules, a, cfg):
    exclude = DEFAULT_EXCLUDE + cfg.get("exclude", []) + ([] if a.include_tests else TEST_EXCLUDE)
    allow = cfg.get("allow", {})
    if a.diff:
        files = [f for f in sh("git", "diff", "--name-only", "--diff-filter=AM", a.diff, "--", *a.scope).splitlines()
                 if os.path.exists(f)]
    else:
        files = tracked(a.scope)
    files = [f for f in files if not match_any(f, exclude) and os.path.isfile(f)]
    total, per_rule = 0, {}
    for rid, title, globs, rx in rules:
        crx = re.compile(rx)
        hits = []
        for f in files:
            if not match_any(f, globs) or match_any(f, allow.get(rid, [])):
                continue
            try:
                with open(f, encoding="utf-8", errors="replace") as fh:
                    text = fh.read()
            except OSError:
                continue
            if len(text) > 2_000_000:
                continue
            only = added_lines(a.diff, f) if a.diff else None
            if r"\n" in rx:  # multi-line rule: match on the whole text, report the first line
                for m in crx.finditer(text):
                    i = text.count("\n", 0, m.start()) + 1
                    if only is None or i in only or i + 1 in only:
                        hits.append((f, i, " ".join(m.group(0).split())[:140]))
                continue
            for i, line in enumerate(text.splitlines(), 1):
                if only is not None and i not in only:
                    continue
                if crx.search(line):
                    hits.append((f, i, line.strip()[:140]))
        per_rule[rid] = len(hits)
        if hits:
            print(f"\n{rid}  {title}  ({len(hits)})")
            for f, i, s in hits[: a.max_hits]:
                print(f"  {f}:{i}: {s}")
            if len(hits) > a.max_hits:
                print(f"  … {len(hits) - a.max_hits} more (raise --max-hits)")
        total += len(hits)
    print(f"\n{total} candidates in {len(files)} files"
          + (f" (added lines since {a.diff})" if a.diff else "")
          + " — every one must be read and verified before it is a finding")
    return 1 if total else 0


def cmd_surface(a):
    if not a.diff:
        print("(whole tree: surface is most useful with --diff BASE; showing counts only — raise --max-hits to list lines)")
        a.max_hits = min(a.max_hits, 0) if a.max_hits == 15 else a.max_hits
    return scan(SURFACE, a, load_cfg())


def cmd_defaults(a):
    return scan(DEFAULTS, a, load_cfg())


UNTRUSTED_EXPR = re.compile(
    r"\$\{\{\s*github\.(event\.(issue\.(title|body)|pull_request\.(title|body|head\.ref|head\.label)|"
    r"comment\.body|review\.body|review_comment\.body|head_commit\.(message|author\.(name|email))|"
    r"commits|pages|discussion\.(title|body)|workflow_run\.(head_branch|head_commit))|head_ref)[^}]*\}\}")
AGENT_ACTION = re.compile(r"uses:\s*[\w.-]*/(claude-code-action|claude-code-base-action|codex-action|"
                          r"gemini-cli-action|copilot|ai-|openai)[\w./-]*", re.I)


def cmd_actions(a):
    wf_dir = os.path.join(a.root, ".github", "workflows")
    if not os.path.isdir(wf_dir):
        print("no .github/workflows directory")
        return 0
    n = 0

    def out(rid, f, i, msg):
        nonlocal n
        n += 1
        print(f"{rid:<16} {f}:{i}: {msg}")

    for name in sorted(os.listdir(wf_dir)):
        if not name.endswith((".yml", ".yaml")):
            continue
        f = os.path.relpath(os.path.join(wf_dir, name))
        with open(f, encoding="utf-8", errors="replace") as fh:
            lines = fh.read().splitlines()
        text = "\n".join(lines)
        triggers = set(re.findall(r"^\s{0,4}(pull_request_target|workflow_run|issue_comment|issues|"
                                  r"pull_request_review_comment|pull_request_review|discussion_comment|"
                                  r"pull_request|push|schedule|workflow_dispatch)\s*:", text, re.M))
        if re.search(r"^on:\s*\[?([^\n\]]*)", text, re.M):
            triggers |= set(re.findall(r"[\w_]+", re.search(r"^on:\s*\[?([^\n\]]*)", text, re.M).group(1)))
        untrusted_trigger = triggers & {"pull_request_target", "workflow_run", "issue_comment", "issues",
                                        "pull_request_review_comment", "pull_request_review", "discussion_comment"}
        if not re.search(r"^permissions\s*:", text, re.M):
            out("A-PERMS-MISSING", f, 1, "no top-level `permissions:` — the token gets the repository default")
        for i, line in enumerate(lines, 1):
            s = line.strip()
            if re.search(r"permissions\s*:\s*write-all", s):
                out("A-PERMS-WRITEALL", f, i, s)
            m = re.search(r"uses:\s*([\w.-]+/[\w./-]+)@([\w.-]+)", s)
            if m and not m.group(1).startswith(("actions/", "github/")) and not re.fullmatch(r"[0-9a-f]{40}", m.group(2)):
                out("A-UNPINNED", f, i, f"{m.group(1)}@{m.group(2)} — pin third-party actions to a full commit SHA")
            if UNTRUSTED_EXPR.search(s):
                out("A-INJECTION", f, i, "untrusted event field interpolated — pass it via env: and quote \"$VAR\" in the script")
            if re.search(r"runs-on:.*self-hosted", s):
                out("A-SELF-HOSTED", f, i, "self-hosted runner — never for untrusted triggers or public-repo PRs")
            if untrusted_trigger & {"pull_request_target", "workflow_run"} and re.search(
                    r"ref:\s*\$\{\{\s*github\.(event\.pull_request\.head\.(sha|ref)|head_ref|event\.workflow_run\.head_(sha|branch))", s):
                out("A-PWN-REQUEST", f, i, "checks out untrusted PR code in a privileged trigger")
            if AGENT_ACTION.search(s) and untrusted_trigger:
                guarded = re.search(r"author_association|github\.actor\s*==|contains\(fromJSON", text)
                out("A-AGENT-UNTRUSTED", f, i,
                    f"AI agent action on {'/'.join(sorted(untrusted_trigger))}"
                    + ("" if guarded else " with no author/association check — prompt injection from any commenter"))
            if untrusted_trigger and re.search(r"\$\{\{\s*secrets\.(?!GITHUB_TOKEN)", s):
                out("A-SECRET-UNTRUSTED", f, i, "secret used in a workflow with an untrusted trigger — confirm the step cannot run attacker code")
    print(f"\n{n} candidates in workflows — verify each against the trigger and what the step runs")
    return 1 if n else 0


MANIFESTS = {
    "requirements*.txt": "python", "pyproject.toml": "python", "setup.py": "python", "Pipfile": "python",
    "package.json": "node", "go.mod": "go", "Cargo.toml": "rust", "Gemfile": "ruby", "pom.xml": "java",
    "build.gradle*": "java", "composer.json": "php",
}
LOCKS = {"python": ["poetry.lock", "uv.lock", "Pipfile.lock", "requirements*.lock", "pdm.lock"],
         "node": ["package-lock.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb"],
         "go": ["go.sum"], "rust": ["Cargo.lock"], "ruby": ["Gemfile.lock"], "java": [], "php": ["composer.lock"]}


def cmd_deps(a):
    files = [f for f in sh("git", "ls-files", cwd=a.root).splitlines() if not match_any(f, ["node_modules/", "vendor/"])]
    n = 0
    eco_dirs = {}
    for f in files:
        for g, eco in MANIFESTS.items():
            if fnmatch.fnmatch(os.path.basename(f), g):
                eco_dirs.setdefault((eco, os.path.dirname(f)), []).append(f)
    for (eco, d), mans in sorted(eco_dirs.items()):
        locks = [f for f in files if os.path.dirname(f) == d and any(fnmatch.fnmatch(os.path.basename(f), g) for g in LOCKS[eco])]
        print(f"{eco:<7} {d or '.'}: {', '.join(os.path.basename(m) for m in mans)}  lock: {', '.join(os.path.basename(x) for x in locks) or 'NONE'}")
        if not locks and LOCKS[eco]:
            n += 1
            print(f"  DEP-NO-LOCK      no lock file — builds resolve whatever is newest today")
        for m in mans:
            p = os.path.join(a.root, m)
            try:
                text = open(p, encoding="utf-8", errors="replace").read()
            except OSError:
                continue
            for i, line in enumerate(text.splitlines(), 1):
                s = line.strip()
                if re.search(r"(git\+|https?://|file:|github:)[^\s\"']+", s) and not s.startswith("#") \
                        and not re.search(r"(?i)^(homepage|repository|documentation|url|bugs|changelog|source)\b|\"(homepage|url|repository)\"", s):
                    n += 1
                    print(f"  DEP-DIRECT-URL   {m}:{i}: {s[:120]}")
                if re.search(r"--(extra-)?index-url|extra-index-url|\[\[tool\.(poetry|uv)\.source\]\]|registry\s*=", s):
                    n += 1
                    print(f"  DEP-EXTRA-INDEX  {m}:{i}: {s[:120]} — dependency confusion risk if names are not reserved")
                if eco == "node" and re.search(r"\"(preinstall|install|postinstall|prepare)\"\s*:", s):
                    n += 1
                    print(f"  DEP-INSTALL-HOOK {m}:{i}: {s[:120]}")
                if eco == "python" and m.endswith(".txt") and re.match(r"^[A-Za-z0-9_.\-\[\]]+\s*(>=|>|~=)?[^=]*$", s) and "==" not in s and s and not s.startswith(("-", "#")):
                    n += 1
                    print(f"  DEP-OPEN-RANGE   {m}:{i}: {s[:120]}")
                if eco == "node" and re.search(r"\"[^\"]+\"\s*:\s*\"(\*|latest|>=?[^\"]*)\"", s) and "engines" not in s:
                    n += 1
                    print(f"  DEP-OPEN-RANGE   {m}:{i}: {s[:120]}")
    print(f"\n{n} candidates — advisory lookups (pip-audit, npm audit, osv-scanner) need the network; ask before running")
    return 1 if n else 0


def main():
    p = argparse.ArgumentParser(description="Read-only security candidate finder.")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("surface", "defaults"):
        s = sub.add_parser(name)
        s.add_argument("--diff", metavar="BASE")
        s.add_argument("--scope", nargs="*", default=[])
        s.add_argument("--max-hits", type=int, default=15)
        s.add_argument("--include-tests", action="store_true", help="also scan test files (excluded by default)")
    for name in ("actions", "deps"):
        s = sub.add_parser(name)
        s.add_argument("--root", default=".")
    a = p.parse_args()
    sys.exit({"surface": cmd_surface, "defaults": cmd_defaults, "actions": cmd_actions, "deps": cmd_deps}[a.cmd](a))


if __name__ == "__main__":
    main()
