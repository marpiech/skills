# marpiech-release-python — project adapter

<!-- Location: <project>/.claude/adapters/marpiech-release-python.md (commit it with the project).
     Names, commands and patterns only — never a token. The deny pattern may name what must
     not ship; keep this file out of the published artifacts (it is not in the package). -->

## Package
- dist: <name>; index: <https://pypi.org>; requires-python: <spec> (oldest tested: <3.X>)
- version files: <files>; generated: <file> (regenerate with `<command>`)
- changelog: <file> (Unreleased → version); mirrored into: <file or none>

## Flow
- <dev branches> → <integration branch> (CI) → <release branch> → tag v<version>
- trigger: <tag + release.yml (Trusted Publishing) | manual upload with injected token>
- guard: <hooks/pre-push + CI check | none>

## Gates
- <command> — <what it catches>
- clean install: <command>

## Audit
- deny: `<regex of names/hosts/ids that must not ship>`
- allow (recorded YYYY-MM-DD, by <who>): `<regex of accepted lines>` — <reason>

## Downstream
- <consumer> installs <pinned | unpinned> — <what to check before a major>

## Learned in this project (newest first)
- YYYY-MM-DD — <project-specific learning>
