# CI traps that each cost real time somewhere

Generic forms of problems seen in production pipelines. Check the matching entry before
concluding anything from a CI result.

1. **Inside a reusable (called) workflow, `github.ref` and `github.event_name` are the
   CALLER's.** A job guarded by `if: github.ref == 'refs/heads/main'` shows *skipped*
   whenever another branch's workflow calls it — by design, not a coverage gap.

2. **A green step is not proof the work happened.** Steps written to be fail-safe
   (`continue-on-error`, `set +e … exit 0`, `|| true`) succeed when their tool could not
   even run (image pull failed, vulnerability DB unavailable). When it matters, assert
   the work in the log (e.g. one "scan complete" line per image).

3. **Push succeeded but no run appeared.** Check, in order: does the workflow's `on:`
   match this branch and these paths; is the workflow disabled; is the provider
   degraded (status page — it can lag; API calls returning HTTP 5xx are a stronger
   signal). During an outage, manual dispatch can fail too; once the API answers again,
   re-dispatch or push an empty commit.

4. **A job "failed" with zero steps and no runner name** = the platform never handed the
   job to a runner. There is no code error to find. Wait until the API responds, then
   cancel and re-run. Self-hosted runners log the acquisition failure in their
   diagnostic logs.

5. **Results gathered while a deploy is rolling are invalid.** Restarting services
   produce transient 4xx/5xx and false end-to-end failures. Judge only after the deploy
   job concluded.

6. **Shared branches carry other people's commits.** A run may deploy work that is not
   yours, and its failure may not be your commit. Read `git log` of the run's sha and
   attribute honestly.

7. **Run lists include cancelled, superseded runs.** A newer push cancels in-flight runs
   of an older one. The newest run for the head commit is the one that matters.

8. **Self-hosted runners share the host.** Local services left listening on a port the
   CI stack binds make the pipeline fail at "port already in use". Keep local proxies
   and dev servers off the CI's ports while a deploy can run.

9. **Network middleboxes can break tools that connect to bare IP addresses.** A
   transparent proxy that resets TLS connections without a hostname (SNI) breaks e.g. a
   cluster CLI pointed at an IP endpoint — after every gate passed. Fix: a DNS-based
   endpoint; diagnose with a packet capture rather than allowlist changes.

10. **The unit gate is real.** Running the affected suite locally before pushing is
    cheaper than learning about it from a red deploy.
