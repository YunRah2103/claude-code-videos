#!/usr/bin/env python3
"""Minimal read-only MCP bridge: Claude Sonnet can ask local Ollama Qwen for code.

No generated code is executed or written to files by this bridge.
No Claude/Anthropic account, model or API configuration is changed.
"""
import json
import sys
import urllib.error
import urllib.request

BASE = "http://127.0.0.1:11434"
MODEL = "smtek/Qwen3.8-27B:Q3_K_M"
MAX_PROMPT = 20000
TOOLS = [
    {
        "name": "qwen_status",
        "description": "Check whether locally running Ollama has the Qwen 27B model. No generation.",
        "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
    },
    {
        "name": "qwen_generate_code",
        "description": (
            "Ask the local Qwen 27B worker to generate code for a specific task. "
            "Text only: never modifies files or executes code. Claude reviews the result. "
            "Use when the user asks to delegate coding to Qwen."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Focused coding task with acceptance criteria."},
                "context": {"type": "string", "description": "Optional non-secret relevant source excerpts."},
                "deep_thinking": {
                    "type": "boolean",
                    "description": "Enable extended reasoning for complex work (default: false; may take much longer).",
                    "default": False,
                },
            },
            "required": ["task"],
            "additionalProperties": False,
        },
    },
]


def ollama_json(path, payload=None, timeout=10):
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        BASE + path, data=data, method="POST" if data is not None else "GET",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)


def tool_result(message, is_error=False):
    return {"content": [{"type": "text", "text": str(message)}], "isError": is_error}


def execute_tool(name, args):
    if not isinstance(args, dict):
        return tool_result("Arguments must be an object.", True)
    try:
        if name == "qwen_status":
            data = ollama_json("/api/tags")
            names = [item.get("name", "") for item in data.get("models", [])]
            return tool_result(
                f"Local Ollama reachable at {BASE}. Model {MODEL} installed: {MODEL in names}."
            )
        if name == "qwen_generate_code":
            task, context = args.get("task"), args.get("context", "")
            deep_thinking = args.get("deep_thinking", False)
            if not isinstance(deep_thinking, bool):
                return tool_result("deep_thinking must be a boolean.", True)
            if not isinstance(task, str) or not task.strip() or len(task) > MAX_PROMPT:
                return tool_result("task must be non-empty and <= 20000 characters.", True)
            if not isinstance(context, str) or len(context) > MAX_PROMPT:
                return tool_result("context must be a string <= 20000 characters.", True)
            prompt = (
                "You are a focused coding worker. Solve only this task. "
                "Begin the final response with complete runnable code, not plans or reasoning. "
                "Follow the task\u0027s requested output format; only add short instructions after the code. "
                "Do not claim files were created, commands run, tests passed, or videos rendered. "
                "Do not invent missing project context.\n\n"
                f"TASK:\n{task.strip()}\n\nRELEVANT CONTEXT:\n{context}\n"
            )
            data = ollama_json("/api/generate", {
                "model": MODEL, "prompt": prompt, "stream": False,
                "think": deep_thinking,
                # -1 removes the artificial 2,500-token output cap. The model
                # still has its configured context/memory limits.
                "options": {"num_predict": -1},
            }, timeout=3600)
            answer = data.get("response", "")
            if not isinstance(answer, str) or not answer.strip():
                reason = "Qwen returned only reasoning and no final code." if data.get("thinking") else "Qwen returned an empty response."
                return tool_result(reason, True)
            count = data.get("eval_count") or 0
            duration = data.get("eval_duration") or 0
            speed = f"{count / (duration / 1e9):.1f}" if duration else "unknown"
            truncated = data.get("done_reason") == "length"
            suffix = "\nWARNING: Ollama stopped at a length/context limit; verify completeness." if truncated else ""
            return tool_result(
                "UNTRUSTED LOCAL QWEN OUTPUT — Claude must review before use:\n"
                + answer
                + f"\n\nTokens generated: {count}. Eval rate: {speed} tok/s."
                + "\nThis tool did not create files or run commands."
                + suffix,
                is_error=truncated,
            )
        return tool_result(f"Unknown tool: {name}", True)
    except (OSError, TimeoutError, urllib.error.URLError, ValueError, json.JSONDecodeError) as exc:
        return tool_result(
            f"Local Ollama request failed ({type(exc).__name__}). "
            "Confirm Ollama is running on this computer. Nothing was changed.",
            True,
        )


def dispatch(message):
    method, params = message.get("method"), message.get("params") or {}
    if method == "initialize":
        return {
            "protocolVersion": "2025-03-26", "capabilities": {"tools": {}},
            "serverInfo": {"name": "local-qwen-worker", "version": "0.1.0"},
        }
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call":
        return execute_tool(params.get("name"), params.get("arguments") or {})
    raise ValueError("Method not found")


def main():
    for line in sys.stdin:
        try:
            message = json.loads(line)
            if "id" not in message:  # MCP notifications have no response
                continue
            try:
                result = dispatch(message)
                reply = {"jsonrpc": "2.0", "id": message["id"], "result": result}
            except (ValueError, KeyError, AttributeError):
                reply = {
                    "jsonrpc": "2.0", "id": message["id"],
                    "error": {"code": -32601, "message": "Method not found"},
                }
            print(json.dumps(reply, ensure_ascii=False), flush=True)
        except (ValueError, TypeError):
            print(json.dumps({
                "jsonrpc": "2.0", "id": None,
                "error": {"code": -32700, "message": "Parse error"},
            }), flush=True)


if __name__ == "__main__":
    main()
