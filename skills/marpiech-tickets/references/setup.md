# Token setup (one time per person)

The assistant never sees or types the token. The user creates it and stores it in the
team's secrets tool (or their own shell environment) themselves.

## Jira Cloud

1. Create an API token in the Atlassian account security settings ("API tokens" →
   "Create API token"); label it e.g. `marpiech-tickets`. Copy it once.
2. Store three values under these **names** in the project's secrets tool (or export
   them in your shell profile for a personal setup):
   - `JIRA_URL`   — `https://<site>.atlassian.net`
   - `JIRA_EMAIL` — the account that created the token
   - `JIRA_TOKEN` — the token
   Optional: `JIRA_PROJECT` — default project key (lets you type `123` for `ACME-123`).
   Type the secret yourself, e.g. in Claude Code with the `!` prefix:
   `! <secrets-tool> secrets set JIRA_TOKEN=<paste>` — so the value never enters the
   conversation.
3. Record in the project adapter only the injection command (`secrets-run`), never values.
4. Verify: `<secrets-run> python3 <skill-dir>/scripts/tickets.py whoami` → `OK: <name>`.

Least privilege: use an account that can see only the projects it needs. A leaked token
is revoked on the same API-tokens page.

## GitHub issues

`gh auth login` once; the script uses gh's own credentials. Set `TICKETS_BACKEND=github`
(or pass `--backend github`) and optionally `GH_REPO=owner/name`.
