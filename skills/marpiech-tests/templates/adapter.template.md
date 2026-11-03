# marpiech-tests — project adapter

<!-- Location: <project>/.claude/adapters/marpiech-tests.md (commit it with the project).
     Commands, paths and marker names only — no credentials, no private hostnames. -->

## Types
| type | where | run (single file) |
|------|-------|-------------------|
| unit | <dir> | <command> |
| unit (real dependency) | <dir> | <command + what must be running> |
| API / CLI e2e | <dir> | <command, with credential injection> |
| UI e2e | <dir> | <command> |

## Fixtures / factories
- <path> — <what it builds>

## Markers
- <marker> — <meaning>; allowed environments: <list>
- default deselection: <addopts>; run deselected tests with: <flag>

## Gate
- before push: <command(s)>
- full suite: <command>

## End-to-end prerequisites
- <services to start, seed script, test users (names only)>

## Known flaky tests
- <test id> — <cause, owner, since>

## Learned in this project (newest first)
- YYYY-MM-DD — <project-specific learning>
