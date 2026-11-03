# marpiech-tickets — project adapter

<!-- Location: <project>/.claude/adapters/marpiech-tickets.md (commit it with the project).
     Variable NAMES and injection commands only — never token values. -->

## Settings
- backend: jira                                   [jira | github]
- jira-url: https://<site>.atlassian.net          [ask]
- project: <KEY>                                  [prefix from git log]
- secrets-run: <command prefix that injects JIRA_URL, JIRA_EMAIL, JIRA_TOKEN>   [empty]
- active-parent-query: <JQL / gh query>           [none]
- parent-rule: <how new tickets choose a parent>  [ask]
- states: start = "<name>", review = "<name>", done = "<name>"   [from transitions]
- comment-convention: INFO/TECH                   [INFO/TECH]
- assignee-on-close: <unchanged | me | accountId> [unchanged]
- time-logging: <policy>                          [none]
- evidence-for: <reporters/roles>                 [none]

## Learned in this project (newest first)
- YYYY-MM-DD — <project-specific learning>
