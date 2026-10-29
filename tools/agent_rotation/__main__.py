"""Inspect offline routing state; this interface never sends model requests."""
import argparse
from contextlib import closing
import json
import sqlite3
import time
from pathlib import Path
from .core import Ledger, Registry
from .tasks import TaskStore
from .metrics import Metrics


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, default=Path('out/agent-rotation/state.db'))
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('status')
    sub.add_parser('report')
    plan = sub.add_parser('plan')
    plan.add_argument('--task', required=True)
    create = sub.add_parser('create')
    create.add_argument('--id', required=True)
    create.add_argument('--goal', required=True)
    create.add_argument('--file', required=True, action='append')
    show = sub.add_parser('show')
    show.add_argument('--id', required=True)
    preflight = sub.add_parser('preflight', help='inspect readiness without sending or changing state')
    preflight.add_argument('--id', required=True)
    args = parser.parse_args()
    if args.command == 'preflight':
        try:
            with closing(sqlite3.connect(args.state.resolve().as_uri() + '?mode=ro', uri=True)) as db:
                row = db.execute('SELECT status FROM tasks WHERE id=?', (args.id,)).fetchone()
                if row is None:
                    parser.exit(2, 'Error: task not found\n')
                blocked = db.execute('SELECT 1 FROM blocks WHERE worker=?', ('openrouter',)).fetchone() is not None
                reserved = db.execute('SELECT 1 FROM reservations WHERE task_id=?', (args.id,)).fetchone() is not None
                has_metrics = db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='request_metrics'").fetchone()
                attempted = (db.execute('SELECT 1 FROM request_metrics WHERE task_id=?', (args.id,)).fetchone() is not None) if has_metrics else None
                print(json.dumps({'task_status': row[0], 'provider_blocked': blocked, 'reservation_present': reserved,
                                  'recorded_attempt': attempted, 'can_run': False,
                                  'request_sent': False, 'reason': 'Supervised execution is not enabled; verify account, sandbox and recovery separately.'}, indent=2))
        except (sqlite3.Error, OSError):
            parser.exit(2, 'Error: state database unavailable or incomplete\n')
        return
    ledger, registry = Ledger(args.state), Registry.defaults()
    if args.command == 'report':
        print(json.dumps(Metrics(args.state).report(), indent=2))
        return
    if args.command in ('create', 'show'):
        store = TaskStore(args.state)
        try:
            if args.command == 'create':
                store.create(args.id, args.goal, args.file)
            print(json.dumps(store.get(args.id), indent=2))
        except (ValueError, KeyError) as exc:
            parser.exit(2, f'Error: {exc}\n')
        return
    if args.command == 'status':
        for worker in registry.workers:
            status = 'eligible' if (worker.enabled and worker.automatic and worker.free_verified
                                     and ledger.available(worker, time.time())) else 'unavailable'
            print(f'{worker.name}: {status} (automatic={worker.automatic}, free_verified={worker.free_verified})')
    elif args.command == 'plan':
        worker = registry.select('code', ledger, time.time())
        print(f'Task: {args.task}')
        print(f'Worker: {worker.name}' if worker else 'Worker: unavailable; no verified free automatic provider')
        print('Planning only; no request was sent.')


if __name__ == '__main__':
    main()
