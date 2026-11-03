#!/usr/bin/env python3
"""ci.py — observe GitHub Actions through the `gh` CLI (read-only).

  ci.py find    [--branch B] [--workflow W] [--sha S] [--limit N]
      List recent runs (newest first) with id, workflow, branch, event, sha, status.
  ci.py watch   RUN_ID [--interval S] [--timeout S]
      Print every job state change until the run completes; exit 0 on success,
      1 on any other conclusion, 2 on timeout. Silence never means progress: every
      terminal job state is printed. Designed to run under a background monitor.
  ci.py watch   --branch B [--workflow W] [--sha S] [--appear S]
      Wait (up to --appear seconds, default 180) for a run of that branch/sha to
      appear, then watch it. No run appearing is itself reported (exit 3).
  ci.py why     RUN_ID [--lines N]
      Failed jobs, failed steps, and the matching error lines of each failed job's log.
      Flags jobs that failed with no steps and no runner (infrastructure, not code).
  ci.py landed  SHA --branch B [--workflow W] [--remote origin]
      Is SHA on the deploy branch, and did a completed run of W on B whose head
      contains SHA conclude success? Exit 0 = landed, 1 = not (yet).

Exit codes are meant to be read by the caller; output is plain text for humans.
"""
import argparse
import json
import re
import shutil
import subprocess
import sys
import time


def gh(*args, check=True):
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        raise RuntimeError(r.stderr.strip()[:300] or f"gh {' '.join(args[:3])} failed")
    return r.stdout


def git(*args):
    return subprocess.run(["git", *args], capture_output=True, text=True)


def runs(branch=None, workflow=None, limit=10):
    args = ["run", "list", "--limit", str(limit), "--json",
            "databaseId,workflowName,headBranch,event,headSha,status,conclusion,createdAt,url"]
    if branch:
        args += ["--branch", branch]
    if workflow:
        args += ["--workflow", workflow]
    return json.loads(gh(*args) or "[]")


def contains(head, sha):
    """True if `sha` is an ancestor of (or equal to) `head` in the local clone."""
    if head.startswith(sha) or sha.startswith(head):
        return True
    return git("merge-base", "--is-ancestor", sha, head).returncode == 0


def cmd_find(a):
    rs = runs(a.branch, a.workflow, a.limit)
    if a.sha:
        rs = [r for r in rs if contains(r["headSha"], a.sha)]
    if not rs:
        print("no runs found" + (" — push succeeded but no run? check the CI status page / triggers" if a.branch else ""))
        return 1
    for r in rs:
        print(f"{r['databaseId']}  {r['createdAt'][:16]}  {r['workflowName'][:28]:28}  {r['headBranch'][:20]:20}  "
              f"{r['event'][:12]:12}  {r['headSha'][:8]}  {r['status']} {r['conclusion'] or ''}")
    return 0


def job_lines(run_id):
    d = json.loads(gh("run", "view", str(run_id), "--json", "status,conclusion,jobs,headSha,workflowName,url"))
    lines = []
    for j in d.get("jobs") or []:
        st = j.get("conclusion") or ("running" if j.get("status") == "in_progress" else j.get("status"))
        if st not in ("queued", "pending", "waiting"):
            lines.append(f"job {j.get('name', '')[:40]:40} {st}")
    lines.append(f"RUN {d.get('status')} {d.get('conclusion') or ''}".rstrip())
    return d, lines


def watch_id(run_id, interval, timeout):
    seen, start, d = set(), time.time(), None
    print(f"watching run {run_id}", flush=True)
    while time.time() - start < timeout:
        try:
            d, lines = job_lines(run_id)
        except RuntimeError as e:  # API hiccup: report it, keep going
            print(f"(gh error, retrying: {e})", flush=True)
            time.sleep(interval)
            continue
        for ln in lines:
            if ln not in seen and not ln.startswith("RUN in_progress") and not ln.startswith("RUN queued"):
                print(ln, flush=True)
                seen.add(ln)
        if d.get("status") == "completed":
            print(f"DONE run {run_id} sha {d.get('headSha', '')[:8]} -> {d.get('conclusion')}  {d.get('url', '')}", flush=True)
            return 0 if d.get("conclusion") == "success" else 1
        time.sleep(interval)
    print(f"TIMEOUT after {timeout}s — run {run_id} still {d.get('status') if d else 'unknown'}", flush=True)
    return 2


def cmd_watch(a):
    if a.run_id:
        return watch_id(a.run_id, a.interval, a.timeout)
    if not a.branch:
        sys.exit("watch: give RUN_ID or --branch")
    start = time.time()
    while time.time() - start < a.appear:
        rs = runs(a.branch, a.workflow, 10)
        if a.sha:
            rs = [r for r in rs if contains(r["headSha"], a.sha)]
        if rs:
            r = rs[0]  # newest; older ones for the same sha are usually cancelled/superseded
            print(f"found run {r['databaseId']} ({r['workflowName']}, {r['event']}, sha {r['headSha'][:8]})", flush=True)
            return watch_id(r["databaseId"], a.interval, a.timeout)
        time.sleep(15)
    print(f"NO RUN appeared for branch {a.branch}{' sha ' + a.sha[:8] if a.sha else ''} within {a.appear}s — "
          "check workflow triggers/path filters and the CI provider's status page", flush=True)
    return 3


# Whole words only: "libgpg-error0" or "no-fail-fast" must not count as failures.
ERR = re.compile(r"\b(errors?|failed|failures?|fatal|assert\w*|exception|traceback|denied|refused|"
                 r"timed out|timeout|exit code [1-9]\d*)\b", re.I)


def cmd_why(a):
    d = json.loads(gh("run", "view", str(a.run_id), "--json", "headSha,conclusion,status,jobs,workflowName,url"))
    print(f"run {a.run_id} {d.get('workflowName')} sha {d.get('headSha', '')[:8]}: {d.get('status')} {d.get('conclusion') or ''}")
    print(d.get("url", ""))
    bad = [j for j in d.get("jobs") or [] if j.get("conclusion") not in (None, "success", "skipped", "neutral")]
    if not bad:
        print("no failed jobs" + (" (run still in progress)" if d.get("status") != "completed" else ""))
        return 0
    for j in bad:
        steps = j.get("steps") or []
        print(f"\n## job: {j.get('name')} -> {j.get('conclusion')}  (id {j.get('databaseId')})")
        if not steps:
            print("   NO STEPS RAN — the job was never picked up by a runner. Infrastructure, not your code:"
                  " check runner availability / CI status, then re-run. Do not chase a code error.")
            continue
        for s in steps:
            if s.get("conclusion") in ("failure", "cancelled", "timed_out"):
                print(f"   FAILED STEP: {s.get('name')} ({s.get('conclusion')})")
        log = subprocess.run(["gh", "run", "view", "--job", str(j.get("databaseId")), "--log-failed"],
                             capture_output=True, text=True).stdout
        if not log:
            log = subprocess.run(["gh", "run", "view", "--job", str(j.get("databaseId")), "--log"],
                                 capture_output=True, text=True).stdout
        lines = [ln.split("\t")[-1].strip() for ln in log.splitlines()]
        marked = [ln for ln in lines if "##[error]" in ln]  # the CI's own error annotations first
        other = [ln for ln in lines if ERR.search(ln) and ln not in marked]
        show = marked[-a.lines:]
        room = a.lines - len(show)
        show += other[-room:] if room > 0 else []  # fill with the LAST matches: nearest the failure
        print(f"   {len(marked)} error annotations, {len(other)} other matching lines; showing {len(show)}:")
        for h in show:
            print("   | " + h[:240])
    return 1


def cmd_landed(a):
    git("fetch", "--quiet", a.remote, a.branch)
    ref = f"{a.remote}/{a.branch}"
    if git("merge-base", "--is-ancestor", a.sha, ref).returncode != 0:
        print(f"NOT LANDED: {a.sha[:8]} is not on {ref}")
        return 1
    print(f"on branch: {a.sha[:8]} is on {ref}")
    for r in runs(a.branch, a.workflow, 20):
        if r["status"] != "completed" or not contains(r["headSha"], a.sha):
            continue
        if r["conclusion"] == "success":
            print(f"LANDED: run {r['databaseId']} ({r['workflowName']}) on sha {r['headSha'][:8]} succeeded  {r['url']}")
            return 0
        if r["conclusion"] in ("cancelled", "skipped"):
            continue  # superseded; look further back
        print(f"NOT LANDED: newest completed run carrying it, {r['databaseId']}, concluded {r['conclusion']}  {r['url']}")
        return 1
    pending = [r for r in runs(a.branch, a.workflow, 10) if r["status"] != "completed"]
    print("NOT YET: no completed successful run carries it"
          + (f"; in flight: {', '.join(str(r['databaseId']) for r in pending)}" if pending else ""))
    return 1


def main():
    if not shutil.which("gh"):
        sys.exit("ci.py needs the `gh` CLI (gh auth login)")
    p = argparse.ArgumentParser(description="Observe GitHub Actions (read-only).")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("find"); s.add_argument("--branch"); s.add_argument("--workflow")
    s.add_argument("--sha"); s.add_argument("--limit", type=int, default=10)
    s = sub.add_parser("watch"); s.add_argument("run_id", nargs="?"); s.add_argument("--branch")
    s.add_argument("--workflow"); s.add_argument("--sha"); s.add_argument("--interval", type=int, default=20)
    s.add_argument("--timeout", type=int, default=3600); s.add_argument("--appear", type=int, default=180)
    s = sub.add_parser("why"); s.add_argument("run_id"); s.add_argument("--lines", type=int, default=25)
    s = sub.add_parser("landed"); s.add_argument("sha"); s.add_argument("--branch", required=True)
    s.add_argument("--workflow"); s.add_argument("--remote", default="origin")
    a = p.parse_args()
    try:
        sys.exit({"find": cmd_find, "watch": cmd_watch, "why": cmd_why, "landed": cmd_landed}[a.cmd](a))
    except RuntimeError as e:
        sys.exit(f"ci.py: {e}")


if __name__ == "__main__":
    main()
