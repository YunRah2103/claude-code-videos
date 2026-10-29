"""Single-attempt staging; Git worktrees isolate edits, not hostile code.

Generated code is parsed and staged, never executed or promoted. Network access
remains disabled unless policy, account attestation, quota and helper permit it.
Running/uncertain tasks are never automatically retried after interruption.
"""
import importlib.util
from pathlib import Path, PurePosixPath
import sqlite3
import time

from .core import transaction
from .isolation import create_workspace
from .openrouter_adapter import execute
from .validation import stage_python


class RunError(Exception):
    """Concise failure with no provider response or sensitive task content."""


def _reservation(ledger, task_id, worker_name):
    with transaction(ledger.path) as db:
        row = db.execute('SELECT worker FROM reservations WHERE task_id=?', (task_id,)).fetchone()
    return row is not None and row[0] == worker_name


def run_python_task(store, ledger, metrics, source: Path, workspace_root: Path,
                    task_id: str, worker, policy, *, adapter=execute) -> Path:
    """Send a task at most once, staging a single new Python file for review.

    Account verification is an operator attestation, not independently checked.
    A Git worktree is NOT a security sandbox. Do not execute generated code here.
    Files, metrics and state are not one atomic transaction: interrupted tasks
    require manual inspection and may never be restarted automatically.
    """
    if (policy.enabled is not True or policy.zero_spend_account_verified is not True
        or worker.name != 'openrouter' or not worker.enabled or not worker.automatic
        or not worker.free_verified or 'code' not in worker.capabilities
        or not isinstance(policy.model, str) or not policy.model.endswith(':free')
        or policy.model not in policy.allowed_models):
        raise RunError('Provider unavailable: free-use safety gates are not satisfied')
    if adapter is execute and importlib.util.find_spec('tools.openrouter_task') is None:
        raise RunError('Provider unavailable: PR #8 helper is not installed')
    try:
        task = store.get(task_id)
        if task['status'] != 'ready' or len(task['files']) != 1:
            raise ValueError('task must be ready and declare one output')
        name = task['files'][0]
        if not isinstance(name, str) or '\\' in name:
            raise ValueError('invalid output')
        relative = PurePosixPath(name)
        if relative.is_absolute() or not relative.parts or '..' in relative.parts or relative.suffix != '.py':
            raise ValueError('invalid output')
        # Transition occurs before all external actions and serializes concurrent attempts.
        store.transition(task_id, 'running')
    except (KeyError, ValueError):
        raise RunError('Task unavailable: not ready or invalid output declaration') from None
    result = None
    try:
        workspace = create_workspace(source, workspace_root, task_id)
        result = adapter(task['goal'], task_id, policy, worker, ledger, now=time.time())
        if not _reservation(ledger, task_id, worker.name):
            ledger.block(worker.name, 'adapter returned without a reservation')
            raise ValueError('missing quota reservation')
        usage = result.usage if isinstance(result.usage, dict) else {}
        metrics.record(task_id, worker.name, 'response_received',
                       prompt_tokens=usage.get('prompt_tokens'), completion_tokens=usage.get('completion_tokens'),
                       reasoning_tokens=usage.get('reasoning_tokens'), total_tokens=usage.get('total_tokens'),
                       cost=usage.get('cost'))
        output = stage_python(workspace, str(relative), result.code)
        store.transition(task_id, 'review')
        return output
    except Exception:
        try:
            if _reservation(ledger, task_id, worker.name):
                ledger.block(worker.name, 'interrupted task requires manual review')
                if result is None:
                    try:
                        metrics.record(task_id, worker.name, 'uncertain')
                    except (ValueError, sqlite3.Error):
                        pass
            store.transition(task_id, 'interrupted')
        except Exception:
            # Keep a 'running' task if storage fails. Never infer it is safe to retry.
            pass
        raise RunError('Task interrupted; inspect state, workspace and provider before any recovery') from None
