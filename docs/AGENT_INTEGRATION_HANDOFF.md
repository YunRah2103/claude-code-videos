# Agent integration handoff (for Codex)

Status labels: VERIFIED AUTOMATIC · VERIFIED SUPERVISED · MANUAL HANDOFF · OFFLINE TESTED ONLY · AUTHENTICATED BUT UNTESTED · BLOCKED · UNAVAILABLE

## Providers

| Provider | Status | Evidence | Command |
|---|---|---|---|
| OpenRouter `cohere/north-mini-code:free` | VERIFIED SUPERVISED | One live free request returned 200, `finish_reason: stop`, cost 0. Code passed tests. | `python3 tools/openrouter_task.py --task T --output out/openrouter/X.py` |
| Gemini `gemini-2.5-flash` (direct API) | AUTHENTICATED BUT UNTESTED | Model list 200. One live generation returned 404 (not diagnosed). | `python3 tools/gemini_task.py --task T --output out/gemini/X.py --max-tokens 256` |
| Gemini CLI 0.66.0 | BLOCKED | Google-account login needs a manual code paste. | none |

Gemini's free tier is stated on Google's pricing page (2026-10-28) for `gemini-2.5-flash`. Free-tier content may be used to improve Google products.

## Other agents

| Agent | Status | Notes |
|---|---|---|
| Codex 0.165.0 | VERIFIED SUPERVISED | ChatGPT login; one-shot coding task created a file and passed a test. |
| Kilo Code 7.8.18 | VERIFIED SUPERVISED | `kilo/kilo-auto/free` answered and edited a test file. |
| Kiro CLI 2.35.1 | MANUAL HANDOFF | Free Builder ID login. Writes need per-action approval. |
| OpenCode 1.19.5 / 2.2.0 | BLOCKED | Free quota exhausted for Big Pickle and beam-free. |
| Copilot CLI 1.0.105 | BLOCKED | Device-code login rejected: "Unsupported Media Type". |
| Autohand 0.9.9 | BLOCKED | Classifier denied the run; model did not respond. |
| Pi 0.73.1 | BLOCKED | Classifier denied the run. |
| Mistral Vibe 3.0.3 | MANUAL HANDOFF | Sign-in needs an interactive terminal. |
| Clixad 0.0.1-beta.40 | BLOCKED | Requires age and terms confirmation; free credits depend on offers. |
| Antigravity agy 1.4.9 | BLOCKED | Installed; not authenticated. |

## Branches and PRs

- `ccr-82d3dced-0l557o`: holds the OpenRouter utility (`945aeb7`) with unrelated changes. **Not merged.**
- `gemini-coding-utility` → PR #7: Gemini utility, tests, docs and this handoff.

## Provider interface (for the rotation adapter)

Each provider utility exposes: `--task FILE`, `--output PATH` (under `out/`), `--model`, `--max-tokens`, `--dry-run`.

- **Model policy:** allowlist in code. No automatic fallback to billable models.
- **Retries:** none. One request per run.
- **Errors:** rate limit (429), auth/permission (401/403), not found (404), timeout (may have been processed, do not repeat), truncated reply (`length`/`MAX_TOKENS`), empty or non-JSON reply.
- **Output:** code written only under `out/`; reviewed and tested before production.
- **Credentials:** protected Claude Cloud Network Secrets. Never passed as arguments or stored.

## Security requirements

- No keys in commands, files or chat. Respect classifier denials. Do not change auto-mode.
- Generated code is untrusted; it is never executed without review.
- No billing changes or paid models without explicit approval.

## Remaining blockers

1. Gemini generation returns 404. Diagnosis needs a separate authorised request.
2. The OpenRouter utility needs merging from `ccr-82d3dced-0l557o` into a clean branch.
3. No orchestrator exists yet. Codex should build it on the interface above.
