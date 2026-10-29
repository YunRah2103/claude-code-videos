"""Supervised free-agent rotation CLI.

Offline commands never send model requests. `run` sends at most one request, and only
after a fresh read-only account check, a fresh read-only model check and an approval
typed on standard input. Generated code is staged and syntax-checked, never executed.
"""
import argparse
import ast
import contextlib
import hashlib
import json
import sqlite3
import sys
import tempfile
import time
from pathlib import Path

from .context import pack_context
from .core import Ledger, Registry, Worker, transaction
from .kilo_adapter import assess_kilo
from .metrics import Metrics
from .openrouter_adapter import Policy
from .orchestrator import RunError, run_python_task
from .tasks import TaskStore

REPO_ROOT = Path(__file__).resolve().parents[2]
ALLOWED_MODELS = ('cohere/north-mini-code:free',)
DEFAULT_MODEL = ALLOWED_MODELS[0]
DEFAULT_MAX_TOKENS = 256
MAX_TOKENS_LIMIT = 2048
MAX_GOAL_BYTES = 16000
MAX_CONTEXT_BYTES = 8000
MAX_REVIEW_BYTES = 100000
REVIEW_LINES = 200
APPROVAL_PREFIX = 'APPROVE ONE LIVE REQUEST '
RISKY_MODULES = {'os', 'subprocess', 'socket', 'shutil', 'ctypes', 'pickle', 'marshal',
                 'importlib', 'urllib', 'http', 'requests'}
RISKY_CALLS = {'eval', 'exec', 'compile', '__import__', 'open', 'input', 'breakpoint'}
TEMPLATES = {
    'python-utility': 'Write a small standard-library Python module of pure functions with unittest tests.',
    'pixel-animation': 'Write deterministic pixel-art animation helpers (interpolation, easing, frame timing) '
                       'using only the standard library, with unittest tests.',
    'car-sprite-geometry': 'Write deterministic geometry helpers for a top-down car sprite (wheel positions, '
                           'rotation, anchor points) using only the standard library, with unittest tests.',
    'wheel-rotation': 'Write wheel_rotation_degrees(distance_pixels, wheel_radius_pixels): rotation in degrees '
                      'equals distance divided by radius, converted from radians. Raise ValueError if the '
                      'radius is zero or negative. Use only the math module.',
    'parallax-layers': 'Write deterministic parallax layer offset helpers (speed per layer, wrap-around) using '
                       'only the standard library, with unittest tests.',
    'ffmpeg-script': 'Write a Python function that builds an ffmpeg argument list (no shell, not executed) '
                     'for an input, output and frame rate, with unittest tests of the argument list.',
    'remotion-props': 'Write Python that builds JSON props for a Remotion composition from frame timing, '
                      'using only the standard library, with unittest tests. Output is JSON text, not TypeScript.',
    'video-render-tool': 'Write Python helpers that compute render frame ranges and output filenames, '
                         'using only the standard library, with unittest tests.',
}
SUFFIX = '\n\nReturn complete Python code only, in one code block, with no prose.'


def live_worker():
    """Worker settings for one supervised attempt; built only after fresh checks pass."""
    return Worker('openrouter', frozenset({'code'}), True, True, True, 1, 86400, daily_limit=1, monthly_limit=1)


def live_policy(model, max_tokens):
    return Policy(enabled=True, zero_spend_account_verified=True, allowed_models=(model,), model=model,
                  max_tokens=max_tokens)


@contextlib.contextmanager
def _ro(path):
    """Read-only connection for offline status views; never creates or alters state."""
    db = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)
    try:
        yield db
    finally:
        db.close()


def open_state(path):
    return Ledger(path), TaskStore(path), Metrics(path)


def workspace_root(state):
    """Workspaces must sit outside the repository (the orchestrator refuses otherwise)."""
    digest = hashlib.sha256(str(Path(state).resolve()).encode('utf-8')).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / 'claude-code-videos-rotation' / digest


def staged_path(state, task_id, file_name):
    return workspace_root(state) / task_id / file_name


def provider_rows(state):
    """Offline view. A provider is never shown as operational from installation alone."""
    blocked_reason = None
    if Path(state).exists():
        with _ro(state) as db:
            row = db.execute('SELECT reason FROM blocks WHERE worker=?', ('openrouter',)).fetchone()
        blocked_reason = row[0] if row else None
    kilo = assess_kilo()
    return [
        {'provider': 'openrouter', 'capabilities': 'code',
         'status': 'BLOCKED' if blocked_reason else 'UNAVAILABLE (not verified)',
         'detail': ('provider block preserved: ' + blocked_reason + '; manual review required')
                   if blocked_reason else 'run preflight --online to verify spending cap and model price'},
        {'provider': 'gemini', 'capabilities': 'code', 'status': 'DISABLED',
         'detail': 'live generation unresolved (HTTP 404 and 502 on record)'},
        {'provider': 'kilo', 'capabilities': 'code', 'status': 'DISABLED',
         'detail': kilo.reason},
        {'provider': 'claude', 'capabilities': 'review', 'status': 'REVIEW ONLY', 'detail': 'no automatic routing'},
    ]


def _table_exists(db, name):
    return db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone() is not None


def _local_checks(state, task_id, model, now):
    """Read-only checks. Returns (facts, checks); facts is None when the task does not exist."""
    checks = []
    if model not in ALLOWED_MODELS or not model.endswith(':free'):
        checks.append(('model allowlisted and free', False, 'model is not on the free allowlist'))
    else:
        checks.append(('model allowlisted and free', True, model))
    with _ro(state) as db:
        row = db.execute('SELECT status, files FROM tasks WHERE id=?', (task_id,)).fetchone()
        blocked = db.execute('SELECT reason FROM blocks WHERE worker=?', ('openrouter',)).fetchone()
        reserved = db.execute('SELECT 1 FROM reservations WHERE task_id=?', (task_id,)).fetchone()
        attempted = None
        if _table_exists(db, 'request_metrics'):
            attempted = db.execute('SELECT 1 FROM request_metrics WHERE task_id=?', (task_id,)).fetchone()
        used = db.execute('SELECT COUNT(*) FROM reservations WHERE worker=? AND created>?',
                          ('openrouter', now - 86400)).fetchone()[0]
    if row is None:
        return None, checks + [('task exists', False, 'no such task')]
    facts = {
        'task_status': row[0],
        'provider_blocked': blocked is not None,
        'reservation_present': reserved is not None,
        'recorded_attempt': attempted is not None,
    }
    checks.append(('task ready', row[0] == 'ready', f'status is {row[0]}'))
    files = json.loads(row[1])
    valid_output = (len(files) == 1 and files[0].endswith('.py') and '..' not in files[0]
                    and not files[0].startswith('/') and '\\' not in files[0])
    checks.append(('single safe .py output', valid_output, files[0] if valid_output else 'invalid output'))
    checks.append(('provider not blocked', blocked is None,
                   'blocked: ' + blocked[0] if blocked else 'not blocked'))
    checks.append(('no earlier attempt for this task', not facts['recorded_attempt'] and not facts['reservation_present'],
                   'attempt already recorded or reserved' if (facts['recorded_attempt'] or facts['reservation_present']) else 'none'))
    checks.append(('daily quota available', used < 1, f'{used} of 1 reservation used in 24h'))
    return facts, checks


def _online_checks(model, opener=None):
    """Fresh read-only checks against OpenRouter metadata endpoints. Never generates text."""
    from tools import openrouter_task as helper
    kwargs = {} if opener is None else {'opener': opener}
    spend = helper.account_spend_status(**kwargs)
    listed_free = helper.model_is_listed_free(model, **kwargs)
    checks = [
        ('zero-spend cap verified (read-only)', spend['zero_spend_verified'], 'limit 0 and remaining 0'),
        ('no management or provisioning key', not spend['management_or_provisioning'], 'key type checked'),
        ('model listed at zero price (read-only)', listed_free, model),
    ]
    return checks


def _all_ok(checks):
    return all(ok for _, ok, _ in checks)


def cmd_preflight(args):
    if not Path(args.state).exists():
        return _fail(2, 'Error: state database unavailable or incomplete')
    now = time.time()
    model = args.model
    try:
        facts, checks = _local_checks(args.state, args.id, model, now)
    except Exception:
        return _fail(2, 'Error: state database unavailable or incomplete')
    if facts is None:
        return _fail(2, 'Error: task not found')
    online = None
    if args.online:
        try:
            online = _online_checks(model)
        except Exception as exc:
            return _fail(2, f'Error: online check failed ({getattr(exc, "code", "UNKNOWN")}); nothing was sent for generation')
    can_run = _all_ok(checks) and online is not None and _all_ok(online)
    report = dict(facts)
    report.update({
        'task_id': args.id,
        'checks': [{'check': n, 'ok': ok, 'detail': d} for n, ok, d in checks],
        'online_checks': 'not run (use --online)' if online is None else
                         [{'check': n, 'ok': ok, 'detail': d} for n, ok, d in online],
        'can_run': can_run,
        'request_sent': False,
        'reason': ('all checks passed; run asks for typed approval' if can_run
                   else ('online checks not run; use preflight --online' if online is None
                         else 'a check failed; see checks')),
    })
    print(json.dumps(report, indent=2))
    return 0


def _fail(code, message):
    print(message, file=sys.stderr)
    return code


def cmd_run(args):
    if not Path(args.state).exists():
        return _fail(2, 'Error: state database unavailable; create the task first')
    model, max_tokens = args.model, args.max_tokens
    if model not in ALLOWED_MODELS:
        return _fail(3, f'Refused: model {model!r} is not on the free allowlist. No request was sent.')
    if not (1 <= max_tokens <= MAX_TOKENS_LIMIT):
        return _fail(3, f'Refused: --max-tokens must be between 1 and {MAX_TOKENS_LIMIT}. No request was sent.')
    now = time.time()
    try:
        row, checks = _local_checks(args.state, args.id, model, now)
    except Exception:
        return _fail(2, 'Error: state database unavailable or incomplete')
    if row is None:
        return _fail(2, 'Error: task not found')
    failed = [f'  - {n}: {d}' for n, ok, d in checks if not ok]
    if failed:
        return _fail(3, 'Refused: safety checks failed; no request was sent.\n' + '\n'.join(failed))
    if not sys.stdin.isatty():
        return _fail(3, 'Refused: approval must be typed at an interactive terminal. No request was sent.')
    try:
        online = _online_checks(model)
    except Exception as exc:
        return _fail(3, f'Refused: fresh account check failed ({getattr(exc, "code", "UNKNOWN")}); no request was sent.')
    if not _all_ok(online):
        failed = [f'  - {n}' for n, ok, _ in online if not ok]
        return _fail(3, 'Refused: fresh account or model check failed; no request was sent.\n' + '\n'.join(failed))
    if not sys.stdin.isatty():
        return _fail(3, 'Refused: approval must be typed at an interactive terminal. No request was sent.')
    expected = APPROVAL_PREFIX + args.id
    print(f'Send ONE live request to {model} (max {max_tokens} tokens) for task {args.id}?')
    print(f'Type exactly:  {expected}')
    typed = sys.stdin.readline().strip()
    if typed != expected:
        return _fail(3, 'Not approved. No request was sent.')
    ledger, store, metrics = open_state(args.state)
    try:
        output = run_python_task(store, ledger, metrics, REPO_ROOT, workspace_root(args.state), args.id,
                                 live_worker(), live_policy(model, max_tokens))
    except RunError as exc:
        print(f'Run stopped: {exc}', file=sys.stderr)
        if exc.failure_code:
            print(f'Failure code: {exc.failure_code} (stage: {exc.failure_stage}). No automatic retry.', file=sys.stderr)
        print('Next: run review --id %s, then history --id %s.' % (args.id, args.id), file=sys.stderr)
        return 1
    _record_stage(args.state, args.id, output)
    print(f'Staged for review: {output}')
    print('Next: review --id %s' % args.id)
    return 0


def _static_findings(tree):
    findings = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split('.')[0] in RISKY_MODULES:
                    findings.add(f'imports {alias.name.split(".")[0]}')
        elif isinstance(node, ast.ImportFrom) and node.module:
            if node.module.split('.')[0] in RISKY_MODULES:
                findings.add(f'imports from {node.module.split(".")[0]}')
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in RISKY_CALLS:
            findings.add(f'calls {node.func.id}')
    return sorted(findings)


def _record_stage(state, task_id, output):
    """Remember the digest of exactly what was staged, so review can detect later edits."""
    digest = hashlib.sha256(Path(output).read_bytes()).hexdigest()
    with transaction(state) as db:
        db.execute('CREATE TABLE IF NOT EXISTS staged_outputs '
                   '(task_id TEXT PRIMARY KEY, sha256 TEXT NOT NULL, staged_at REAL NOT NULL)')
        db.execute('INSERT OR REPLACE INTO staged_outputs VALUES (?,?,?)', (task_id, digest, time.time()))


def _approval_problem(state, task_id, path):
    """Return None when the staged file is present, unchanged and valid; otherwise the reason."""
    if not path.is_file() or path.is_symlink():
        return 'staged file is missing'
    with _ro(state) as db:
        if not _table_exists(db, 'staged_outputs'):
            return 'no staging record exists'
        row = db.execute('SELECT sha256 FROM staged_outputs WHERE task_id=?', (task_id,)).fetchone()
    if row is None:
        return 'no staging record exists'
    if hashlib.sha256(path.read_bytes()).hexdigest() != row[0]:
        return 'staged file changed after staging'
    try:
        ast.parse(path.read_text(encoding='utf-8'))
    except (SyntaxError, UnicodeDecodeError, ValueError):
        return 'staged file is not valid Python'
    return None


def cmd_review(args):
    try:
        _, store, _ = open_state(args.state)
        details = store.get(args.id)
    except (KeyError, ValueError):
        return _fail(2, 'Error: task not found')
    file_name = details['files'][0]
    path = staged_path(args.state, args.id, file_name)
    print(f"Task: {args.id}\nStatus: {details['status']}")
    if path.exists() and path.stat().st_size <= MAX_REVIEW_BYTES:
        code = path.read_text(encoding='utf-8')
        try:
            tree = ast.parse(code)
            print('Syntax: passed (not executed)')
            findings = _static_findings(tree)
        except SyntaxError:
            print('Syntax: FAILED')
            findings = ['not analysed']
        print(f'Generated file: {path}')
        print('Static findings: ' + ('none' if findings == [] else ', '.join(findings)))
        print('Execution: disabled (no verified sandbox). Review the code by reading it.')
        lines = code.splitlines()
        print(f'----- first {min(len(lines), REVIEW_LINES)} of {len(lines)} lines -----')
        print('\n'.join(lines[:REVIEW_LINES]))
        print('-----')
    else:
        print('Generated file: none staged (check status and history)')
    if args.approve or args.reject:
        if details['status'] != 'review':
            return _fail(3, 'Refused: only tasks in review can be approved or rejected.')
        if args.approve:
            problem = _approval_problem(args.state, args.id, path)
            if problem:
                return _fail(3, f'Refused: {problem}. Task stays in review; nothing was approved.')
        target = 'complete' if args.approve else 'failed'
        store.transition(args.id, target)
        print(f'Decision recorded: {target}. Copy the file into the repository manually after your own review.')
    return 0


def cmd_history(args):
    with _ro(args.state) as db:
        if args.id:
            events = db.execute('SELECT status, timestamp FROM task_events WHERE task_id=? ORDER BY id',
                                (args.id,)).fetchall()
            if not events:
                return _fail(2, 'Error: task not found')
            print(f'Task: {args.id}')
            for status, stamp in events:
                print(f'  {time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(stamp))}Z  {status}')
            outcome = db.execute('SELECT outcome, prompt_tokens, completion_tokens, total_tokens, cost '
                                 'FROM request_metrics WHERE task_id=?', (args.id,)).fetchone()
            failure = db.execute('SELECT failure_stage, failure_code FROM failure_diagnostics WHERE task_id=?',
                                 (args.id,)).fetchone()
            print('Outcome: ' + (outcome[0] if outcome else 'no provider attempt recorded'))
            print('Failure: ' + (f'{failure[1]} at {failure[0]}' if failure else 'none recorded'))
            if outcome:
                print('Tokens (provider-reported; unknown shown as ?): prompt=%s completion=%s total=%s cost=%s' % (
                    *(('?' if v is None else v) for v in outcome[1:4]), '?' if outcome[4] is None else outcome[4]))
            return 0
        rows = db.execute('SELECT id, status FROM tasks ORDER BY id').fetchall()
        if not rows:
            print('No tasks yet. Create one with: create --id NAME --goal-file FILE --file out_name.py')
            return 0
        for task_id, status in rows:
            outcome = db.execute('SELECT outcome FROM request_metrics WHERE task_id=?', (task_id,)).fetchone()
            print(f'{task_id:<28} {status:<12} attempt: {outcome[0] if outcome else "none"}')
    return 0


def cmd_report(args):
    _, _, metrics = open_state(args.state)
    data = metrics.report()
    print(json.dumps(data, indent=2))
    print('Note: an unknown value is not zero. Only provider-reported numbers are shown.')
    return 0


def cmd_status(args):
    print(f'State: {args.state}')
    if Path(args.state).exists():
        with _ro(args.state) as db:
            counts = db.execute('SELECT status, COUNT(*) FROM tasks GROUP BY status').fetchall()
        print('Tasks: ' + (', '.join(f'{s}={n}' for s, n in counts) if counts else 'none'))
    else:
        print('Tasks: no state yet')
    print('Execution of generated code: DISABLED (no verified sandbox)')
    print('Unattended routing: DISABLED (live runs require preflight --online and typed approval)')
    for row in provider_rows(args.state):
        print(f"{row['provider']}: {row['status']} - {row['detail']}")
    return 0


def cmd_providers(args):
    for row in provider_rows(args.state):
        print(f"{row['provider']:<11} {row['status']:<14} capabilities={row['capabilities']}")
        print(f"            {row['detail']}")
    return 0


def cmd_templates(args):
    for name, text in TEMPLATES.items():
        print(f'{name}: {text}')
    return 0


def _goal_text(args):
    provided = sum([args.goal is not None, args.goal_file is not None, bool(args.goal_stdin)])
    if provided > 1:
        raise ValueError('give only one of --goal-file, --goal-stdin or --goal')
    if provided == 0 and not args.template:
        raise ValueError('give --goal-file, --goal-stdin, --goal or --template')
    parts = [TEMPLATES[args.template]] if args.template else []
    if args.template and args.template not in TEMPLATES:
        raise ValueError('unknown template; run templates')
    if args.goal_file:
        parts.append(Path(args.goal_file).read_text(encoding='utf-8'))
    elif args.goal_stdin:
        parts.append(sys.stdin.read())
    elif args.goal is not None:
        parts.append(args.goal)
    goal = '\n'.join(p.strip() for p in parts if p and p.strip()) + SUFFIX
    if args.context:
        root = Path.cwd().resolve()
        rels = []
        for name in args.context:
            resolved = Path(name).resolve()
            try:
                rels.append(str(resolved.relative_to(root)))
            except ValueError:
                raise ValueError('context files must be inside the current directory') from None
        packed = pack_context(root, rels, MAX_CONTEXT_BYTES)
        goal += '\n\nContext files:\n' + '\n'.join(f'--- {k} ---\n{v}' for k, v in packed.items())
    if len(goal.encode('utf-8')) > MAX_GOAL_BYTES:
        raise ValueError(f'task goal exceeds {MAX_GOAL_BYTES} bytes; split the task')
    return goal


def cmd_create(args):
    try:
        goal = _goal_text(args)
        _, store, _ = open_state(args.state)
        store.create(args.id, goal, args.file)
        store.transition(args.id, 'ready')
    except (ValueError, KeyError, OSError) as exc:
        return _fail(2, f'Error: {exc}')
    print(f'Created task {args.id} (ready). The goal text is stored, not printed.')
    print('Next: preflight --id %s' % args.id)
    return 0


def cmd_show(args):
    try:
        _, store, _ = open_state(args.state)
        details = store.get(args.id)
    except KeyError:
        return _fail(2, 'Error: task not found')
    details.pop('goal', None)
    print(json.dumps(details, indent=2))
    return 0


def cmd_plan(args):
    ledger = Ledger(args.state)
    worker = Registry.defaults().select('code', ledger, time.time())
    print(f'Worker: {worker.name}' if worker else 'Worker: unavailable; no verified free automatic provider')
    print('Planning only; no request was sent.')
    return 0


def build_parser():
    parser = argparse.ArgumentParser(prog='python -m tools.agent_rotation',
                                     description='Supervised free-agent coding rotation. Offline unless run is approved.')
    parser.add_argument('--state', type=Path, default=Path('out/agent-rotation/state.db'),
                        help='state database (default: out/agent-rotation/state.db)')
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('status', help='show providers, state and safety settings')
    sub.add_parser('providers', help='list providers and why each is or is not usable')
    sub.add_parser('templates', help='list coding-task templates')
    sub.add_parser('report', help='token usage and provider-reported cost')
    history = sub.add_parser('history', help='task events, outcomes and failure codes')
    history.add_argument('--id')
    create = sub.add_parser('create', help='register a ready coding task')
    create.add_argument('--id', required=True)
    create.add_argument('--template', help='coding-task template name (see templates)')
    create.add_argument('--goal-file', help='read the task text from a file (preferred)')
    create.add_argument('--goal-stdin', action='store_true', help='read the task text from standard input')
    create.add_argument('--goal', help='task text on the command line (avoid: stays in shell history)')
    create.add_argument('--file', required=True, action='append', help='one repository-relative .py output')
    create.add_argument('--context', action='append', help='file to include as context (repeatable, bounded)')
    preflight = sub.add_parser('preflight', help='read-only readiness check; add --online for fresh account checks')
    preflight.add_argument('--id', required=True)
    preflight.add_argument('--model', default=DEFAULT_MODEL)
    preflight.add_argument('--online', action='store_true', help='read-only account and model metadata checks')
    run = sub.add_parser('run', help='one approved supervised request, staged for review')
    run.add_argument('--id', required=True)
    run.add_argument('--model', default=DEFAULT_MODEL)
    run.add_argument('--max-tokens', type=int, default=DEFAULT_MAX_TOKENS)
    review = sub.add_parser('review', help='inspect staged code without executing it')
    review.add_argument('--id', required=True)
    decision = review.add_mutually_exclusive_group()
    decision.add_argument('--approve', action='store_true')
    decision.add_argument('--reject', action='store_true')
    show = sub.add_parser('show', help='task details without goal text')
    show.add_argument('--id', required=True)
    plan = sub.add_parser('plan', help='choose a worker (no request)')
    plan.add_argument('--task', help='accepted for compatibility; never printed')
    return parser


COMMANDS = {
    'status': cmd_status, 'providers': cmd_providers, 'templates': cmd_templates, 'report': cmd_report,
    'history': cmd_history, 'create': cmd_create, 'preflight': cmd_preflight, 'run': cmd_run,
    'review': cmd_review, 'show': cmd_show, 'plan': cmd_plan,
}


def main(argv=None):
    args = build_parser().parse_args(argv)
    if args.command == 'run' and not 1 <= args.max_tokens <= MAX_TOKENS_LIMIT:
        return _fail(3, 'Refused: --max-tokens out of range. No request was sent.')
    return COMMANDS[args.command](args)


if __name__ == '__main__':
    sys.exit(main())
