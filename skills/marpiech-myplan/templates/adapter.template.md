# marpiech-myplan — project adapter

<!-- Location: <project>/.claude/adapters/marpiech-myplan.md (commit it with the project).
     Delete lines you do not need. Commands only — never credentials, tokens or private
     hostnames; secrets are injected by the project's secrets tool. -->

## Settings
- plan-dir: claude-todos/                         [marpiech-init todos dir]
- ticket-system: <tracker, project key>           [ask]
- ticket-parent-rule: <how to pick the epic/milestone>   [ask]
- ticket-labels: myplan                           [none]
- assignee: <current user | team>                 [current user]
- branch-policy: <trunk-only | branch-per-ticket + pattern>   [from CLAUDE.md]
- tests:
  - ui-e2e: <location> (copy <pattern file>) — `<command>`
  - api: <location> — `<command>`
  - unit: <location> — `<command>`
- run-command: <rebuild/restart + where to read logs>
- full-suite-command: <command>
- review-tool: <command>                          [fresh subagent]
- delivery: <PR to X | push to deploy branch Y>   [ask]
- time-logging: <policy>                          [none]

## Project rules to check in 11c / 11e
- <rule> — <how to check>

## Learned in this project (newest first)
- YYYY-MM-DD — <project-specific learning>
