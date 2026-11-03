# Secrets backends — commands and caveats

Read when a backend is not supported by the helper, when logging in, or when choosing a
backend for a new project. In every command below, values come from a prompt, stdin or a
file in a private temp directory — never from a command argument.

## Choosing a backend (bootstrap)

| situation | backend |
|-----------|---------|
| team, several environments, deployed services | a hosted or self-hosted manager (Infisical, Doppler, Vault, a cloud secret manager) |
| solo or small project, local only | `.env` files kept out of git, plus `.env.example` |
| secrets must be versioned with the code (GitOps) | SOPS-encrypted files (age or a cloud KMS key) |
| team already uses a password manager | 1Password references (`op://vault/item/field`) |

## Infisical (helper: full)

- Login: `infisical login` (browser or interactive). Self-hosted: export
  `INFISICAL_API_URL=https://<your instance>/api` in your shell profile — not in the repo.
- Machine identities (CI): `INFISICAL_TOKEN` from the CI secret store; never commit it.
- Inject: `infisical run --env <env> [--path /Folder] -- <cmd>`.
- Names: `infisical secrets --env <env> --path <p> -o json` returns `secretKey` and
  `secretValue` — the helper parses it and prints only names.
- Write: `infisical secrets set KEY=@<file>` reads the value from a file; `KEY=value` puts
  it on argv (process list, shell history) — avoid. The command's output can echo the
  value; do not show it.
- Folders hold most keys in many projects: list them with
  `infisical secrets folders --env <env>`; use `--recursive` for a full listing.
- Avoid: `--plain` and `-o dotenv > .env` (prints or persists every value).

## Plain .env files (helper: full)

- Gitignore `.env` and `.env.*`, keep `!.env.example`; mode 600 on files holding values.
- The helper selects `.env.<env>` (falls back to `.env`); `SECRETS_DOTENV_FILE` overrides.
- Injection loads the file into the child process only; prefer it over `source .env`,
  which leaves values in the interactive shell.

## SOPS (helper: read, inject; write via `sops edit`)

- Encrypted files are committed; the key (age key file, cloud KMS) is not.
- Edit: `sops edit secrets.<env>.yaml` (opens a decrypted temp copy in the editor and
  re-encrypts on save).
- Inject: `sops exec-env secrets.<env>.yaml '<cmd>'` (the helper loads and injects the
  same way).
- Never `sops -d file > plain.yaml` into the repository.

## Doppler (helper: read, inject; write interactively)

- Login: `doppler login`; project and config via `doppler setup` (writes `doppler.yaml`,
  which holds no secrets).
- Inject: `doppler run --config <env> -- <cmd>`.
- Write: `doppler secrets set KEY` with no value prompts for it.

## 1Password (helper: read, inject via `.env.op`)

- `.env.op` holds references only (`DB_PASSWORD=op://Dev/acme-db/password`) and can be
  committed.
- Inject: `op run --env-file .env.op -- <cmd>`.
- Write: edit the item in the app or `op item edit` with a prompted value.

## HashiCorp Vault (documented commands only)

- Login: `vault login -method=<oidc|userpass|…>`; `VAULT_ADDR` in the shell profile.
- Names: `vault kv list <mount>/<path>`; metadata: `vault kv metadata get …`.
- Inject: an agent template or `envconsul`; avoid `vault kv get -field=…` in scripts that
  log their output.
- Write: `vault kv put <mount>/<path> KEY=-` reads the value from stdin.

## Cloud secret managers (documented commands only)

- Values are read by workloads through their own identity; agents rarely need values.
- Names: `gcloud secrets list`, `aws secretsmanager list-secrets --query 'SecretList[].Name'`,
  `az keyvault secret list --vault-name <v> --query '[].name'`.
- Write a new version from stdin / file:
  `gcloud secrets versions add <name> --data-file=-`,
  `aws secretsmanager put-secret-value --secret-id <id> --secret-string file://<tmpfile>`.
- Disaster-recovery replicas in a separate account/project limit the blast radius —
  never write to a replica by hand; let the sync job do it.

## CI secret stores

- GitHub: `gh secret list` (names only); `gh secret set NAME` prompts for the value
  (or `< file`). Values are write-only — they cannot be read back.
- Masking only hides exact values: base64-encoded or split values are printed in clear.
