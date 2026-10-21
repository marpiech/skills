# marpiech-init — project adapter

<!-- Location: <project>/.claude/adapters/marpiech-init.md  (commit it with the project)
     Written by INIT mode; read by SYNC and AUDIT. Delete lines you do not need.
     Never put credentials, private hostnames or personal data here. -->

## Settings
- claude-md: CLAUDE.md                            [CLAUDE.md]
- claude-md-limit: 20000                          [20000 characters]
- deep-docs-dir: claude-docs                      [claude-docs, or the existing docs dir]
- todos-dir: claude-todos                         [claude-todos]
- ticket-system: Jira, prefix ACME                [none]
- trunk-branch: main                              [default remote branch]
- branch-policy: branch-per-ticket                [trunk-only | branch-per-ticket]
- secrets-source: environment via `<tool> run --` [environment variables]

## Verified commands (names only — no values)
- install: make install
- run-local: make dev
- unit-tests: make test
- lint: make lint
- e2e: make e2e

## Sections intentionally omitted from CLAUDE.md (and why)
- <e.g. "Architecture — single-module CLI, README covers it">

## Learned in this project (appended by the skill — newest first)
- YYYY-MM-DD — <project-specific learning>
