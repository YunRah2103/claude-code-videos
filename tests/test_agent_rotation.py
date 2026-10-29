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

class TaskStateTests(unittest.TestCase):
    def test_state_survives_restart_and_duplicate_ids_do_not_overwrite(self):
        from tools.agent_rotation.tasks import TaskStore
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'tasks.db'
            store = TaskStore(path)
            store.create('t1', 'Build wheel helper', ['a.py'])
            with self.assertRaises(ValueError):
                store.create('t1', 'Different job', ['b.py'])
            store.transition('t1', 'ready')
            loaded = TaskStore(path).get('t1')
            self.assertEqual(loaded['goal'], 'Build wheel helper')
            self.assertEqual(loaded['status'], 'ready')
            self.assertEqual(len(loaded['history']), 2)

    def test_invalid_transition_and_unknown_task_rejected(self):
        from tools.agent_rotation.tasks import TaskStore
        with tempfile.TemporaryDirectory() as tmp:
            store = TaskStore(Path(tmp) / 'tasks.db')
            store.create('t1', 'Build', ['a.py'])
            with self.assertRaises(ValueError): store.transition('t1', 'complete')
            with self.assertRaises(KeyError): store.get('missing')

class ContextTests(unittest.TestCase):
    def test_only_declared_files_and_limits_are_included(self):
        from tools.agent_rotation.context import pack_context
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'a.py').write_text('print(1)')
            (root / 'secret.txt').write_text('private')
            bundle = pack_context(root, ['a.py'], 20)
            self.assertEqual(bundle, {'a.py': 'print(1)'})
            with self.assertRaises(ValueError): pack_context(root, ['a.py'], 2)
            with self.assertRaises(ValueError): pack_context(root, ['../secret.txt'], 100)

    def test_symlink_and_binary_rejected(self):
        from tools.agent_rotation.context import pack_context
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'binary').write_bytes(b'\x00\xff')
            (root / 'link').symlink_to(root / 'binary')
            for name in ('binary', 'link'):
                with self.assertRaises(ValueError): pack_context(root, [name], 100)

class TaskCLITests(unittest.TestCase):
    def test_create_and_inspect_task(self):
        import subprocess, sys
        with tempfile.TemporaryDirectory() as tmp:
            prefix = [sys.executable, '-m', 'tools.agent_rotation', '--state', str(Path(tmp) / 'state.db')]
            create = subprocess.run(prefix + ['create', '--id', 'wheel', '--goal', 'Wheel tests', '--file', 'tests/test_wheel.py'], capture_output=True, text=True)
            self.assertEqual(create.returncode, 0, create.stderr)
            show = subprocess.run(prefix + ['show', '--id', 'wheel'], capture_output=True, text=True)
            self.assertEqual(show.returncode, 0, show.stderr)
            self.assertIn('Wheel tests', show.stdout)
            self.assertIn('planned', show.stdout)
            duplicate = subprocess.run(prefix + ['create', '--id', 'wheel', '--goal', 'other', '--file', 'x'], capture_output=True, text=True)
            self.assertNotEqual(duplicate.returncode, 0)
            self.assertNotIn('Traceback', duplicate.stderr)

class QuotaCalendarTests(unittest.TestCase):
    def test_daily_and_monthly_limits_enforced_across_restart(self):
        from datetime import datetime, timezone
        def ts(day): return datetime(2026, 10, day, 12, tzinfo=timezone.utc).timestamp()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'state.db'
            ledger = Ledger(path)
            worker = Worker('free', frozenset({'code'}), True, True, True, 10, 60, daily_limit=1, monthly_limit=2)
            self.assertTrue(ledger.reserve(worker, 'a', ts(1)))
            self.assertFalse(ledger.reserve(worker, 'b', ts(1) + 120))
            self.assertTrue(ledger.reserve(worker, 'b', ts(2)))
            self.assertFalse(Ledger(path).reserve(worker, 'c', ts(3)))
