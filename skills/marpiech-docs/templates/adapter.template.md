# marpiech-docs — project adapter

<!-- Location: <project>/.claude/adapters/marpiech-docs.md (commit it with the project).
     Paths, public URLs and names of roles/labels only — no credentials, no private hosts. -->

## Documentation map
| layer | audience | where | platform | owner |
|-------|----------|-------|----------|-------|
| agent | Claude | CLAUDE.md, <deep-docs dir>/ | markdown | <team> |
| user  | <who> | <dir or owner/repo> → <public URL> | <mkdocs / hosted editor / …> | <who> |
| API   | <who> | <generated where> | generated | — |

## Settings
- impact-map: .claude/doc-impact-map.json        (docs_repo: <owner/repo or ../path, if separate>)
- agent-budget: 20000                            [characters per file]
- nav: <SUMMARY.md | mkdocs.yml>; exclude: <unpublished dirs>
- build: <mkdocs build --strict | npm run build | none>
- spelling: <American | British>
- audience: <reader and roles>; never document: <internal-only roles/features>
- sources of truth: <CLI reference dir>, <routes/templates dirs>, <enum/role definitions>
- page template: <path to an exemplary page>

## Terminology (canonical ← never write)
- <Label> ← <rejected form>, <rejected form>

## Decision matrix additions
- <change> → <docs to update>

## Co-editing
- <none | who edits where; add-only rules; how to notify page owners>

## Learned in this project (newest first)
- YYYY-MM-DD — <project-specific learning>
