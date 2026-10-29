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

    def read(self):
        return self._body

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
            task_file.write_text("write code")
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = task.main(["--task", str(task_file), "--output", str(Path(tmp) / "x.py"), "--dry-run"], opener)
        self.assertEqual(code, 0)
        self.assertEqual(opener.calls, [])
        self.assertIn("max_tokens", out.getvalue())

    def test_main_writes_code_to_output(self):
        opener = FakeOpener(FakeResponse(200, GOOD_BODY))
        with tempfile.TemporaryDirectory() as tmp:
            task_file = Path(tmp) / "task.txt"
            task_file.write_text("write code")
            output = Path(tmp) / "sub" / "x.py"
            with contextlib.redirect_stdout(io.StringIO()):
                code = task.main(["--task", str(task_file), "--output", str(output)], opener)
            self.assertEqual(code, 0)
            self.assertEqual(output.read_text(), "print(1)\n")

    def test_output_inside_production_tree_is_refused(self):
        opener = FakeOpener(FakeResponse(200, GOOD_BODY))
        with tempfile.TemporaryDirectory() as tmp:
            task_file = Path(tmp) / "task.txt"
            task_file.write_text("write code")
            with contextlib.redirect_stderr(io.StringIO()):
                code = task.main(["--task", str(task_file), "--output", str(ROOT / "tools" / "x.py")], opener)
        self.assertEqual(code, 1)
        self.assertEqual(opener.calls, [])


if __name__ == "__main__":
    unittest.main()
