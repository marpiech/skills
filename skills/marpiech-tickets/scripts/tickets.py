#!/usr/bin/env python3
"""tickets.py — one small CLI over issue trackers, for the marpiech-tickets skill.

Backends
  jira    Jira Cloud REST v3. Needs env JIRA_URL, JIRA_EMAIL, JIRA_TOKEN (API token),
          optional JIRA_PROJECT (lets you pass a bare number: 1544 -> ACME-1544).
  github  GitHub issues through the `gh` CLI (uses gh's own login; no token here).
          Optional env GH_REPO=owner/name, else the current repository.

Pick the backend with --backend or env TICKETS_BACKEND (default: jira).

Credentials are read from the environment only — inject them with the project's
secrets tool (e.g. `<secrets-tool> run -- python3 tickets.py ...`). They are never
printed, logged or passed on a command line.

WRITE commands (comment, transition, create, set-parent, assign, worklog, attach)
print what they would do and exit unless --yes is given. Confirm with the user first.

Usage
  tickets.py whoami
  tickets.py get KEY [--json] [--comments N]
  tickets.py search QUERY [--max N]           # JQL for jira; gh search syntax for github
  tickets.py comments KEY [--last N]
  tickets.py transitions KEY
  tickets.py attachment ID OUTFILE            # jira: download one attachment
  tickets.py comment KEY FILE [--yes]         # FILE: text; see "comment format" below
  tickets.py transition KEY "TARGET" [--yes]  # transition name or target status name
  tickets.py create --summary S [--type Task] [--parent KEY] [--labels a,b]
                    [--desc-file FILE] [--project P] [--yes]
  tickets.py set-parent KEY PARENT [--yes]
  tickets.py assign KEY ACCOUNT|me [--yes]
  tickets.py worklog KEY SECONDS [--yes]
  tickets.py attach KEY FILE [--yes]

Comment format (FILE): blank lines separate paragraphs; consecutive "- " lines form a
bullet list; `@[Display Name](accountId)` becomes a real mention (plain names notify
nobody); `[text](https://url)` becomes a link.
"""
import argparse
import base64
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
import uuid


def die(msg, code=1):
    print(f"tickets: {msg}", file=sys.stderr)
    sys.exit(code)


def dry_run(args, what):
    """Writes are opt-in: without --yes, describe the action and stop."""
    if not getattr(args, "yes", False):
        print(f"DRY RUN (add --yes to execute): {what}")
        sys.exit(0)


# ---------------------------------------------------------------- comment text -> ADF
MENTION = re.compile(r"@\[([^\]]+)\]\(([^)\s]+)\)")
LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)\s]+)\)")
TOKEN = re.compile(r"@\[[^\]]+\]\([^)\s]+\)|\[[^\]]+\]\(https?://[^)\s]+\)")


def inline(text):
    nodes, pos = [], 0
    for m in TOKEN.finditer(text):
        if m.start() > pos:
            nodes.append({"type": "text", "text": text[pos:m.start()]})
        tok = m.group(0)
        mm = MENTION.fullmatch(tok)
        if mm:
            nodes.append({"type": "mention", "attrs": {"id": mm.group(2), "text": "@" + mm.group(1)}})
        else:
            lm = LINK.fullmatch(tok)
            nodes.append({"type": "text", "text": lm.group(1),
                          "marks": [{"type": "link", "attrs": {"href": lm.group(2)}}]})
        pos = m.end()
    if pos < len(text):
        nodes.append({"type": "text", "text": text[pos:]})
    return nodes or [{"type": "text", "text": text}]


def to_adf(text):
    content, bullets = [], []

    def flush():
        if bullets:
            content.append({"type": "bulletList", "content": [
                {"type": "listItem", "content": [{"type": "paragraph", "content": inline(b)}]}
                for b in bullets]})
            bullets.clear()

    for line in text.splitlines():
        s = line.rstrip()
        if s.startswith("- "):
            bullets.append(s[2:])
        elif not s.strip():
            flush()
        else:
            flush()
            content.append({"type": "paragraph", "content": inline(s)})
    flush()
    return {"type": "doc", "version": 1, "content": content or [{"type": "paragraph", "content": []}]}


def adf_text(node, depth=0):
    """ADF -> readable markdown-ish text (mentions and links kept visible)."""
    if node is None:
        return ""
    if isinstance(node, list):
        return "".join(adf_text(n, depth) for n in node)
    t, c = node.get("type"), node.get("content")
    if t == "text":
        href = next((m["attrs"]["href"] for m in node.get("marks", []) if m.get("type") == "link"), None)
        return f"[{node.get('text', '')}]({href})" if href else node.get("text", "")
    if t == "mention":
        return "@" + node.get("attrs", {}).get("text", "").lstrip("@")
    if t == "hardBreak":
        return "\n"
    if t == "paragraph":
        return adf_text(c, depth) + "\n\n"
    if t == "heading":
        return "#" * node.get("attrs", {}).get("level", 1) + " " + adf_text(c, depth).strip() + "\n\n"
    if t in ("bulletList", "orderedList"):
        out = []
        for i, item in enumerate(c or [], 1):
            marker = "- " if t == "bulletList" else f"{i}. "
            out.append("  " * depth + marker + adf_text(item.get("content"), depth + 1).strip())
        return "\n".join(out) + "\n\n"
    if t == "codeBlock":
        return "```\n" + adf_text(c, depth) + "\n```\n\n"
    if t == "taskList":
        return "\n".join(("[x] " if i.get("attrs", {}).get("state") == "DONE" else "[ ] ")
                         + adf_text(i.get("content"), depth).strip() for i in c or []) + "\n\n"
    if t in ("mediaSingle", "mediaGroup", "mediaInline"):
        return "[image/attachment — see Attachments]\n\n"
    if t == "inlineCard":
        return node.get("attrs", {}).get("url", "[link]")
    return adf_text(c, depth) if c is not None else ""


# ---------------------------------------------------------------- jira backend
class Jira:
    def __init__(self):
        self.base = (os.environ.get("JIRA_URL") or "").rstrip("/")
        email, token = os.environ.get("JIRA_EMAIL"), os.environ.get("JIRA_TOKEN")
        missing = [n for n, v in (("JIRA_URL", self.base), ("JIRA_EMAIL", email), ("JIRA_TOKEN", token)) if not v]
        if missing:
            die("missing env " + ", ".join(missing)
                + " — inject them with the project's secrets tool (see the skill's adapter)")
        if not self.base.startswith("https://") and not os.environ.get("TICKETS_ALLOW_HTTP"):
            die("JIRA_URL must be https://")
        self.auth = "Basic " + base64.b64encode(f"{email}:{token}".encode()).decode()
        self.project = os.environ.get("JIRA_PROJECT", "")

    def key(self, k):
        if k.isdigit():
            if not self.project:
                die(f"'{k}' has no project prefix and JIRA_PROJECT is unset")
            return f"{self.project}-{k}"
        return k

    def call(self, method, path, payload=None, raw=None, headers=None):
        data = raw if raw is not None else (json.dumps(payload).encode() if payload is not None else None)
        req = urllib.request.Request(self.base + path, data=data, method=method)
        req.add_unredirected_header("Authorization", self.auth)  # never forwarded on redirects
        req.add_header("Accept", "application/json")
        if payload is not None:
            req.add_header("Content-Type", "application/json")
        for k, v in (headers or {}).items():
            req.add_header(k, v)
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                body = r.read()
                return json.loads(body) if body.strip() else {}
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:500]
            die(f"{method} {path} -> HTTP {e.code}: {detail}")
        except urllib.error.URLError as e:
            die(f"{method} {path} -> {e.reason}")

    # read
    def whoami(self, a):
        d = self.call("GET", "/rest/api/3/myself")
        print(f"OK: {d.get('displayName')} (accountId {d.get('accountId')})")

    def get(self, a):
        k = self.key(a.key)
        fields = ("summary,description,status,assignee,reporter,issuetype,priority,labels,components,"
                  "parent,subtasks,issuelinks,fixVersions,attachment,created,updated,comment")
        d = self.call("GET", f"/rest/api/3/issue/{k}?fields={fields}")
        if a.json:
            print(json.dumps(d, indent=2))
            return
        f = d.get("fields", {})
        nm = lambda x: x.get("name") if isinstance(x, dict) else x  # noqa: E731
        print(f"# {d.get('key')}  {f.get('summary', '')}\n{self.base}/browse/{d.get('key')}\n")
        print(f"- Type: {nm(f.get('issuetype'))} · Status: {nm(f.get('status'))} · Priority: {nm(f.get('priority'))}")
        print(f"- Assignee: {(f.get('assignee') or {}).get('displayName', 'Unassigned')}"
              f" · Reporter: {(f.get('reporter') or {}).get('displayName', '')}")
        if f.get("parent"):
            p = f["parent"]
            print(f"- Parent: {p.get('key')}  {p.get('fields', {}).get('summary', '')}")
        for label, val in (("Labels", ", ".join(f.get("labels") or [])),
                           ("Components", ", ".join(c.get("name", "") for c in f.get("components") or [])),
                           ("Fix versions", ", ".join(v.get("name", "") for v in f.get("fixVersions") or []))):
            if val:
                print(f"- {label}: {val}")
        print(f"- Created: {f.get('created', '')[:10]} · Updated: {f.get('updated', '')[:10]}")
        print("\n## Description\n")
        print(adf_text(f.get("description")).strip() or "_(no description)_")
        atts = f.get("attachment") or []
        if atts:
            print("\n## Attachments (download: tickets.py attachment ID OUT — then LOOK at images)\n")
            for x in atts:
                print(f"- id={x.get('id')}  {x.get('mimeType')}  {x.get('filename')}  "
                      f"by {(x.get('author') or {}).get('displayName', '')}")
        for title, items in (("Subtasks", f.get("subtasks") or []),):
            if items:
                print(f"\n## {title}\n")
                for s in items:
                    print(f"- {s.get('key')}  [{nm(s.get('fields', {}).get('status'))}]  {s.get('fields', {}).get('summary', '')}")
        links = f.get("issuelinks") or []
        if links:
            print("\n## Linked issues\n")
            for ln in links:
                rel, other = ln.get("type", {}), ln.get("outwardIssue") or ln.get("inwardIssue") or {}
                verb = rel.get("outward") if ln.get("outwardIssue") else rel.get("inward")
                print(f"- {verb}: {other.get('key')}  {other.get('fields', {}).get('summary', '')}")
        comments = (f.get("comment") or {}).get("comments") or []
        if comments and a.comments:
            print(f"\n## Comments (last {min(a.comments, len(comments))} of {len(comments)})\n")
            for c in comments[-a.comments:]:
                print(f"--- {c.get('created', '')[:10]} {c['author']['displayName']}:")
                print(adf_text(c.get("body")).strip() + "\n")

    def search(self, a):
        q = urllib.parse.quote(a.query)
        # /rest/api/3/search was removed (HTTP 410); /search/jql is the replacement.
        d = self.call("GET", f"/rest/api/3/search/jql?maxResults={a.max}&fields=summary,status,issuetype&jql={q}")
        for i in d.get("issues", []):
            f = i["fields"]
            print(f"{i['key']}  [{f['status']['name']}]  {f.get('issuetype', {}).get('name', '')}: {f['summary']}")

    def comments(self, a):
        d = self.call("GET", f"/rest/api/3/issue/{self.key(a.key)}/comment?maxResults=100")
        for c in (d.get("comments") or [])[-a.last:]:
            body = adf_text(c.get("body")).strip()
            mentions = re.findall(r"@\S+", body)
            print(f"--- id={c['id']} {c.get('created', '')[:10]} {c['author']['displayName']} mentions={mentions or 'none'}")
            print(body + "\n")

    def transitions(self, a):
        d = self.call("GET", f"/rest/api/3/issue/{self.key(a.key)}/transitions")
        for t in d.get("transitions", []):
            print(f"{t['id']}\t{t['name']}\t-> {t['to']['name']}")

    def attachment(self, a):
        req = urllib.request.Request(f"{self.base}/rest/api/3/attachment/content/{a.id}")
        req.add_unredirected_header("Authorization", self.auth)  # never forwarded on redirects
        try:
            with urllib.request.urlopen(req, timeout=120) as r, open(a.out, "wb") as fh:
                shutil.copyfileobj(r, fh)
        except urllib.error.HTTPError as e:
            die(f"attachment {a.id} -> HTTP {e.code}")
        print(f"saved {a.out} ({os.path.getsize(a.out)} bytes)")

    # write
    def comment(self, a):
        k, text = self.key(a.key), open(a.file, encoding="utf-8").read()
        dry_run(a, f"comment on {k} ({len(text)} chars):\n{text}")
        d = self.call("POST", f"/rest/api/3/issue/{k}/comment", {"body": to_adf(text)})
        print(f"commented on {k} (id={d.get('id')})")

    def transition(self, a):
        k, target = self.key(a.key), a.target.lower()
        ts = self.call("GET", f"/rest/api/3/issue/{k}/transitions").get("transitions", [])
        match = [t for t in ts if target in (t["name"].lower(), t["to"]["name"].lower(), str(t["id"]))]
        if not match:
            die(f"no transition matching '{a.target}'. Available: "
                + ", ".join(f"{t['name']} -> {t['to']['name']}" for t in ts))
        t = match[0]
        dry_run(a, f"transition {k} via '{t['name']}' -> {t['to']['name']}")
        self.call("POST", f"/rest/api/3/issue/{k}/transitions", {"transition": {"id": t["id"]}})
        print(f"transitioned {k} -> {t['to']['name']}")

    def create(self, a):
        project = a.project or self.project or die("--project or JIRA_PROJECT required")
        fields = {"project": {"key": project}, "summary": a.summary, "issuetype": {"name": a.type}}
        if a.parent:
            fields["parent"] = {"key": self.key(a.parent)}
        if a.labels:
            fields["labels"] = [x.strip() for x in a.labels.split(",") if x.strip()]
        if a.desc_file:
            fields["description"] = to_adf(open(a.desc_file, encoding="utf-8").read())
        dry_run(a, f"create {a.type} in {project}: '{a.summary}' parent={a.parent} labels={a.labels}")
        d = self.call("POST", "/rest/api/3/issue", {"fields": fields})
        print(f"created {d.get('key')}  {self.base}/browse/{d.get('key')}")

    def set_parent(self, a):
        k = self.key(a.key)
        dry_run(a, f"set parent of {k} to {a.parent}")
        self.call("PUT", f"/rest/api/3/issue/{k}", {"fields": {"parent": {"key": self.key(a.parent)}}})
        print(f"{k} parent -> {a.parent}")

    def assign(self, a):
        k = self.key(a.key)
        acct = self.call("GET", "/rest/api/3/myself")["accountId"] if a.account == "me" else a.account
        dry_run(a, f"assign {k} to {a.account}")
        self.call("PUT", f"/rest/api/3/issue/{k}/assignee", {"accountId": acct})
        print(f"{k} assigned")

    def worklog(self, a):
        k = self.key(a.key)
        dry_run(a, f"log {a.seconds}s ({a.seconds / 3600:.2f}h) on {k}")
        d = self.call("POST", f"/rest/api/3/issue/{k}/worklog", {"timeSpentSeconds": a.seconds})
        print(f"logged {d.get('timeSpent')} on {k}")

    def attach(self, a):
        k = self.key(a.key)
        if not os.path.isfile(a.file):
            die(f"no such file: {a.file}")
        dry_run(a, f"attach {a.file} to {k}")
        boundary = uuid.uuid4().hex
        ctype = mimetypes.guess_type(a.file)[0] or "application/octet-stream"
        with open(a.file, "rb") as fh:
            body = (f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
                    f"filename=\"{os.path.basename(a.file)}\"\r\nContent-Type: {ctype}\r\n\r\n").encode() \
                   + fh.read() + f"\r\n--{boundary}--\r\n".encode()
        d = self.call("POST", f"/rest/api/3/issue/{k}/attachments", raw=body,
                      headers={"X-Atlassian-Token": "no-check",
                               "Content-Type": f"multipart/form-data; boundary={boundary}"})
        for x in d if isinstance(d, list) else []:
            print(f"attached {x.get('filename')} id={x.get('id')}")


# ---------------------------------------------------------------- github backend
class GitHub:
    def __init__(self):
        if not shutil.which("gh"):
            die("the github backend needs the `gh` CLI (logged in via `gh auth login`)")
        self.repo = ["--repo", os.environ["GH_REPO"]] if os.environ.get("GH_REPO") else []

    def gh(self, *args, capture=True):
        r = subprocess.run(["gh", *args, *self.repo], capture_output=capture, text=True)
        if r.returncode != 0:
            die(f"gh {' '.join(args[:2])} failed: {(r.stderr or '').strip()[:400]}")
        return r.stdout

    @staticmethod
    def num(k):
        return k.lstrip("#").split("-")[-1]

    def whoami(self, a):
        r = subprocess.run(["gh", "api", "user", "--jq", ".login"], capture_output=True, text=True)
        print(f"OK: {r.stdout.strip()}" if r.returncode == 0 else "not logged in: run `gh auth login`")

    def get(self, a):
        fields = "number,title,state,body,author,assignees,labels,milestone,comments,createdAt,updatedAt,url"
        d = json.loads(self.gh("issue", "view", self.num(a.key), "--json", fields))
        if a.json:
            print(json.dumps(d, indent=2))
            return
        print(f"# #{d['number']}  {d['title']}\n{d['url']}\n")
        print(f"- State: {d['state']} · Author: {d['author']['login']} · Assignees: "
              f"{', '.join(x['login'] for x in d['assignees']) or 'none'}")
        if d.get("labels"):
            print(f"- Labels: {', '.join(x['name'] for x in d['labels'])}")
        if d.get("milestone"):
            print(f"- Milestone: {d['milestone'].get('title')}")
        print("\n## Description\n")
        print((d.get("body") or "").strip() or "_(no description)_")
        imgs = re.findall(r"!\[[^\]]*\]\((https?://[^)]+)\)|<img[^>]+src=\"([^\"]+)\"", d.get("body") or "")
        if imgs:
            print("\n## Images in the description (download with `gh` or the browser, then LOOK at them)\n")
            for i in imgs:
                print("- " + (i[0] or i[1]))
        cs = d.get("comments") or []
        if cs and a.comments:
            print(f"\n## Comments (last {min(a.comments, len(cs))} of {len(cs)})\n")
            for c in cs[-a.comments:]:
                print(f"--- {c['createdAt'][:10]} {c['author']['login']}:\n{c['body'].strip()}\n")

    def search(self, a):
        print(self.gh("issue", "list", "--search", a.query, "--limit", str(a.max), "--state", "all"), end="")

    def comments(self, a):
        a.comments, a.json = a.last, False
        self.get(a)

    def transitions(self, a):
        print("github issues: open | closed | closed:not_planned (use `transition KEY closed`)")

    def attachment(self, a):
        die("github: attachments are URLs in the issue body; download them directly")

    def comment(self, a):
        text = open(a.file, encoding="utf-8").read()
        dry_run(a, f"comment on #{self.num(a.key)}:\n{text}")
        self.gh("issue", "comment", self.num(a.key), "--body-file", a.file)
        print(f"commented on #{self.num(a.key)}")

    def transition(self, a):
        n, t = self.num(a.key), a.target.lower()
        dry_run(a, f"set #{n} to {t}")
        if t in ("open", "reopen", "reopened"):
            self.gh("issue", "reopen", n)
        elif t in ("closed", "close", "done", "completed"):
            self.gh("issue", "close", n, "--reason", "completed")
        elif t in ("closed:not_planned", "not planned", "wontfix"):
            self.gh("issue", "close", n, "--reason", "not planned")
        else:
            die("github targets: open | closed | closed:not_planned")
        print(f"#{n} -> {t}")

    def create(self, a):
        args = ["issue", "create", "--title", a.summary,
                "--body-file", a.desc_file] if a.desc_file else ["issue", "create", "--title", a.summary, "--body", ""]
        if a.labels:
            args += ["--label", a.labels]
        if a.parent:
            args += ["--milestone", a.parent]
        dry_run(a, f"create issue '{a.summary}' labels={a.labels} milestone={a.parent}")
        print(self.gh(*args).strip())

    def set_parent(self, a):
        dry_run(a, f"set milestone of #{self.num(a.key)} to {a.parent}")
        self.gh("issue", "edit", self.num(a.key), "--milestone", a.parent)
        print("done")

    def assign(self, a):
        who = "@me" if a.account == "me" else a.account
        dry_run(a, f"assign #{self.num(a.key)} to {who}")
        self.gh("issue", "edit", self.num(a.key), "--add-assignee", who)
        print("done")

    def worklog(self, a):
        die("github issues have no worklog; put the estimate in the resolution comment")

    def attach(self, a):
        die("github: the CLI cannot upload attachments; link the file or paste the image in the browser")


# ---------------------------------------------------------------- cli
def main():
    p = argparse.ArgumentParser(description="Issue-tracker CLI (jira | github).")
    p.add_argument("--backend", default=os.environ.get("TICKETS_BACKEND", "jira"), choices=["jira", "github"])
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("whoami")
    s = sub.add_parser("get"); s.add_argument("key"); s.add_argument("--json", action="store_true")
    s.add_argument("--comments", type=int, default=5)
    s = sub.add_parser("search"); s.add_argument("query"); s.add_argument("--max", type=int, default=30)
    s = sub.add_parser("comments"); s.add_argument("key"); s.add_argument("--last", type=int, default=5)
    s = sub.add_parser("transitions"); s.add_argument("key")
    s = sub.add_parser("attachment"); s.add_argument("id"); s.add_argument("out")

    def w(name, *pos):
        s = sub.add_parser(name)
        for x in pos:
            s.add_argument(x)
        s.add_argument("--yes", action="store_true", help="execute (default: dry run)")
        return s
    w("comment", "key", "file")
    w("transition", "key", "target")
    s = w("create"); s.add_argument("--summary", required=True); s.add_argument("--type", default="Task")
    s.add_argument("--parent"); s.add_argument("--labels"); s.add_argument("--desc-file"); s.add_argument("--project")
    w("set-parent", "key", "parent")
    w("assign", "key", "account")
    s = w("worklog", "key"); s.add_argument("seconds", type=int)
    w("attach", "key", "file")

    a = p.parse_args()
    backend = Jira() if a.backend == "jira" else GitHub()
    getattr(backend, a.cmd.replace("-", "_"))(a)


if __name__ == "__main__":
    main()
