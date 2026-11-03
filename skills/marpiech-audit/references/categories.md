# Audit categories — what to look for

Read in Step 4 (things grep cannot see) and when building a project's catalogue. Each
category lists greppable shapes (candidates for `audit-checks.json`) and reading checks
(require opening the code). Default scores: I / NR / IR → priority.

## A. Security — 10 / 9 / 2 → 45

Greppable:
- credential literals and key material in tracked files — including infrastructure state
  (`*.tfstate`), manifests (`secret.yaml`), fixtures and scripts, not only source code;
- hardcoded hosts/ports in application logic (not in configuration defaults);
- SQL built by string interpolation; regex or LIKE fragments built from input without
  escaping (check sibling calls: one escaped, one not, is a classic);
- filesystem paths joined from a client-supplied id without rejecting `..`, absolute
  paths and NUL in one central builder;
- storage URLs (`s3://`, `gs://`) rendered to users.

Reading:
- **security switches parked in log mode**: an enforcement flag whose default is
  permissive and which no deployed environment overrides is inert everywhere — check
  each environment's config, not the prose describing it.

## I. Tenant isolation — 10 / 9 / 2 → 45

Greppable:
- tenant-scope parameters that are optional (`project_id: str | None = None`) on
  repository/service methods — a caller can omit them and read across tenants;
- tenant scope accepted from query/form/header parameters instead of the session.

Reading:
- list/search/get-all queries without a tenant filter (exempt: explicitly global admin
  methods, named as such);
- fetch-by-id followed by use without comparing the entity's tenant to the session's;
- **proxies forwarding an unbound id**: a handler passes a path id to another service
  without resolving it locally and checking ownership; authenticating the caller is not
  authorizing the resource, and the downstream service usually trusts the token too;
- **context mistaken for access**: middleware that copies a client header into the
  session's "current project", and a guard that only checks the value is non-empty.

## H. Authorization — 9 / 8 / 3 → 24

Greppable:
- routers declared without auth dependencies (then read each endpoint);
- mutation endpoints (POST/PUT/PATCH/DELETE) without a permission check in dependencies
  or body;
- legacy permission sources (raw identity-provider claims) where the project uses a
  resolved-permissions helper.

Reading:
- **fail-open checks**: `if a and b and a != b: deny` — when either is missing, access
  is granted;
- permissions enforced **only in templates** (button hidden) — grep the permission name in
  server code;
- **twin divergence**: the API endpoint checks a permission its HTML twin does not;
- docstrings claiming "admin only" over a weaker check — the docstring is not enforcement;
- non-idempotent GET handlers (writes or commits on read).

## C. Architecture / layering — 8 / 6 / 3 → 16

Encode the project's own layering rules, e.g.: repositories never commit; routes never
touch the database; routes never import repositories (the root cause of the previous
two); naming of injected collaborators; required columns on entity models (with the
exemptions for join tables, append-only logs and owned child rows written down).

## J. Single source of truth — 7 / 6 / 3 → 14

- the same cross-service client call with similar surrounding logic in 3+ places;
- permission/session extraction copied outside the auth helpers;
- business operations (create report, start job) reachable through 2+ code paths that
  each re-implement them.

## F. Code quality — 6 / 4 / 2 → 12

- linter on an expanded rule set: complexity (`C901` > 10), exception chaining
  (`raise` in `except` without `from`), simplifications; ignore rules that fire on the
  framework's idioms;
- broad exceptions swallowed silently;
- raw SQL where the project uses an ORM (except components that deliberately do not);
- stale TODO/FIXME markers.

## B. Duplication — 7 / 5 / 3 → 11.7

- identical blocks > 5 lines in several files; the same inline pattern 3+ times;
- duplicated helpers that should live in a shared module.

## E. Naming & structure — 4 / 2 / 1 → 8

- file and directory naming conventions (plural modules, entity directories);
- migration file name length or format limits.

## D. UI conventions — 5 / 3 / 2 → 7.5

- formatting done in templates instead of the shared filters (dates, numbers);
- deprecated components still imported;
- design-system violations (raw palette colors in component styles, external CSS
  frameworks) — with exemptions for contexts that cannot use the system (e-mail, PDF).

## G. Oversized files — 5 / 4 / 4 → 5

- > 500 lines large, > 800 must split, > 5000 probably generated or vendored (look first).

## Diff-scope attribution

- NEW = the line is not in the base version of the file; PRE-EXISTING otherwise.
- For metrics (complexity, size), measure base vs head: "C901 20 → 22" is attributable,
  "C901 22" is not.
- `git blame -L <line>,<line> <file>` settles doubtful cases.
