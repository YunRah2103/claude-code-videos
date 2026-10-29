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
blocks the provider. The existing helper has a 400-second timeout and an
unbounded response read; harden those before unattended use. Kilo preflight
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
