# repo-memory conventions

The full specification behind `SKILL.md`. Read this before creating a new memory file
or restructuring an existing one. Contents:

1. File format
2. Frontmatter schema
3. Read protocol in detail
4. Tip, not truth
5. Owns only what has no other home
6. Capabilities, not paths
7. Coexistence with other knowledge stores
8. Worked examples (good and bad)
9. Writing a good Log entry — checklist

All examples use a fictional project, `acme-shop` (ticket prefix `ACME`).

---

## 1. File format

One memory file (default name `MEMORY.md`) is **about one subject** — the directory or
topic it sits in. It has three parts: frontmatter, a **Durable** section, and a **Log**.

```markdown
---
summary: <one line — what this directory/topic is>
why: <the core decision and its motivation>
created: 2026-01-15
last-verified: 2026-01-15
# optional fields, only when they carry signal (§2)
status: stable
relations:
  - docs/payments.md
  - "[[../orders/MEMORY.md]]"
---

# <Subject> memory

## Durable
Curated, settled decisions and conventions for this subtree. Edit in place as
understanding improves — this is the part read at Level 1. Keep it tight.

## Log
Append-only, newest first. Raw observations from real work, each dated. Promote
anything that becomes settled up into Durable; leave the dated trail here.

### 2026-01-15 — short title of what happened
- what we found / did, and the *why*
- unexpected: <gotcha>            # optional inline fields, same vocabulary as §2
- revisit-when: <triggering event>
```

- **Durable** = what is true now (read first). **Log** = how we got here (read when
  working in this subtree). Either section may be omitted while empty.
- The **root memory file is a thin index**: pointer lines to the other files, one line
  each, with a hook that says *why you would open it*. It never inlines content.

Root index line format:

```markdown
- [payments retries](services/payments/MEMORY.md) — why retries are idempotency-keyed, not time-boxed; the provider double-charges on timeout
```

A good hook names the **surprise**, not the topic. "payments notes" is useless;
"provider double-charges on timeout" is what makes a future reader open the file.

## 2. Frontmatter schema

Keep required fields minimal so updating stays a two-minute habit. Add optional fields
**only when they carry signal** — empty ceremony fields train the next reader to skip
frontmatter.

**Required**

| field | meaning |
|-------|---------|
| `summary` | one line — what this is |
| `why` | the decision and its motivation (memory's whole reason to exist) |
| `created` | date the file was first written (`YYYY-MM-DD`) |
| `last-verified` | date someone last confirmed it against reality (bump via `mem-stamp.sh`) |

**Optional — add where the value lives**

| field | use it for |
|-------|-----------|
| `hard` | what was difficult, what fought back, the time sinks |
| `unexpected` | surprising or counterintuitive behaviour, gotchas |
| `rejected` | alternatives considered and why they lost — **stops re-litigation** |
| `invariants` | constraints that must hold / footguns ("never do X because Y") |
| `failure-modes` | known ways this breaks |
| `source-of-truth` | what is canonical here — THIS entry, or the place it names (binary) |
| `relations` | links to related code, other memory files, ADRs, docs, tickets/PRs |
| `scope` | what this does **not** cover, and where to look instead |
| `status` | `stable` \| `experimental` \| `deprecated` (feeds tip-not-truth) |
| `revisit-when` | the **event** that should trigger re-verification ("when we upgrade the payment SDK") — event-based freshness beats a date |
| `provenance` | the PR/commit/ticket/conversation it came from, so it can be re-derived |

The same vocabulary (`unexpected:`, `rejected:`, `invariants:`, …) can be used as inline
bullet prefixes inside individual Log entries — that is where most of it naturally lands.

## 3. Read protocol in detail

Spend the **minimum** context needed — memory is an accelerant, not required reading.

- **Level 0 — always (session start):** the root index, nothing else.
- **Level 1 — on a task:** `scripts/mem-search.sh <terms>` to find candidate files. For
  each hit, read **frontmatter + Durable** only. Often that is enough.
- **Level 2 — when relevant:** read a file's full body (Durable + Log) when it is in the
  subtree being changed, or its summary says it is relevant.
- **Level 3 — only if Level 2 says so:** follow `relations` links out to code, ADRs,
  other memory files, external docs.

Choosing search terms: use the nouns of the task (module names, domain words, the
external system involved, the error message's distinctive token, the ticket key).
Run 2–4 searches with different terms rather than one broad one. Prefer the **nearest**
memory file to the code being touched; ascend only if it points upward. Discovery is
lexical only — never build an embedding/vector index and never read the whole tree
"to be safe".

## 4. Tip, not truth

A memory file is a **point-in-time observation, not live state.** Its durable
*reasoning* (the why, rejected paths, surprises) is high-trust — it rarely changes. Its
*mechanical claims* (paths, line numbers, function names, exact behaviour) are **hints to
verify**, because code moves under them.

Before asserting a mechanical claim taken from memory:

1. Verify against the current code (open the file, grep the symbol, run the thing).
2. IF it checks out → state it, and mention the file's age if you lean on it.
3. ELSE → **ignore the memory**, tell the user, and offer the correction (update Durable,
   bump `last-verified`, or set `status: deprecated`).

Staleness signals: days since `last-verified` (printed by `mem-search.sh`), `status`,
and whether a `revisit-when` event has already happened. A confidently-wrong stale note
costs more than no note.

## 5. Owns only what has no other home

The single rule that decides what goes into a memory file:

- **No canonical home → memory is the source of truth → record it fully.** Decisions,
  rationale, "why it is weird", rejected alternatives, footguns, the story behind a
  workaround. These exist nowhere else; if memory does not hold them, they are lost.
- **Has a canonical home → link, never copy.** Code, config, schemas, migrations,
  external guidelines, CLAUDE.md rules. Copies go stale the moment the source changes.

`source-of-truth` per entry is therefore binary: this entry *is* the truth, or it
*names* where the truth lives. Never half-copy.

## 6. Capabilities, not paths

Write **durable content**: capabilities, domain concepts, reasoning, trade-offs. Treat
structural facts (file paths, layout, line numbers) as **possibly-stale hints**, never as
an entry's primary content.

- Good: "Cart totals are recomputed server-side on every checkout step because the client
  copy drifted when coupons expired mid-session (rejected: trusting the client total)."
- Bad: "Totals are in `cart/totals.py` line 240." ← will rot. If a location matters, say
  *what* it does and let the reader grep for its current place.

## 7. Coexistence with other knowledge stores

Most repositories already have several knowledge stores. The memory file fills the gap
none of them do — the *why* and the *surprises*, co-located with the code.

| store | holds | memory's relationship |
|-------|-------|-----------------------|
| `CLAUDE.md` / `AGENTS.md` | always-loaded rules and conventions | link to it; never restate a rule |
| docs directory (`docs/`, ADRs) | formal architecture, design records | point there; capture the field note a doc is too formal for |
| task tracker / todo files | in-flight work | memory is settled knowledge, not a task list |
| Claude Code's personal auto-memory (`~/.claude/projects/…`) | one user's private preferences, never shared | not a substitute: repo memory is committed and shared with the team |
| **repo memory files** | decisions, gotchas, rejected paths, tribal knowledge, next to the code | the source of truth for these |

IF a fact is a broadly-applicable rule → it belongs in CLAUDE.md; memory links to it.
Memory is for the local, the historical, and the surprising.

## 8. Worked examples

### Good — `services/payments/MEMORY.md`

```markdown
---
summary: payment capture + retry layer in front of the card provider
why: the provider's capture call times out but still succeeds; naive retries
     double-charged customers, so every capture carries an idempotency key
created: 2026-01-10
last-verified: 2026-03-02
status: stable
rejected: time-boxed retry window (still double-charged on slow days);
          polling the provider for status before retry (rate-limited, 4× latency)
invariants: never generate the idempotency key inside the retry loop — one key per
            customer intent, created before the first attempt
revisit-when: we change payment provider or their SDK major version
relations:
  - docs/adr/0007-idempotent-captures.md
  - "PR #412"
---

# payments memory

## Durable
- Idempotency key = order id + attempt intent, created once (see invariants).
- A timeout is NOT a failure signal; the reconciliation job is the arbiter.

## Log
### 2026-03-02 — re-verified after SDK patch upgrade
- behaviour unchanged; last-verified bumped. unexpected: sandbox never times out,
  so the double-charge cannot be reproduced there — use the recorded fixture.

### 2026-01-10 — chose idempotency keys
- hard: two days lost assuming our code double-submitted; it was the provider.
```

Why it is good: the *why* and *rejected* paths are recorded fully (no other home);
location detail is framed as behaviour; it links to the ADR instead of restating it;
`last-verified` and `revisit-when` make staleness legible.

### Bad — what not to do

```markdown
---
summary: payment stuff
---
The retry code is in retry.py line 88. It uses requests. See CLAUDE.md which says use
async everywhere and type hints and...
```

Why it is bad: no `why`, no dates (rot is invisible); pins a line number
(capabilities-not-paths violation); copies CLAUDE.md rules instead of linking
(owns-only-what-has-no-home violation); the summary carries zero signal.

## 9. Writing a good Log entry — checklist

Before saving an entry, check each line:

1. **Dated heading** `### YYYY-MM-DD — <what happened>` — newest first.
2. **Would a teammate six months from now need this?** IF the fact is derivable from
   code, git log, or an existing doc → do not write it (link instead).
3. **States the why**, not just the what.
4. **Uses a prefix** (`unexpected:`, `rejected:`, `invariants:`, `hard:`,
   `failure-modes:`, `revisit-when:`) where one fits — they are grep targets.
5. **Names a provenance** (ticket key, PR, commit) when one exists.
6. **No secrets, no customer data, no personal data.** Memory is committed to git.
7. **2–5 bullets.** Longer → it is probably a doc; write the doc and link it.
8. IF the entry settles something → also edit **Durable** (promote) and bump
   `last-verified`.
