# Resolution comment format (INFO / TECH)

Every resolution comment has two labelled paragraphs, in this order.

**INFO:** for a non-technical reader (reporter, product owner, QA). At most three
sentences, plain language, no file names or commit hashes. It says *what changed for
the user* and *how to check it* (where to look, what to do). The reviewer accepts the
ticket from this paragraph alone — if they could not tell how to verify, rewrite it.

**TECH:** for engineers. Root cause (for bugs), what was done, commits, the
deploy/CI run that shipped it, tests and validation run, effort estimate if the team
tracks it. Jargon is fine.

## Templates

New work:
```
INFO: <what changed, plainly, ≤3 sentences>. To check: <where to look / what to do>.

TECH: Fixed in <commit>, shipped by run <run id>. <root cause + what was done>.
Tests: <what was run>. <Effort: Xh, if tracked>.
```

Already done (fast-path close):
```
INFO: Already working on <environment> — <one plain sentence>. To check: <where to look>.

TECH: Reporter confirmed: "<quote>". Shipped in <commits> — <one-line summary>.
```

Closed after an audit, no explicit acceptance:
```
INFO: <plain statement that it is done>. To check: <where to look>.

TECH: Audited against current code — <what was checked, where it lives>. Gaps: <none | …>.
```

Wording changes (from screenshots): quote each string as `"before" → "after"` in INFO so
the reporter can verify without opening the UI.

## Evidence for reviewers who accept from the comment

When the adapter's `evidence-for` matches the reporter, add *after the deploy landed*:
1. a screenshot of the changed area **on the environment they review**, cropped to the
   part that changed, attached to the ticket (`tickets.py attach`), named in INFO;
2. a direct link to that page as `[label](https://…)` inside INFO.
Never attach a screenshot from a local/dev environment the reviewer cannot open, and
never one that shows personal or customer data that the reviewer may not see.
