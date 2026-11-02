# Gemini coding tasks

`tools/gemini_task.py` sends one coding task to the Gemini API and saves the generated
code. It is a one-shot helper, not an agent.

## Status

- Authentication: the protected Gemini API-key secret is attached by Claude Cloud's proxy
  to `generativelanguage.googleapis.com`. A model-list request returned HTTP 200 without any
  key sent by the tool.
- Default model: `gemini-3.8-flash`. Google's pricing page (updated 2026-10-28) lists it as
  free of charge for text input and output. Its metadata reports `generateContent` support.
  Free-tier content may be used to improve Google's products, so do not send private code.
- Why 2.5 failed: one earlier request to `gemini-2.5-flash` returned **HTTP 404**. Google's
  models page says it is limiting 2.5 models to users who used them in the past, and that new
  projects should use 3.8 Flash or 3.5 Flash-Lite. This likely explains the 404, though the
  docs don't confirm it for this project. Do not retry 2.5.
- Live generation with `gemini-3.8-flash`: **one** authorised request, `--max-tokens 256`.
  It returned **HTTP 502** (upstream or gateway error). Not retried. No code was generated.
  Any further request needs separate authorisation.
- Unattended routing: **disabled** (`ROUTING_ENABLED = False`) until one authorised live
  generation is verified.
- Status: **AUTHENTICATED BUT UNTESTED** for generation.
- The Google-account (OAuth) login is not used; it failed and needs a manual code paste.

## Rules

- Only Flash text models are accepted: `gemini-<version>-flash`, `-flash-lite` or `-preview`.
  Pro, image, audio, TTS, Gemma and `-latest` aliases are refused.
- No key is read, printed or stored by the tool. No `x-goog-api-key` header is sent.
- `maxOutputTokens` defaults to 8192 and cannot exceed it. Only `finishReason: STOP` is accepted.
- One request per run. Rate limits and errors are reported, never retried.
- Generated code goes under `out/gemini/` and is reviewed and tested before entering production.

## Usage

1. Write the task to `out/gemini/tasks/<name>.txt`.
2. Dry-run first (no request is sent):
   `python3 tools/gemini_task.py --task out/gemini/tasks/<name>.txt --output out/gemini/<name>.py --dry-run`
3. Run once, only after confirming the project has no billing enabled:
   `python3 tools/gemini_task.py --task out/gemini/tasks/<name>.txt --output out/gemini/<name>.py`
4. Review the code, then run its tests from `out/gemini/`.

## Tests

`python3 -m unittest tests.test_gemini_task -v` runs offline and makes no API requests.
