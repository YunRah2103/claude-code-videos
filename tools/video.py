"""Small local tools; verbose output and image processing never need LLM tokens."""
import argparse
import ast
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "videos/new-car-trap/src"


def run_logged(command, log, cwd=None):
    log = Path(log).resolve()
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("wb") as stream:
        result = subprocess.run(command, cwd=cwd, stdout=stream, stderr=subprocess.STDOUT)
    with log.open("rb") as stream:
        stream.seek(max(0, log.stat().st_size - 4000))
        tail = stream.read().decode("utf-8", errors="replace").splitlines()[-20:]
    print(f"exit={result.returncode}; full log: {log}")
    print("\n".join(tail))
    return result.returncode if result.returncode >= 0 else 128 - result.returncode


def doctor():
    missing = []
    for name in ("ffmpeg", "ffprobe", "rg"):
        found = shutil.which(name)
        print(f"{name}: {found or 'MISSING'}")
        if not found:
            missing.append(name)
    for name in ("PIL", "numpy", "pocketsphinx"):
        found = importlib.util.find_spec(name) is not None
        print(f"{name}: {'OK' if found else 'MISSING'}")
        if not found:
            missing.append(name)
    if os.environ.get("CLAUDE_CODE_REMOTE") == "true":
        print("Ponytail: hosted cloud cannot load plugins; CLAUDE.md fallback provided")
    elif shutil.which("claude"):
        result = subprocess.run(["claude", "plugin", "list", "--json"],
                                text=True, capture_output=True)
        if result.returncode:
            print("Ponytail: could not inspect installation; run claude plugin list")
        else:
            plugins = json.loads(result.stdout)
            found = any(p.get("id") == "ponytail@ponytail" and p.get("enabled")
                        for p in plugins)
            print(f"Ponytail: {'installed and enabled' if found else 'NOT INSTALLED; run bash tools/setup.sh'}")
    else:
        print("Ponytail: CLI absent here; local install needs claude; cloud uses CLAUDE.md fallback")
    return int(bool(missing))


def preview(source, output, times):
    source = Path(source).resolve()
    module = ast.parse((source / "render.py").read_text())
    durations = [n.value.value for n in module.body if isinstance(n, ast.Assign)
                 and any(isinstance(t, ast.Name) and t.id == "DUR" for t in n.targets)
                 and isinstance(n.value, ast.Constant)
                 and type(n.value.value) in (int, float)]
    if not durations or not math.isfinite(durations[0]) or durations[0] <= 0:
        raise ValueError("render.py must declare a positive numeric DUR constant")
    duration = durations[0]
    if times is None:
        times = [duration * fraction for fraction in (.03, .22, .35, .55, .75, .91)]
    if not all(math.isfinite(t) and 0 <= t < duration for t in times):
        raise ValueError(f"Preview times must be finite and in [0, {duration}) seconds")
    from PIL import Image, ImageDraw
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    stamps = [str(t) for t in times]
    code = run_logged([sys.executable, "render.py", "still", str(output), *stamps],
                      output / "render.log", cwd=source)
    if code:
        return code
    rows = math.ceil(len(times) / 3)
    sheet = Image.new("RGB", (810, rows * 510), "#171923")
    draw = ImageDraw.Draw(sheet)
    for i, stamp in enumerate(stamps):
        x, y = (i % 3) * 270, (i // 3) * 510
        with Image.open(output / f"f_{stamp}.png") as frame:
            sheet.paste(frame.resize((270, 480), Image.Resampling.NEAREST), (x, y))
        draw.text((x + 10, y + 488), f"{stamp}s", fill="white")
    sheet.save(output / "sheet.jpg", quality=93)
    print(f"Preview sheet: {output / 'sheet.jpg'}")
    return 0


def probe(media):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                             "format=duration:stream=codec_type,codec_name,width,height,avg_frame_rate,sample_rate,channels",
                             "-of", "json", str(media)], capture_output=True, text=True)
    if result.returncode:
        print(result.stderr[-1000:], file=sys.stderr)
        return result.returncode
    print(json.dumps(json.loads(result.stdout), indent=2))
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    run = commands.add_parser("run", help="Keep full log, show bounded tail, preserve failure")
    run.add_argument("--log", required=True)
    run.add_argument("command", nargs=argparse.REMAINDER)
    commands.add_parser("doctor", help="Check tools and render dependencies")
    frames = commands.add_parser("preview", help="Render example explainer stills and a compact sheet")
    frames.add_argument("--src", default=SOURCE, help="Episode src directory containing render.py")
    frames.add_argument("--out", default="out/preview")
    frames.add_argument("--times", type=float, nargs="+", help="Seconds; default: six points across the episode")
    metadata = commands.add_parser("probe", help="Read only useful media metadata")
    metadata.add_argument("media")
    args = parser.parse_args()
    try:
        if args.action == "run":
            command = args.command[1:] if args.command[:1] == ["--"] else args.command
            if not command:
                parser.error("run needs a command after --")
            return run_logged(command, args.log)
        if args.action == "doctor":
            return doctor()
        if args.action == "preview":
            return preview(args.src, args.out, args.times)
        return probe(args.media)
    except (OSError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
