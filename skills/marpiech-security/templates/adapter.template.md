# marpiech-security — project adapter

<!-- Location: <project>/.claude/adapters/marpiech-security.md (commit it with the project).
     Trust boundaries, enforcement points and decisions only — never secrets, never
     details of an unfixed vulnerability (keep those private until fixed). -->

## Trust boundaries
- internet-facing: <services / routes>
- internal only: <services> (trusts: <what>)
- users and roles: <list>
- tenancy: <how data is partitioned; the id that scopes queries>

## Enforcement
- authentication: <where>
- authorisation: <where>
- webhooks / service-to-service: <how verified>

## Accepted risks (decision reference)
- YYYY-MM-DD — <risk> — <why accepted, where decided>

## Tools
- local: <semgrep / bandit / … commands>
- network advisory tools allowed: <none | pip-audit, npm audit, osv-scanner>

## Learned in this project (newest first)
- YYYY-MM-DD — <lesson>
