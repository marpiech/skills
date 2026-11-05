---
name: marpiech-security
description: Adversarial security review — of a change (differential review of a diff or PR), of the whole repository (fail-open defaults, sharp edges, injection sinks, secrets), of CI and AI-agent workflows (privileged triggers that run untrusted code, untrusted event text interpolated into scripts, unpinned third-party actions, agents that any commenter can steer by prompt injection), and of the dependency supply chain (missing lock files, open ranges, direct URL dependencies, install hooks, extra package indexes). A read-only helper finds candidates; every candidate is then verified by tracing attacker-controlled input to a dangerous sink, checking preconditions and impact, and labelled CONFIRMED, PLAUSIBLE or FALSE POSITIVE before it is reported — no unverified findings, no working exploits against real systems. Also triages incoming vulnerability reports and checks that a security fix has no missed variants. Use when the user says "/marpiech-security", "security review", "is this change safe?", "review this PR for security", "threat model", "check our GitHub Actions", "is our CI safe?", "supply-chain check", "audit dependencies", "insecure defaults", "we got a vulnerability report", "did the fix cover everything?", or before merging changes to authentication, authorisation, sessions, crypto, file handling, templates rendering user data, CI workflows or dependency manifests.
---

# marpiech-security — find what an attacker would, prove it, fix it at the source

## Purpose

Rule-compliance audits ask "does the code follow our rules?"; a security review asks
"what can someone who wants to misuse this system make it do?". The two find different
things. This skill looks at code the way an attacker does: where untrusted data enters,
where it can reach something dangerous, which defaults fail open, which CI step runs a
stranger's code with the repository's secrets, which dependency could be swapped. It is
strict about evidence: a helper finds candidates cheaply, and each candidate becomes a
finding only after its path from attacker-controlled input to impact has been traced and
verified. Outcome: a short, ranked list of verified findings, each with its source → sink
path, preconditions, impact, and the one place to fix it — plus the false positives that
were ruled out, so nobody re-investigates them.

`<SKILL_DIR>` = the directory holding this SKILL.md; `<SEC>` =
`python3 <SKILL_DIR>/scripts/security.py` (stdlib + git; read-only, never uses the
network, never runs project code).

Relationship to other skills: /marpiech-audit checks the project's own rules (and keeps
cheap greppable security regressions in its catalogue); /marpiech-secrets owns secret
scanning and leak response. This skill uses both when installed and does not duplicate
them.

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

1. Look for `.claude/adapters/marpiech-security.md` and the helper config
   `.claude/security.json` in the repository root.
2. IF present → read: the system's trust boundaries (who the users and roles are, what
   is internet-facing, which services trust which), where authentication and
   authorisation are enforced, tenancy model, accepted risks (each with the decision that
   accepted it), the helper's excludes and allow-list, advisory tools the team allows to
   run (they use the network), and project learnings.
3. ELSE → use defaults: every HTTP entry point is internet-facing, every user is
   untrusted, no accepted risks. Read CLAUDE.md and the architecture docs it links for the
   trust boundaries; write down the ones you inferred and show them to the user in the
   report. Offer to save them as the adapter (`templates/adapter.template.md`).
4. IF /marpiech-memory is installed → READ mode for "security", "auth", "permission",
   the touched modules: earlier incidents and accepted risks live there.

---

## Algorithm

### Step 2 — Choose the mode and scope

```
"is this change / PR safe?", called before a merge     → DIFF     (--diff <merge-base>)
"security review of <service | repo>", periodically    → SWEEP    (--scope <paths> or whole repo)
"check our CI / GitHub Actions / agent workflows"      → CI
"supply chain", "audit dependencies", a manifest diff  → DEPS
"we got a report", "is this CVE relevant?"             → TRIAGE
"did the fix cover everything?"                        → VARIANTS
```

A DIFF that touches `.github/workflows/` also runs CI; one that touches a dependency
manifest or lock file also runs DEPS. A SWEEP runs all four helper commands.

### Step 3 — Model the attacker (five minutes, written down)

Before reading code, write in three to six lines:
- **Entry points** in scope: HTTP routes, form posts, file uploads, webhooks, message
  consumers, CLI arguments, CI triggers, environment the attacker can influence.
- **Attackers**: anonymous internet user, authenticated user of another tenant, a
  low-privilege user, a pull-request author from a fork, an issue commenter, a
  compromised dependency.
- **Assets**: other tenants' data, credentials and tokens, the ability to run code
  (server, CI runner), money/credits, audit trail integrity, availability.

Every finding later names one attacker, one entry point and one asset. A candidate that
cannot be tied to all three is not a finding.

### Step 4 — Collect candidates (cheap, mechanical)

Run what the mode needs; add `--diff <base>` in DIFF mode (only ADDED lines are scanned):

```bash
<SEC> surface  [--diff BASE] [--scope …]   # which security-sensitive areas the scope touches
<SEC> defaults [--diff BASE] [--scope …]   # fail-open / insecure defaults and dangerous calls
<SEC> actions                              # CI workflows and AI-agent workflows
<SEC> deps                                 # manifests, lock files, ranges, URL deps, hooks, indexes
```

Plus:
- IF /marpiech-secrets is installed → its `scan` (committed env files, key material,
  secret-shaped strings in files and history). ELSE grep for key material yourself and
  never print a matched value — print the file, line and a masked prefix only.
- IF /marpiech-audit is installed → its security, isolation and authorisation
  categories (`references/categories.md` A, I, H) for the same scope.
- Language tools the project already has (e.g. `bandit`, `semgrep` with local rules,
  `gosec`, `brakeman`) — run them only if installed and configured offline.
- Advisory databases (`pip-audit`, `npm audit`, `osv-scanner`) use the network: run them
  only when the adapter allows it or the user agrees in this session.

### Step 5 — Read what grep cannot see

The helper finds shapes; the expensive bugs are in logic. For each entry point in scope,
read the code path end to end with `references/review-checklist.md` open, and answer:
1. **Who may call this, and where is that enforced?** Server-side, on every path (HTML
   and API twins, bulk and single, export and view), or only by hiding a button?
2. **Whose data does it touch?** Is every query scoped by the caller's tenant/owner, and
   is a client-supplied id checked against the caller before use?
3. **What does untrusted input reach?** Follow it to SQL, shell, file paths, templates,
   redirects, outbound requests (SSRF), deserialisers, logs (log injection), headers.
4. **What happens when something is missing or fails?** A missing field, an exception, a
   timeout, an unset environment variable — does the check fail closed?
5. **What is trusted that should not be?** Client-sent roles, prices, ids, filenames,
   `X-Forwarded-*` headers, webhook payloads without signature checks, JWTs without
   signature/expiry/audience checks.

DIFF mode: read the full functions the diff touches and their callers, not only the
changed lines. A removed check is as important as an added sink — read deletions too
(`git diff <base> -- <file>` shows them; the helper only scans additions).

### Step 6 — Verify every candidate (the gate)

FOR each candidate (helper hit or reading observation), fill the verification record
from `references/review-checklist.md` §Verification:
- **Source**: the attacker-controlled input, concretely (parameter, header, file field,
  PR title, issue comment).
- **Path**: the functions from source to sink, with file:line for each hop.
- **Sink**: what dangerous thing happens (query, command, file write, render, request,
  privilege decision).
- **Guards on the path**: validation, escaping, parameterisation, authorisation,
  framework protection (autoescape, ORM binding, CSRF middleware). Check each guard
  actually applies to this path.
- **Preconditions**: authentication needed? a role? a feature flag? a race?
- **Impact**: what the attacker gains, against which asset (Step 3).

Verdict:
- **CONFIRMED** — the path exists with no effective guard; impact stated. Demonstrated
  only locally (a unit test, a local request against a local instance, a crafted input
  file) — never against a shared, staging or production system without the user's
  explicit request for that specific test.
- **PLAUSIBLE** — the path likely exists but one hop could not be confirmed (dynamic
  dispatch, configuration not in the repo). Say exactly which hop.
- **FALSE POSITIVE** — say which guard stops it, with file:line. Record it so it is not
  re-investigated (Step 10).

Spot-check every "X is never validated" or "Y is not set anywhere" claim yourself —
absence claims are the most common error, human or agent.

### Step 7 — Rate severity

| severity | meaning (impact × reach) |
|----------|--------------------------|
| **Critical** | unauthenticated (or any-user) code execution, cross-tenant data access, credential theft, CI that runs a stranger's code with deploy secrets |
| **High** | privilege escalation, an authenticated user reading/changing another user's data, stored XSS in a shared view, SSRF to internal services, signature checks off on tokens or webhooks |
| **Medium** | needs an unlikely precondition or yields limited data; reflected XSS behind auth; missing rate limits on credential endpoints; open redirect used in auth flows |
| **Low** | defence in depth: a missing header, verbose errors, a debug flag in a non-deployed default, an unpinned action in a workflow with no secrets |

Raise one level when the asset is clinical, financial or personal data; lower one level
when a verified compensating control exists (state it).

### Step 8 — Report

```
## Security review — <mode> — <scope> — <date>
Attacker model: <entry points · attackers · assets, 3–6 lines>
Helper: surface <n> · defaults <n> · actions <n> · deps <n> · secrets <n>  →  verified <n>

### Findings (Critical first; max ~10)
- [High] CONFIRMED — <what an attacker can do, in one sentence>
  source <param @ file:line> → <hop file:line> → sink <file:line>
  preconditions: <…> · impact: <asset> · fix at: <the one place> — <how>
  test: <the regression test that proves the fix>
- [Medium] PLAUSIBLE — … — unconfirmed hop: <which and why>

### Ruled out (false positives, with the guard that stops each)
### Accepted risks touched (decision reference)
### Not covered (what this review did not look at)
```

Write findings for defenders: describe the class of problem and the path, never a
weaponised payload or a step-by-step exploit for a real deployed system.

### Step 9 — Fix (only when asked) and check variants

1. Fix at the **source of the weakness**, once: the central query builder, the
   authorisation dependency, the path-builder that rejects `..`, the workflow's trigger —
   not every caller. IF the fix is a pattern change (e.g. parameterise every query in a
   module), make it in one place that everything uses.
2. Regression test first — IF /marpiech-tests is installed → use it; the test must fail
   on the vulnerable code (the attacker's input succeeds) and pass after the fix.
3. **VARIANTS**: describe the weakness as a code shape and grep the whole repository for
   it; verify each hit with Step 6. IF the shape is mechanical and /marpiech-audit is
   installed → propose it as a catalogue check so it cannot return silently.
4. A leaked credential is never "fixed" by deleting it from the code: IF
   /marpiech-secrets is installed → its rotate-first response; ELSE tell the user to
   rotate the credential first, then clean history.

### Step 10 — Record

1. Accepted risks the user decides on → the adapter's "Accepted risks" with the date and
   the reason (and in /marpiech-memory, if installed).
2. False positives that will recur → `.claude/security.json` `allow` (rule id → path)
   with a one-line reason in the adapter, or narrow the helper rule in this skill if the
   false positive is generic (Self-update log).
3. Generic lessons (a new sink shape, a new CI trap) → this skill's Self-update log and,
   if it changes a step or the checklist, the step or the checklist itself.

---

## Rules & guardrails

- **Verified or labelled.** Nothing is reported as a vulnerability without a Step 6
  record; PLAUSIBLE findings name the unconfirmed hop.
- **No attacks on real systems.** Demonstrate locally only. Never send crafted input to
  shared, staging or production systems, scan networks, brute-force, or test third-party
  services unless the user explicitly asks for that specific action on a system they own.
- **No weaponised output.** Reports describe the weakness, the path and the fix — not a
  ready-to-use exploit.
- **Never print secrets.** Show file, line and a masked prefix; never a value. Never
  write a found secret anywhere.
- **Network only with consent.** The helper never uses it; advisory lookups need the
  adapter's permission or the user's yes in this session.
- Do not weaken a control to make a test or a build pass. Do not commit, push or open
  issues for findings unless the user asks; security findings may need private handling
  (no public issue for an unfixed vulnerability).
- Stay in scope; list what was not covered rather than implying it was.

---

## Adapting this skill to your project

**1. Placeholders and their defaults**

| setting | default | how to discover the right value |
|---------|---------|----------------------------------|
| trust boundaries (users, roles, internet-facing parts) | everything internet-facing, every user untrusted | architecture docs, ingress/proxy config, CLAUDE.md |
| where authn/authz is enforced | none assumed | auth middleware/dependencies, decorators, policy modules |
| tenancy model | none | how queries are scoped; a tenant/org/project id in sessions |
| accepted risks | none | security decisions in memory, ADRs |
| helper excludes / allow-list | tests excluded; none allowed | `.claude/security.json` |
| advisory tools allowed (network) | ask each time | team policy |
| local tools | none | `bandit`, `semgrep`, `gosec` configs in the repo |

**2. Files:** adapter `<project>/.claude/adapters/marpiech-security.md`
(`templates/adapter.template.md`); helper config `<project>/.claude/security.json`
(`templates/security.template.json`). Both committed with the project; neither holds
secrets.

**3. Example adapter for a fictional project**

```markdown
# marpiech-security — project adapter (acme-shop)

## Trust boundaries
- internet-facing: storefront (anonymous + customers), api (customers, partners with API keys)
- internal only: admin (staff via SSO), worker (queue consumer, trusts api messages)
- tenancy: every row has store_id; the session's store_id is the only one a user may touch

## Enforcement
- authn: libs/auth/dependencies.py `current_user`; authz: `require_role()` on routes
- webhooks: payments webhook verifies the HMAC header in payments/webhooks.py

## Accepted risks
- 2026-02-01 — staff admin has no rate limit on search (internal only, SSO) — decided in docs/adr/014

## Tools
- local: `semgrep --config .semgrep/` ; network advisory tools allowed: `pip-audit`, `npm audit`

## Learned in this project
- 2026-03-04 — export endpoints are twins of list endpoints; check both for store_id
```

---

## CLAUDE.md snippet

```markdown
## Security review (skill: marpiech-security)
- Before merging changes to auth, sessions, permissions, crypto, file handling, templates
  that render user data, CI workflows or dependency manifests: `/marpiech-security` on the diff.
- Periodically: `/marpiech-security` sweep (defaults, CI/agent workflows, supply chain).
- Only verified findings (source → sink, preconditions, impact) are reported; never test
  against shared or production systems; never print a secret.
```

---

## Self-update log

Generic learnings, newest first. Project-specific learnings go to the project's adapter.

- 2026-11-05 — initial generic version. Shape taken from widely used security-review
  skill collections (differential review, insecure defaults, sharp edges, supply-chain and
  CI/agent-workflow audits, false-positive verification, variant analysis) and rewritten
  as one procedure with a single verification gate. First run on a large monorepo: test
  files dominated the candidate count (tests define `eval` methods and build SQL in
  fixtures) — tests are now excluded by default; `text(` matched `read_text(` — SQL
  sinks now need a word boundary and an SQL keyword; `yaml.load(open(...), Loader=SafeLoader)`
  was a false positive because the look-ahead stopped at the inner `)`.
