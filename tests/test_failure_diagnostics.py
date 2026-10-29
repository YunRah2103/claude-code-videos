import json
import tempfile
import unittest
from pathlib import Path
from tools.agent_rotation.core import Ledger, Worker
from tools.agent_rotation.openrouter_adapter import AdapterError, Policy, execute
from test_openrouter_adapter import FakeHelper

class DiagnosticsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.ledger = Ledger(Path(self.tmp.name)/'db')
        self.worker = Worker('openrouter', frozenset({'code'}), True, True, True, 5, 60)
        self.policy = Policy(True, True, ('test:free',), 'test:free', 128)

    def run_failure(self, helper):
        with self.assertRaises(AdapterError) as ctx:
            execute('SECRET_PROMPT', 't1', self.policy, self.worker, self.ledger, now=100, helper=helper)
        return ctx.exception

    def test_syntax_failure_preserves_safe_usage(self):
        h = FakeHelper({'content':'SECRET_OUTPUT !', 'model':'test:free', 'finish_reason':'stop',
                        'usage':{'prompt_tokens':12,'completion_tokens':4,'total_tokens':16,'cost':0}})
        e = self.run_failure(h)
        self.assertEqual(e.failure_code, 'PYTHON_SYNTAX_INVALID')
        self.assertTrue(e.response_received)
        self.assertEqual(e.usage['total_tokens'], 16)
        self.assertNotIn('SECRET', str(e))
        self.assertIsNone(e.__context__)
        self.assertFalse(self.ledger.available(self.worker, 10000))
        self.assertEqual(h.calls, 1)
        with self.assertRaises(AdapterError): execute('again', 't1', self.policy, self.worker, self.ledger, now=10000, helper=h)
        self.assertEqual(h.calls, 1)

    def test_timeout_is_uncertain_and_no_usage_is_invented(self):
        class TimeoutHelper(FakeHelper):
            def send(self, payload):
                self.calls += 1
                raise TimeoutError('SECRET')
        h = TimeoutHelper()
        e = self.run_failure(h)
        self.assertEqual(e.failure_code, 'REQUEST_TIMEOUT')
        self.assertIsNone(e.response_received)
        self.assertIsNone(e.usage['cost'])
        self.assertNotIn('SECRET', str(e))
        self.assertIsNone(e.__context__)

    def test_failure_classifications(self):
        cases = [({'content':'x','model':'wrong','finish_reason':'stop'}, 'UNEXPECTED_MODEL'),
                 ({'content':'x','model':'test:free','finish_reason':'length'}, 'INCOMPLETE_GENERATION'),
                 ({'content':'','model':'test:free','finish_reason':'stop'}, 'EMPTY_GENERATED_CONTENT')]
        for i, (reply, code) in enumerate(cases):
            ledger = Ledger(Path(self.tmp.name)/f'db{i}')
            with self.assertRaises(AdapterError) as ctx:
                execute('x','t',self.policy,self.worker,ledger,now=100,helper=FakeHelper(reply))
            self.assertEqual(ctx.exception.failure_code, code)

    def test_transport_and_decoding_classification(self):
        import urllib.error
        cases = [(urllib.error.URLError('private'), 'NETWORK_FAILURE'),
                 (json.JSONDecodeError('private', 'secret', 0), 'RESPONSE_DECODING_FAILED'),
                 (urllib.error.HTTPError('https://invalid', 429, 'secret', {}, None), 'HTTP_FAILURE')]
        for i, (exception, expected) in enumerate(cases):
            class Broken(FakeHelper):
                def send(self, payload):
                    self.calls += 1
                    raise exception
            helper = Broken()
            ledger = Ledger(Path(self.tmp.name)/f'transport{i}')
            with self.assertRaises(AdapterError) as caught:
                execute('secret prompt','t',self.policy,self.worker,ledger,now=100,helper=helper)
            self.assertEqual(caught.exception.failure_code, expected)
            self.assertNotIn('private', str(caught.exception))
            self.assertEqual(helper.calls, 1)
            self.assertFalse(ledger.available(self.worker, 10000))

    def test_missing_usage_remains_unknown(self):
        helper = FakeHelper({'content':'answer=1', 'model':'test:free', 'finish_reason':'stop'})
        result = execute('x','t',self.policy,self.worker,self.ledger,now=100,helper=helper)
        self.assertIsNone(result.usage['cost'])
        self.assertIsNone(result.usage['prompt_tokens'])

    def test_nested_reported_reasoning_tokens_are_retained(self):
        helper = FakeHelper({'content':'x=1', 'model':'test:free', 'finish_reason':'stop',
                             'usage':{'completion_tokens_details':{'reasoning_tokens':3}}})
        result = execute('x','t',self.policy,self.worker,self.ledger,now=100,helper=helper)
        self.assertEqual(result.usage['reasoning_tokens'], 3)

    def test_invalid_response_and_cost_are_rejected(self):
        for i, reply in enumerate(({'choices': []}, {'content':'x=1','model':'test:free','finish_reason':'stop','usage':{'cost': 'private'}})):
            with self.assertRaises(AdapterError) as caught:
                execute('x','t',self.policy,self.worker,Ledger(Path(self.tmp.name)/f'bad{i}'),now=100,helper=FakeHelper(reply))
            self.assertEqual(caught.exception.failure_code, 'INVALID_PROVIDER_RESPONSE')
            self.assertNotIn('private', str(caught.exception))

    def test_legacy_unstructured_errors_fail_closed_without_messages(self):
        class TaskError(Exception): pass
        cases = [('request timed out; the server may still have processed it, so not retrying', 'REQUEST_TIMEOUT'),
                 ('HTTP 200 with a non-JSON body', 'RESPONSE_DECODING_FAILED'),
                 ('authentication or permission failure (HTTP 401); not retrying', 'HTTP_FAILURE'),
                 ('rate limited (HTTP 429, Retry-After=SECRET); not retrying', 'HTTP_FAILURE')]
        for i, (message, expected) in enumerate(cases):
            class Wrapped(FakeHelper):
                def send(self, payload): raise TaskError(message)
            with self.assertRaises(AdapterError) as caught:
                execute('x','t',self.policy,self.worker,Ledger(Path(self.tmp.name)/f'wrap{i}'),now=100,helper=Wrapped())
            self.assertEqual(caught.exception.failure_code, 'INTERNAL_ADAPTER_ERROR')
            self.assertNotIn('SECRET', str(caught.exception))

    def test_pr8_helper_real_response_pipeline_offline(self):
        try:
            from tools import openrouter_task as pr8
        except ImportError:
            self.skipTest('PR #8 helper is a separate dependency')
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, size=-1):
                return json.dumps({'model':'test:free', 'choices':[{'finish_reason':'stop',
                    'message':{'content':'SECRET_INVALID !'}}],
                    'usage':{'prompt_tokens':7,'completion_tokens':3,'total_tokens':10}}).encode()
        calls = []
        class Helper:
            build_payload = staticmethod(pr8.build_payload)
            parse_reply = staticmethod(pr8.parse_reply)
            extract_code = staticmethod(pr8.extract_code)
            @staticmethod
            def send(payload):
                def opener(request, timeout):
                    calls.append(1)
                    return Response()
                return pr8.send(payload, opener=opener)
        with self.assertRaises(AdapterError) as caught:
            execute('secret prompt', 't', self.policy, self.worker, self.ledger, now=100, helper=Helper())
        self.assertEqual(caught.exception.failure_code, 'PYTHON_SYNTAX_INVALID')
        self.assertEqual(caught.exception.usage['total_tokens'], 10)
        self.assertIsNone(caught.exception.usage['cost'])
        self.assertEqual(calls, [1])
        self.assertIsNone(caught.exception.__context__)

    def test_structured_helper_error_does_not_depend_on_message_text(self):
        try:
            from tools.openrouter_task import TaskError
        except ImportError:
            self.skipTest('hardened PR #8 helper is a separate dependency')
        class Wrapped(FakeHelper):
            def send(self, payload):
                raise TaskError('SECRET arbitrary wording', code='REQUEST_TIMEOUT')
        e = self.run_failure(Wrapped())
        self.assertEqual(e.failure_code, 'REQUEST_TIMEOUT')
        self.assertIsNone(e.response_received)
        self.assertNotIn('SECRET', str(e))

    def test_real_helper_timeout_produces_structured_diagnostic_offline(self):
        try:
            from tools import openrouter_task as pr8
        except ImportError:
            self.skipTest('hardened PR #8 helper is a separate dependency')
        class Helper:
            build_payload = staticmethod(pr8.build_payload)
            parse_reply = staticmethod(pr8.parse_reply)
            extract_code = staticmethod(pr8.extract_code)
            @staticmethod
            def send(payload):
                def timeout(request, timeout):
                    raise TimeoutError('secret')
                return pr8.send(payload, opener=timeout)
        error = self.run_failure(Helper())
        self.assertEqual(error.failure_code, 'REQUEST_TIMEOUT')
        self.assertIsNone(error.response_received)
        self.assertNotIn('secret', str(error))

    def test_real_helper_oversize_response_is_classified_without_content(self):
        try:
            from tools import openrouter_task as pr8
        except ImportError:
            self.skipTest('hardened PR #8 helper is a separate dependency')
        class Response:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, size=-1): return b'x' * size
        class Helper:
            build_payload = staticmethod(pr8.build_payload)
            parse_reply = staticmethod(pr8.parse_reply)
            extract_code = staticmethod(pr8.extract_code)
            @staticmethod
            def send(payload): return pr8.send(payload, opener=lambda request, timeout: Response())
        error = self.run_failure(Helper())
        self.assertEqual(error.failure_code, 'RESPONSE_TOO_LARGE')
        self.assertTrue(error.response_received)
        self.assertIsNone(error.usage['cost'])
