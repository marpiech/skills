# Debug log — <symptom in one line>

<!-- Working notes for one debugging session. Keep in the scratch area, not the repo.
     No secret values, no customer data — names and synthetic examples only. -->

## Frame
- actual:
- expected:
- since when (last good / first bad):
- where (env, input, user, platform):
- how often:
- first error (verbatim):
- mode:

## Reproduction
- command:
- result:

## Shrink
| axis | step | result |
|------|------|--------|

Smallest failing unit:

## Hypotheses
| # | hypothesis | prediction if true | cheapest refutation | result |
|---|------------|--------------------|---------------------|--------|

## Proof
- explains every symptom: yes/no — how
- switched on/off by:
- one level below the surface:

## Fix
- place:
- regression test (failed before → passes now):
- attempts so far: 1 / 2 / 3 (three = stop and re-frame)

## Verify
- [ ] regression test passes
- [ ] original reproduction shows expected result
- [ ] neighbouring suites pass
- [ ] verified in the environment where it was seen

## Variants
- shape:
- hits fixed / listed:
