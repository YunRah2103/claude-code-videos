"""Offline tests for tools/gemini_task.py; no Gemini API requests are made."""
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

import gemini_task as task  # noqa: E402

GOOD_BODY = {
    "modelVersion": "gemini-2.5-flash",
    "candidates": [
        {
            "finishReason": "STOP",
            "content": {"parts": [{"text": "```python\nprint(1)\n```"}]},
        }
    ],
    "usageMetadata": {"promptTokenCount": 20, "candidatesTokenCount": 3},
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


def http_error(code, headers=None):
    return urllib.error.HTTPError(task.ENDPOINT, code, "err", headers or {}, None)


class ModelSelectionTest(unittest.TestCase):
    def test_flash_models_are_allowed(self):
        for model in ("gemini-2.5-flash", "gemini-2.5-flash-lite", "gemini-3-flash-preview", "gemini-3.6-flash"):
            with self.subTest(model=model):
                self.assertTrue(task.is_allowed_model(model))

    def test_billable_or_alias_models_are_rejected(self):
        for model in (
            "gemini-2.5-pro",
            "gemini-3.1-pro-preview",
            "gemini-flash-latest",
            "gemini-3-pro-image-preview",
            "gemini-2.5-flash-tts",
            "gemma-4-31b-it",
            "gemini-2.5-flash/../../x",
        ):
            with self.subTest(model=model):
                self.assertFalse(task.is_allowed_model(model))


class RequestTest(unittest.TestCase):
    def test_payload_shape_and_limits(self):
        payload = task.build_payload("hi")
        self.assertEqual(payload["generationConfig"]["maxOutputTokens"], 8192)
        self.assertEqual(payload["contents"][0]["parts"][0]["text"], "hi")
        with self.assertRaises(task.TaskError):
            task.build_payload("hi", max_tokens=8193)

    def test_endpoint_uses_selected_model(self):
        self.assertTrue(task.endpoint_for("gemini-2.5-flash").endswith("/models/gemini-2.5-flash:generateContent"))

    def test_request_carries_no_api_key_header(self):
        opener = FakeOpener(FakeResponse(200, GOOD_BODY))
        task.send(task.endpoint_for("gemini-2.5-flash"), task.build_payload("hi"), opener)
        request = opener.calls[0]
        self.assertIsNone(request.get_header("X-goog-api-key"))
        self.assertIsNone(request.get_header("Authorization"))

    def test_rate_limit_is_reported_and_not_retried(self):
        opener = FakeOpener(error=http_error(429, {"Retry-After": "9"}))
        with self.assertRaisesRegex(task.TaskError, "429"):
            task.send(task.endpoint_for("gemini-2.5-flash"), task.build_payload("hi"), opener)
        self.assertEqual(len(opener.calls), 1)

    def test_other_http_errors_are_reported(self):
        opener = FakeOpener(error=http_error(403))
        with self.assertRaisesRegex(task.TaskError, "HTTP 403"):
            task.send(task.endpoint_for("gemini-2.5-flash"), task.build_payload("hi"), opener)
        self.assertEqual(len(opener.calls), 1)


class ReplyTest(unittest.TestCase):
    def test_complete_reply_is_accepted(self):
        reply = task.parse_reply(200, GOOD_BODY)
        self.assertEqual(reply["finish_reason"], "STOP")
        self.assertIn("print(1)", reply["content"])

    def test_max_tokens_truncation_is_rejected(self):
        body = json.loads(json.dumps(GOOD_BODY))
        body["candidates"][0]["finishReason"] = "MAX_TOKENS"
        with self.assertRaisesRegex(task.TaskError, "incomplete"):
            task.parse_reply(200, body)

    def test_blocked_prompt_without_candidates_is_rejected(self):
        with self.assertRaisesRegex(task.TaskError, "no candidates"):
            task.parse_reply(200, {"promptFeedback": {"blockReason": "SAFETY"}})

    def test_api_error_body_is_reported_without_details(self):
        with self.assertRaisesRegex(task.TaskError, "API error"):
            task.parse_reply(400, {"error": {"status": "INVALID_ARGUMENT", "message": "secret detail"}})

    def test_empty_content_is_rejected(self):
        body = json.loads(json.dumps(GOOD_BODY))
        body["candidates"][0]["content"]["parts"] = [{"text": "   "}]
        with self.assertRaisesRegex(task.TaskError, "empty"):
            task.parse_reply(200, body)

    def test_parts_are_joined_in_order(self):
        body = json.loads(json.dumps(GOOD_BODY))
        body["candidates"][0]["content"]["parts"] = [{"text": "x = "}, {"text": "1"}]
        self.assertEqual(task.parse_reply(200, body)["content"], "x = 1")


class CodeExtractionTest(unittest.TestCase):
    def test_fenced_block_is_preferred(self):
        self.assertEqual(task.extract_code("prose\n```python\nx = 1\n```\n"), "x = 1\n")

    def test_unfenced_code_is_used_whole(self):
        self.assertEqual(task.extract_code("x = 2"), "x = 2\n")

    def test_missing_code_is_rejected(self):
        with self.assertRaisesRegex(task.TaskError, "no code"):
            task.extract_code("   ")


class MainTest(unittest.TestCase):
    def run_main(self, argv, opener):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = task.main(argv, opener)
        return code, out.getvalue(), err.getvalue()

    def test_dry_run_sends_nothing_and_omits_key(self):
        opener = FakeOpener(error=http_error(429))
        with tempfile.TemporaryDirectory() as tmp:
            task_file = Path(tmp) / "task.txt"
            task_file.write_text("write code")
            code, out, _ = self.run_main(["--task", str(task_file), "--output", str(Path(tmp) / "x.py"), "--dry-run"], opener)
        self.assertEqual(code, 0)
        self.assertEqual(opener.calls, [])
        self.assertIn("generateContent", out)
        self.assertNotIn("key", out.lower())

    def test_main_writes_code_to_output(self):
        opener = FakeOpener(FakeResponse(200, GOOD_BODY))
        with tempfile.TemporaryDirectory() as tmp:
            task_file = Path(tmp) / "task.txt"
            task_file.write_text("write code")
            output = Path(tmp) / "sub" / "x.py"
            code, out, _ = self.run_main(["--task", str(task_file), "--output", str(output)], opener)
            self.assertEqual(code, 0)
            self.assertEqual(output.read_text(), "print(1)\n")
        self.assertIn("finishReason=STOP", out)

    def test_paid_model_is_refused_before_any_request(self):
        opener = FakeOpener(FakeResponse(200, GOOD_BODY))
        with tempfile.TemporaryDirectory() as tmp:
            task_file = Path(tmp) / "task.txt"
            task_file.write_text("write code")
            code, _, err = self.run_main(
                ["--task", str(task_file), "--output", str(Path(tmp) / "x.py"), "--model", "gemini-2.5-pro"], opener
            )
        self.assertEqual(code, 1)
        self.assertEqual(opener.calls, [])
        self.assertIn("not an allowed", err)

    def test_output_inside_production_tree_is_refused(self):
        opener = FakeOpener(FakeResponse(200, GOOD_BODY))
        with tempfile.TemporaryDirectory() as tmp:
            task_file = Path(tmp) / "task.txt"
            task_file.write_text("write code")
            code, _, _ = self.run_main(["--task", str(task_file), "--output", str(ROOT / "tools" / "x.py")], opener)
        self.assertEqual(code, 1)
        self.assertEqual(opener.calls, [])


if __name__ == "__main__":
    unittest.main()
