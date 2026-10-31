#!/usr/bin/env python3
"""Read-only local llama.cpp Phase A diagnostic. Standard-library Python only."""
import base64
import json
import os
import pathlib
import random
import shutil
import struct
import sys
import time
import urllib.error
import urllib.request
import zlib

BASE = os.environ.get("QWEN_API_BASE", "http://127.0.0.1:8080").rstrip("/")
OUT = pathlib.Path.home() / "qwen_diagnostics"
OUT.mkdir(parents=True, exist_ok=True)
report = {"api_base": BASE, "checks": {}, "warnings": []}

def req(method, path, body=None, timeout=15):
    payload = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(BASE + path, data=payload, method=method,
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return json.load(response)

def result(name, status, **fields):
    report["checks"][name] = {"status": status, **fields}
    print(f"[{status.upper()}] {name}", flush=True)

def error(exc):
    if isinstance(exc, urllib.error.HTTPError):
        return f"HTTP {exc.code}: {exc.read(500).decode(errors='replace')}"
    return str(exc)[:500]

def png_square(rgb):
    # White background, black outlined square filled with a random colour.
    rows = []
    for y in range(128):
        row = bytearray()
        for x in range(128):
            inside = 28 <= x < 100 and 28 <= y < 100
            edge = inside and (x in (28, 29, 98, 99) or y in (28, 29, 98, 99))
            row.extend((0, 0, 0) if edge else rgb if inside else (255, 255, 255))
        rows.append(b"\0" + bytes(row))
    def chunk(tag, data):
        return (struct.pack("!I", len(data)) + tag + data +
                struct.pack("!I", zlib.crc32(tag + data) & 0xffffffff))
    return (b"\x89PNG\r\n\x1a\n" +
            chunk(b"IHDR", struct.pack("!2I5B", 128, 128, 8, 2, 0, 0, 0)) +
            chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) +
            chunk(b"IEND", b""))

def text_of(message):
    content = message.get("content", "")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return " ".join(item.get("text", "") for item in content if isinstance(item, dict))
    return str(content)

def finish():
    file = OUT / "phase_a_report.json"
    file.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"\nReport: {file}", flush=True)
    print("Share the report and llama-server's Vulkan/offload log lines.", flush=True)

def main():
    print("Phase A: no downloads, restarts, installs or model-generated code execution.")
    try:
        health = req("GET", "/health")
        if health.get("status") != "ok":
            raise RuntimeError(f"Unexpected health response: {health}")
        result("llama.cpp health", "pass", payload=health)
    except Exception as exc:
        result("llama.cpp health", "fail", error=error(exc))
        report["warnings"].append("Start your EXISTING llama-server; no download needed.")
        finish()
        return 1
    try:
        props = req("GET", "/props")
        (OUT / "server_props.json").write_text(json.dumps(props, indent=2), encoding="utf-8")
        ctx = props.get("default_generation_settings", {}).get("n_ctx")
        if not isinstance(ctx, int):
            ctx = props.get("n_ctx")
        result("backend context", "pass" if isinstance(ctx, int) else "unknown",
               backend_n_ctx=ctx, evidence="server_props.json")
    except Exception as exc:
        result("backend context", "unknown", error=error(exc))
    try:
        modeldata = req("GET", "/v1/models")
        ids = [entry["id"] for entry in modeldata.get("data", []) if entry.get("id")]
        if not ids:
            raise RuntimeError("No model IDs discovered")
        model = ids[0]
        result("model discovery", "pass", model_ids=ids)
    except Exception as exc:
        result("model discovery", "fail", error=error(exc))
        finish()
        return 1
    try:
        start = time.perf_counter()
        answer = req("POST", "/v1/chat/completions", {
            "model": model, "stream": False, "max_tokens": 120, "temperature": 0,
            "messages": [{"role": "user", "content":
                          "Give exactly three brief reasons why automotive wheels have spokes."}]
        }, timeout=240)
        elapsed = round(time.perf_counter() - start, 2)
        generated = text_of(answer["choices"][0]["message"])
        usage = answer.get("usage") or {}
        n = usage.get("completion_tokens")
        wall_rate = round(n / elapsed, 2) if isinstance(n, int) and elapsed > 0 else None
        result("text generation", "pass" if generated.strip() else "fail",
               answer=generated[:800], elapsed_seconds=elapsed, completion_tokens=n,
               wall_tokens_per_second=wall_rate,
               timing_details=answer.get("timings") or {})
    except Exception as exc:
        result("text generation", "fail", error=error(exc))
    try:
        colours = {"red": (235, 25, 30), "green": (0, 165, 60),
                   "blue": (20, 60, 240), "yellow": (255, 218, 20)}
        expected = random.SystemRandom().choice(list(colours))
        png = png_square(colours[expected])
        (OUT / "vision_test.png").write_bytes(png)
        data_uri = "data:image/png;base64," + base64.b64encode(png).decode("ascii")
        answer = req("POST", "/v1/chat/completions", {
            "model": model, "stream": False, "max_tokens": 128, "temperature": 0,
            "messages": [{"role": "user", "content": [
                {"type": "text", "text": "Look at the image. What is the fill colour of the large centre square? Reply with only the colour name."},
                {"type": "image_url", "image_url": {"url": data_uri}}
            ]}]
        }, timeout=240)
        reply = text_of(answer["choices"][0]["message"]).strip()
        result("vision image recognition", "pass" if expected in reply.lower() else "fail",
               expected_color=expected, model_answer=reply[:300],
               test_image="vision_test.png",
               note="Basic recognition only; not proof of advanced 3D reference matching.")
    except Exception as exc:
        result("vision image recognition", "fail", error=error(exc))
    found = []
    for exe in (shutil.which("blender"), shutil.which("blender.exe")):
        if exe and exe not in found:
            found.append(exe)
    for base in (pathlib.Path(r"C:\Program Files\Blender Foundation"),
                 pathlib.Path(r"C:\Program Files (x86)\Blender Foundation")):
        if base.exists():
            found.extend(str(p) for p in base.glob("Blender*/blender.exe") if str(p) not in found)
    result("Blender executable detection", "pass" if found else "unknown",
           paths=found, note="Blender may be installed in a nonstandard location.")
    report["warnings"] += [
        "GPU Vulkan offloading must be verified using llama-server startup logs and AMD metrics.",
        "Open WebUI connection requires a separate real UI text/image upload test.",
        "A recognition pass is not proof that Qwen will build accurate Blender geometry."
    ]
    finish()
    return 0

if __name__ == "__main__":
    sys.exit(main())
