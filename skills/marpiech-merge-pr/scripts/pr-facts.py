#!/usr/bin/env python3
"""pr-facts.py — collect the facts a merge review needs, read-only, via the `gh` CLI.

Prints one markdown report: identity, branches, fork/draft status, size, mergeability,
review decision, CI checks, changed files, linked issues, ticket keys, and — when a doc
impact map exists — which documentation pages the change probably affects.

Usage (from the repository):
  pr-facts.py [PR]                  # number or URL; default: the PR of the current branch
  pr-facts.py [PR] --map FILE       # doc impact map (default .claude/doc-impact-map.json)
  pr-facts.py [PR] --ticket-regex 'ACME-[0-9]+'

Doc impact map (JSON):
  {
    "docs_repo": "owner/docs-repo",      // optional: docs live in ANOTHER repository
    "rules": [
      {"match": "src/api/", "doc_pages": ["docs/api.md"], "note": "API reference"}
    ]
  }
  Same repository   → a rule is OPEN when none of its doc_pages is in the PR diff.
  Other repository  → a rule is OPEN when a doc page's last commit is older than the PR's
                      last commit (a prompt, not proof: a typo fix makes a page "fresh").
Exit code: 0 always (it informs; the reviewer decides).
"""
import argparse
import json
import os
import re
import shutil
import subprocess
import sys

FIELDS = ("number,title,url,author,state,isDraft,isCrossRepository,headRepositoryOwner,"
          "headRefName,baseRefName,headRefOid,additions,deletions,changedFiles,files,"
          "mergeable,mergeStateStatus,reviewDecision,labels,body,closingIssuesReferences,"
          "commits,updatedAt")


def gh(*args, check=True):
    r = subprocess.run(["gh", *args], capture_output=True, text=True)
    if check and r.returncode != 0:
        sys.exit(f"pr-facts: gh {' '.join(args[:3])} failed: {r.stderr.strip()[:300]}")
    return r


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("pr", nargs="?")
    ap.add_argument("--map", default=".claude/doc-impact-map.json")
    ap.add_argument("--ticket-regex", default=r"\b[A-Z][A-Z0-9]{1,9}-[0-9]+\b")
    a = ap.parse_args()
    if not shutil.which("gh"):
        sys.exit("pr-facts: needs the `gh` CLI (gh auth login)")

    sel = [a.pr] if a.pr else []
    d = json.loads(gh("pr", "view", *sel, "--json", FIELDS).stdout)
    n = str(d["number"])

    print(f"# PR #{n}: {d['title']}\n{d['url']}\n")
    print(f"- Author: {d['author']['login']} · State: {d['state']}{' · DRAFT' if d['isDraft'] else ''}")
    fork = d["isCrossRepository"]
    print(f"- Branches: {d['headRefName']} → {d['baseRefName']}"
          + (f" · FROM FORK ({(d.get('headRepositoryOwner') or {}).get('login')}) — untrusted code" if fork else ""))
    print(f"- Size: {d['changedFiles']} files, +{d['additions']} / -{d['deletions']}"
          + (" · LARGE (>500 lines): organise findings by module" if d['additions'] + d['deletions'] > 500 else ""))
    print(f"- Mergeable: {d['mergeable']} · Merge state: {d['mergeStateStatus']} · Review decision: {d['reviewDecision'] or 'none'}")
    labels = [x["name"] for x in d.get("labels") or []]
    print(f"- Labels: {', '.join(labels) or 'none'}")
    issues = [f"#{i['number']}" for i in d.get("closingIssuesReferences") or []]
    text = " ".join([d["title"], d.get("body") or "", d["headRefName"]]
                    + [c.get("messageHeadline", "") for c in d.get("commits") or []])
    keys = sorted(set(re.findall(a.ticket_regex, text)))
    print(f"- Linked issues: {', '.join(issues) or 'none'} · Ticket keys: {', '.join(keys) or 'none'}")

    # CI checks: gh exits non-zero when checks fail or are pending, so do not use check=True.
    r = gh("pr", "checks", n, "--json", "name,bucket,workflow,link", check=False)
    try:
        checks = json.loads(r.stdout) if r.stdout.strip() else []
    except json.JSONDecodeError:
        checks = []
    print("\n## CI checks\n")
    if not checks:
        print("- none reported" + (f" ({r.stderr.strip()[:120]})" if r.stderr.strip() else ""))
    else:
        by = {}
        for c in checks:
            by.setdefault(c.get("bucket", "?"), []).append(c)
        print("- " + " · ".join(f"{k}: {len(v)}" for k, v in sorted(by.items())))
        for c in by.get("fail", []) + by.get("cancel", []) + by.get("pending", []):
            print(f"  - {c['bucket'].upper()}: {c.get('workflow', '')} / {c['name']}  {c.get('link', '')}")

    files = [f["path"] for f in d.get("files") or []]
    print("\n## Changed files\n")
    for f in d.get("files") or []:
        print(f"- {f['path']}  (+{f['additions']} / -{f['deletions']})")

    print("\n## Documentation impact\n")
    if "docs:skip" in labels:
        print("- skipped: PR has the `docs:skip` label")
    elif not os.path.isfile(a.map):
        print(f"- no map at {a.map} — judge by hand (new commands, endpoints, UI, config?)")
    else:
        m = json.load(open(a.map, encoding="utf-8"))
        docs_repo, open_rules = m.get("docs_repo"), 0
        pr_date = (d.get("commits") or [{}])[-1].get("committedDate") or d.get("updatedAt", "")
        for rule in m.get("rules", []):
            hits = [f for f in files if f.startswith(rule["match"])]
            if not hits:
                continue
            pages = rule.get("doc_pages", [])
            if not docs_repo:
                stale = [p for p in pages if p not in files]
                is_open = len(stale) == len(pages) and pages
            else:
                stale = []
                for p in pages:
                    rr = gh("api", f"repos/{docs_repo}/commits?path={p}&per_page=1",
                            "--jq", ".[0].commit.committer.date", check=False)
                    date = rr.stdout.strip()
                    if not date or date < pr_date:
                        stale.append(f"{p} (last change {date[:10] or 'never'})")
                is_open = bool(stale)
            if is_open:
                open_rules += 1
                print(f"- OPEN `{rule['match']}` ({len(hits)} files) → {', '.join(stale)}"
                      f"{' — ' + rule['note'] if rule.get('note') else ''}")
        if not open_rules:
            print("- no open documentation impact")
        if "docs-followup" in labels:
            print("- PR has `docs-followup`: file a follow-up ticket after merging")


if __name__ == "__main__":
    main()
