import tempfile
import unittest
from pathlib import Path
from tools.agent_rotation.core import Registry, Ledger, Worker

class RoutingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.ledger = Ledger(Path(self.tmp.name) / 'state.db')
        self.worker = Worker('free', frozenset({'code'}), True, True, True, 2, 60)

    def test_default_registry_never_routes(self):
        self.assertIsNone(Registry.defaults().select('code', self.ledger, 100))

    def test_route_requires_enabled_verified_free_and_capability(self):
        eligible = self.worker
        disabled = Worker('disabled', frozenset({'code'}), False, True, True, 2, 60)
        paid = Worker('paid', frozenset({'code'}), True, True, False, 2, 60)
        manual = Worker('manual', frozenset({'code'}), True, False, True, 2, 60)
        r = Registry([disabled, paid, manual, eligible])
        self.assertEqual(r.select('code', self.ledger, 100).name, 'free')
        self.assertIsNone(r.select('render', self.ledger, 100))

    def test_atomic_reservation_and_rolling_limit_survive_restart(self):
        self.assertTrue(self.ledger.reserve(self.worker, 'task1', 100))
        self.assertFalse(self.ledger.reserve(self.worker, 'task1', 101))
        self.assertTrue(self.ledger.reserve(self.worker, 'task2', 101))
        reopened = Ledger(Path(self.tmp.name) / 'state.db')
        self.assertFalse(reopened.reserve(self.worker, 'task3', 102))
        self.assertTrue(reopened.reserve(self.worker, 'task3', 161))

    def test_exhausted_worker_is_not_selected(self):
        self.ledger.block('free', 'quota exhausted')
        self.assertIsNone(Registry([self.worker]).select('code', self.ledger, 100))

class CLITests(unittest.TestCase):
    def test_status_and_plan_work_without_providers(self):
        import subprocess, sys
        with tempfile.TemporaryDirectory() as tmp:
            for command in (['status'], ['plan', '--task', 'Add wheel tests']):
                result = subprocess.run([sys.executable, '-m', 'tools.agent_rotation',
                                         '--state', str(Path(tmp) / 'state.db'), *command],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('unavailable', result.stdout.lower())

class PlannerTests(unittest.TestCase):
    def test_dependencies_and_file_conflicts_block_parallel_work(self):
        from tools.agent_rotation.planner import Task, ready_batch
        tasks = [Task('a', ('src/a.py',), ()), Task('b', ('src/a.py',), ()),
                 Task('c', ('src/c.py',), ('a',))]
        self.assertEqual([t.id for t in ready_batch(tasks, set())], ['a'])
        self.assertEqual([t.id for t in ready_batch(tasks, {'a'})], ['b', 'c'])

    def test_rejects_traversal_unknown_dependencies_and_cycles(self):
        from tools.agent_rotation.planner import Task, ready_batch
        for tasks in ([Task('a', ('../secret',), ())],
                      [Task('a', ('x',), ('missing',))],
                      [Task('a', ('x',), ('b',)), Task('b', ('y',), ('a',))]):
            with self.assertRaises(ValueError):
                ready_batch(tasks, set())

class ConcurrencyTests(unittest.TestCase):
    def test_only_one_concurrent_reservation_gets_last_slot(self):
        from concurrent.futures import ThreadPoolExecutor
        with tempfile.TemporaryDirectory() as tmp:
            ledger = Ledger(Path(tmp) / 'state.db')
            worker = Worker('free', frozenset({'code'}), True, True, True, 1, 60)
            with ThreadPoolExecutor(max_workers=8) as pool:
                results = list(pool.map(lambda n: ledger.reserve(worker, f'task{n}', 100), range(8)))
            self.assertEqual(sum(results), 1)
