# Agent rotation: offline foundation

```bash
python -m tools.agent_rotation status
python -m tools.agent_rotation plan --task 'Implement a wheel helper'
python -m tools.agent_rotation create --id wheel --goal 'Test wheel motion' --file tests/test_wheel.py
python -m tools.agent_rotation show --id wheel
python -m unittest discover -s tests -v
```

This is a foundation, not an agent launcher. Every default provider is disabled;
no model requests are made and plan does not persist tasks; create explicitly records a task. Historical access
and free usage are not proof of current availability or account billing status.
The CLI does not currently offer enabling a provider.

`core.py` contains a capability registry and SQLite reservation ledger. A
reservation is atomic across processes, survives restarts, applies rolling, optional UTC daily and monthly request counts and prevents repeated task IDs. A block stops selection until a
future explicit recovery mechanism is built. Never remove a reservation merely
because a request timed out: it may have reached the provider. Selection alone
is advisory; any future executor must reserve atomically before a request and
must fail closed. The ledger only records local reservations, not provider-side
usage, financial credit limits, or other clients' requests. Keep state under
ignored `out/`; do not rely on it as proof of zero cost.

`planner.py` returns ready tasks with no overlapping declared repository paths.
It does not launch agents, isolate workspaces, or monitor writes. It assumes
complete, canonical file declarations and does not resolve symlinks; actual
execution needs enforced isolation and post-run diff review.

Remaining: safe provider-specific allowlists and billing verification; complete
quota policies, recovery and rate-limit handling; task state and idempotency;
controlled subprocess execution, timeouts, validation, isolated output and
integration; concurrency-safe workspaces; provider and failure classification;
token metrics, tests, real benchmarks, security review and a reviewable PR.
Until those exist, do not use this as an autonomous coding system.

`tasks.py` records a small lifecycle and append-only status history. A task in
`running` after interruption is not automatically restarted: the prior request
may have been processed. Its `interrupted` status requires manual review before
marking review or failed. This is a state store only, not execution recovery.

`context.py` can package explicitly named UTF-8 files under a byte cap, rejecting
symlinks and traversal. It does not identify secrets or guarantee protection
against a concurrent filesystem change; inspect selected content before sharing
it with an external model. No context is sent by this module.

## Provider and validation status

The guarded OpenRouter adapter uses the separate PR #8 helper when present. It
can make one request only when supplied an enabled policy, a specific allowed
`:free` model, an enabled worker and an operator-verified zero-spend account;
those inputs default to disabled. A flag is not independent proof of billing
protection. The adapter has only offline tests in this environment and is not
wired into the CLI. On uncertain failures it retains the quota reservation and
blocks the provider. The integrated helper uses a 30-second per-socket timeout and a 1 MiB response cap; a socket timeout is not a total wall-clock deadline. Kilo preflight
reports unavailable here; its primary model being free does not establish that
background requests are free. Gemini remains disabled.

`isolation.py` creates detached Git worktrees outside the source checkout to
separate edits. **A Git worktree is not a security sandbox**; never run untrusted
code or an agent with normal host permissions on that basis. The OS sandbox probe
failed in this environment. `validation.py` checks syntax and exclusively stages
Python; it does not establish correctness or safety. Its caller must provide an
owned staging directory and ensure no concurrent filesystem modifications.
`metrics.py` preserves missing provider values as unknown. Recorded requests are
not a complete provider usage ledger after crashes or activity in other clients.

The Python `orchestrator.run_python_task` provides a single-attempt guarded path:
it moves a ready task to running, creates a detached worktree, reserves quota
through the adapter, records available usage and stages a new Python file for
review. It never executes or promotes output. The adapter's policy still needs a
verified zero-spend cap and the separate PR #8 helper; the path has only been
tested with mocks here. State, quota, metrics and filesystem actions do not share
one transaction. Interrupted or running tasks must be investigated manually,
not resubmitted under another ID. This interface is not exposed as a CLI run
command until these safeguards and a real secure test environment are available.

`python -m tools.agent_rotation report` prints recorded usage; unknown values
remain counted separately. `python -m tools.agent_rotation.benchmark` measures
local SQLite reservation overhead only, with simulated workers and zero API
calls. It does not measure coding success, model performance or token savings.

## Failure diagnostics and manual recovery

The adapter reports a fixed failure code and stage plus tri-state request,
response and model verification flags. A missing value is unknown; it is not
zero or proof that a request was not sent. Only validated numeric usage and
provider-reported cost are stored; prompts, generated text, response bodies,
HTTP messages and exception text are excluded from diagnostics. The failure
row and metric insert share one SQLite transaction; an existing metric is never
replaced. If storage itself fails, the task may remain `running` and diagnostics
may be incomplete: do not infer that no request was sent.

All post-reservation failures leave the task `interrupted`, retain the reservation
and block the provider. `PYTHON_SYNTAX_INVALID` with a received response is a
known completed response, whereas `REQUEST_TIMEOUT` leaves delivery unknown.
Neither is automatically retried. Static syntax checks do not execute code or
prove correctness. Git worktrees are not security sandboxes.

Before any separately authorised recovery, an operator must inspect task history,
reservation and diagnostic records, review the existing block and check provider
request/usage history and the account's zero-spend protection where available.
Reconcile incomplete or conflicting records manually; a timeout may have been
processed even if usage is not visible. If the state remains uncertain, keep the
provider blocked. Never delete a reservation or silently resubmit under a new ID.
Any decision to lift a block requires explicit authorisation and a separate,
reviewed action; this code has no automatic unblock or retry.

The integrated helper supplies fixed transport error codes. Older helpers without
structured codes fail closed as `INTERNAL_ADAPTER_ERROR`. The standalone helper
CLI cannot send requests; the rotation CLI's `preflight` is read-only. No raw response is retained, so this change cannot identify the cause of the
previous live failure retroactively.
