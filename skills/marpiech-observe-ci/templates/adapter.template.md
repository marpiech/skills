# marpiech-observe-ci — project adapter

<!-- Location: <project>/.claude/adapters/marpiech-observe-ci.md (commit it with the project).
     Public URLs and command names only — no tokens, no private hostnames or IPs. -->

## Pipeline
| push to | workflow | gates | deploys to |
|---------|----------|-------|------------|
| <branch> | <file.yml> | <jobs that block> | <environment> |

## Fail-safe steps (green does not prove they ran)
- <step> — assert with `<command>` expecting <result>

## Health
- <environment>: <public health URL> (version at <URL>)

## Runner notes
- <hosted | self-hosted>; diagnostic logs: <where>; ports it binds: <ports>

## Status page
- <provider status URL>

## Learned in this project (newest first)
- YYYY-MM-DD — <project-specific learning>
