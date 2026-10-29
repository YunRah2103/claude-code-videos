"""Inspect offline routing state; this interface never sends model requests."""
import argparse
import json
import time
from pathlib import Path
from .core import Ledger, Registry
from .tasks import TaskStore


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--state', type=Path, default=Path('out/agent-rotation/state.db'))
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('status')
    plan = sub.add_parser('plan')
    plan.add_argument('--task', required=True)
    create = sub.add_parser('create')
    create.add_argument('--id', required=True)
    create.add_argument('--goal', required=True)
    create.add_argument('--file', required=True, action='append')
    show = sub.add_parser('show')
    show.add_argument('--id', required=True)
    args = parser.parse_args()
    ledger, registry = Ledger(args.state), Registry.defaults()
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
