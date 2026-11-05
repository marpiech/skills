# marpiech-uidesign — project adapter

<!-- Location: <project>/.claude/adapters/marpiech-uidesign.md (commit it with the project).
     Checker config: .claude/uidesign.json. This file holds POINTERS and project mechanics only.
     Design content (values, components, decisions) lives in the design system — link, never copy.
     No secrets: name environment variables, never their values. -->

## Sources of truth (link, never copy)
- tokens: <file(s)> (light <selector>, dark <selector>)
- components: <dir(s)> — catalogue <file>, gallery/stories <where>
- formatters: <module(s)> (<names>)
- decisions: <file> → <heading> (D1…)

## Domain
- <none | genomics> — <which screens>

## House overrides of skill defaults (each cites its decision)
- <rule id> → <project rule> (D<n>)

## Accepted exceptions
- <path or screen>: <rule> — <why> (D<n> / date)

## Render
- URL: $<VAR>; login: $<USER_VAR> / $<PASSWORD_VAR> via `<secrets tool> run --`
- theme switch: <attribute / class / OS emulation>; widths: <1440, 768, 390>
- runner: <where the Playwright runner lives / which browser tool>

## Change log (newest first)
- YYYY-MM-DD — <check tuned / exception accepted / pair pinned, and why>
