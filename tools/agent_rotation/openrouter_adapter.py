"""Guarded PR #8 adapter with safe, structured failure metadata."""
import ast
from dataclasses import dataclass
import importlib
import json
import math
import socket
import urllib.error
from typing import Any

FIELDS = ('prompt_tokens', 'completion_tokens', 'total_tokens', 'reasoning_tokens', 'cost')
FAILURE_CODES = frozenset({'HTTP_FAILURE', 'NETWORK_FAILURE', 'REQUEST_TIMEOUT', 'RESPONSE_DECODING_FAILED',
    'INVALID_PROVIDER_RESPONSE', 'UNEXPECTED_MODEL', 'INCOMPLETE_GENERATION', 'EMPTY_GENERATED_CONTENT',
    'PYTHON_SYNTAX_INVALID', 'OUTPUT_STAGING_FAILED', 'INTERNAL_ADAPTER_ERROR', 'UNEXPECTED_COST', 'RESPONSE_TOO_LARGE',
    'SAFETY_POLICY_REJECTED', 'HELPER_UNAVAILABLE', 'REQUEST_VALIDATION_FAILED', 'QUOTA_OR_DUPLICATE'})


def safe_usage(raw):
    raw = raw if isinstance(raw, dict) else {}
    result = {}
    for key in FIELDS[:-1]:
        value = raw.get(key)
        if key == 'reasoning_tokens' and value is None and isinstance(raw.get('completion_tokens_details'), dict):
            value = raw['completion_tokens_details'].get('reasoning_tokens')
        result[key] = value if type(value) is int and 0 <= value <= 2**63 - 1 else None
    cost = raw.get('cost')
    try:
        result['cost'] = cost if type(cost) in (int, float) and math.isfinite(cost) and cost >= 0 else None
    except OverflowError:
        result['cost'] = None
    return result


class AdapterError(Exception):
    """Only fixed codes and sanitised numerical metadata leave the adapter."""
    def __init__(self, failure_code, *, stage='preflight', request_sent=False,
                 response_received=False, model_verified=None, finish_reason_status='unknown', usage=None):
        failure_code = failure_code if failure_code in FAILURE_CODES else 'INTERNAL_ADAPTER_ERROR'
        super().__init__(failure_code)
        self.failure_code = failure_code
        self.failure_stage = stage if stage in {'preflight', 'transport', 'response', 'syntax', 'staging', 'internal'} else 'internal'
        self.request_sent = request_sent if type(request_sent) is bool else None
        self.response_received = response_received if type(response_received) is bool else None
        self.model_verified = model_verified if type(model_verified) is bool else None
        self.finish_reason_status = finish_reason_status if finish_reason_status in {'unknown', 'complete', 'incomplete'} else 'unknown'
        self.usage = safe_usage(usage)
        self.usage_available = any(value is not None for value in self.usage.values())


@dataclass(frozen=True)
class Policy:
    enabled: bool = False
    zero_spend_account_verified: bool = False
    allowed_models: tuple[str, ...] = ()
    model: str = ''
    max_tokens: int = 128


@dataclass(frozen=True)
class Result:
    code: str
    model: str
    usage: dict[str, Any]


def _execute(task: str, task_id: str, policy: Policy, worker, ledger, *, now: float, helper=None) -> Result:
    if (policy.enabled is not True or policy.zero_spend_account_verified is not True
        or worker.name != 'openrouter' or 'code' not in worker.capabilities or not isinstance(policy.model, str)
        or not policy.model.endswith(':free') or policy.model not in policy.allowed_models
        or not isinstance(policy.max_tokens, int) or isinstance(policy.max_tokens, bool)
        or not 1 <= policy.max_tokens <= 2048
        or not isinstance(task, str) or not task.strip() or len(task.encode('utf-8')) > 32000):
        raise AdapterError('SAFETY_POLICY_REJECTED')
    if helper is None:
        try:
            helper = importlib.import_module('tools.openrouter_task')
        except ImportError:
            raise AdapterError('HELPER_UNAVAILABLE') from None
    payload_invalid = False
    try:
        payload = helper.build_payload(task, policy.model, policy.max_tokens)
    except Exception:
        payload_invalid = True
    if payload_invalid:
        raise AdapterError('REQUEST_VALIDATION_FAILED')
    if not ledger.reserve(worker, task_id, now):
        raise AdapterError('QUOTA_OR_DUPLICATE')
    transport_failure = None
    try:
        status, data = helper.send(payload)
    except Exception as exc:
        ledger.block(worker.name, 'request failed; manual investigation required')
        # Trust only fixed structured codes, never parse exception messages.
        structured = getattr(exc, 'code', None)
        transport_codes = {'REQUEST_TIMEOUT', 'RESPONSE_DECODING_FAILED', 'HTTP_FAILURE', 'NETWORK_FAILURE', 'RESPONSE_TOO_LARGE'}
        if structured in transport_codes:
            code = structured
        elif isinstance(exc, (TimeoutError, socket.timeout)) or (isinstance(exc, urllib.error.URLError) and isinstance(exc.reason, (TimeoutError, socket.timeout))):
            code = 'REQUEST_TIMEOUT'
        elif isinstance(exc, (json.JSONDecodeError, UnicodeDecodeError)):
            code = 'RESPONSE_DECODING_FAILED'
        elif isinstance(exc, urllib.error.HTTPError):
            code = 'HTTP_FAILURE'
        elif isinstance(exc, (urllib.error.URLError, ConnectionError, OSError)):
            code = 'NETWORK_FAILURE'
        else:
            code = 'INTERNAL_ADAPTER_ERROR'
        received = True if code in {'HTTP_FAILURE', 'RESPONSE_DECODING_FAILED', 'RESPONSE_TOO_LARGE'} else None
        transport_failure = AdapterError(code, stage='transport', request_sent=True if received else None, response_received=received)
    if transport_failure:
        raise transport_failure

    usage = safe_usage(data.get('usage') if isinstance(data, dict) else None)
    raw_usage = data.get('usage') if isinstance(data, dict) and isinstance(data.get('usage'), dict) else {}
    meta = dict(stage='response', request_sent=True, response_received=True, usage=usage)
    def reject(code, **more):
        ledger.block(worker.name, 'response rejected; manual investigation required')
        raise AdapterError(code, **(meta | more)) from None
    if not isinstance(data, dict) or status != 200 or data.get('error'):
        reject('HTTP_FAILURE' if status != 200 else 'INVALID_PROVIDER_RESPONSE')
    if raw_usage.get('cost') is not None and usage['cost'] is None:
        reject('INVALID_PROVIDER_RESPONSE')
    # Examine envelope before PR #8 parse_reply so metadata survives its errors.
    model = data.get('model')
    choices = data.get('choices')
    if choices is not None:
        if not isinstance(choices, list) or not choices or not isinstance(choices[0], dict):
            reject('INVALID_PROVIDER_RESPONSE')
        finish = choices[0].get('finish_reason')
        message = choices[0].get('message')
        content = message.get('content') if isinstance(message, dict) else None
    else:  # Adapter-compatible test helpers may already return a parsed envelope.
        finish = data.get('finish_reason')
        content = data.get('content')
    if not isinstance(model, str):
        reject('INVALID_PROVIDER_RESPONSE')
    verified = model == policy.model
    if not verified:
        reject('UNEXPECTED_MODEL', model_verified=False)
    meta['model_verified'] = True
    meta['finish_reason_status'] = 'complete' if finish == 'stop' else ('incomplete' if isinstance(finish, str) else 'unknown')
    if finish != 'stop':
        reject('INCOMPLETE_GENERATION')
    if not isinstance(content, str) or not content.strip():
        reject('EMPTY_GENERATED_CONTENT')
    if usage['cost'] is not None and usage['cost'] != 0:
        reject('UNEXPECTED_COST')
    invalid_reply = False
    try:
        reply = helper.parse_reply(status, data)
        code = helper.extract_code(reply.get('content', ''))
    except Exception:
        invalid_reply = True
    if invalid_reply:
        reject('INVALID_PROVIDER_RESPONSE')
    if not isinstance(code, str) or not code.strip():
        reject('EMPTY_GENERATED_CONTENT')
    try:
        size = len(code.encode('utf-8'))
    except UnicodeError:
        size = 100001
    if size > 100000:
        reject('INVALID_PROVIDER_RESPONSE')
    invalid_syntax = False
    try:
        ast.parse(code)
    except (SyntaxError, ValueError, TypeError):
        invalid_syntax = True
    if invalid_syntax:
        reject('PYTHON_SYNTAX_INVALID', stage='syntax')
    usage['requests'] = 1
    return Result(code=code, model=policy.model, usage=usage)


def execute(task: str, task_id: str, policy: Policy, worker, ledger, *, now: float, helper=None) -> Result:
    """Re-raise only a fresh safe error, without a provider response traceback."""
    failure = None
    try:
        return _execute(task, task_id, policy, worker, ledger, now=now, helper=helper)
    except AdapterError as exc:
        failure = AdapterError(exc.failure_code, stage=exc.failure_stage, request_sent=exc.request_sent,
                               response_received=exc.response_received, model_verified=exc.model_verified,
                               finish_reason_status=exc.finish_reason_status, usage=exc.usage)
    except Exception:
        try:
            ledger.block(worker.name, 'internal error; manual investigation required')
        except Exception:
            pass
        failure = AdapterError('INTERNAL_ADAPTER_ERROR', stage='internal', request_sent=None,
                               response_received=None)
    raise failure
