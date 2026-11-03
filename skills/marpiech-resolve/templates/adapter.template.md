# marpiech-resolve — project adapter

<!-- Location: <project>/.claude/adapters/marpiech-resolve.md (commit it with the project).
     Commands and names only — never credentials, tokens, private hostnames or personal
     data. Test users are referred to by ROLE; their credentials live in the secrets tool. -->

## Routes (see references/delivery-routes.md; first one is the default)
- <name> (keywords: …): branch …; sync …; local stack …; gate …; push …; watch …; after …

## Commands
- tests: unit `<cmd>` (copy <file>); api `<cmd>`; ui `<cmd>` (copy <file>)
- lint-command: <exact CI lint command>
- run-command: <rebuild + read logs>

## UI
- ui-verification: <how to screenshot as which role, locally and on the review env>
- ui-rules: <component library + style rules>
- consult-skills: <project skills to read for certain work>

## Packages
- <dir> → <package name> (<how it is published>)

## Diagnosis (read-only)
- <env>: <how to list workloads, read logs, check running version>

## Review
- review-tool: <command>                          [fresh subagent]

## Learned in this project (newest first)
- YYYY-MM-DD — <project-specific learning>
