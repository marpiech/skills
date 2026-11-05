# Security review checklist

Read in Steps 5–6. Section 1 is the reading checklist per area; section 2 is the CI and
agent-workflow checklist; section 3 is the supply-chain checklist; section 4 is the
verification record every finding needs; section 5 is the triage of incoming reports.

## 1. Reading checklist by area

**Authentication and sessions**
- Every route that is not deliberately public requires authentication — check the router
  or dependency default, then the exceptions.
- Session cookies: `HttpOnly`, `Secure`, `SameSite`; session rotated on login and
  privilege change; logout invalidates server-side state.
- Tokens: signature, expiry, audience and issuer verified; algorithm pinned (never
  `none`, never "whatever the header says"); decoding without verification used only
  for display, never for a decision.
- Password reset / invite / magic-link tokens: cryptographically random, single-use,
  short-lived, compared in constant time, not logged.
- Credential endpoints (login, reset, OTP) have rate limits or lockouts.

**Authorisation**
- The check happens on the server for every path to the same data: HTML route and API
  twin, single and bulk, view and export, list and detail, synchronous and background
  job.
- "Has a project/org in context" is not the same as "may access that project": verify
  the membership lookup, not just the presence of an id.
- Checks fail closed: a missing field, a `None` role, an exception in the policy → deny.
- Enforcement switches ("log-only", "audit mode", feature flags) — check what each
  deployed environment actually sets, not what the docs say.

**Tenant isolation**
- Every list/search/count/export query is scoped by the caller's tenant; joins do not
  reintroduce other tenants' rows.
- Fetch-by-id checks ownership; proxies that forward a client-supplied id to another
  service either check it first or the downstream service checks it.
- Caches and background jobs keep the tenant in the key and in the job payload.

**Injection sinks**
- SQL: parameters bound by the driver/ORM; identifiers (table/column names) from an
  allow-list, never from input. `LIKE`/regex fragments from input are escaped.
- Shell: argument lists, never `shell=True` with input; no input in `bash -c` strings.
- Paths: one central builder rejects `..`, absolute paths, NUL and symlinks out of the
  root; archives are extracted with member-path checks (zip-slip).
- Templates/HTML: autoescape on; every `|safe`, `Markup`, `innerHTML`,
  `dangerouslySetInnerHTML`, `v-html` traced to its data; user content in attributes,
  URLs (`javascript:`), CSS and inline scripts handled by context.
- Redirects: targets from an allow-list or relative only (open redirects matter most in
  login/OAuth flows).
- Outbound requests (SSRF): URLs from users resolved and checked against internal
  ranges and metadata endpoints after DNS resolution; redirects re-checked.
- Deserialisation: no `pickle`/unsafe YAML/Java serialisation of untrusted data; model
  files from users loaded in safe modes only.
- Logs and headers: CR/LF stripped from values written to logs or headers.

**Files and uploads**
- Size limits, type checks by content not name, storage outside the web root, generated
  names, downloads with `Content-Disposition` and a safe content type.
- Signed/time-limited URLs for private objects; storage URLs or bucket paths never
  rendered to users who cannot already read them.

**Webhooks and service-to-service**
- Signatures verified (HMAC with constant-time compare, timestamp to stop replay) before
  any parsing beyond what the check needs.
- Internal services authenticate each other; "internal network" is not authentication.

**Secrets and configuration**
- No credential literals; no fallbacks such as `getenv("SECRET", "dev-secret")` that make
  production silently use a known value — fail at start instead.
- Debug modes, permissive CORS (`*` with credentials is never valid), verbose error pages
  off in deployed environments.
- TLS verification never disabled outside a clearly local-only path.

**Data protection**
- Personal, clinical and financial data: minimum fields returned, not in logs, not in
  URLs, not in analytics; exports audited.

## 2. CI and AI-agent workflows

- `pull_request_target` and `workflow_run` run with secrets and a write token: they must
  never check out and execute the PR's code (build, test, install scripts) — run
  untrusted code in `pull_request` (no secrets) and pass only artefacts across.
- Untrusted event text (`issue.title/body`, `comment.body`, PR title/body/head ref,
  commit messages, branch names) is never interpolated into `run:` with `${{ }}` — pass
  it through `env:` and quote it (`"$TITLE"`).
- Top-level `permissions:` set to the minimum (`contents: read`), raised per job only
  where needed; never `write-all`.
- Third-party actions pinned to a full commit SHA (a tag can be moved); first-party
  actions at least to a major version.
- Self-hosted runners never serve public-repository PRs or untrusted triggers; they keep
  state between jobs.
- Secrets are scoped to the jobs/environments that need them; deploy secrets behind
  environment protection rules.
- **AI agents in CI** (code-review or coding agents triggered by issues, comments or PRs):
  - anyone who can write the triggering text can steer the agent (prompt injection);
    restrict triggers to trusted authors (`author_association` in OWNER/MEMBER/
    COLLABORATOR) or require a maintainer label;
  - give the agent the narrowest token and tools: read-only by default, no shell on
    untrusted triggers, no access to deploy secrets;
  - never let agent output flow into a privileged step (merging, publishing, deploying)
    without a human approval;
  - treat files the agent reads (README, issue text, PR diff) as untrusted data.
- Caches: a cache written by an untrusted job must not be restored by a privileged one.

## 3. Supply chain

- Every ecosystem has a committed lock file; CI installs from it (`npm ci`,
  `pip install --require-hashes` / `uv sync --frozen`, `go mod verify`).
- Ranges in libraries are fine; in applications the lock file is what matters — but
  open ranges with no lock file mean every build can differ.
- Direct URL / git dependencies are pinned to a commit, from a trusted host.
- Extra package indexes: internal package names are reserved on the public index, or the
  installer uses the internal index only for those names (dependency confusion).
- Install-time hooks (`postinstall`, `setup.py` code, build scripts) of new dependencies
  are read before adding them.
- New dependency checklist: maintained, widely used, not a near-duplicate name of a
  popular package (typosquatting), license compatible, transitive tree size reasonable.
- Container images pinned by digest for release builds; base images from trusted
  publishers; no `curl | sh` in Dockerfiles without a checksum.
- Agent skills and plugins are dependencies too: read a skill's scripts and any network
  calls before installing or updating it.

## 4. Verification record (one per candidate)

```
id:            <helper rule or R-n for a reading observation>
attacker:      <who, from Step 3>
source:        <input, file:line>
path:          <hop file:line> → <hop file:line> → …
sink:          <dangerous operation, file:line>
guards:        <each guard on the path and whether it applies here>
preconditions: <auth, role, flag, timing>
impact:        <asset and what the attacker gains>
demonstrated:  <local test / local request / not demonstrated (why)>
verdict:       CONFIRMED | PLAUSIBLE (unconfirmed hop: …) | FALSE POSITIVE (guard: file:line)
severity:      Critical | High | Medium | Low (+/- reason)
fix at:        <the one place>
```

## 5. Triage of an incoming report (TRIAGE mode)

1. Restate the claim as a verification record with the reporter's source, path and sink.
2. Reproduce locally only, on the reported version; confirm the version is deployed.
3. Decide: **accept** (record verified, severity set), **need more information** (name
   exactly what is missing), or **dismiss** (name the guard or the precondition that
   cannot be met, with file:line).
4. For an advisory about a dependency: is the vulnerable function reachable from our
   code, with attacker-controlled input? Version in the lock file? Fixed version
   available? Reachability decides urgency, not the advisory's score alone.
5. Keep reports and unfixed findings private (no public issue) until fixed.
