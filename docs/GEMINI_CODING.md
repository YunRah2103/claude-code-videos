# Gemini coding tasks

`tools/gemini_task.py` sends one coding task to the Gemini API and saves the generated
code. It is a one-shot helper, not an agent.

## Status

- Authentication: the protected Gemini API-key secret is attached by Claude Cloud's proxy
  to `generativelanguage.googleapis.com`. A model-list request returned HTTP 200 without any
  key sent by the tool.
- Free-tier eligibility: Google's pricing page (updated 2026-10-28) lists `gemini-2.5-flash`
  as free of charge for text input and output. Free-tier content may be used to improve
  Google's products, so do not send private or confidential code.
- Live generation: **one** request was made with `gemini-2.5-flash` and `--max-tokens 256`.
  It returned **HTTP 404**. The model metadata GET for the same model returned HTTP 200, so the
  failure is on the generation path. The cause is not yet diagnosed. Do not retry without
  separate authorisation.
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
