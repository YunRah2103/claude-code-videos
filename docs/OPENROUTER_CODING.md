# OpenRouter helper: integration status

The standalone CLI is **inspection-only**: `--dry-run` constructs a request but
prints the task text locally; without that flag it refuses to send. The helper's
`send` function remains callable by Python code, so callers must enforce the
rotation policy, reviewed task, account-level zero-spend protection and quota
ledger. A `:free` suffix alone does not prove a particular account cannot be billed.
No CLI command in this integration enables a model request.

The transport reads at most 1 MiB plus one byte and fails closed for larger
responses. The default socket timeout is 30 seconds; this limits individual
socket operations, not total wall-clock duration of a slowly streaming response.
There is no automatic retry. A timeout leaves delivery unknown and a reservation
must remain consumed. Structured error codes carry no raw HTTP error bodies or
credential values. The adapter recognises these codes; an older helper lacking
codes fails closed as `INTERNAL_ADAPTER_ERROR`.

For an offline readiness check of an existing task:

```bash
python -m tools.agent_rotation --state out/agent-rotation/state.db preflight --id TASK_ID
```

This reads the existing database, reports the task state, existing reservation and OpenRouter block,
and never sends a request or unblocks a provider. A future supervised run command
needs explicit task review, a verified current zero-spend account, a specific
approved model, a unique durable reservation, bounded transport and a human
review step. It must refuse unattended calls and keep uncertain requests from
being resent. The current code does not implement that CLI.

Git worktrees only separate edits; they are not security sandboxes. Do not run
generated code or tests on the host. A reviewed, isolated execution environment
is needed before testing any untrusted output. Gemini remains disabled.
