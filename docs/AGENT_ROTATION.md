# Agent rotation: offline foundation

```bash
python -m tools.agent_rotation status
python -m tools.agent_rotation plan --task 'Implement a wheel helper'
python -m unittest discover -s tests -v
```

This is a foundation, not an agent launcher. Every default provider is disabled;
no model requests are made and plan does not persist tasks. Historical access
and free usage are not proof of current availability or account billing status.
The CLI does not currently offer enabling a provider.

`core.py` contains a capability registry and SQLite reservation ledger. A
reservation is atomic across processes, survives restarts, applies a rolling
request count and prevents repeated task IDs. A block stops selection until a
future explicit recovery mechanism is built. Never remove a reservation merely
because a request timed out: it may have reached the provider. Selection alone
is advisory; any future executor must reserve atomically before a request and
must fail closed. The ledger only records local reservations, not provider-side
usage, daily/monthly credit limits, or other clients' requests. Keep state under
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
