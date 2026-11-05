---
name: marpiech-publish-check
description: Check what the world will see before anything becomes public — open-sourcing a repository, pushing to a public remote, publishing a package, sharing a skill, a gist or a docs site. Lists every file that would be published (including untracked files a careless `git add -A` would sweep in) and flags risky ones (env and key files, credential JSON, infrastructure state, database dumps, archives, notebooks with outputs, logs, agent-local files); scans content for secret shapes (redacted, never printed), terms from a private deny list kept outside the repository (company, product, customer, people, internal host names), e-mail addresses, non-documentation IPs, home-directory paths, internal host names, bucket URLs and cloud resource ids, and ticket keys; checks git metadata (author e-mails, remotes with embedded tokens, files deleted but still in history, large blobs); then reads the diff as an outsider. A failed check blocks the publication. Proposes a whitelist `.gitignore` for repos that publish only a subset. Use when the user says "/marpiech-publish-check", "is this safe to publish?", "open-source this repo", "make the repo public", "before I push to GitHub", "publication check", "does this leak anything?", "check for internal names", or before the first push of a repository or package that will be public.
---

# marpiech-publish-check — nothing leaves that should not

## Purpose

Publishing is irreversible: a pushed commit is cloned, cached, mirrored and indexed within
minutes, and deleting it later does not unpublish it. Most leaks are not dramatic secrets;
they are the internal host name in an example, a customer's name in a test fixture, a home
path in a notebook output, a personal e-mail in commit metadata, a `.env` deleted three
commits ago but still in history, a file nobody meant to add. This skill runs a fixed,
repeatable check before anything becomes public — files, content, metadata, history, and
one careful read as an outsider — and blocks the publication until every flag is either
removed or deliberately allowed with a reason. Outcome: a publication you can defend, and
a project-local record of what is deliberately public.

`<SKILL_DIR>` = the directory holding this SKILL.md; `<PC>` =
`python3 <SKILL_DIR>/scripts/publish_check.py` (stdlib + git; read-only, no network).

---

## Step 0 — Self-update (every run, takes a second)

1. Run `<SKILL_DIR>/scripts/self-update.sh`.
2. Interpret the exit code:
   - `0` → nothing to do (up to date, offline, or a copied install). Continue silently.
   - `10` → updates are available. Show the user the printed commit list and file
     summary in one short message and ASK whether to update. IF yes → run
     `<SKILL_DIR>/scripts/self-update.sh --apply`, then re-read this SKILL.md before
     continuing (it may have changed). IF no → continue with the current version.
   - `20` → the clone has local edits or diverged history. Tell the user in one line;
     do not attempt to fix it; continue with the current version.
3. Never pull, reset, or stash on your own. Never run self-update more than once per
   session.

## Step 1 — Load the project adapter

1. Look for `.claude/adapters/marpiech-publish-check.md` and `.publish-allow` in the
   repository root. (In a repository that publishes only a whitelist, the adapter may
   itself be unpublished — that is fine; it is read locally.)
2. IF present → read: what is meant to be public (paths, or "everything tracked"), where
   the deny list lives (a path OUTSIDE this repository), the ticket-key pattern, tools
   allowed (e.g. gitleaks), the publication target (public remote, package index, docs
   host), and the log of earlier checks.
3. ELSE → defaults: everything tracked is meant to be public; deny list at
   `$PUBLISH_DENY_FILE` or `~/.config/marpiech-publish-check/deny.txt`; no ticket
   pattern. IF no deny list exists → Step 2 builds one with the user.
4. IF /marpiech-memory is installed → READ mode for "public", "open source", "publish":
   earlier decisions about what may be shown live there.

---

## Algorithm

### Step 2 — Fix the target and the deny list

1. **Target**: what exactly becomes public and how — the whole repository and its
   history (making a repo public, first push to a public remote), only new commits (a
   push to an already-public repo), a built artefact (package, docs site, container), or
   a single file (gist, snippet). The target decides which steps apply:

   | target | Steps |
   |--------|-------|
   | repo goes public / first public push | 3, 4, 5 (full history), 6, 7 |
   | push of new commits to a public repo | 3, 4 (`--history <n new commits>`), 6 |
   | package / artefact | IF /marpiech-release-python applies → its artefact audit; ELSE unpack the artefact into an empty scratch dir and run 4 on it |
   | single file | 4 on that file, 6 |

2. **Deny list** — the private list of what must never appear publicly. It lives
   **outside** the repository (it names exactly what must not leak, so it is sensitive
   itself). IF none exists → propose one from what you can see, then ask the user to
   complete it, in one message:
   - organisation, product, team and customer names (and their short forms);
   - people's names and handles other than the intended author;
   - internal domains, host names, cluster/namespace names, cloud project ids, bucket
     names, database names;
   - internal project names of sibling repositories this code was derived from.
   Write it with `templates/deny.template.txt` to the path from Step 1. Never commit it.
3. **Ticket pattern** — the project's ticket-key regex (e.g. `ACME-[0-9]+`) when ticket
   keys must not leak.

### Step 3 — What would be published (files)

```bash
<PC> files [--all-untracked]
git status --short          # what is staged right now
git add -A -n               # what `git add -A` would add (dry run)
```

FOR each flagged file:
- ENV / KEY / CREDENTIALS / STATE / DUMP → must not be published. IF tracked → stop:
  remove it from the index (`git rm --cached`) and IF it ever held a real credential →
  rotate first (IF /marpiech-secrets is installed → its rotate-first response), then
  decide about history (Step 5).
- ARCHIVE / LOG / NOTEBOOK / LARGE / JUNK / AGENT-LOCAL → open it; publish only if it is
  meant to be public and clean (notebooks: clear outputs first).
- Untracked, not ignored → decide per file: ignore it, or add it on purpose.

For repositories that publish only part of their tree, propose a **whitelist**
`.gitignore` (`templates/whitelist.gitignore.template`): ignore everything, re-include
only the published paths, and re-ignore known dangerous names inside them. A whitelist
fails safe — a new file is private until someone decides otherwise.

### Step 4 — What the content says (scan)

```bash
<PC> scan [paths] --deny <deny file> [--ticket-regex '<RX>'] [--history N]
```

Also, when installed: `gitleaks detect --redact` (thorough secret scan, current tree and
history); IF /marpiech-secrets is installed → its `scan`.

FOR each finding, read the line in context and decide:

| rule | default decision |
|------|------------------|
| SECRET | never publish. Remove; rotate if it was ever real; never print the value. |
| DENY | remove or generalise ("a production genomics platform", `<PROJECT>`, `acme-shop`). |
| EMAIL | replace with `@example.com` unless it is the intended public contact. |
| IP | replace with a documentation address (`192.0.2.x`, `198.51.100.x`, `203.0.113.x`). |
| HOME | replace with `~` or `<HOME>`; it names a person and a machine layout. |
| HOST | replace with `example.com` / `<HOST>`. |
| CLOUD | replace with `<BUCKET>` / `<PROJECT_ID>`. |
| TICKET | remove the key; keep the lesson. |

A deliberate example (a documented `@example.com` address, a regex quoted in a skill)
goes into `.publish-allow` (`RULE path-glob [text-regex]`) with a one-line reason in the
adapter. Never widen the allow list to silence a real hit.

### Step 5 — What the metadata and history say

```bash
<PC> meta
```

- **Identities**: every author and committer name and e-mail is published with every
  clone. IF an address is not meant to be public → tell the user; the fix for future
  commits is the host's no-reply address (`git config user.email`); rewriting existing
  history is the user's decision (Step 7).
- **Remotes with embedded credentials** → remove the token from the URL and rotate it.
- **HISTORY-ONLY files** (deleted but still downloadable) and history findings from
  Step 4 → a file removed in a later commit is still public. Options, in order of
  preference: (a) publish a fresh repository with a squashed history; (b) rewrite history
  with a dedicated tool (`git filter-repo`) — destructive, the user runs it and pushes;
  (c) accept, only if the content is harmless. Any real credential found in history is
  rotated first, whatever is decided about the history.
- **Branches and tags**: only the ones meant to be public are pushed (`git push <remote>
  <branch>`, never `--all` or `--mirror` for a first public push).

### Step 6 — Read it as an outsider (the step no script replaces)

Read the full diff to be published (`git diff <last public commit>..HEAD`, or every file
for a first publication) once, top to bottom, as a stranger would, and answer in writing:
1. Could someone learn the source organisation's name, customers, people, internal
   systems or infrastructure layout from this? (Stories, incident dates, "as we did for
   X", example values that are real values.)
2. Does any instruction widen someone's attack surface if followed — disabling TLS
   verification, `curl | sh`, world-writable permissions, printing secrets, running
   code fetched from the network unseen?
3. Does every example look like an example (`acme-shop`, `example.com`, `ACME-123`)?
4. Are licence and attribution right for anything adapted from elsewhere (keep upstream
   licence notices; MIT/Apache text needs its notice; unlicensed text is re-expressed,
   not copied)?

IF any answer is "yes / no / not sure" in the wrong direction → generalise and re-run
Step 4.

### Step 7 — Verdict and hand-off

```
## Publication check — <target> — <date>
Files:   <n> to publish · flagged <n> (resolved <n>)
Content: SECRET <n> · DENY <n> · EMAIL <n> · IP <n> · HOME <n> · HOST <n> · CLOUD <n> · TICKET <n>  (allowed <n>)
Meta:    identities <list> · history-only risky files <n> · remotes ok
Outsider read: <done — notes>
Verdict: PASS | BLOCKED (<what remains>)
```

- PASS → the user publishes (or asks you to push). Push only the intended branch; never
  force-push.
- BLOCKED → list each remaining item with its fix. Never publish "with known issues".
- Record the run (date, target, verdict, allow-list changes) in the adapter's log.

---

## Rules & guardrails

- **A failed check blocks publication.** No exceptions for "it's only a test repo".
- **Never print a secret.** The helper redacts; when reading a file, quote the line
  with the value masked.
- **The deny list never enters the repository** it protects (the helper warns if it
  does). It is not published, not committed, not pasted into issues.
- **History rewrites and force-pushes are the user's actions.** Propose the command and
  its consequences; do not run it. Rotate leaked credentials first, always.
- **Ask before any outward action**: making a repository public, pushing, publishing a
  package, creating a gist.
- Allow-list entries are deliberate and explained; review them on every run.

---

## Adapting this skill to your project

**1. Placeholders and their defaults**

| setting | default | how to discover the right value |
|---------|---------|----------------------------------|
| what is public | everything tracked | `.gitignore` shape; the README; the user |
| publication target | the public remote | `git remote -v`, package config, docs host config |
| deny-list path | `$PUBLISH_DENY_FILE` or `~/.config/marpiech-publish-check/deny.txt` | outside the repo, always |
| ticket pattern | none | recent commit messages |
| allow list | `.publish-allow` | — |
| extra tools | gitleaks if installed | `which gitleaks` |

**2. Files:** adapter `<project>/.claude/adapters/marpiech-publish-check.md`
(`templates/adapter.template.md`); allow list `<project>/.publish-allow`; deny list
outside the project (`templates/deny.template.txt`); whitelist `.gitignore`
(`templates/whitelist.gitignore.template`).

**3. Example adapter for a fictional project**

```markdown
# marpiech-publish-check — project adapter (acme-shop-sdk)

## Target
- public GitHub repo; published paths: src/, docs/, README.md, LICENSE (whitelist .gitignore)
- package: PyPI via /marpiech-release-python

## Deny list
- ~/.config/marpiech-publish-check/acme.txt (company, customers, internal hosts)
- tickets: ACME-[0-9]+

## Allow list reasons
- EMAIL docs/* @example\.com — documentation examples
- HOST tests/* \.local — mDNS test fixture names, not real hosts

## Log (newest first)
- 2026-04-02 — first public push: PASS after removing 3 customer names from fixtures,
  squashed history (an old .env), author e-mail switched to the no-reply address
```

---

## CLAUDE.md snippet

```markdown
## Publication (skill: marpiech-publish-check)
- Before making anything public (repo, first push to a public remote, package, gist,
  docs site): `/marpiech-publish-check` — files, content vs the private deny list,
  metadata and history, then an outsider read. A failed check blocks publication.
- The deny list lives outside this repository. Never print secrets; rotate before
  rewriting history; history rewrites and force-pushes are done by a human.
```

---

## Self-update log

Generic learnings, newest first. Project-specific learnings go to the project's adapter.

- 2026-11-05 — initial generic version, generalised from the publication check a public
  skills repository runs before every push (whitelist `.gitignore`, secret grep, surface
  grep for source-project names, outsider read) plus the "prepare for open-sourcing"
  practice of checking history and metadata. First runs: file names such as
  `CLAUDE.local.md` and `.env.local` matched the internal-host pattern — the host rule now
  ignores names that continue with a file extension or are preceded by a dot; commit
  author e-mails are the most commonly overlooked exposure.
