import sqlite3
import subprocess
import tempfile
import unittest
from pathlib import Path
from tools.agent_rotation.core import Ledger, Worker
from tools.agent_rotation.tasks import TaskStore
from tools.agent_rotation.metrics import Metrics
from tools.agent_rotation.openrouter_adapter import Policy, Result
from tools.agent_rotation.orchestrator import run_python_task, RunError

class OrchestratorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'source'; self.repo.mkdir()
        subprocess.run(['git','init','-q',str(self.repo)], check=True)
        subprocess.run(['git','-C',str(self.repo),'config','user.email','test@example.invalid'], check=True)
        subprocess.run(['git','-C',str(self.repo),'config','user.name','Test'], check=True)
        (self.repo / 'base.txt').write_text('base')
        subprocess.run(['git','-C',str(self.repo),'add','base.txt'], check=True)
        subprocess.run(['git','-C',str(self.repo),'commit','-qm','initial'], check=True)
        db = self.root / 'state.db'
        self.store, self.ledger, self.metrics = TaskStore(db), Ledger(db), Metrics(db)
        self.store.create('t1', 'Write a new wheel utility', ['output.py'])
        self.store.transition('t1', 'ready')
        self.worker = Worker('openrouter', frozenset({'code'}), True, True, True, 2, 60)
        self.policy = Policy(True, True, ('model:free',), 'model:free', 128)
        self.calls = 0
    def adapter(self, task, task_id, policy, worker, ledger, *, now):
        self.calls += 1
        if not ledger.reserve(worker, task_id, now): raise RuntimeError('quota')
        return Result('answer = 42\n', policy.model, {'prompt_tokens': 8, 'completion_tokens': 4, 'total_tokens': 12, 'reasoning_tokens': None, 'cost': 0})
    def run_job(self, adapter=None, policy=None):
        return run_python_task(self.store, self.ledger, self.metrics, self.repo, self.root/'workspaces', 't1', self.worker, policy or self.policy, adapter=adapter or self.adapter)
    def test_single_attempt_stages_in_detached_worktree_pending_review(self):
        path = self.run_job()
        self.assertEqual(path.read_text(), 'answer = 42\n')
        self.assertFalse((self.repo/'output.py').exists())
        self.assertEqual(self.store.get('t1')['status'], 'review')
        self.assertEqual(self.metrics.report()['requests'], 1)
        self.assertEqual(self.metrics.report()['known_total_tokens'], 12)
        with self.assertRaises(RunError): self.run_job()
        self.assertEqual(self.calls, 1)
    def test_default_disabled_does_not_create_workspace_or_call_adapter(self):
        with self.assertRaises(RunError): self.run_job(policy=Policy())
        self.assertEqual(self.store.get('t1')['status'], 'ready')
        self.assertFalse((self.root/'workspaces').exists())
        self.assertEqual(self.calls, 0)
    def test_uncertain_failure_never_retries_and_blocks_provider(self):
        def fail(task, task_id, policy, worker, ledger, *, now):
            self.calls += 1
            ledger.reserve(worker, task_id, now)
            raise TimeoutError('secret prompt')
        with self.assertRaises(RunError) as caught: self.run_job(adapter=fail)
        self.assertNotIn('secret prompt', str(caught.exception))
        self.assertEqual(self.store.get('t1')['status'], 'interrupted')
        self.assertEqual(self.metrics.report()['requests'], 1)
        self.assertFalse(self.ledger.available(self.worker, 9999999999))
        with self.assertRaises(RunError): self.run_job(adapter=fail)
        self.assertEqual(self.calls, 1)
    def test_invalid_code_does_not_enter_review(self):
        def invalid(task, task_id, policy, worker, ledger, *, now):
            ledger.reserve(worker, task_id, now)
            return Result('bad python !', policy.model, {})
        with self.assertRaises(RunError): self.run_job(adapter=invalid)
        self.assertEqual(self.store.get('t1')['status'], 'interrupted')
        self.assertFalse((self.repo/'output.py').exists())
    def test_adapter_without_reservation_is_rejected(self):
        def unsafe(*args, **kwargs): return Result('answer = 1', 'model:free', {})
        with self.assertRaises(RunError): self.run_job(adapter=unsafe)
        self.assertEqual(self.store.get('t1')['status'], 'interrupted')
    def test_two_concurrent_invocations_never_send_twice(self):
        from concurrent.futures import ThreadPoolExecutor
        def run(_):
            try: return self.run_job()
            except RunError: return None
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(run, range(2)))
        self.assertEqual(sum(result is not None for result in results), 1)
        self.assertEqual(self.calls, 1)
    def test_missing_real_helper_stays_ready(self):
        from unittest.mock import patch
        with patch('tools.agent_rotation.orchestrator.importlib.util.find_spec', return_value=None):
            with self.assertRaises(RunError):
                run_python_task(self.store, self.ledger, self.metrics, self.repo, self.root/'workspaces', 't1', self.worker, self.policy)
        self.assertEqual(self.store.get('t1')['status'], 'ready')
        self.assertFalse((self.root/'workspaces').exists())
