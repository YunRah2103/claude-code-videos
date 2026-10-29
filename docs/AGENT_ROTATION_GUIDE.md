# Free-agent rotation: user guide

The rotation CLI helps you delegate one small coding task at a time to a verified free model,
then review the result yourself. It is **supervised**: nothing is sent automatically, and
generated code is never executed.

Commands below were run against this repository. Commands that send a model request are marked **LIVE**.

## Quick start: Claude Code Cloud (bash)

```bash
python3 -m tools.agent_rotation status
python3 -m tools.agent_rotation providers
python3 -m tools.agent_rotation templates
```

Create a task from a file (keeps task text out of shell history):

```bash
cat > /tmp/wheel-goal.txt <<'EOF'
Write a function calculating wheel rotation from car travel distance and wheel radius.
EOF
python3 -m tools.agent_rotation create --id wheel-1 --goal-file /tmp/wheel-goal.txt --file wheel_rotation.py
python3 -m tools.agent_rotation preflight --id wheel-1 --online
```

`--online` makes only read-only account and price checks. It sends no generation request.

## Quick start: Windows PowerShell

```powershell
cd C:\path\to\claude-code-videos
python -m tools.agent_rotation status
python -m tools.agent_rotation providers
Set-Content -Path $env:TEMP\wheel-goal.txt -Value "Write a function calculating wheel rotation from car travel distance and wheel radius."
python -m tools.agent_rotation create --id wheel-1 --goal-file $env:TEMP\wheel-goal.txt --file wheel_rotation.py
python -m tools.agent_rotation preflight --id wheel-1 --online
```

## Commands

| Command | Sends a request? | Purpose |
|---|---|---|
| `status` | No | Providers, state, and safety settings |
| `providers` | No | Each provider's status and why |
| `templates` | No | Coding-task templates |
| `create --id ID --goal-file F --file out.py` | No | Register a ready task (also `--template NAME`, `--context FILE`) |
| `preflight --id ID [--online]` | No (**read-only**) | Readiness checks; `--online` reads account and price |
| `run --id ID` | **LIVE**, once | Requires all checks, then typed approval |
| `review --id ID [--approve\|--reject]` | No | Inspect staged code; decide |
| `history [--id ID]` | No | Task events, outcome, failure code, tokens |
| `report` | No | Provider-reported tokens and cost |
| `show --id ID` | No | Task details (goal text is never printed) |

Exit codes: `0` success, `1` a run stopped after a request was attempted, `2` input or state problem, `3` refused, no request sent.

## Authorising one live request

`run` sends at most one request, and only when all of these hold:

1. The model is on the allowlist (`cohere/north-mini-code:free`) and is `:free`.
2. The task is `ready`, has one safe `.py` output, and has never been attempted.
3. The provider is not blocked.
4. The daily quota (1 request per 24 hours) is free.
5. `preflight --online` shows the spend cap is zero and the price is zero **at that moment**.
6. You type `APPROVE ONE LIVE REQUEST <task-id>` at an interactive terminal when prompted.

```bash
python3 -m tools.agent_rotation run --id wheel-1
```

Approval must be typed at an interactive terminal. `run` refuses piped or redirected input, and sends nothing in that case.

If a run fails, it is **not retried**. Read `history --id wheel-1` and do not repeat the run without a new decision.

## Reviewing generated code

```bash
python3 -m tools.agent_rotation review --id wheel-1
python3 -m tools.agent_rotation review --id wheel-1 --approve
```

`review` prints the staged file path, a syntax result, static findings (risky imports or calls),
and the first 200 lines. Execution is disabled. Read the code yourself. Approving only marks the
task complete. Approval is refused if the staged file is missing, changed since staging, or not valid Python. It does not copy the file into the repository. Do that manually after review.

## Usage and cost

```bash
python3 -m tools.agent_rotation report
```

An **unknown** value means the provider did not report it. It is not zero.

## Provider blocks

A block means an earlier attempt could not be verified as safe. The CLI has **no unblock command**.
Clearing a block is a human decision. Record why before any change, and never create a new task ID to
get around a block.

## Disabled features

- Generated-code execution: no verified sandbox.
- Gemini: live generation returned HTTP 404 and 502. Disabled.
- Kilo: installed or not, its billing and model eligibility are unverified. Disabled.
- Unattended routing: off. Every live request needs a person.
- Claude as a worker: review only.

## Token use

- Use templates and `--context` files to keep prompts small. `--context` is limited to 8000 bytes.
- The goal is limited to 16000 bytes. Split larger tasks.
- Token savings have **not been measured** yet. No savings figure is claimed.
