---
name: marpiech-secrets
description: Work with a project's secrets without ever printing them — through one stdlib helper over the project's secrets backend (Infisical, plain .env files, SOPS, Doppler, 1Password references; Vault and cloud secret managers by documented commands). Injects secrets into commands instead of extracting them, answers "is X set?" with presence, length and a fingerprint, compares environments by key name and fingerprint, writes values read from stdin (never from argv) behind a dry run and a second confirmation for protected environments, scans for leaks (committed or un-ignored env files, secret-looking strings in files and history) and walks a rotate-first response, and bootstraps a safe setup (.env.example, gitignore, injection pattern). Use when the user says "/marpiech-secrets", "get/set/rotate the secret", "is X configured in staging?", "what's different between staging and prod config?", "run this with the secrets", "add a new env var", "did we leak a key?", "scan for secrets", "set up secrets for this project", or when another workflow needs credentials (ticket tracker, CI, package publishing, a local stack).
---

# marpiech-secrets — secrets without exposure

## Purpose

Secrets leak through ordinary convenience: a value printed to the terminal ends up in a
transcript, an exported `.env` file gets committed, a value on a command line shows up in
the process list and shell history, a staging key is reused in production. An agent makes
this worse, because everything it sees is in its context and its logs. This skill makes
the safe path the easy one: secrets are **injected** into the commands that need them,
**inspected** only by name, length and fingerprint, **written** from stdin behind a
confirmation, and **scanned for** before they leave the machine. Outcome: the task gets
done, and no secret value appears in the conversation, a file, a commit or a log.

`<SKILL_DIR>` = the directory holding this SKILL.md; `<SEC>` =
`python3 <SKILL_DIR>/scripts/secrets.py` (stdlib; calls the backend's own CLI).

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

1. Look for `.claude/adapters/marpiech-secrets.md` in the repository root.
2. IF present → read: backend, environments (and which are **protected**), folder paths
   and what each holds, which secrets live elsewhere (cloud secret manager, CI secrets,
   cluster secrets), login procedure, consumers of each critical secret (for rotation),
   and project learnings. Export the adapter's non-secret settings for the helper
   (`SECRETS_BACKEND`, `SECRETS_PROTECTED_ENVS`, file paths) when they differ from the
   defaults.
3. ELSE → `<SEC> which` detects the backend from the repo (`.infisical.json`,
   `.sops.yaml`, `doppler.yaml`, `.env.op`, `.env*`). Offer at the end to save what you
   learned as the adapter (`templates/adapter.template.md`).
4. IF the backend's CLI is not logged in → tell the user the login command (adapter, or
   `references/backends.md`) and suggest they run it themselves with the `!` prefix.
   Never ask the user to paste a password or token into the conversation.

---

## Algorithm — pick the task

```
"run X with the secrets", tests/stack need credentials   → A. INJECT
"is X set?", "what keys exist?", "staging vs prod?"      → B. INSPECT
"add / change / rotate a secret"                          → C. WRITE
"did we leak?", before a push or publish                  → D. SCAN (and E if found)
"set up secrets for this project"                         → F. BOOTSTRAP
```

### A. Inject — the default for anything that needs a secret

1. `<SEC> run --env <env> [--path <folder>] -- <command>` — the backend puts the secrets
   into the child process's environment; nothing is written to disk or printed.
2. Choose the **least** environment that works: dev or local for tests, never production
   unless the task is explicitly about production.
3. IF the command echoes its environment or config (debug flags, `env`, `printenv`,
   verbose HTTP logs) → do not run it that way; turn the verbosity off first.
4. IF a tool insists on a file → prefer the tool's own "read from env" option; ELSE
   write the file to a private temp directory (`umask 077`, in RAM when available),
   use it, delete it in the same command, and never inside the repository.
5. Other skills (tickets, CI, publishing) get their credentials this way:
   `<SEC> run --env dev -- python3 <other skill script> …`.

### B. Inspect — names, lengths, fingerprints; never values

1. `<SEC> keys --env <env> [--path <folder>] [--recursive]` — key names.
2. `<SEC> has KEY… --env <env>` — present / EMPTY / MISSING, length, 8-char fingerprint.
   Two environments holding the same fingerprint hold the same value.
3. `<SEC> diff <envA> <envB> [--recursive]` — keys only in one environment (the usual
   cause of "works in staging, fails in prod"), and keys whose values differ.
   - **Identical** values between a protected environment and a non-protected one are a
     finding worth raising (shared credentials widen the impact of a leak) — report the
     count and names, and let the user decide.
4. IF the user explicitly asks to see a value → explain the exposure (the value will be in
   the transcript), and only after a clear yes show it once; prefer telling them the
   backend command to run themselves with `!`, so it never reaches the model.

### C. Write — dry run, stdin, confirmation

1. Clarify: key name, environment(s), folder, and whether this is **create**, **update**
   or **rotate** (C.4).
2. Dry run: `<SEC> set KEY --env <env> [--path <folder>]` → shows create/update and the
   current fingerprint. Show it to the user.
3. On approval:
   - the user supplies the value by running
     `python3 <SKILL_DIR>/scripts/secrets.py set KEY --env <env> --yes` in **their own
     terminal** (a hidden prompt, asked twice — the `!` prefix may not offer an
     interactive prompt), OR the value is generated without passing through the
     conversation, e.g. `openssl rand -base64 32 | <SEC> set KEY --env <env> --yes`;
   - protected environments also need `--confirm-env <env>`, given only after the user
     approved that specific environment in this conversation;
   - backends without helper support (SOPS, Doppler, 1Password, Vault): use the
     backend's own editor or prompt (`sops edit`, `doppler secrets set` interactive,
     `op item edit`) — see `references/backends.md`.
4. **Rotation** = create the new value → update every consumer (adapter "consumers"; CI
   secrets, deployed services, other environments) → verify the consumers work → revoke
   the old credential at its issuer. A rotation is not done until the old credential is
   revoked.
5. Verify with `<SEC> has KEY --env <env>`: the new fingerprint is shown and differs from
   the old one.
6. IF the key is new → add it to `.env.example` (name only, empty or placeholder value)
   and to the configuration docs (IF /marpiech-docs is installed → its IMPACT mode).

### D. Scan — before pushing, publishing or sharing

1. `<SEC> scan [paths] [--history N]` — reports:
   - `TRACKED-ENV`: an env file is committed → E;
   - `UNIGNORED-ENV`: an env file is not gitignored → add the pattern to `.gitignore`
     now (keep `!.env.example`);
   - `SECRET?` / `HISTORY?`: secret-looking strings in tracked files or recent commits
     (values redacted). With gitleaks installed the helper uses it instead.
2. Judge each hit: test fixtures and documented fake values are fine only if they cannot
   work anywhere; everything else → E.
3. Also check where secrets travel besides git: built container images (`docker history`,
   files copied into the image), CI logs (masking can miss transformed values), package
   archives (`tar -tzf` / `unzip -l` the build output before publishing).

### E. Leak response — rotate first, clean up second

1. Treat the secret as compromised the moment it was pushed, published, pasted or
   logged. Removing it from history does **not** undo exposure; forks, caches and
   clones keep it.
2. Rotate it (C.4) — revoke the old credential at the issuer.
3. Then remove it from the current tree, add ignore rules, and move it into the backend.
4. Rewriting history (`git filter-repo`) on a shared branch needs the user's explicit
   decision and coordination with everyone who has a clone; never force-push on your own.
5. Record the incident and the fix in project memory (IF /marpiech-memory is installed),
   without the value.

### F. Bootstrap a project with no secrets setup

1. Inventory configuration the code reads (`os.environ`, `process.env`, `getenv`,
   settings classes) → the list of key names.
2. Propose a backend (`references/backends.md`: a team with a hosted manager → that
   manager; a solo project → `.env` files kept out of git; secrets that must live in the
   repo → SOPS).
3. Create `.env.example` from `templates/env.example.template` (names, no values) and
   gitignore rules `.env`, `.env.*`, `!.env.example`.
4. Document the injection command in the project's CLAUDE.md (snippet below) and the
   adapter.

---

## Rules & guardrails

- Never print, echo, log or quote a secret value; never put one in a command argument,
  a commit, a ticket, a PR, a doc, a screenshot or the conversation.
- Never export secrets to a file in the repository; never write a secret into a file
  that is not gitignored (the helper refuses).
- Never read `.env` files with `cat`/`Read` to "check" them — use `has` / `keys`.
- Never write to a protected environment, a backup or replica, or a CI secret store
  without an explicit approval for that environment in this conversation.
- Never disable masking, TLS verification or audit logging to make something work.
- Never ask the user to paste a credential into the chat; give them a command to run.
- A leaked secret is rotated, not just deleted.

---

## Adapting this skill to your project

Adapter: `<project>/.claude/adapters/marpiech-secrets.md` (template:
`templates/adapter.template.md`; backend notes: `references/backends.md`).

| setting | default | how to discover |
|---------|---------|-----------------|
| backend | auto-detected | `.infisical.json`, `.sops.yaml`, `doppler.yaml`, `.env.op`, `.env*` |
| environments | backend's list | `infisical` UI/CLI, Doppler configs, `.env.<env>` files |
| protected environments | `prod,production` | which environments serve real users or data |
| folders / paths | `/` | `infisical secrets folders --env <env>` |
| secrets stored elsewhere | none | cluster manifests referencing secret stores, CI secret names |
| login | backend default | self-hosted domain via `INFISICAL_API_URL` in the user's shell profile |
| consumers per critical secret | none | grep the key name across code, CI and deploy config |

Example for a fictional project:

```markdown
# marpiech-secrets — project adapter (acme-shop)

## Backend
- infisical (self-hosted): the user's shell exports INFISICAL_API_URL; login with
  `infisical login` (browser)
- environments: dev, staging, prod; protected: prod
- folders: / (application), /Infrastructure (database, identity provider), /Payments

## Stored elsewhere
- cluster runtime secrets: the cloud secret manager, synced into the cluster; change
  them there, not in Infisical
- CI: repository secrets PYPI_TOKEN, REGISTRY_TOKEN (GitHub settings)

## Consumers (for rotation)
- PAYMENTS_API_KEY → checkout service (staging, prod), nightly reconciliation job
- DB_PASSWORD → api, worker, migrations job, backup job

## Learned in this project
- 2026-03-01 — most keys live in folders; use `keys --recursive` for a full picture
```

---

## CLAUDE.md snippet

```markdown
## Secrets (skill: marpiech-secrets)
- Never print secret values or read `.env` files directly. Run commands that need
  credentials with `/marpiech-secrets` inject (`secrets.py run --env dev -- <cmd>`).
- "Is X set?" / "staging vs prod?" → `/marpiech-secrets` inspect (names + fingerprints).
- New or changed secret → `/marpiech-secrets` write (dry run; value via stdin; prod needs
  explicit approval). Before any push or publish: `/marpiech-secrets` scan.
```

---

## Self-update log

Generic learnings, newest first. Project-specific learnings go to the project's adapter.

- 2026-11-03 — initial generic version, distilled from a production team's secrets-CLI
  skill, minus its unsafe conveniences (plain value dumps, exporting to `.env`). Infisical
  `secrets set` takes values on argv; the helper passes `KEY=@file` from a 0700 temp dir
  (in RAM when available) instead, and never relays the CLI's stdout, which can echo the
  value. Infisical projects often keep most keys in folders — the root path can look
  nearly empty; use `--recursive`.
