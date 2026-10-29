# Agent integration handoff (for Codex)

Status key: **Verified** = tested here. **Planned** = not tested. **Blocked** = needs a human step.

## Gemini

- **Verified:** Claude Cloud's proxy attaches the protected Gemini API-key secret to
  `generativelanguage.googleapis.com`. `GET /v1beta/models` returned HTTP 200 with no key
  sent by us. The list includes 46 `generateContent` models.
- **Verified (offline):** `tools/gemini_task.py` passes 20 unit tests, with model allowlisting,
  no key header, finishReason checks and output-path rules.
- **Not verified:** Live generation. Free-tier eligibility and billing status cannot be
  confirmed from the API, so no inference request was made.
- **Blocked:** Gemini CLI 0.66.0 is installed at an isolated scratch prefix but unauthenticated.
  Google-account OAuth failed with exit 41 because its code paste-back needs a manual step.
  The API-key route is not wired into the CLI.
- **Usable command (after billing is confirmed):**
  `python3 tools/gemini_task.py --task <file> --output out/gemini/<name>.py`

## OpenRouter

- **Verified:** Free model `cohere/north-mini-code:free` returned HTTP 200, `finish_reason: stop`
  and cost 0 for a one-shot coding task, and the output tests passed.
- **Usable:** `tools/openrouter_task.py`, on branch `ccr-82d3dced-0l557o` (commit `945aeb7`).
  **Not merged to main.** That branch also contains unrelated changes, so merge carefully.

## Other agents

| Agent | Status | Notes |
|---|---|---|
| OpenCode 1.19.5 | Installed, blocked | Big Pickle and beam-free returned "Free usage limit reached". |
| Kilo Code 7.8.18 | Verified | `kilo/kilo-auto/free` answered and edited a test file. |
| Codex 0.165.0 | Verified | ChatGPT login; one-shot coding task created and ran a test. |
| Kiro CLI 2.35.1 | Partial | Free Builder ID login. Writes need per-action approval; run was not unattended. |
| Copilot CLI 1.0.105 | Blocked | Device-code login fails with "Unsupported Media Type". |
| Autohand 0.9.9 | Blocked | Classifier denied the run; model did not respond. Do not retry. |
| Pi 0.73.1 | Blocked | Classifier denied the run. |
| Mistral Vibe 3.0.3 | Blocked | Needs an interactive terminal for sign-in. |
| Kiro/Antigravity/Clixad | Blocked | Clixad needs age and terms confirmation and offer-based credits. |

## Security requirements

- Never put keys in commands, files or chat. Use Claude Cloud's protected Network Secrets.
- Respect classifier denials. Do not bypass them or change auto-mode.
- Generated code goes under `out/` and is reviewed and tested before production.
- No billing or paid models without explicit approval.

## Known free-tier restrictions

- Gemini: Free tier applies to Flash-family text models per project. Limits and model lists change;
  confirm in AI Studio, since third-party sources disagree.
- OpenRouter: `:free` models only. The key had a $0 spending cap.

## Recommended interface for Codex

- One entry point per provider, each taking `--task`, `--output`, `--model`, `--dry-run`.
- Models allowlisted in code; no automatic fallback to billable models.
- One request per run, no retries; rate limits are reported, not retried.
- Offline unit tests with a fake opener, so routine tests make no API calls.
- Output only under `out/`; promote code into production only after human review.
