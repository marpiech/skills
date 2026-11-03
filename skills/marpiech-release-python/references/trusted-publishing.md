# Trusted Publishing (OIDC) — setup and traps

Trusted Publishing lets a CI workflow publish to PyPI without any stored token: the
index trusts a specific repository + workflow file + environment, and the workflow
exchanges a short-lived OIDC token at publish time. A leaked long-lived token is the
failure it removes.

## One-time setup (the user does the account part)

1. On PyPI → the project → Publishing → add a trusted publisher:
   owner, repository, workflow file name (`release.yml`), environment (`pypi`).
   For a project that does not exist yet, use a "pending publisher".
2. In the repository settings → Environments → create `pypi`. Optional: required
   reviewers (adds a manual approval before every publish) and a tag rule (`v*`).
3. Add `.github/workflows/release.yml` from `templates/release.yml.template`.
4. Dry run: Actions → release → Run workflow (dry run = true). Every gate runs; nothing
   publishes.
5. First real release: push a `v<version>` tag on the bumped commit.

## Traps

- **A job-level `permissions:` block replaces the workflow's defaults** — it does not
  add to them. A publish job listing only `id-token: write` loses `contents: read`, and
  `actions/checkout` fails with "Repository not found", which reads like a wrong tag or a
  missing repo. List both.
- **The tag must match the version.** Check it in the workflow before building; a
  mismatch publishes a version nobody asked for.
- **Shallow checkouts change git-derived data.** Anything computed from history
  (setuptools_scm versions, dates in generated manifests) needs `fetch-depth: 0`.
- **Installed entry points look in site-packages.** A check run through the installed CLI
  (`mytool verify`) inspects the installed copy, not the repository; pass the repository
  path explicitly when the check is about the committed files.
- **Re-running a release run**: the publish action's `skip-existing: true` lets a re-run
  succeed after the files exist (it never overwrites — the index forbids that anyway).
  Without it, a re-run after a partial failure always ends red and tells you nothing.
- **No required reviewers = pushing the tag publishes.** Decide deliberately; the
  confirmation step in the skill (A.8) is then the only human gate.
- **Build in the publish job from the same commit** the gates tested, or upload the
  gate job's artifacts — never build from a different ref.
- **Do not publish from pull requests or forks.** Trigger only on tags (and manual
  dispatch defaulting to dry run).

## Fallback: token upload

- Create a **project-scoped** token on the index, store it in the secrets backend (never
  in `~/.pypirc` in plain text, never in the repository), and inject per command:
  `TWINE_USERNAME=__token__` + `TWINE_PASSWORD` from the backend → `python -m twine upload dist/*`.
- Rotate the token after anyone who had it leaves; prefer moving to Trusted Publishing.
