# Diagnosing "X fails on environment Y"

Read in Phase 2 when a ticket reports a failure in a deployed environment. All steps
are read-only unless the user explicitly approves otherwise. Commands are examples for
Kubernetes and Docker; the adapter's `diagnosis` section gives this project's real
equivalents (contexts, namespaces, how to reach logs). Never paste secrets or customer
data from the environment into the conversation or the ticket.

## 1. Is the environment running the code you think it is?

A surprising share of "the fix doesn't work there" is "the fix never deployed".
- Is the commit on the deploy branch? `git branch -r --contains <sha>`
- Did the deploy run for it conclude successfully? (/marpiech-observe-ci, or the CI CLI)
- Does the running version match? (image tag / version endpoint / build info)
Only after all three hold, debug the code.

## 2. Do not trust the hypothesis — including the user's

"Probably disk", "must be a timeout" — collect evidence first; the answer often differs.

## 3. Runtime state (cheap, check first)

```bash
kubectl -n <ns> get pods                       # CrashLoopBackOff, READY 0/1, RESTARTS climbing
kubectl -n <ns> get pod <pod> -o jsonpath='{.status.containerStatuses[0].lastState}'
#   exitCode 137 + OOMKilled → memory limit hit (not disk, not a logic bug)
#   exitCode 143             → SIGTERM, often a failing liveness probe
kubectl -n <ns> logs <pod> --previous --tail=200   # the crashed container's last words
```

Disk vs memory, quickly:
```bash
kubectl -n <ns> exec <pod> -c <container> -- df -h <data-dir>       # disk usage
kubectl -n <ns> get pod <pod> -o yaml | grep -A 8 resources:        # memory/cpu limits
```
`df` at 2 % plus OOMKilled = memory, whatever the guess was.

## 4. Reproduce locally with the real input, and measure

1. Obtain the failing input the way the adapter allows (never from a production store
   without the user's approval; respect data privacy rules).
2. Copy it into the locally running component (`docker cp <file> <container>:<path>`).
3. Run the failing step in isolation and measure:
   ```bash
   docker exec <container> python3 -c '
   import resource, time; t0 = time.time()
   # … call the failing function on the copied file …
   print("peak MB:", resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024)
   print("seconds:", round(time.time() - t0, 1))'
   ```
Rule of thumb: loading a large JSON/pickle fully into Python objects costs 4–10× the
file size in memory. Compare the measured peak with the container's limit.

## 5. Prove the fix with numbers

Re-run the same measurement with the fix (e.g. streaming instead of loading the whole
file). Put the before/after numbers ("peak 6.2 GB → 14 MB") in the TECH part of the
resolution comment — numbers persuade, "should help" does not.
