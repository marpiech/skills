#!/usr/bin/env python3
"""secrets.py — work with a project's secrets WITHOUT printing their values (python3 stdlib).

Values are read into memory only to compute presence, length and a short fingerprint;
they are never printed, logged or written anywhere except to the backend on `set --yes`.

  secrets.py which
      Detect the secrets backend(s) this repository uses.
  secrets.py keys    [--env E] [--path P] [--recursive]
      Key NAMES in an environment (no values).
  secrets.py has     KEY [KEY...] [--env E] [--path P]
      present / MISSING, value length, 8-char sha256 fingerprint (compare without revealing).
  secrets.py diff    ENV_A ENV_B [--path P] [--recursive]
      Keys only in A, only in B, and keys whose fingerprints differ.
  secrets.py run     [--env E] [--path P] -- COMMAND...
      Run COMMAND with the secrets injected as environment variables.
  secrets.py set     KEY [--env E] [--path P] [--yes] [--confirm-env E]
      Value from stdin (hidden prompt on a terminal) — never from argv. Dry run unless --yes.
      Environments listed in SECRETS_PROTECTED_ENVS (default "prod,production") also need
      --confirm-env <same name>.
  secrets.py scan    [PATH...] [--history N]
      Leak check: env files that are tracked or not gitignored, secret-looking strings in
      tracked files and in the last N commits (default 200). Uses gitleaks if installed.

Backend: --backend or SECRETS_BACKEND, else auto-detected:
  infisical  (.infisical.json)        env = Infisical environment slug, path = folder
  dotenv     (.env / .env.<env>)      env selects .env.<env>; SECRETS_DOTENV_FILE overrides
  sops       (.sops.yaml)             SECRETS_SOPS_FILE (default secrets.<env>.(yaml|json|env))
  doppler    (doppler.yaml)           env = Doppler config
  op         (.env.op / op:// refs)   SECRETS_OP_ENV_FILE (default .env.op) of op:// references
Self-hosted Infisical: set INFISICAL_API_URL in your environment (not in this repo).

Exit codes: 0 ok / nothing found, 1 findings or missing keys, 2 usage or backend error.
"""
import argparse
import getpass
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

PROTECTED = {e.strip() for e in os.environ.get("SECRETS_PROTECTED_ENVS", "prod,production").split(",") if e.strip()}
SECRET_RX = re.compile(
    r"(-----BEGIN [A-Z ]*PRIVATE KEY-----|AKIA[0-9A-Z]{16}|gh[pousr]_[A-Za-z0-9]{30,}|"
    r"github_pat_[A-Za-z0-9_]{30,}|xox[abpr]-[A-Za-z0-9-]{10,}|sk-[A-Za-z0-9_-]{20,}|"
    r"AIza[0-9A-Za-z_-]{35}|glpat-[A-Za-z0-9_-]{20}|"
    r"(?i:(?:password|passwd|secret|token|api[_-]?key)\w*['\"]?\s*[:=]\s*['\"][^\s'\"$<{]{12,}['\"])|"
    r"^\s*(?:export\s+)?[A-Z0-9_]*(?:PASSWORD|PASSWD|SECRET|TOKEN|API_KEY)[A-Z0-9_]*=[^\s'\"$<{]{12,}\s*$)")
ENV_NAME = re.compile(r"(^|/)\.env(\.[\w.-]+)?$")
ENV_SAFE = re.compile(r"\.(example|sample|template|dist|op)$")


def die(msg, code=2):
    sys.stdout.flush()
    print(f"secrets: {msg}", file=sys.stderr)
    sys.exit(code)


def sh(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def redact(match):
    """Show what kind of secret it is, never any of its characters."""
    m = re.match(r"\s*(?:export\s+)?([\w'\"-]+?['\"]?\s*[:=])", match)
    if m:
        return m.group(1).strip() + " <redacted>"
    return match[:4] + "<redacted>" if not match.startswith("-----") else "private key block"


def fp(value):
    return hashlib.sha256(value.encode()).hexdigest()[:8]


def parse_dotenv(text):
    out = {}
    for ln in text.splitlines():
        ln = ln.strip()
        if not ln or ln.startswith("#") or "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        k = k.removeprefix("export ").strip()
        v = v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "'\"":
            v = v[1:-1]
        out[k] = v
    return out


# ------------------------------------------------------------------ backends
def detect():
    found = []
    if os.path.exists(".infisical.json"):
        found.append("infisical")
    if os.path.exists(".sops.yaml"):
        found.append("sops")
    if os.path.exists("doppler.yaml"):
        found.append("doppler")
    if os.path.exists(os.environ.get("SECRETS_OP_ENV_FILE", ".env.op")):
        found.append("op")
    if any(os.path.exists(f) for f in (".env", ".env.local", ".env.development")):
        found.append("dotenv")
    return found


def backend(a):
    b = a.backend or os.environ.get("SECRETS_BACKEND") or (detect() or [None])[0]
    if not b:
        die("no backend found — set SECRETS_BACKEND or see the skill's bootstrap step")
    tool = {"infisical": "infisical", "sops": "sops", "doppler": "doppler", "op": "op"}.get(b)
    if tool and not shutil.which(tool):
        die(f"backend {b} needs the `{tool}` CLI on PATH")
    return b


def dotenv_file(env):
    f = os.environ.get("SECRETS_DOTENV_FILE")
    if f:
        return f
    for cand in ([f".env.{env}"] if env else []) + [".env"]:
        if os.path.exists(cand):
            return cand
    die(f"no dotenv file for env {env or '(default)'}")


def sops_file(env):
    f = os.environ.get("SECRETS_SOPS_FILE")
    if f:
        return f
    for ext in ("yaml", "json", "env"):
        cand = f"secrets.{env or 'dev'}.{ext}"
        if os.path.exists(cand):
            return cand
    die("set SECRETS_SOPS_FILE to the encrypted file")


def load(b, env, path, recursive=False):
    """Return {KEY: value} in memory. Never print the result."""
    if b == "infisical":
        cmd = ["infisical", "secrets", "--env", env or "dev", "--path", path or "/", "-o", "json", "--silent"]
        cmd += ["--recursive"] if recursive else []
        r = sh(cmd)
        if r.returncode != 0:
            die("infisical failed (logged in? `infisical login`; self-hosted → INFISICAL_API_URL): "
                + r.stderr.strip()[:200])
        return {s.get("secretKey") or s.get("key"): s.get("secretValue") or s.get("value") or ""
                for s in json.loads(r.stdout or "[]")}
    if b == "dotenv":
        return parse_dotenv(open(dotenv_file(env), encoding="utf-8").read())
    if b == "sops":
        r = sh(["sops", "-d", "--output-type", "dotenv", sops_file(env)])
        if r.returncode != 0:
            die("sops could not decrypt: " + r.stderr.strip()[:200])
        return parse_dotenv(r.stdout)
    if b == "doppler":
        cmd = ["doppler", "secrets", "download", "--no-file", "--format", "json"] + (["--config", env] if env else [])
        r = sh(cmd)
        if r.returncode != 0:
            die("doppler failed: " + r.stderr.strip()[:200])
        return json.loads(r.stdout or "{}")
    if b == "op":
        refs = parse_dotenv(open(os.environ.get("SECRETS_OP_ENV_FILE", ".env.op"), encoding="utf-8").read())
        out = {}
        for k, ref in refs.items():
            r = sh(["op", "read", ref]) if ref.startswith("op://") else None
            out[k] = (r.stdout.rstrip("\n") if r and r.returncode == 0 else "") if r else ref
        return out
    die(f"unknown backend {b}")


# ------------------------------------------------------------------ commands
def cmd_which(a):
    found = detect()
    print("backends detected: " + (", ".join(found) if found else "none"))
    if os.environ.get("SECRETS_BACKEND"):
        print(f"SECRETS_BACKEND={os.environ['SECRETS_BACKEND']} (overrides detection)")
    for t in ("infisical", "sops", "doppler", "op", "vault", "gitleaks"):
        if shutil.which(t):
            print(f"cli available: {t}")
    return 0 if found else 1


def cmd_keys(a):
    b = backend(a)
    keys = sorted(load(b, a.env, a.path, a.recursive))
    print(f"{len(keys)} keys ({b}, env {a.env or 'default'}, path {a.path or '/'}):")
    for k in keys:
        print(f"  {k}")
    return 0


def cmd_has(a):
    b = backend(a)
    data, missing = load(b, a.env, a.path), 0
    for k in a.keys:
        if k in data and data[k] != "":
            print(f"present  {k}  len={len(data[k])}  fp={fp(data[k])}")
        elif k in data:
            print(f"EMPTY    {k}")
            missing += 1
        else:
            print(f"MISSING  {k}")
            missing += 1
    return 1 if missing else 0


def cmd_diff(a):
    b = backend(a)
    x, y = load(b, a.env_a, a.path, a.recursive), load(b, a.env_b, a.path, a.recursive)
    only_a, only_b = sorted(set(x) - set(y)), sorted(set(y) - set(x))
    differ = sorted(k for k in set(x) & set(y) if x[k] != y[k])
    for k in only_a:
        print(f"only in {a.env_a}: {k}")
    for k in only_b:
        print(f"only in {a.env_b}: {k}")
    for k in differ:
        print(f"differs: {k}  ({fp(x[k])} vs {fp(y[k])})")
    same = len(set(x) & set(y)) - len(differ)
    print(f"{len(only_a)} only in {a.env_a}, {len(only_b)} only in {a.env_b}, {len(differ)} differ, {same} identical")
    return 1 if only_a or only_b else 0


def cmd_run(a):
    cmd = a.command[1:] if a.command[:1] == ["--"] else a.command
    if not cmd:
        die("run: give a command after --")
    b = backend(a)
    if b == "infisical":
        os.execvp("infisical", ["infisical", "run", "--env", a.env or "dev", "--path", a.path or "/", "--silent", "--"] + cmd)
    if b == "doppler":
        os.execvp("doppler", ["doppler", "run"] + (["--config", a.env] if a.env else []) + ["--"] + cmd)
    if b == "op":
        os.execvp("op", ["op", "run", "--env-file", os.environ.get("SECRETS_OP_ENV_FILE", ".env.op"), "--"] + cmd)
    env = dict(os.environ)
    env.update(load(b, a.env, a.path))  # dotenv, sops: inject into the child only
    os.execvpe(cmd[0], cmd, env)


def read_value(key):
    if sys.stdin.isatty():
        v = getpass.getpass(f"value for {key} (hidden): ")
        if v != getpass.getpass("repeat: "):
            die("values do not match")
        return v
    return sys.stdin.read().rstrip("\n")


def cmd_set(a):
    b = backend(a)
    env = a.env or "dev"
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", a.key):
        die(f"invalid key name {a.key!r}")
    current = load(b, a.env, a.path)
    action = "update" if a.key in current else "create"
    print(f"{action} {a.key} in {b} env {env} path {a.path or '/'}"
          + (f" (current fp={fp(current[a.key])})" if a.key in current else ""))
    if env in PROTECTED and a.confirm_env != env:
        die(f"{env} is protected: repeat it with --confirm-env {env} after the user approved", 1)
    if not a.yes:
        print("dry run — re-run with --yes to write (the value is read from stdin, never argv)")
        return 0
    value = read_value(a.key)
    if not value:
        die("empty value — nothing written")
    if b == "infisical":
        ram = "/dev/shm" if os.path.isdir("/dev/shm") and os.access("/dev/shm", os.W_OK) else None
        with tempfile.TemporaryDirectory(dir=ram) as d:  # 0700 dir, in RAM if possible; never argv
            vf = os.path.join(d, "v")
            fd = os.open(vf, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w") as fh:
                fh.write(value)
            r = sh(["infisical", "secrets", "set", f"{a.key}=@{vf}", "--env", env,
                    "--path", a.path or "/", "--silent"])
        if r.returncode != 0:  # stdout may echo the value: never relay it
            die("infisical set failed: " + r.stderr.strip()[:200].replace(value, "***"))
    elif b == "dotenv":
        f = dotenv_file(a.env)
        if sh(["git", "check-ignore", "-q", f]).returncode != 0 and os.path.isdir(".git"):
            die(f"{f} is not gitignored — refusing to write a secret into it")
        lines = open(f, encoding="utf-8").read().splitlines()
        rx = re.compile(rf"^(export\s+)?{re.escape(a.key)}=")
        new = [ln for ln in lines if not rx.match(ln)] + [f"{a.key}={json.dumps(value)}"]
        old_umask = os.umask(0o077)
        try:
            open(f, "w", encoding="utf-8").write("\n".join(new) + "\n")
        finally:
            os.umask(old_umask)
        if os.stat(f).st_mode & 0o077:
            os.chmod(f, 0o600)
            print(f"tightened {f} to mode 600 (it holds secrets)")
    else:
        die(f"set is not implemented for {b} — use its own CLI ({'sops edit' if b == 'sops' else b}) "
            "so the value never reaches the conversation")
    print(f"written: {a.key} in {env} (fp={fp(value)})")
    return 0


def tracked_files(paths):
    r = sh(["git", "ls-files", "-z", "--", *paths])
    return [f for f in r.stdout.split("\0") if f] if r.returncode == 0 else []


def cmd_scan(a):
    findings = 0
    if not os.path.isdir(".git") and sh(["git", "rev-parse", "--git-dir"]).returncode != 0:
        die("scan: run inside a git repository")
    files = tracked_files(a.paths)
    for f in files:
        if ENV_NAME.search(f) and not ENV_SAFE.search(f):
            print(f"TRACKED-ENV   {f} is committed — rotate what it holds, then untrack it")
            findings += 1
    for root, dirs, names in os.walk("."):
        dirs[:] = [d for d in dirs if d not in (".git", "node_modules", ".venv", "venv")]
        for n in names:
            p = os.path.relpath(os.path.join(root, n))
            if ENV_NAME.search(p) and not ENV_SAFE.search(p) and p not in files \
                    and sh(["git", "check-ignore", "-q", p]).returncode != 0:
                print(f"UNIGNORED-ENV {p} is not gitignored — one `git add -A` from a leak")
                findings += 1
    if shutil.which("gitleaks"):
        r = sh(["gitleaks", "detect", "--redact", "--no-banner", "--log-opts", f"-n {a.history}"])
        print("gitleaks: " + ("no leaks" if r.returncode == 0 else "LEAKS FOUND (values redacted):"))
        if r.returncode != 0:
            print("\n".join(ln for ln in (r.stdout + r.stderr).splitlines() if ln.strip())[:4000])
            findings += 1
        return 1 if findings else 0
    for f in files:
        try:
            text = open(f, encoding="utf-8", errors="ignore").read()
        except (IsADirectoryError, FileNotFoundError):
            continue
        for i, ln in enumerate(text.splitlines(), 1):
            m = SECRET_RX.search(ln)
            if m:
                print(f"SECRET?       {f}:{i}: {redact(m.group(0))}")
                findings += 1
    log = sh(["git", "log", f"-n{a.history}", "-p", "--no-color", "--format=commit %h"]).stdout
    commit = "?"
    for ln in log.splitlines():
        if ln.startswith("commit "):
            commit = ln.split()[1]
        elif ln.startswith("+") and not ln.startswith("+++"):
            m = SECRET_RX.search(ln)
            if m:
                print(f"HISTORY?      commit {commit}: {redact(m.group(0))}")
                findings += 1
    print(f"{findings} findings (pattern scan; install gitleaks for a thorough one)")
    return 1 if findings else 0


def main():
    p = argparse.ArgumentParser(description="Secrets without printing values.")
    p.add_argument("--backend", choices=["infisical", "dotenv", "sops", "doppler", "op"])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("which")
    for name in ("keys", "has", "run", "set"):
        s = sub.add_parser(name)
        s.add_argument("--env"); s.add_argument("--path")
        if name == "keys":
            s.add_argument("--recursive", action="store_true", help="infisical: include sub-folders")
        if name == "has":
            s.add_argument("keys", nargs="+")
        if name == "run":
            s.add_argument("command", nargs=argparse.REMAINDER)
        if name == "set":
            s.add_argument("key"); s.add_argument("--yes", action="store_true"); s.add_argument("--confirm-env")
    s = sub.add_parser("diff"); s.add_argument("env_a"); s.add_argument("env_b"); s.add_argument("--path")
    s.add_argument("--recursive", action="store_true", help="infisical: include sub-folders")
    s = sub.add_parser("scan"); s.add_argument("paths", nargs="*"); s.add_argument("--history", type=int, default=200)
    a = p.parse_args()
    for name in ("env", "path"):
        if not hasattr(a, name):
            setattr(a, name, None)
    sys.exit({"which": cmd_which, "keys": cmd_keys, "has": cmd_has, "diff": cmd_diff,
              "run": cmd_run, "set": cmd_set, "scan": cmd_scan}[a.cmd](a))


if __name__ == "__main__":
    main()
