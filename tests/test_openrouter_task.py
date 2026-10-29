"""Offline tests for tools/openrouter_task.py; no OpenRouter requests are made."""
import contextlib
import io
import json
import sys
import tempfile
import unittest
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import openrouter_task as task  # noqa: E402

GOOD_BODY = {
    "model": "cohere/north-mini-code:free",
    "choices": [{"finish_reason": "stop", "message": {"content": "```python\nprint(1)\n```"}}],
    "usage": {"completion_tokens": 3, "cost": 0},
}


class FakeResponse:
    def __init__(self, status, body):
        self.status = status
        self._body = json.dumps(body).encode()

    def read(self, size=-1):
        return self._body[:size] if size >= 0 else self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeOpener:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def __call__(self, request, timeout):
        self.calls.append(request)
        if self.error:
            raise self.error
        return self.response


def rate_limit_error():
    return urllib.error.HTTPError(task.ENDPOINT, 429, "Too Many Requests", {"Retry-After": "7"}, None)


class OpenRouterTaskTest(unittest.TestCase):
    def test_only_free_models_are_allowed(self):
        self.assertTrue(task.is_free_model("cohere/north-mini-code:free"))
        self.assertTrue(task.is_free_model("openrouter/free"))
        with self.assertRaises(task.TaskError):
            task.build_payload("hi", "openai/gpt-4o")

    def test_payload_defaults_and_limits(self):
        payload = task.build_payload("hi")
        self.assertEqual(payload["model"], task.DEFAULT_MODEL)
        self.assertEqual(payload["max_tokens"], 8192)
        self.assertFalse(payload["stream"])
        with self.assertRaises(task.TaskError):
            task.build_payload("hi", max_tokens=8193)

    def test_request_carries_no_authorization_header(self):
        opener = FakeOpener(FakeResponse(200, GOOD_BODY))
        task.send(task.build_payload("hi"), opener)
        self.assertIsNone(opener.calls[0].get_header("Authorization"))

    def test_auth_failure_is_classified_and_not_retried(self):
        opener = FakeOpener(error=urllib.error.HTTPError(task.ENDPOINT, 401, "no", {}, None))
        with self.assertRaisesRegex(task.TaskError, "authentication or permission"):
            task.send(task.build_payload("hi"), opener)
        self.assertEqual(len(opener.calls), 1)

    def test_timeout_is_reported_without_retry(self):
        opener = FakeOpener(error=TimeoutError())
        with self.assertRaisesRegex(task.TaskError, "timed out"):
            task.send(task.build_payload("hi"), opener)
        self.assertEqual(len(opener.calls), 1)

    def test_non_json_success_body_is_a_task_error(self):
        class TextResponse(FakeResponse):
            def read(self, size=-1):
                return b"<html>proxy page</html>"

        opener = FakeOpener(TextResponse(200, {}))
        with self.assertRaisesRegex(task.TaskError, "non-JSON"):
            task.send(task.build_payload("hi"), opener)

    def test_truncated_reply_is_rejected(self):
        body = {"choices": [{"finish_reason": "length", "message": {"content": "def f("}}]}
        with self.assertRaises(task.TaskError):
            task.parse_reply(200, body)

    def test_api_error_is_reported(self):
        with self.assertRaises(task.TaskError):
            task.parse_reply(200, {"error": {"message": "no"}})

    def test_rate_limit_is_reported_and_not_retried(self):
        opener = FakeOpener(error=rate_limit_error())
        with self.assertRaisesRegex(task.TaskError, "429"):
            task.send(task.build_payload("hi"), opener)
        self.assertEqual(len(opener.calls), 1)

    def test_extract_code_prefers_fenced_block(self):
        self.assertEqual(task.extract_code("prose\n```python\nx = 1\n```\n"), "x = 1\n")
        self.assertEqual(task.extract_code("x = 2"), "x = 2\n")

    def test_dry_run_sends_nothing(self):
        opener = FakeOpener(error=rate_limit_error())
        with tempfile.TemporaryDirectory() as tmp:
            task_file = Path(tmp) / "task.txt"
            task_file.write_text("SECRET_PROMPT_DO_NOT_LOG")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = task.main(["--task", str(task_file), "--output", str(Path(tmp) / "x.py"), "--dry-run"], opener)
        self.assertEqual(code, 0)
        self.assertEqual(opener.calls, [])
        self.assertIn("max_tokens", out.getvalue())
        self.assertNotIn("SECRET_PROMPT_DO_NOT_LOG", out.getvalue())

    def test_main_refuses_unsupervised_live_request(self):
        opener = FakeOpener(FakeResponse(200, GOOD_BODY))
        with tempfile.TemporaryDirectory() as tmp:
            task_file = Path(tmp) / "task.txt"
            task_file.write_text("write code")
            output = Path(tmp) / "sub" / "x.py"
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                code = task.main(["--task", str(task_file), "--output", str(output)], opener)
            self.assertNotEqual(code, 0)
            self.assertFalse(output.exists())
            self.assertEqual(opener.calls, [])

    def test_output_inside_production_tree_is_refused(self):
        opener = FakeOpener(FakeResponse(200, GOOD_BODY))
        with tempfile.TemporaryDirectory() as tmp:
            task_file = Path(tmp) / "task.txt"
            task_file.write_text("write code")
            with contextlib.redirect_stderr(io.StringIO()):
                code = task.main(["--task", str(task_file), "--output", str(ROOT / "tools" / "x.py")], opener)
        self.assertEqual(code, 1)
        self.assertEqual(opener.calls, [])


class BoundedTransportTests(unittest.TestCase):
    def test_response_size_limit_and_timeout(self):
        calls = []
        class LargeResponse:
            status = 200
            def __enter__(self): return self
            def __exit__(self, *args): return False
            def read(self, size=-1):
                calls.append(size)
                return b'x' * size
        def opener(request, timeout):
            self.assertLessEqual(timeout, 60)
            return LargeResponse()
        with self.assertRaises(task.TaskError) as caught:
            task.send(task.build_payload('x'), opener)
        self.assertEqual(caught.exception.code, 'RESPONSE_TOO_LARGE')
        self.assertEqual(calls, [task.MAX_RESPONSE_BYTES + 1])

    def test_timeout_has_stable_code_and_unknown_delivery(self):
        opener = FakeOpener(error=TimeoutError('SECRET'))
        with self.assertRaises(task.TaskError) as caught:
            task.send(task.build_payload('x'), opener)
        self.assertEqual(caught.exception.code, 'REQUEST_TIMEOUT')
        self.assertIsNone(caught.exception.response_received)
        self.assertNotIn('SECRET', str(caught.exception))

    def test_network_error_does_not_expose_reason(self):
        opener = FakeOpener(error=urllib.error.URLError('SECRET_CREDENTIAL'))
        with self.assertRaises(task.TaskError) as caught:
            task.send(task.build_payload('x'), opener)
        self.assertEqual(caught.exception.code, 'NETWORK_FAILURE')
        self.assertNotIn('SECRET_CREDENTIAL', str(caught.exception))
        self.assertEqual(len(opener.calls), 1)


if __name__ == "__main__":
    unittest.main()
