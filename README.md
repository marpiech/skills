# marpiech skills

Generic, project-agnostic [Claude Code](https://claude.com/claude-code) skills. Each skill
is an explicit, step-by-step workflow that works in any repository and is bound to a
specific project through a small adapter file — no project knowledge lives in the skill.

## Skills

| skill | what it does | typical use |
|-------|--------------|-------------|
| [marpiech-memory](skills/marpiech-memory/SKILL.md) | grep-based `MEMORY.md` files next to the code: decisions, gotchas, rejected alternatives | read at session start, update at session end |

## Install

```sh
git clone https://github.com/marpiech/skills.git ~/src/marpiech-skills

# all projects
mkdir -p ~/.claude/skills
ln -s ~/src/marpiech-skills/skills/marpiech-memory ~/.claude/skills/marpiech-memory

# or a single project
mkdir -p .claude/skills
ln -s ~/src/marpiech-skills/skills/marpiech-memory .claude/skills/marpiech-memory
```

Use symlinks, not copies: each skill starts with a self-update check against this clone
and asks before pulling anything.

## Adapting to a project

Every skill reads an optional adapter at `<project>/.claude/adapters/<skill-name>.md`
with project-specific values (commands, branch model, ticket prefix, …). Each SKILL.md
has an "Adapting this skill to your project" section with a template and an example,
and a "CLAUDE.md snippet" telling Claude when to use the skill in that project.

## Conventions

- Skills contain no credentials, hostnames, or organisation-specific details.
- Scripts are POSIX shell / bash or Python standard library only.
- Skills improve themselves: generic learnings go into the skill's "Self-update log",
  project-specific learnings into the project's adapter.
