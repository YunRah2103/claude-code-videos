"""Send one free-tier Gemini coding task and save the generated code.

Authentication comes from Claude Cloud's network proxy, which attaches the protected
Gemini API-key secret to requests for generativelanguage.googleapis.com. This tool
never reads, prints or stores a key and sends no x-goog-api-key header itself.

    python3 tools/gemini_task.py --task out/gemini/tasks/x.txt --output out/gemini/x.py
    python3 tools/gemini_task.py --task out/gemini/tasks/x.txt --output out/gemini/x.py --dry-run
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "out"
ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
DEFAULT_MODEL = "gemini-2.5-flash"
DEFAULT_MAX_TOKENS = 8192
TIMEOUT_SECONDS = 400
# Flash and Flash-Lite text models only. Pro, image, audio, TTS and "-latest"
# aliases can point at billable models, so they are rejected rather than guessed.
ALLOWED_MODEL = re.compile(r"^gemini-\d+(\.\d+)?-flash(-lite)?(-preview)?$")
FENCE = re.compile(r"```(?:python)?\n(.*?)```", re.S)


class TaskError(Exception):
    """A validation, request or reply problem to report to the caller."""


def is_allowed_model(model):
    return bool(ALLOWED_MODEL.match(model))


def build_payload(task, max_tokens=DEFAULT_MAX_TOKENS):
    if not 1 <= max_tokens <= DEFAULT_MAX_TOKENS:
        raise TaskError(f"max_tokens must be between 1 and {DEFAULT_MAX_TOKENS}")
    return {
        "contents": [{"role": "user", "parts": [{"text": task}]}],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }


def endpoint_for(model):
    return ENDPOINT.format(model=model)


def send(url, payload, opener=urllib.request.urlopen):
    """Send one request. Rate limits and errors are reported, never retried."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with opener(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read()
    except urllib.error.HTTPError as error:
        raise TaskError(describe_http_error(error)) from None
    except urllib.error.URLError as error:
        raise TaskError(f"network error: {error.reason}; not retrying") from None
    except TimeoutError:
        raise TaskError("request timed out; the server may still have processed it, so not retrying") from None
    try:
        return response.status, json.loads(body)
    except ValueError:
        raise TaskError(f"HTTP {response.status} with a non-JSON body") from None


def describe_http_error(error):
    """Classify an HTTP error by status and Google's status name only; never echo the body."""
    if error.code == 429:
        retry_after = error.headers.get("Retry-After", "unknown")
        return f"rate limited (HTTP 429, Retry-After={retry_after}); not retrying"
    if error.code in (401, 403):
        return f"authentication or permission failure (HTTP {error.code}); not retrying"
    if error.code == 404:
        return "not found (HTTP 404): model or endpoint unavailable to this project; not retrying"
    return f"HTTP {error.code} from Gemini API; not retrying"


def parse_reply(status, data):
    if status != 200 or "error" in data:
        error = data.get("error") or {}
        raise TaskError(f"API error (HTTP {status}): {str(error.get('status', ''))[:120]}")
    candidates = data.get("candidates") or []
    if not candidates:
        raise TaskError("reply has no candidates (the prompt may have been blocked)")
    candidate = candidates[0]
    finish_reason = candidate.get("finishReason")
    parts = (candidate.get("content") or {}).get("parts") or []
    content = "".join(part.get("text", "") for part in parts)
    if finish_reason != "STOP":
        raise TaskError(f"incomplete reply (finishReason={finish_reason!r}); the code may be truncated")
    if not content.strip():
        raise TaskError("reply content is empty")
    return {
        "model": data.get("modelVersion"),
        "finish_reason": finish_reason,
        "content": content,
        "usage": data.get("usageMetadata") or {},
    }


def extract_code(content):
    match = FENCE.search(content)
    code = (match.group(1) if match else content).strip()
    if not code:
        raise TaskError("no code found in reply")
    return code + "\n"


def check_output_path(path):
    """Keep generated code out of production files: only ROOT/out/ or paths outside the repo."""
    resolved = path.resolve()
    inside_repo = ROOT in resolved.parents
    if inside_repo and OUT_DIR not in resolved.parents:
        raise TaskError(f"output must be under {OUT_DIR} when inside the repository")


def main(argv=None, opener=urllib.request.urlopen):
    parser = argparse.ArgumentParser(description="Run one free-tier Gemini coding task.")
    parser.add_argument("--task", required=True, type=Path, help="text file with the coding task")
    parser.add_argument("--output", required=True, type=Path, help="file to write the generated code to")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--dry-run", action="store_true", help="print the request without sending it")
    args = parser.parse_args(argv)
    try:
        if not is_allowed_model(args.model):
            raise TaskError(f"model {args.model!r} is not an allowed free Flash model")
        check_output_path(args.output)
        payload = build_payload(args.task.read_text(), args.max_tokens)
        url = endpoint_for(args.model)
        if args.dry_run:
            print(json.dumps({"url": url, "body": payload}, indent=2))
            return 0
        status, data = send(url, payload, opener)
        reply = parse_reply(status, data)
        code = extract_code(reply["content"])
    except (TaskError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(code)
    usage = reply["usage"]
    print(
        f"HTTP 200 | model={reply['model']} | finishReason={reply['finish_reason']} | "
        f"prompt_tokens={usage.get('promptTokenCount')} | "
        f"output_tokens={usage.get('candidatesTokenCount')} | wrote {args.output}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
