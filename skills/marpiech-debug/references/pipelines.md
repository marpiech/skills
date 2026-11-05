# PIPELINE mode — workflow engines, batch jobs, schedulers

Read in Step 4–5 when a job, data pipeline or workflow run failed (WDL/Cromwell,
Nextflow, Snakemake, CWL, Airflow, a cloud batch service, a cluster scheduler). The
project adapter supplies the concrete commands; this file supplies the order of work.

## 1. Locate the run and its artefacts

For the failed run, collect (read-only):
- the run id in the application, the engine's workflow id, and the scheduler/batch job id;
- the engine's **metadata** (per-call status, failures, inputs as resolved, outputs);
- the engine log, and for the failed task: its stdout, stderr, the generated command
  script, and the exit code;
- the exact workflow version (a tag or commit) and the inputs file as submitted.

Credentials for the storage holding these are injected into the command that reads them
(the project's secrets tool), never written to a temporary file and never printed.

## 2. Read time-to-failure first

| failed after | usually means | look at |
|--------------|---------------|---------|
| seconds | the engine could not even start the workflow: syntax, imports, unresolved relative imports (the workflow was passed as a local file instead of a URL / bundle), engine configuration, permissions to read the workflow | engine log head |
| a few minutes, before any real task ran | inputs: required input missing, not namespaced as the engine expects (`workflow_name.input`), wrong type, a file that does not exist or is not readable, an index file (`.tbi`, `.bai`, `.crai`) missing next to its data file | metadata `inputs` and the first failure message |
| after tasks ran | a task's own failure: tool error, out of memory, disk full, wrong container tag, a timeout or preemption | the failed task's stderr and exit code |
| at the very end | output collection or upload: an output glob matched nothing, a permission to write the output location | the engine log tail and the output definitions |

## 3. Typical causes and their tells

- **Empty `select_first` / "all values were empty"** — an optional input the workflow
  needs was never set, or was set under a name the engine did not map. Compare the
  submitted keys with the workflow's declared inputs.
- **Exit code 137 / OOMKilled** — memory; check the task's requested memory against the
  input size, not only the tool.
- **Exit code 127** — command not found: the container image lacks the tool or the tag
  points at a different image than expected.
- **Preempted / retried N times** — spot/preemptible capacity; check retry settings
  before blaming the code.
- **Works for one sample, fails for another** — data shape: an empty file, a contig name
  convention (`chr1` vs `1`), a sample with no reads in a region, a header field missing.
- **Quota / API not enabled / permission denied** — infrastructure, not the workflow;
  report to whoever owns the account instead of editing the workflow.
- **Template/escaping bugs in generated job scripts** — a script built inside another
  language's string formatting (braces, dollar signs, quotes) is a frequent source of
  "works when typed by hand". Print the *generated* script (without secrets) and diff it
  with the hand-written one.

## 4. Reproduce small

- Re-run only the failed task with its resolved inputs (most engines can run a single
  task or resume from cache), or run the tool command from the generated script in the
  same container image locally on a tiny input.
- Shrink the input (one chromosome, a few thousand reads/variants) before re-running a
  whole workflow; pipelines are expensive and slow to iterate.
- Never resubmit production analyses as an experiment; use a test project/organisation
  and test data the adapter names.

## 5. Fix and verify

- Fix where the defect originates: the workflow definition, the input-building code, the
  container, or the engine configuration — and add a check at submission time when the
  failure was a predictable input problem (missing index file, un-namespaced key), so the
  user gets a clear error in seconds instead of a failed run in minutes.
- Verify with the small reproduction, then one real run on test data; record the run id.
- Add the failure mode to the adapter's known-failures table.
