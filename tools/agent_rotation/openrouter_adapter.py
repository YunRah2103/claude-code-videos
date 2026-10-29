"""Fail-closed adapter for the separately maintained PR #8 OpenRouter helper.

No credentials are accessed. This module never retries and never writes generated
code. A caller must separately verify the account's zero-spend cap immediately
before use; the flag is an operator attestation, not an API-based billing check.
"""
import ast
from dataclasses import dataclass
import importlib
import math
from typing import Any


class AdapterError(Exception):
    """Concise failure, with no prompt, response or secret values."""


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


def execute(task: str, task_id: str, policy: Policy, worker, ledger, *, now: float, helper=None) -> Result:
    """Make at most one request after safety gates and an atomic quota reservation.

    Reservations remain consumed on errors or timeouts. Generated Python is
    syntax checked, but must still be tested in an isolated execution environment
    and reviewed before promotion. Context and task content may leave the system.
    """
    if (policy.enabled is not True or policy.zero_spend_account_verified is not True
        or worker.name != 'openrouter' or 'code' not in worker.capabilities or not isinstance(policy.model, str)
        or not policy.model.endswith(':free') or policy.model not in policy.allowed_models
        or not isinstance(policy.max_tokens, int) or isinstance(policy.max_tokens, bool)
        or not 1 <= policy.max_tokens <= 2048
        or not isinstance(task, str) or not task.strip() or len(task.encode('utf-8')) > 32000):
        raise AdapterError('OpenRouter unavailable: safety policy or task validation failed')
    if helper is None:
        try:
            helper = importlib.import_module('tools.openrouter_task')
        except ImportError:
            raise AdapterError('OpenRouter unavailable: PR #8 helper is not installed') from None
    try:
        payload = helper.build_payload(task, policy.model, policy.max_tokens)
    except Exception:
        raise AdapterError('OpenRouter request validation failed') from None
    if not ledger.reserve(worker, task_id, now):
        raise AdapterError('OpenRouter unavailable: quota, block or duplicate task')
    try:
        status, data = helper.send(payload)
        reply = helper.parse_reply(status, data)
    except Exception:
        # Preserve reservation and block: outcome could be unknown after timeout.
        ledger.block(worker.name, 'request failed; manual investigation required')
        raise AdapterError('OpenRouter request failed or returned incomplete output; provider blocked') from None
    if not isinstance(reply, dict) or reply.get('finish_reason') != 'stop' or reply.get('model') != policy.model:
        ledger.block(worker.name, 'unexpected response model or incomplete response')
        raise AdapterError('OpenRouter response failed model or completion validation')
    raw_usage = reply.get('usage') if isinstance(reply.get('usage'), dict) else {}
    cost = raw_usage.get('cost')
    if cost is not None and (isinstance(cost, bool) or not isinstance(cost, (float, int)) or not math.isfinite(cost) or cost != 0):
        ledger.block(worker.name, 'unexpected reported cost')
        raise AdapterError('OpenRouter reported unexpected cost; provider blocked')
    try:
        code = helper.extract_code(reply.get('content', ''))
        if not isinstance(code, str) or not code.strip() or len(code.encode('utf-8')) > 100000:
            raise ValueError('invalid code')
        ast.parse(code)
    except Exception:
        raise AdapterError('Generated code failed syntax validation; not accepted') from None
    usage = {}
    for name in ('prompt_tokens', 'completion_tokens', 'total_tokens', 'reasoning_tokens'):
        value = raw_usage.get(name)
        usage[name] = value if isinstance(value, int) and not isinstance(value, bool) and value >= 0 else None
    usage['cost'] = cost
    usage['requests'] = 1
    return Result(code=code, model=policy.model, usage=usage)
