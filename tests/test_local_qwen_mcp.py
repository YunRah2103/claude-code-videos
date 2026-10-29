"""Offline tests for the optional local Qwen MCP bridge."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

PATH = Path(__file__).resolve().parents[1] / "tools" / "local_qwen_mcp.py"
spec = importlib.util.spec_from_file_location("local_qwen_mcp", PATH)
bridge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)


class LocalQwenTests(unittest.TestCase):
    def test_handshake(self):
        result = bridge.dispatch({"method": "initialize"})
        self.assertIn("tools", result["capabilities"])

    def test_tools(self):
        tools = bridge.dispatch({"method": "tools/list"})["tools"]
        self.assertEqual([t["name"] for t in tools], ["qwen_status", "qwen_generate_code"])

    def test_validation(self):
        with mock.patch.object(bridge, "ollama_json") as call:
            self.assertTrue(bridge.execute_tool("qwen_generate_code", {"task": ""})["isError"])
            self.assertTrue(bridge.execute_tool("qwen_generate_code", {"task": "hi", "context": 44})["isError"])
            call.assert_not_called()

    def test_status(self):
        with mock.patch.object(bridge, "ollama_json", return_value={
            "models": [{"name": bridge.MODEL}]
        }):
            self.assertIn("installed: True", bridge.execute_tool("qwen_status", {})["content"][0]["text"])

    def test_generate_returns_text(self):
        with mock.patch.object(bridge, "ollama_json", return_value={
            "response": "def wheel(): pass", "eval_count": 100, "eval_duration": 1e9
        }) as call:
            result = bridge.execute_tool("qwen_generate_code", {"task": "wheel"})
            self.assertFalse(result["isError"])
            self.assertIn("def wheel(): pass", result["content"][0]["text"])
            self.assertEqual(call.call_args.args[0], "/api/generate")

    def test_unavailable(self):
        with mock.patch.object(bridge, "ollama_json", side_effect=OSError("offline")):
            self.assertTrue(bridge.execute_tool("qwen_status", {})["isError"])

    def test_stdio(self):
        messages = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize"},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        ]
        run = subprocess.run(
            [sys.executable, str(PATH)],
            input="\n".join(json.dumps(x) for x in messages) + "\n",
            text=True, capture_output=True, check=True,
        )
        lines = [json.loads(x) for x in run.stdout.splitlines()]
        self.assertEqual([x["id"] for x in lines], [1, 2])


if __name__ == "__main__":
    unittest.main()
