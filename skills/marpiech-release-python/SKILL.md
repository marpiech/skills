---
name: marpiech-release-python
description: Release a Python package to PyPI (or another index) safely, remembering that a published version can never be replaced — only yanked. Checks readiness (versions agree in every file, bumped past the latest tag and the release branch, tag and index version still free, changelog section ready and released sections untouched, sources parse on the oldest supported Python, CI green), runs the project's own release gates, builds wheel and sdist, AUDITS THE BUILT ARTIFACTS (unwanted files, secrets, customer or host names minus a recorded allow-list, sdist-only files, what is new since the last release), runs a clean-install gate on the oldest Python, then publishes — preferably by pushing a tag to a Trusted Publishing (OIDC) workflow with no stored token, else an upload with an injected token — only after an explicit yes, and verifies the published files' hashes against the local build. Also sets up the tag-triggered release workflow and a version-guard pre-push hook. Use when the user says "/marpiech-release-python", "release", "publish to PyPI", "cut a release", "bump the version", "tag v1.2.3", "is this ready to release?", "set up trusted publishing", "yank a release", or after work lands on the release branch of a Python package.
---

# marpiech-release-python — releases you cannot take back, done carefully

## Purpose

A PyPI version is immutable: once `name 1.4.0` is uploaded it can never be replaced, and
anything doing an unpinned install picks it up within minutes. Most release accidents
are therefore unrecoverable in place — a version that reports the wrong number because
two files disagree, a wheel that silently dropped its data files, an sdist that ships the
changelog with a customer's name in it, a release that only installs on the
maintainer's Python. This skill turns a release into a sequence of checks against the
**built artifacts**, not the source tree, ending in one deliberate, confirmed publish
and a verification that what landed is what was audited.

`<SKILL_DIR>` = the directory holding this SKILL.md; `<REL>` =
`python3 <SKILL_DIR>/scripts/release.py` (stdlib + git; only `check` and `published`
contact the index, read-only; it never uploads).

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

1. Look for `.claude/adapters/marpiech-release-python.md` in the repository root.
2. IF present → read: distribution name, index, branch flow (dev → integration →
   release branch → tag), how the release is triggered (tag + workflow, or manual
   upload), version files (and which are generated), changelog files, oldest supported
   Python, project release gates (manifests, checksums, data-file checks), the deny
   pattern and its **allow-list of accepted occurrences**, the clean-install command,
   downstream consumers, and project learnings.
3. ELSE → discover: `<REL> version`; `pyproject.toml` / `setup.py` / `setup.cfg` for the
   name, `requires-python` and build backend; `git tag --list 'v*'`; `.github/workflows/`
   for an existing release workflow; `CHANGELOG*`. Offer at the end to save the adapter
   (`templates/adapter.template.md`).
4. IF /marpiech-memory is installed → READ for "release": past release accidents are
   the most valuable memory a package has.

---

## Algorithm — pick the task

```
"release / publish / cut a release / is it ready?"       → A. RELEASE (steps 1–10)
"bump the version"                                        → A.2 only
"set up trusted publishing / a release workflow / guard"  → B. SETUP
"we published something wrong"                            → C. MISTAKE
```

### A. Release

**A.1 Readiness.**
1. On the release branch named by the adapter, clean tree, up to date with the remote,
   the commit pushed. IF the project integrates on another branch first → that
   branch's CI must be green on the same tree before promoting.
2. CI green on the exact commit (IF /marpiech-observe-ci is installed → its STATUS / LANDED).
3. `<REL> check --base <remote>/<release branch> --min-python <oldest> [--name <dist>]` —
   every BLOCK is resolved before going on; read every WARN.

**A.2 Version and notes.**
1. Choose the number with the user (semantic versioning: breaking → major, feature →
   minor, fix → patch; pre-releases `1.4.0rc1` for trial runs).
2. Edit **every** version declaration `<REL> version` lists; regenerate generated version
   files with the project's generator, never by hand-editing one of them.
   Dynamic versioning (setuptools_scm, hatch-vcs): the tag is the version — nothing to
   edit, but the tag must be on the right commit.
3. Changelog: rename `Unreleased` to the version (with the date), mirror into any second
   file the project keeps (README "Updates"). Released sections are immutable: notes for
   work after a tag go under `Unreleased`, never into a released section.
4. `<REL> version` agrees; commit the bump (explicit paths) and push it.

**A.3 Project gates.** Run the adapter's release gates (e.g. regenerated manifests,
checksums of packaged data, compatibility tests) and the full test suite — **on the
oldest supported Python** as well as the current one when the package claims an old
`requires-python`; the syntax check in `check` is not a substitute.

**A.4 Build.** In a clean state: remove `dist/` and `build/`, then `python -m build`
(both wheel and sdist), then `python -m twine check dist/*` (metadata renders).

**A.5 Audit the artifacts — the step that catches what source checks miss.**
`<REL> audit dist --deny '<project deny pattern>' --allow '<accepted-lines pattern>' --previous <dir with last release's wheel>`
- `UNWANTED`: tests, notebooks, env files, keys, caches inside the artifact → fix the
  packaging config (`references/packaging-traps.md`).
- `SECRET?`: stop; IF /marpiech-secrets is installed → its leak response.
- `DENIED`: customer, person, host or internal identifiers in files that ship. Remove
  them, or — if the user decides an occurrence is acceptable — record it in the adapter's
  allow-list with the reason. A deny check with known, unrecorded hits stops being read.
- **sdist-only files** (README, CHANGELOG, PKG-INFO, LICENSE …) are public too: the
  README is the index's project page, the changelog ships in every sdist.
- `NEW` / `REMOVED` versus the previous release: every new file is intended; every
  removed one is not data the package still needs.
- Metadata: Name, Version, `Requires-Python` set and correct.
- To get the previous release's files: `pip download <dist>==<prev> --no-deps -d <dir>`.

**A.6 Clean-install gate.** A fresh environment with the **oldest** supported Python and
nothing from the repo: install the built wheel (not the source tree), import the package,
run the CLI's `--help`, check packaged data is present and found from the installed
location, run a smoke command. Use a container (`python:<oldest>-slim`) or a fresh venv
in a temp dir. Watch for dependencies that only ship sdists (they need a compiler on a
clean machine). Template commands: `references/packaging-traps.md` → "Clean-install gate".

**A.7 Downstream.** Who installs this unpinned (pipelines, images, other packages)? A
breaking change reaches them the moment the release lands — check with the user whether
consumers need a pin or an update first.

**A.8 Confirm — the point of no return.** Show the user: version, commit, gates and
their results, audit summary, changelog entry, the publish command. Publish only on an
explicit yes in this conversation.

**A.9 Publish.**
- **Trusted Publishing (preferred)**: `git tag -a v<version> -m "<dist> <version>"` on
  the bumped commit, then `git push origin v<version>` — the tag workflow re-runs the gates
  and publishes via OIDC; no token exists to leak. Watch the run (IF
  /marpiech-observe-ci is installed → WATCH).
- **Manual upload (fallback)**: token injected, never typed or stored in a file —
  IF /marpiech-secrets is installed → `secrets.py run --env <env> -- python -m twine upload dist/*`
  with `TWINE_USERNAME=__token__` and `TWINE_PASSWORD` held by the secrets backend; then
  tag the same commit and push the tag.
- Never upload artifacts other than the ones you audited (do not rebuild in between).

**A.10 Verify.**
1. `<REL> published --name <dist> --version <version> --dist dist` — PUBLISHED and every
   sha256 matches the local, audited build (for a CI-built release, compare against the
   workflow's artifacts or audit the downloaded files the same way as A.5).
2. Install from the index in a fresh environment (`pip install <dist>==<version>`), import,
   smoke command. The index may take a minute to serve a new version.
3. Create the hosting platform's release notes from the changelog section if the project
   does that (`gh release create v<version> --notes-file …` — an outward action: ask).
4. Record the release in project memory (IF /marpiech-memory is installed): version,
   time, anything surprising.

### B. Setup — tag-triggered Trusted Publishing and guards

1. Read `references/trusted-publishing.md`. On the index, the **user** registers a
   trusted publisher (repository, workflow file name, environment name) — an account
   action; give them the exact values, do not ask for credentials.
2. Copy `templates/release.yml.template` to `.github/workflows/release.yml`, fill the
   placeholders (dist name, oldest Python, gate commands), and keep its safeguards:
   tag == version check, `workflow_dispatch` dry run by default, gates before publish,
   job-level permissions that list `contents: read` **and** `id-token: write`.
3. Optional guard: copy `templates/pre-push.template.sh` to `hooks/pre-push`; each clone
   enables it with `git config core.hooksPath hooks`. It refuses a push to the release
   branch whose shipped files changed without a version bump. Mirror the rule in CI if
   the release branch has no protection.
4. Recommend branch protection / a required check on the release branch — a hook is a
   convenience (`--no-verify` skips it), the server-side check is the guarantee.
5. Dry-run the workflow (`workflow_dispatch` with dry run) before the first real tag.

### C. Mistake after publishing

1. Never try to overwrite — the index refuses, and deleting a version does not free its
   number.
2. Broken but harmless → publish a fixed patch release (A again).
3. Broken and harmful (wrong results, crashes on import, leaked data) → **yank** the
   version on the index (an account action the user performs; yanked versions are skipped
   by unpinned installs but still installable when pinned), publish a fix, and say in the
   changelog why the version was yanked.
4. Leaked a secret or personal data in an artifact → treat as a leak: rotate secrets
   first (IF /marpiech-secrets is installed → its leak response); ask the user about
   contacting the index's support for removal of personal data; yanking does not remove
   the files.

---

## Rules & guardrails

- Publishing (tag push or upload) only after an explicit yes for that version in this
  conversation. Never re-tag or move a pushed tag.
- Never store an index token in a file, a repository, or the conversation; prefer
  Trusted Publishing; else inject the token per command.
- Audit the artifacts you will publish — not a different build, not the source tree.
- Never edit a released changelog section or reuse a version number.
- Never force-push the release branch or tags.
- Never skip a failing gate to make a release date; tell the user what failed.

---

## Adapting this skill to your project

Adapter: `<project>/.claude/adapters/marpiech-release-python.md` (template:
`templates/adapter.template.md`; workflow: `templates/release.yml.template`; hook:
`templates/pre-push.template.sh`; traps: `references/packaging-traps.md`).

| setting | default | how to discover |
|---------|---------|-----------------|
| distribution name | from pyproject / setup | `[project] name` |
| index | https://pypi.org | `RELEASE_INDEX_URL`, `.pypirc` repository names (no secrets) |
| branch flow | trunk → tag | CLAUDE.md, branch list, CI triggers |
| trigger | tag `v*` + workflow, else manual upload | `.github/workflows/*` with `pypa/gh-action-pypi-publish` |
| version files | `<REL> version` | generated files carry a "generated" header |
| oldest Python | `requires-python` lower bound | classifiers, CI matrix |
| release gates | full test suite | CI release job, CLAUDE.md |
| deny pattern + allow-list | none | customer/host names from project memory; past scrubs |
| clean-install command | fresh `python:<oldest>-slim` | an existing install-test script or Dockerfile |
| downstream consumers | none | who pins or installs it |

Example for a fictional project:

```markdown
# marpiech-release-python — project adapter (acme-shop)

## Package
- dist: acme-shop-sdk; index: https://pypi.org; requires-python >=3.9 (oldest tested: 3.9)
- version files: pyproject.toml; src/acme_sdk/_version.py is GENERATED (`make version`)
- changelog: CHANGELOG.md (Unreleased → version); README "What's new" mirrors it

## Flow
- feature branches → main (CI) → tag v<version> on main → release.yml → PyPI (Trusted Publishing)
- hook: hooks/pre-push (git config core.hooksPath hooks)

## Gates
- `make test` on 3.9 and 3.12; `make check-schemas` (bundled JSON schemas match the API)
- clean install: `docker build -f Dockerfile.installtest .` (asserts the CLI and bundled schemas)

## Audit
- deny: `acme-internal|staging\.example\.com|customer-[a-z]+`
- allow (recorded 2026-02-10): lines containing "schema source: staging.example.com" — public test host

## Downstream
- acme-checkout service installs `acme-shop-sdk` unpinned in its image — warn before a major

## Learned in this project
- 2026-03-01 — hatch drops files outside `src/` from the sdist unless listed in `[tool.hatch.build]`
```

---

## CLAUDE.md snippet

```markdown
## Releasing (skill: marpiech-release-python)
- A published version is immutable. Release only with `/marpiech-release-python`: check →
  bump every version file + changelog → gates on the oldest Python → build → audit the
  built wheel AND sdist → clean install → explicit yes → tag (Trusted Publishing) → verify hashes.
- Never edit a released changelog section; new notes go under "Unreleased".
```

---

## Self-update log

Generic learnings, newest first. Project-specific learnings go to the project's adapter.

- 2026-11-03 — initial generic version, distilled from a small team's PyPI notes and a
  package whose release history recorded the expensive lessons: a name scrub checked
  one file while three shipped files still carried it (audit the artifacts, wheel AND
  sdist); a deny pattern with unrecorded accepted hits stopped being read (keep an
  allow-list beside it); a released changelog section was edited after its tag (compare
  each section to its own tag); a job-level `permissions:` block replaced the defaults
  and checkout failed with "repository not found"; an installed entry point resolved
  data in site-packages instead of the repo; a shallow checkout changed git-derived
  metadata; a dependency without wheels broke clean installs only.
