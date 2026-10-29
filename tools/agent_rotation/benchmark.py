"""Measure local quota-reservation overhead; no model benchmark or API calls."""
import argparse
import json
from pathlib import Path
import tempfile
import time
from .core import Ledger, Worker


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--iterations', type=int, default=100)
    args = parser.parse_args()
    if not 1 <= args.iterations <= 10000:
        parser.error('iterations must be between 1 and 10000')
    with tempfile.TemporaryDirectory() as tmp:
        ledger = Ledger(Path(tmp) / 'state.db')
        worker = Worker('simulated', frozenset({'code'}), True, True, True, args.iterations, 3600)
        start = time.perf_counter()
        count = sum(ledger.reserve(worker, f'task-{i}', 1000) for i in range(args.iterations))
        elapsed = time.perf_counter() - start
    print(json.dumps({'mode': 'offline-simulated', 'operation': 'local quota reservations',
                      'iterations': args.iterations, 'successful_reservations': count,
                      'wall_seconds': elapsed, 'api_requests': 0, 'provider_tokens': None,
                      'model_success_rate': None, 'baseline': 'unmeasured',
                      'token_savings': None}, indent=2))


if __name__ == '__main__':
    main()
