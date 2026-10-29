# Integration review: OpenRouter and agent rotation

PR #8 is based on main and provides the OpenRouter helper. PR #10 is a draft on
main and imports that helper dynamically. PR #11 targets #10 and fixes SQLite
connection lifetime. PR #12 targets #11 and adds failure diagnostics. PR #8 is
not a Git ancestor of the other stack; an integrated test checkout must include
its files separately. Neither stack is merged by this review.

## Review findings

- PR #8's original standalone CLI can send without the rotation quota ledger or
  current account verification. The proposed helper hardening disables live CLI
  calls, caps response size and uses structured transport errors. It must be
  reviewed before that helper is used as an integration baseline.
- PR #12's original diagnostic tests defined a `fail` helper that overrode
  `unittest.TestCase.fail`, potentially suppressing assertion failures. The
  integration changes rename it and rerun the full suite. The adapter consumes
  the hardened helper's structured codes; older helpers fail closed.
- #10 remains a draft: the provider policy is an operator attestation, Kilo is
  unavailable here, and there is no proven OS sandbox or production-ready CLI
  run command. Git worktrees are not a security boundary.
- #11 closes SQLite connections and rolls back on failure; it depends on #10.
  Failure diagnostics and metrics retain a single record per task, but state,
  reservations and external requests do not share one atomic transaction.
  Interrupted operations need manual review; no automatic resend is safe.

No PR is unconditionally ready to merge into main as a complete free-agent
system. The SQLite fix is reviewable after its base; the helper and diagnostics
need their focused follow-up changes reviewed and integrated. Review and retarget
stacked branches after their bases change, then rerun the full suite on the
resulting exact merge candidates. A clean merge does not establish free billing
or live agent readiness.

## Offline checks and supervised path

Run `python -X dev -W error::ResourceWarning -m unittest discover -s tests -q`
on the combined checkout. Tests use fake provider openers and do not execute
generated code. `python -m tools.agent_rotation --state PATH preflight --id ID`
is an inspection-only, read-only command. It does not print the task goal,
change the provider block or send a request; missing state fails rather than
creating a database. A real supervised CLI would need a current account-level
zero-spend check, a human-reviewed task, an explicit per-attempt approval,
verified allowlist, durable reservation, a protected provider connection and
an isolated test sandbox. None are inferred from this offline preflight.

The provider block and original task history belong to the existing execution
state. Integration tests use temporary SQLite databases and do not modify them.
Gemini remains disabled. A 30-second socket timeout is not a total request
wall-clock deadline. See `OPENROUTER_CODING.md` for the response cap and limits.
