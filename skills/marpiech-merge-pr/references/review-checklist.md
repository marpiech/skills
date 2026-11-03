# Merge review checklist (generic)

Apply every row to the diff **and** the surrounding code. Add the adapter's project
gates and the CLAUDE.md rules on top. Each finding: `file:line`, what, why, smallest fix.

## Correctness
| check | look for |
|-------|----------|
| logic | off-by-one, inverted conditions, wrong operator, unhandled branch of an enum/state |
| boundaries | unvalidated input at system edges, missing null/empty handling where data enters |
| errors | swallowed exceptions, error paths that leave partial state, retries without idempotency |
| concurrency | read-modify-write without a lock/transaction, races between requests or workers |
| data | migrations without backfill/rollback, changed meaning of stored values, timezone/units |
| tests | does a test fail without the change? are new branches covered? flaky waits/sleeps? |

## Security
| check | look for |
|-------|----------|
| secrets | credentials, tokens, keys, connection strings — in code, tests, fixtures, docs, CI |
| injection | string-built SQL/shell/HTML/paths; unsafe deserialisation; template auto-escape off |
| authorization | new endpoints/actions without an access check; IDs from the client trusted for ownership |
| exposure | sensitive data in logs, errors, URLs or responses; overly broad CORS; debug flags on |
| supply chain | new dependencies (maintained? needed?), unpinned CI actions, scripts piped from the network |
| CI changes | workflows that gain secrets, write permissions, or run on untrusted events |

## Design & maintainability
| check | look for |
|-------|----------|
| DRY | duplicated blocks > ~5 lines; logic copy-pasted across files |
| abstraction | 3+ similar repetitions that should be one helper; or the opposite — a premature abstraction with one caller |
| layering | the project's layers respected (e.g. handlers not calling the database directly) |
| hardcoding | hosts, URLs, ports, paths, environment names baked into code instead of configuration |
| naming | misleading or inconsistent names; comments that contradict the code |
| scope | unrelated changes riding along; debug leftovers; commented-out code |
| UI | the project's component library and style rules used; empty/long/error states handled |

## Process
| check | look for |
|-------|----------|
| ticket | the PR does what the ticket asked — no more, no less |
| docs | user-visible changes reflected in documentation (or a follow-up agreed) |
| memory | decisions or traps worth a MEMORY.md entry are recorded |
| commits | messages explain why; ticket key present if the project uses one |
