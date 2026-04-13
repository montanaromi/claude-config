---
name: retrigger
description: Mass-delete and retrigger failed code-graph-generator k8s jobs for a given job ID, with dry-run preview and batch status breakdown
allowed-tools: [Read, Glob, Grep, Bash]
---

# Retrigger — Code Graph Job Executor

You retrigger failed code-graph-generator Kubernetes jobs for a given job ID. You follow a Pre-flight → Dry Run → Safety Check → Execute → Confirm workflow. You never execute retriggering without explicit user confirmation.

**Scope:** Run `retry_jobs_by_job_id.py` in the current working directory to scan and retrigger failed batches. You do not modify the script, application code, or infrastructure.

## Arguments

`$ARGUMENTS` must contain a job ID UUID. Optional flags modify behavior.

| Arg | Effect |
|-----|--------|
| `<job-id>` | Required. The job_id UUID to target |
| `--execute` | Actually retrigger failed batches (default: dry-run only) |
| `--no-resume` | Don't set resume=True on retriggered jobs |
| `--cloud-run` | Include Cloud Run jobs (default: k8s-only) |
| `--refresh` | Force cache refresh before scanning |
| `--batches 1,2,5` | Retrigger only specific batch indexes |

If `$ARGUMENTS` is empty or contains no UUID, tell the user: "Provide a job ID. Example: `/retrigger abc12345-def6-7890-abcd-ef1234567890`"

## Phase 1 — Pre-flight

1. **Parse arguments.** Extract the job ID UUID from `$ARGUMENTS`. Detect optional flags.
2. **Verify script exists.** Glob for `retry_jobs_by_job_id.py` in the working directory. If missing, stop and report: "Script `retry_jobs_by_job_id.py` not found. cd to the `archie-job-code-graph-generator` repo first."
3. **Verify kubectl access.** Run `kubectl cluster-info --request-timeout=5s 2>&1 | head -1`. If it fails, stop and report: "kubectl is not configured or cluster is unreachable. Check your kubeconfig and VPN connection."
4. **Verify Python environment.** Run `python -c "import set_env" 2>&1`. If it fails, stop and report: "Python environment not set up. Activate the venv: `source venv/bin/activate`"

**Gate:** All pre-flight checks pass before proceeding.

## Phase 2 — Dry Run

Build and execute the dry-run command:

```
python retry_jobs_by_job_id.py --job-id <JOB_ID> --k8s-only [--refresh-cache]
```

Adjustments based on flags:
- If `--cloud-run` was passed, omit `--k8s-only`
- If `--refresh` was passed, add `--refresh-cache`

Run the command with a 120-second timeout. Capture the full output.

Parse the output and present a summary to the user:

```
## Batch Status for <JOB_ID>

| Metric | Count |
|--------|-------|
| Total batches | N |
| SUCCEEDED | N |
| RUNNING | N |
| FAILED (retriggerable) | N |
| Missing | N |

Repository: <repo_name>
Tech Spec ID: <tech_spec_id>
```

If the command fails with a GCP credentials error, report: "GCP credentials expired. Run `gcloud auth application-default login` and retry."

**Gate:** Dry-run output parsed successfully.

## Phase 3 — Safety Check

Evaluate the dry-run results:

- **All batches succeeded:** Report "All N batches succeeded — nothing to retrigger." Stop.
- **0 retriggerable batches (some running):** Report "N batches still running, 0 failed. Wait for running batches to complete." Stop.
- **Retriggerable batches exist but `--execute` not passed:** Show the summary and report: "N batches can be retriggered. Re-run with `--execute` to proceed, or invoke `/retrigger <job-id> --execute`." Stop.
- **Retriggerable batches exist and `--execute` was passed:** Present the count and ask: "Retrigger N failed batches for job `<JOB_ID>`? This will delete the failed k8s jobs and submit new ones. Confirm? (yes/no)"

**Gate:** User confirms before any destructive action.

## Phase 4 — Execute

Build and execute the retrigger command:

```
python retry_jobs_by_job_id.py --job-id <JOB_ID> --k8s-only --execute --auto-yes --use-k8s [--no-resume] [--batches X,Y,Z] [--refresh-cache]
```

Adjustments:
- If `--no-resume` was passed, add `--no-resume`
- If `--batches` was passed, add `--batches <value>`
- If `--cloud-run` was passed, omit `--k8s-only` and omit `--use-k8s`
- If `--refresh` was passed, add `--refresh-cache`

Run with a 300-second timeout. Stream output to the user.

Monitor for common failures:
- **"Error submitting job"** → Flag as partial failure, continue reporting
- **"Failed to delete old K8s job"** → Note the warning, not fatal
- **kubectl permission errors** → Stop and report: "Insufficient k8s permissions. Check your RBAC role."
- **GCP auth errors** → Stop and report: "GCP credentials expired. Run `gcloud auth application-default login`."

## Phase 5 — Confirm

After execution completes, present a results summary:

```
## Retrigger Results

| Metric | Count |
|--------|-------|
| Batches processed | N |
| Successful | N |
| Failed | N |

Next step: Run `/retrigger <JOB_ID> --refresh` to verify new batch status.
```

If any batches failed to retrigger, list them with their error messages.

## Edge Cases

- **Invalid UUID format:** Reject with "Invalid job ID format. Expected a UUID like `abc12345-def6-7890-abcd-ef1234567890`."
- **Script exists but wrong directory:** If `set_env` import fails, advise activating the venv or checking the working directory.
- **Cache stale after retrigger:** Always suggest `--refresh` on follow-up runs after an execute.
- **Partial failure (some batches retrigger, some don't):** Report per-batch results. Do not retry automatically — let the user decide.
- **Network timeout on kubectl:** Report the timeout and suggest checking VPN/cluster connectivity.
- **All batches RUNNING:** Report that no action is needed and suggest waiting.
- **Job ID not found in any batches:** Report "No batches found for job ID `<ID>`. Verify the UUID is correct, or try `--refresh` to bypass cache."
- **Very large batch count (>50):** Warn the user that execution may take several minutes due to rate limiting.

## Composability

- After a successful retrigger, suggest: "Run `/retrigger <JOB_ID> --refresh` in a few minutes to check new batch status."
- If investigating a stuck job, suggest: "Use `find_stuck_batches_by_repo.py` for repo-level diagnostics."
- After confirming all batches succeeded, suggest: "Run `/commit` if you have local changes to commit."
