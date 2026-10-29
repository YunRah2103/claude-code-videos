import tempfile
import unittest
from pathlib import Path
from tools.agent_rotation.core import Ledger, Worker
from tools.agent_rotation.openrouter_adapter import execute, Policy, AdapterError

class FakeHelper:
    def __init__(self, reply=None, error=None):
        self.calls = 0
        self.reply = reply or {'content': '```python\nanswer = 42\n```', 'model': 'test:free', 'usage': {'prompt_tokens': 12, 'completion_tokens': 4, 'cost': 0}, 'finish_reason': 'stop'}
        self.error = error
    def build_payload(self, task, model, max_tokens): return {'task': task, 'model': model, 'max_tokens': max_tokens}
    def send(self, payload):
        self.calls += 1
        if self.error: raise RuntimeError(self.error)
        return 200, self.reply
    def parse_reply(self, status, data):
        if data['finish_reason'] != 'stop': raise ValueError('incomplete')
        return data
    def extract_code(self, content): return content.removeprefix('```python\n').removesuffix('```').strip() + '\n'

class AdapterTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.ledger = Ledger(Path(self.tmp.name) / 'state.db')
        self.worker = Worker('openrouter', frozenset({'code'}), True, True, True, 2, 60)
        self.policy = Policy(enabled=True, zero_spend_account_verified=True, allowed_models=('test:free',), model='test:free', max_tokens=128)
        self.helper = FakeHelper()

    def run_task(self, policy=None, task_id='one', helper=None):
        return execute('Write Python', task_id, policy or self.policy, self.worker, self.ledger, now=100, helper=helper or self.helper)

    def test_requires_explicit_account_protection_before_any_call(self):
        for p in (Policy(), Policy(enabled=True, allowed_models=('test:free',), model='test:free'), Policy(enabled=True, zero_spend_account_verified=True, allowed_models=('paid',), model='paid')):
            with self.assertRaises(AdapterError): self.run_task(p)
        self.assertEqual(self.helper.calls, 0)

    def test_one_request_and_duplicate_not_sent_again(self):
        result = self.run_task()
        self.assertEqual(result.code, 'answer = 42\n')
        self.assertEqual(result.usage['prompt_tokens'], 12)
        with self.assertRaises(AdapterError): self.run_task()
        self.assertEqual(self.helper.calls, 1)

    def test_invalid_code_and_truncation_are_rejected(self):
        for n, reply in enumerate(({'content': 'bad syntax !', 'model': 'test:free', 'usage': {}, 'finish_reason': 'stop'}, {'content': 'ok', 'model': 'test:free', 'usage': {}, 'finish_reason': 'length'})):
            with self.assertRaises(AdapterError): self.run_task(task_id=str(n), helper=FakeHelper(reply))

    def test_failed_request_blocks_future_tasks_and_hides_secret(self):
        helper = FakeHelper(error='429 secret-token')
        with self.assertRaises(AdapterError) as caught: self.run_task(helper=helper)
        self.assertNotIn('secret-token', str(caught.exception))
        with self.assertRaises(AdapterError): self.run_task(task_id='two')
        self.assertEqual(self.helper.calls, 0)

    def test_refuses_paid_fallback_returned_by_provider(self):
        helper = FakeHelper({'content':'answer=1', 'model':'paid', 'usage':{}, 'finish_reason':'stop'})
        with self.assertRaises(AdapterError): self.run_task(helper=helper)
