"""Send one free-model coding task to OpenRouter and save the generated code.

Authentication comes from Claude Cloud's network proxy, which attaches the
protected OpenRouter secret to requests for openrouter.ai. This tool never reads,
prints or stores an API key and sends no Authorization header itself.

    python3 tools/openrouter_task.py --task out/openrouter/tasks/x.txt --output out/openrouter/x.py
    python3 tools/openrouter_task.py --task out/openrouter/tasks/x.txt --output out/openrouter/x.py --dry-run
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
ENDPOINT = "https://openrouter.ai/api/v1/chat/completions"
DEFAULT_MODEL = "cohere/north-mini-code:free"
DEFAULT_MAX_TOKENS = 8192
TIMEOUT_SECONDS = 30
MAX_RESPONSE_BYTES = 1024 * 1024
FENCE = re.compile(r"```(?:python)?\n(.*?)```", re.S)


class TaskError(Exception):
    """A validation, request or reply problem to report to the caller."""
    def __init__(self, message, *, code='VALIDATION_ERROR', response_received=None):
        super().__init__(message)
        self.code = code
        self.response_received = response_received


def is_free_model(model):
    return model == "openrouter/free" or model.endswith(":free")


def build_payload(task, model=DEFAULT_MODEL, max_tokens=DEFAULT_MAX_TOKENS):
    if not is_free_model(model):
        raise TaskError(f"refusing non-free model {model!r}; only ':free' models are allowed")
    if not 1 <= max_tokens <= DEFAULT_MAX_TOKENS:
        raise TaskError(f"max_tokens must be between 1 and {DEFAULT_MAX_TOKENS}")
    return {
        "model": model,
        "messages": [{"role": "user", "content": task}],
        "max_tokens": max_tokens,
        "stream": False,
    }


def send(payload, opener=urllib.request.urlopen):
    """Send one request. Rate limits and errors are reported, never retried."""
    request = urllib.request.Request(
        ENDPOINT,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with opener(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
            if len(body) > MAX_RESPONSE_BYTES:
                raise TaskError('response exceeds size limit', code='RESPONSE_TOO_LARGE', response_received=True)
    except urllib.error.HTTPError as error:
        raise TaskError(describe_http_error(error), code='HTTP_FAILURE', response_received=True) from None
    except urllib.error.URLError as error:
        if isinstance(error.reason, TimeoutError):
            raise TaskError('request timed out; delivery is unknown', code='REQUEST_TIMEOUT') from None
        raise TaskError('network error; delivery is unknown', code='NETWORK_FAILURE') from None
    except TimeoutError:
        raise TaskError("request timed out; the server may still have processed it, so not retrying", code='REQUEST_TIMEOUT') from None
    try:
        return response.status, json.loads(body)
    except ValueError:
        raise TaskError(f"HTTP {response.status} with a non-JSON body", code='RESPONSE_DECODING_FAILED', response_received=True) from None


KEY_ENDPOINT = "https://openrouter.ai/api/v1/key"
MODELS_ENDPOINT = "https://openrouter.ai/api/v1/models"


def read_only_json(url, opener=urllib.request.urlopen):
    """GET a metadata endpoint. Never generates text and never retries."""
    request = urllib.request.Request(url, headers={"Accept": "application/json"}, method="GET")
    try:
        with opener(request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read(MAX_RESPONSE_BYTES + 1)
    except urllib.error.HTTPError as error:
        raise TaskError(describe_http_error(error), code='HTTP_FAILURE', response_received=True) from None
    except (urllib.error.URLError, TimeoutError, OSError):
        raise TaskError('metadata request failed; not retrying', code='NETWORK_FAILURE') from None
    if len(body) > MAX_RESPONSE_BYTES:
        raise TaskError('metadata response exceeds size limit', code='RESPONSE_TOO_LARGE', response_received=True)
    try:
        return json.loads(body)
    except ValueError:
        raise TaskError('metadata response was not JSON', code='RESPONSE_DECODING_FAILED', response_received=True) from None


def account_spend_status(opener=urllib.request.urlopen):
    """Return only the spending-protection fields from the key-info endpoint."""
    data = read_only_json(KEY_ENDPOINT, opener).get("data")
    if not isinstance(data, dict):
        raise TaskError('key-info response had no data object', code='INVALID_PROVIDER_RESPONSE', response_received=True)
    return {
        "zero_spend_verified": data.get("limit") == 0 and data.get("limit_remaining") == 0,
        "is_free_tier": data.get("is_free_tier") is True,
        "management_or_provisioning": data.get("is_management_key") is True or data.get("is_provisioning_key") is True,
    }


def model_is_listed_free(model, opener=urllib.request.urlopen):
    """True only if the model is listed with zero prompt and completion prices."""
    entries = read_only_json(MODELS_ENDPOINT, opener).get("data")
    if not isinstance(entries, list):
        raise TaskError('model list had no data array', code='INVALID_PROVIDER_RESPONSE', response_received=True)
    for entry in entries:
        if isinstance(entry, dict) and entry.get("id") == model:
            pricing = entry.get("pricing") or {}
            return str(pricing.get("prompt")) == "0" and str(pricing.get("completion")) == "0"
    return False


def describe_http_error(error):
    """Classify an HTTP error by status only; never echo the body."""
    if error.code == 429:
        return "rate limited (HTTP 429); not retrying"
    if error.code in (401, 403):
        return f"authentication or permission failure (HTTP {error.code}); not retrying"
    return f"HTTP {error.code} from OpenRouter; not retrying"


def parse_reply(status, data):
    if status != 200 or "error" in data:
        raise TaskError(f"API error (HTTP {status})")
    choices = data.get("choices") or []
    if not choices:
        raise TaskError("reply has no choices")
    choice = choices[0]
    finish_reason = choice.get("finish_reason")
    content = (choice.get("message") or {}).get("content") or ""
    if finish_reason != "stop":
        raise TaskError(f"incomplete reply (finish_reason={finish_reason!r}); the code may be truncated")
    if not content.strip():
        raise TaskError("reply content is empty")
    return {
        "model": data.get("model"),
        "finish_reason": finish_reason,
        "content": content,
        "usage": data.get("usage") or {},
    }


def extract_code(content):
    match = FENCE.search(content)
    return (match.group(1) if match else content).strip() + "\n"


def check_output_path(path):
    """Keep generated code out of production files: only ROOT/out/ or paths outside the repo."""
    resolved = path.resolve()
    inside_repo = ROOT in resolved.parents
    if inside_repo and OUT_DIR not in resolved.parents:
        raise TaskError(f"output must be under {OUT_DIR} when inside the repository")


def main(argv=None, opener=urllib.request.urlopen):
    parser = argparse.ArgumentParser(description="Run one free OpenRouter coding task.")
    parser.add_argument("--task", required=True, type=Path, help="text file with the coding task")
    parser.add_argument("--output", required=True, type=Path, help="file to write the generated code to")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--dry-run", action="store_true", help="print the request without sending it")
    args = parser.parse_args(argv)
    try:
        check_output_path(args.output)
        payload = build_payload(args.task.read_text(), args.model, args.max_tokens)
        if args.dry_run:
            safe_payload = dict(payload)
            safe_payload['messages'] = [{'role': 'user', 'content': '[REDACTED]'}]
            print(json.dumps(safe_payload, indent=2))
            return 0
        raise TaskError('standalone live requests disabled; use the reviewed rotation workflow')
    except (TaskError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
