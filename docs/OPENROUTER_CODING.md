# Free OpenRouter coding tasks

`tools/openrouter_task.py` sends one coding task to OpenRouter, saves the generated
code, and reports status, finish reason and cost. It is a one-shot helper, not an agent.

## Rules

- Authentication comes from Claude Cloud's protected network secret. Never put a key
  in a command, file or environment variable.
- Only `:free` models (and `openrouter/free`) are accepted. Default: `cohere/north-mini-code:free`.
- `max_tokens` defaults to 8192 and cannot exceed it. Check `finish_reason == "stop"`.
- One request per run. Rate limits and errors are reported, never retried.
- Generated code goes under `out/` and stays out of production files until it has been
  reviewed and tested.

## Delegating a pixel-animation task

1. Write the task to `out/openrouter/tasks/<name>.txt`. Ask for complete Python code
   using only the standard library, with unittest tests in the same file.
2. Dry-run first (no request is sent):
   `python3 tools/openrouter_task.py --task out/openrouter/tasks/<name>.txt --output out/openrouter/<name>.py --dry-run`
3. Run once:
   `python3 tools/openrouter_task.py --task out/openrouter/tasks/<name>.txt --output out/openrouter/<name>.py`
4. Review the code, then run its tests in `out/openrouter/`:
   `cd out/openrouter && python3 -m unittest <name> -v`
5. Only after review and passing tests, copy the code into `videos/.../src/` or `tools/`
   in a separate, reviewed change.

If the reply has `finish_reason: length`, the code is truncated. Do not raise `--max-tokens`
without the user's approval, because each run is a separate request.

## Tests

`python3 -m unittest tests.test_openrouter_task -v` runs offline with a fake HTTP opener,
so it makes no API requests.
