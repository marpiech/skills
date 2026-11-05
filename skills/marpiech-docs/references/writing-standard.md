# Writing standard for user-facing pages

Read before AUTHOR mode. Part 1 is the review lessons: failure modes that reviewers
flagged again and again on real pages. Part 2 is the plain-language rules. Part 3 is
house-style consistency. Part 4 is the checklist to run before you ship.

The project's adapter can tighten any rule (terminology table, audience, spelling); it
should not loosen Part 1.

---

## Part 1 — Review lessons (check every draft against each)

1. **Document only what is live in the deployed product, not what exists in code.** A
   model that supports something, a route behind a flag, or code on a branch is not a
   feature users can use. When unsure whether a feature is enabled, ask — do not infer
   "it's in the code, so document it".

2. **No invented behaviour.** Every claim must trace to a template, a route, an enum, or
   a screen you saw. Typical inventions: notification events that do not exist, digests
   and icons nobody built, a three-level model where there is one level, filters that
   are not there.
   - **Trap:** listing what an output contains or excludes (archive contents, export
     columns, report sections). Only enumerate it when you can point at the code that
     builds it. When unsure, cut the list — reviewers prefer the section gone over wrong.

3. **Use the product's exact words.** Match the label the UI shows, verified in the
   template — and fix *every* occurrence when you correct one. Keep a terminology table
   (adapter) and grep for the rejected forms.

4. **Write for the reader, not for engineers.** On user pages: no class or module paths,
   no database tables or internal IDs, no "state machine" phrasing, no storage bucket
   paths, no internal field names, no developer slang ("toast" → "a confirmation
   message").

5. **State the required role for each action, verified against the access-control
   code.** Cover the consequential actions (who can *delete*), not only the happy path.
   Reflect ownership rules where they exist (owner + admin), not generic role tiers.
   Never document internal-only roles.

6. **Do not send users to internals.** Raw file browsers, admin consoles and debug
   screens are not user destinations. Mention only the one path the reader needs.

7. **A how-to page must teach the action.** Lead with numbered steps; reference lists
   (routes, fields) go at the end, if at all.

8. **Cut tangents; keep it short.** Reviewers ask to remove far more often than to add.
   When unsure whether a paragraph earns its place, cut it.

9. **A rewritten page may carry a stale screenshot.** After a substantial rewrite,
   re-check every screenshot against the current UI and the demo persona; delete orphaned
   screenshots so they cannot be reused.

10. **One canonical home per topic.** Do not repeat a file-type table or a permission
    matrix on every entity page — say it once and link to it.

11. **A tightly scoped page stays in scope.** A mid-page detour into a different flow
    broadens the page; put it in "See also". Applying review feedback literally can still
    worsen a page — weigh each addition against the page's one job.

---

## Part 2 — Plain-language rules (after ASD-STE100 Simplified Technical English)

ASD-STE100 is a controlled-language specification for technical documentation (from
aerospace maintenance manuals; now used in medical devices, automotive, regulated
industries). It has writing rules and a controlled dictionary. Domain nouns and process
verbs (**technical names** and **technical verbs**) are always allowed, so the domain
vocabulary is not restricted — only the ordinary English around it. It suits readers who
read English as a second language and procedures where a misread step matters.

Enforce the rules; do not try to conform to the dictionary word by word (that needs the
licensed specification and produces stilted web prose).

| rule | on the page | fix |
|------|-------------|-----|
| simplest word that works | no inflated verbs or filler | utilize→use, initiate→start, terminate→stop, prior to→before, in order to→to, approximately→about |
| one word, one meaning | a term keeps one sense site-wide | do not let "run" mean both a job and starting it |
| noun clusters ≤ 3 nouns | stacked nouns are ambiguous | "the confirmation dialog for the classification override" |
| active voice | the actor is clear | "Click **New Order**" not "An order is created by clicking…" |
| simple tenses | present, simple past, simple future | "is processed", not "will have been processed" |
| no `-ing` as a verb | except in technical names and existing page titles | "When you select the panel, the filter applies" |
| keep articles | do not drop the/a for brevity | "Open the project picker" |
| procedure sentence ≤ 20 words | one step, one sentence | split at "and then" / semicolon |
| descriptive sentence ≤ 25 words | conceptual prose | split; do not stack clauses |
| one instruction per sentence | two actions = two steps | "Select the sample." "Click **Run**." |
| paragraph ≤ 6 sentences, one topic | | split or cut |
| warnings: command first, reason second | | "Do not close the tab while the archive builds. Large archives take minutes." |
| no slang, idiom, metaphor, marketing | | "under the hood"→"internally"; drop "powerful", "seamless", "intuitive" |

Exempt: existing page titles and nav labels (the nav is a contract; do not rename pages
to satisfy the `-ing` rule). Agent-facing docs benefit from the same brevity but are not
gated on it.

`docs-check.py style` flags inflated words, long sentences, rejected terms and (with
`--british`) British spellings. Every hit is advisory: a clear 27-word sentence can
stay; a 19-word sentence with three clauses should not.

### Part 2b — Prose that reads as generated (remove it)

Readers stop trusting a page once it sounds machine-written, even when the facts are
right. `docs-check.py style` flags the stock phrases (`SLOP`: "delve", "plays a crucial
role", "in today's fast-paced…", "not just X, but Y", "let's dive in"); the structural
patterns below need a read:

| pattern | fix |
|---------|-----|
| an opening sentence that restates the title or sells the feature | start with what the reader can do or must know |
| a closing "In summary / Overall / In conclusion" paragraph that repeats the page | delete it; end with the last step or "See also" |
| reflexive lists of three ("fast, reliable and secure") | keep only the items that are true and specific |
| "This isn't X — it's Y" and other contrast-for-drama constructions | state Y |
| stacked hedges ("may potentially help to") | one qualifier, or none |
| every bullet opening with a bold label and a colon | use plain bullets unless the label is a real term the reader scans for |
| frequent em-dashes and parenthetical asides | split into sentences |
| rhetorical questions as headings or openers | a heading names the task ("Export a report") |
| emoji in headings, decorative symbols | remove |
| praise of the reader or the product ("great question", "powerful") | remove |

---

## Part 3 — House-style consistency

Consistency defects travel in clusters: when you standardise a term, grep the whole
docs tree, not only your page.

- **A. One spelling variant**, matching the product UI (American or British), checked
  by grep.
- **B. One canonical name per thing.** The UI's exact label, everywhere. When a terse
  label and a fuller term both appear, bridge them once: "Sex (biological sex)".
- **C. Never invent roles, stages or statuses**; spell them identically on every page.
  If stored values differ from display labels, say so once.
  Expand an acronym on first use.
- **D. A fact stated on two pages must agree.** Verify the one true value in code; make
  both pages match, or state it once and link.
- **E. One voice.** Second person for the reader, third person for the product; no
  "we/our" unless the adapter says otherwise.
- **F. One closing section name** ("See also"), 3–5 links, every target existing.
- **G. Right altitude.** A user page is never a developer page (no function names,
  endpoint tables, transaction semantics, architecture diagrams) and never an
  administrator-only page presented as something every reader can do. If a page reads
  like a service tour, rewrite it as the user's task.
- **H. Replace vague quantities with the real value** from code ("valid for 15
  minutes", not "for a limited time").
- **I. Copy-edit:** parallel structure in lists, plural agreement, no ambiguous
  pronouns, no sentence that restates the previous step.

---

## Part 4 — Ship checklist

- [ ] Every factual claim was grep-verified in code or seen in the deployed product.
- [ ] Nothing documented that is not live; no enumerations without code backing.
- [ ] UI labels exactly as shown; terminology table applied site-wide.
- [ ] Required role stated for each action, including destructive ones.
- [ ] Procedural pages lead with numbered steps, one instruction each.
- [ ] No internals: module paths, tables, bucket paths, internal roles, ticket keys,
      internal version labels, "follow-up ticket".
- [ ] No CLI/API content on UI pages (and vice versa).
- [ ] Screenshots current, from the demo persona, no real data, no admin indicators.
- [ ] "See also" with 3–5 existing targets; page listed in the nav.
- [ ] No stock phrases or generated-prose patterns (Part 2b).
- [ ] `docs-check.py links`, `nav`, `style` run; hits read and judged.
