#!/usr/bin/env python3
"""publish_check.py — read-only pre-publication checks for a git repository (stdlib + git).

Answers "what would the world see if this repository (or this push) became public?".
Never prints a secret value: secret-shaped matches are redacted to their kind.

  publish_check.py files [--all-untracked]
      Every file that is (or would be, after `git add -A`) published, with risky ones
      flagged: env/credential/key files, database dumps, archives, notebooks with outputs,
      logs, large binaries, editor/OS junk, agent-local files (CLAUDE.local.md, settings).

  publish_check.py scan [PATH ...] [--deny FILE] [--ticket-regex RX] [--history N] [--allow FILE]
      Content scan of tracked files (and the last N commits' added lines with --history):
        SECRET    credential/key shapes (redacted)
        DENY      terms from the deny list (company, product, customer, people, hosts…)
        EMAIL     addresses outside example domains / noreply
        IP        IPv4 addresses outside loopback, unspecified and documentation ranges
        HOME      absolute home-directory paths (/home/<user>, /Users/<user>, C:\\Users\\<user>)
        HOST      internal host shapes (*.internal, *.local, *.corp, *.lan, cluster DNS)
        CLOUD     bucket URLs, cloud resource names/ARNs, project ids
        TICKET    ticket keys matching --ticket-regex (e.g. 'ACME-[0-9]+')

  publish_check.py meta
      What git metadata exposes: author/committer names and e-mails, remotes, tags and
      branches, submodules, files that exist only in history (deleted but still
      downloadable), and the largest blobs in history.

Deny list: a plain-text file kept OUTSIDE the repository being published (it names what
must not leak, so it is sensitive itself). Default: $PUBLISH_DENY_FILE, else
~/.config/marpiech-publish-check/deny.txt. One term per line, case-insensitive; a line
starting with `re:` is a regular expression; `#` starts a comment.
Allow list (--allow, default .publish-allow if present): `RULE path-glob [text-regex]` per
line, for deliberate examples (e.g. `EMAIL * @example\\.com`).

Exit code: 1 if anything was flagged, else 0.
"""
import argparse
import fnmatch
import ipaddress
import os
import re
import subprocess
import sys

SECRET_RX = re.compile(
    r"(-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,}|"
    r"github_pat_[A-Za-z0-9_]{30,}|xox[abpr]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9_-]{20,}|"
    r"AIza[0-9A-Za-z_-]{35}|glpat-[A-Za-z0-9_-]{20}|"
    r"(?i:(?:password|passwd|secret|token|api[_-]?key)\w*['\"]?\s*[:=]\s*['\"][^\s'\"$<{]{12,}['\"])|"
    r"^\s*(?:export\s+)?[A-Z0-9_]*(?:PASSWORD|PASSWD|SECRET|TOKEN|API_KEY)[A-Z0-9_]*=[^\s'\"$<{]{12,}\s*$)")
EMAIL_RX = re.compile(r"\b[A-Za-z0-9._%+-]+@([A-Za-z0-9-]+\.)+[A-Za-z]{2,}\b")
EMAIL_OK = re.compile(r"@(example\.(com|org|net)|[\w.-]*\.example|users\.noreply\.github\.com)$|^(noreply|no-reply)@", re.I)
IP_RX = re.compile(r"(?<![\w.])(\d{1,3}(?:\.\d{1,3}){3})(?![\w.])")
HOME_RX = re.compile(r"(/home/(?!user\b|<|\$|runner\b)[a-z_][\w.-]*|/Users/(?!<|\$|user\b|Shared\b)[A-Za-z][\w.-]*|"
                     r"[A-Z]:\\\\?Users\\\\?(?!<|user\b|Public\b)[A-Za-z][\w.-]*)")
HOST_RX = re.compile(r"(?<![\w.$/-])[a-z0-9][a-z0-9-]*(\.[a-z0-9-]+)*\.(internal|local|corp|lan|intranet|svc\.cluster\.local)(?![\w.-]*\.[a-z]{2,5}\b|[\w-])")
CLOUD_RX = re.compile(r"((gs|s3|az|abfss?)://[a-z0-9][\w.-]{2,}|arn:aws:[\w-]+:[\w-]*:\d{12}|"
                      r"\bprojects/[a-z][a-z0-9-]{4,28}[a-z0-9]\b|\b\d{12}\.dkr\.ecr\.)", re.I)
DOC_NETS = [ipaddress.ip_network(n) for n in
            ("0.0.0.0/8", "127.0.0.0/8", "192.0.2.0/24", "198.51.100.0/24", "203.0.113.0/24", "255.255.255.255/32")]

RISKY_FILES = [
    ("ENV", r"(^|/)\.env(\.[\w.-]+)?$", r"\.(example|sample|template|dist)$"),
    ("KEY", r"\.(pem|key|p12|pfx|jks|keystore|ppk|asc|gpg)$|(^|/)id_(rsa|ed25519|ecdsa)(\.pub)?$", None),
    ("CREDENTIALS", r"(credential|service[-_]?account|secret|token)[^/]*\.(json|ya?ml|txt|ini)$", r"\.(example|template)\."),
    ("STATE", r"\.tfstate(\.backup)?$|(^|/)\.terraform/", None),
    ("DUMP", r"\.(sql|sqlite3?|db|dump|bak|bson)$", None),
    ("ARCHIVE", r"\.(zip|tar|tgz|tar\.gz|7z|rar|gz)$", None),
    ("LOG", r"\.log$|(^|/)logs?/", None),
    ("JUNK", r"(^|/)(\.DS_Store|Thumbs\.db|\.idea/|\.vscode/settings\.json|__pycache__/|\.pytest_cache/)", None),
    ("AGENT-LOCAL", r"(^|/)(CLAUDE\.local\.md|\.claude/settings\.local\.json|\.claude/projects/)", None),
]


def git(*a):
    r = subprocess.run(["git", *a], capture_output=True, text=True, errors="replace")
    return r.stdout if r.returncode == 0 else ""


def redact(s):
    m = re.match(r"\s*(?:export\s+)?([\w'\"-]+?['\"]?\s*[:=])", s)
    if m:
        return m.group(1).strip() + " <redacted>"
    return "private key block" if s.startswith("-----") else s[:4] + "<redacted>"


def load_deny(path):
    path = path or os.environ.get("PUBLISH_DENY_FILE") or os.path.expanduser("~/.config/marpiech-publish-check/deny.txt")
    rules = []
    if not os.path.exists(path):
        return rules, None
    top = git("rev-parse", "--show-toplevel").strip()
    if top and os.path.realpath(path).startswith(os.path.realpath(top) + os.sep):
        print(f"WARNING deny list {path} is inside the repository — move it out; it names what must not leak")
    for ln in open(path, encoding="utf-8"):
        ln = ln.split("#", 1)[0].strip() if not ln.lstrip().startswith("re:") else ln.strip()
        if not ln:
            continue
        rx = ln[3:].strip() if ln.startswith("re:") else r"\b" + re.escape(ln) + r"\b"
        rules.append((ln, re.compile(rx, re.I)))
    return rules, path


def load_allow(path):
    path = path or (".publish-allow" if os.path.exists(".publish-allow") else None)
    out = []
    if path and os.path.exists(path):
        for ln in open(path, encoding="utf-8"):
            ln = ln.strip()
            if ln and not ln.startswith("#"):
                parts = ln.split(None, 2)
                out.append((parts[0], parts[1] if len(parts) > 1 else "*", re.compile(parts[2]) if len(parts) > 2 else None))
    return out


def allowed(allow, rule, path, text):
    for r, g, rx in allow:
        if r in (rule, "*") and fnmatch.fnmatch(path, g) and (rx is None or rx.search(text)):
            return True
    return False


def ip_flag(s):
    try:
        ip = ipaddress.ip_address(s)
    except ValueError:
        return False
    return not any(ip in n for n in DOC_NETS)


def line_findings(line, deny, ticket_rx):
    out = []
    m = SECRET_RX.search(line)
    if m:
        out.append(("SECRET", redact(m.group(0))))
    for term, rx in deny:
        if rx.search(line):
            out.append(("DENY", term))
    for m in EMAIL_RX.finditer(line):
        if not EMAIL_OK.search(m.group(0)):
            out.append(("EMAIL", m.group(0)))
    for m in IP_RX.finditer(line):
        if ip_flag(m.group(1)) and not re.search(r"(version|v)\s*[:=]?\s*" + re.escape(m.group(1)), line, re.I):
            out.append(("IP", m.group(1)))
    for m in HOME_RX.finditer(line):
        out.append(("HOME", m.group(0)))
    for m in HOST_RX.finditer(line):
        if not m.group(0).lower().endswith(("example.local",)):
            out.append(("HOST", m.group(0)))
    for m in CLOUD_RX.finditer(line):
        out.append(("CLOUD", m.group(0)))
    if ticket_rx:
        for m in ticket_rx.finditer(line):
            out.append(("TICKET", m.group(0)))
    return out


def cmd_files(a):
    tracked = [f for f in git("ls-files", "-z").split("\0") if f]
    untracked = [f for f in git("ls-files", "-z", "--others", "--exclude-standard").split("\0") if f]
    n = 0
    print(f"{len(tracked)} tracked files; {len(untracked)} untracked and NOT ignored (published by `git add -A`)")
    for label, files in (("tracked", tracked), ("untracked", untracked)):
        for f in files:
            for kind, rx, safe in RISKY_FILES:
                if re.search(rx, f, re.I) and not (safe and re.search(safe, f, re.I)):
                    print(f"{kind:<12} {label:<9} {f}")
                    n += 1
                    break
            else:
                if f.endswith(".ipynb") and os.path.exists(f):
                    if re.search(r'"outputs"\s*:\s*\[\s*\{', open(f, encoding="utf-8", errors="ignore").read()):
                        print(f"{'NOTEBOOK':<12} {label:<9} {f} — has outputs (data, paths, tokens can hide there)")
                        n += 1
                elif os.path.isfile(f) and os.path.getsize(f) > 1_000_000:
                    print(f"{'LARGE':<12} {label:<9} {f} — {os.path.getsize(f) // 1024} KiB")
                    n += 1
    if untracked and not a.all_untracked:
        print("(list every untracked file with --all-untracked)")
    elif a.all_untracked:
        for f in untracked:
            print(f"UNTRACKED    {f}")
    print(f"\n{n} flagged files")
    return 1 if n else 0


def cmd_scan(a):
    deny, deny_path = load_deny(a.deny)
    allow = load_allow(a.allow)
    ticket_rx = re.compile(a.ticket_regex) if a.ticket_regex else None
    print(f"deny list: {deny_path or 'none found'} ({len(deny)} terms)")
    files = [f for f in git("ls-files", "-z", "--", *a.paths).split("\0") if f]
    n = 0
    for f in files:
        if not os.path.isfile(f) or os.path.getsize(f) > 5_000_000:
            continue
        try:
            text = open(f, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        for term, rx in deny:  # deny terms in the PATH itself
            if rx.search(f):
                print(f"DENY    {f}: (in the file path) '{term}'")
                n += 1
        for i, line in enumerate(text.splitlines(), 1):
            for rule, what in line_findings(line, deny, ticket_rx):
                if allowed(allow, rule, f, line):
                    continue
                print(f"{rule:<7} {f}:{i}: {what}")
                n += 1
    if a.history:
        log = git("log", f"-n{a.history}", "-p", "--no-color", "--format=commit %h %s")
        commit = "?"
        for ln in log.splitlines():
            if ln.startswith("commit "):
                commit = ln.split()[1]
                for rule, what in line_findings(ln[len("commit ") + len(commit) + 1:], deny, ticket_rx):
                    if rule in ("DENY", "TICKET", "EMAIL", "SECRET"):
                        print(f"{rule:<7} commit {commit} message: {what}")
                        n += 1
            elif ln.startswith("+") and not ln.startswith("+++"):
                for rule, what in line_findings(ln[1:], deny, ticket_rx):
                    if rule in ("SECRET", "DENY") and not allowed(allow, rule, "*", ln):
                        print(f"{rule:<7} commit {commit} (history): {what}")
                        n += 1
    print(f"\n{n} findings — read each; deliberate examples go into the allow list with a reason")
    return 1 if n else 0


def cmd_meta(a):
    n = 0
    people = {}
    for ln in git("log", "--all", "--format=%an\t%ae\t%cn\t%ce").splitlines():
        an, ae, cn, ce = (ln.split("\t") + ["", "", "", ""])[:4]
        for name, mail in ((an, ae), (cn, ce)):
            if mail:
                people[(name, mail)] = people.get((name, mail), 0) + 1
    print("identities in history (published with every clone):")
    for (name, mail), c in sorted(people.items(), key=lambda x: -x[1]):
        flag = "" if EMAIL_OK.search(mail) else "  ← real address"
        n += bool(flag)
        print(f"  {c:>5}  {name} <{mail}>{flag}")
    print("remotes:")
    for ln in sorted(set(git("remote", "-v").splitlines())):
        print("  " + re.sub(r"//[^/@\s]+@", "//<credentials>@", ln))
        if re.search(r"//[^/@\s]+:[^/@\s]+@", ln):
            print("  CREDENTIALS-IN-REMOTE — a token is embedded in the remote URL")
            n += 1
    refs = git("for-each-ref", "--format=%(refname:short)", "refs/heads", "refs/tags").split()
    print(f"branches and tags ({len(refs)}): " + ", ".join(refs[:40]) + (" …" if len(refs) > 40 else ""))
    if os.path.exists(".gitmodules"):
        print("submodules:\n  " + "\n  ".join(git("config", "-f", ".gitmodules", "--get-regexp", "url").splitlines()))
    current = set(git("ls-files").splitlines())
    gone = sorted({f for f in git("log", "--all", "--diff-filter=D", "--name-only", "--format=").splitlines() if f and f not in current})
    risky = [f for f in gone if any(re.search(rx, f, re.I) for _, rx, _ in RISKY_FILES)]
    print(f"files deleted but still in history: {len(gone)}" + (f"; risky by name: {len(risky)}" if risky else ""))
    for f in risky[:30]:
        print(f"  HISTORY-ONLY {f} — still downloadable from history")
        n += 1
    blobs = []
    out = subprocess.run("git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectsize) %(rest)'",
                         shell=True, capture_output=True, text=True).stdout  # fixed command, no input
    for ln in out.splitlines():
        p = ln.split(" ", 2)
        if len(p) == 3 and p[0] == "blob":
            blobs.append((int(p[1]), p[2]))
    seen = {}
    for size, path in blobs:
        seen[path] = max(size, seen.get(path, 0))
    for path, size in sorted(seen.items(), key=lambda x: -x[1])[:5]:
        print(f"  largest blob {size // 1024:>7} KiB  {path}")
    print(f"\n{n} flagged")
    return 1 if n else 0


def main():
    p = argparse.ArgumentParser(description="Read-only pre-publication checks.")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("files"); s.add_argument("--all-untracked", action="store_true")
    s = sub.add_parser("scan"); s.add_argument("paths", nargs="*")
    s.add_argument("--deny"); s.add_argument("--allow"); s.add_argument("--ticket-regex")
    s.add_argument("--history", type=int, default=0)
    sub.add_parser("meta")
    a = p.parse_args()
    if not git("rev-parse", "--git-dir"):
        print("publish_check: run inside a git repository", file=sys.stderr)
        sys.exit(2)
    sys.exit({"files": cmd_files, "scan": cmd_scan, "meta": cmd_meta}[a.cmd](a))


if __name__ == "__main__":
    main()
