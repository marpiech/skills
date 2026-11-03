# Flaky tests — causes, how to confirm, how to fix

Read in mode D. Classify before fixing; the first matching row is usually right.

| cause | how to confirm | fix |
|-------|----------------|-----|
| shared mutable state (module globals, singletons, caches, class attributes) | fails only after another specific test; passes alone | reset in a fixture; build fresh objects per test |
| order dependence | random-order run fails (`pytest -p random_order`, `--randomly-seed`, `vitest --sequence.shuffle`) | make each test arrange its own state |
| data left by earlier runs | fails on the second run, not the first; unique-constraint errors | unique IDs per run; clean up in teardown; transactional fixtures |
| fixed sleeps / missing waits | failure rate rises on a loaded machine | wait for the condition (`expect(...).toBeVisible()`, polling with a deadline) |
| unawaited async work / background tasks | warnings about never-awaited coroutines; assertions racing a task | await it, or expose a hook to wait on completion |
| time and time zones | fails near midnight, month end, DST changes, or in CI's zone | inject a clock or freeze time; compare in UTC |
| randomness without a seed | different values each run | seed the generator in the test; assert properties, not exact values |
| real network or third-party services | fails offline or when the service is slow | mock at the boundary (unit); a stub server (integration) |
| port / file / resource collisions | "address already in use", locked files, parallel runs clash | ephemeral ports (`0`), temp dirs per test, unique names per worker |
| environment drift in CI (shared runners, other jobs) | fails only in CI, on specific runners | isolate (containers, unique resources); do not share a database across concurrent jobs |
| floating-point / ordering of unordered results | values differ in the last digits; set/dict order | approximate comparison; sort before comparing |

Measuring:
- repeat one test N times: `pytest <id> --count 50 -x` (pytest-repeat),
  `for i in $(seq 50); do <cmd> || break; done`, `npx playwright test <file> --repeat-each 20`;
- record the failure rate before and after; a fix is proven by N consecutive passes,
  in random order where possible.

Not fixes: retries, longer sleeps, `skip`, widening a timeout without understanding why.
A quarantine (a flaky marker with a reason and an owner) is a temporary measure the user
must agree to.
