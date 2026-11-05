# Debugging techniques by mode

Read in Steps 4–5 for the mode chosen in Step 2. Each mode lists what to do first, the
tools that usually narrow it fastest, and the traps that waste the most time.

## BUG — reproducible, local

- First: the smallest call that shows it. Prefer a test-runner one-liner
  (`pytest path::test -x`, `node --test file`) or a short script over clicking through a UI.
- Read the stack trace bottom-up to the first frame in *your* code; that frame's inputs
  are the first thing to print.
- Print values at boundaries, not everywhere: function entry/exit of the suspect, the
  serialisation boundary, the query and its parameters.
- A debugger (`breakpoint()`, `node --inspect`, IDE) beats print statements when the
  state is large or the path is unclear. Remove every temporary print before Step 8.
- Trap: "fixing" the line that raises instead of the line that produced the bad value.

## REGRESSION — "used to work"

- First: find a known-good point (a tag, a deploy, a date) and a known-bad point.
- `git bisect run <script>` where the script exits 0 = good, 1–124 = bad, 125 = skip.
  Make the script build what it needs (install, compile) so each commit is tested fairly.
- If the regression came with a deploy, compare the two *deployed* artefacts (image
  digests, lock files, config), not only the commits — configuration and dependency
  changes are regressions too.
- Trap: bisecting with a flaky reproduction. Make the repro deterministic (or run it N
  times per step) first, or bisect will point at a random commit.

## PERFORMANCE — slower than before

- First: a number. Same input, same environment, measured the same way, before and after
  (p50/p95, wall time, memory peak). Without the number there is nothing to verify.
- Profile both versions (`py-spy`, `cProfile`, `perf`, browser performance panel,
  `EXPLAIN ANALYZE` for queries) and compare the top frames.
- Common causes: N+1 queries, a lost index, a cache that no longer hits (key changed),
  a synchronous call added to a hot loop, a payload that grew (pagination removed),
  a regex with catastrophic backtracking, logging at debug level in production.
- Trap: optimising the slowest-looking code rather than the part that changed.

## INTERMITTENT — sometimes, only in CI, only under load

- First: the rate. Run N times; record failures / N. Without a rate, a "fix" cannot be
  told apart from luck.
- Usual causes: ordering (test A leaves state test B reads), time (time zones, DST,
  "now" near midnight, timeouts tuned to a fast machine), concurrency (shared mutable
  state, missing await, races between write and read), environment (parallel workers,
  different CPU count, locale, file-system case sensitivity), external services.
- Stressors that raise the rate: run in parallel, randomise order, run on a loaded
  machine, freeze or skew the clock, throttle the network, fill the disk.
- IF the flaky thing is a test → /marpiech-tests flaky mode owns the procedure.
- Trap: adding a sleep or a retry and calling it fixed. That is a mitigation.

## SERVICE — will not start, 500, 502

- First: the service's own logs from its start, then its configuration as loaded (names
  of variables present, never their values).
- 500 = the service ran and raised: template/serialisation errors, an unregistered
  helper, a missing column after a migration.
- 502/503 = the service is not answering: crashed at start (missing env var, failed
  migration, port in use), out of memory, health check failing, wrong upstream address.
- After changing code: know whether the service hot-reloads or must be rebuilt; a change
  "not taking effect" is usually an old image or a cache.
- Trap: restarting until it works. A crash that disappears on restart will come back.

## PRODUCTION — only there

- Observe only: logs, traces, metrics, audit trail, read-only queries for the specific
  rows involved, the exact deployed version.
- Compare production with staging on: version, configuration (names and fingerprints),
  data shape (volume, a value distribution, an edge case that only real data has),
  traffic (concurrency, payload size), integrations (real vs sandbox upstreams).
- Reproduce the data *shape* elsewhere with synthetic data.
- Trap: "quick test" writes on production. Never, unless the user asks for that action.

## Cross-cutting tricks

- **Diff two worlds.** Whenever "it works there", list every difference (version, config,
  data, platform, time, user/permission) and eliminate them one by one.
- **Timing is evidence.** How long until it fails often names the layer: instantly →
  parsing/config; after a fixed timeout → a call that never returns; after a variable
  time → data-dependent work.
- **Rubber duck in writing.** Explaining the path step by step in the debug log, with the
  actual values, finds a surprising number of bugs before any experiment.
- **Ask what changed in the world**, not only in the code: certificates expiring, quotas,
  a dependency's new major version pulled by an unpinned range, a calendar edge (month end,
  leap day, DST), a new kind of customer input.
