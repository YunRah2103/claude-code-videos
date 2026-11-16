"""ONE Gemini TTS generation (voice Orus) -> out/tyre-patch/vo.wav. No retry loop: on HTTP 429 it stops."""
import base64, json, subprocess, sys, wave
from pathlib import Path

import os
MODEL = os.environ.get("TTS_MODEL", "gemini-2.5-flash-preview-tts")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
SCRIPT = ("Everything a car does, speeding up, braking, turning, goes through four patches of rubber. "
          "Each one is about the size of your hand. "
          "All four together? Barely a sheet of paper. "
          "At a hundred kilometres an hour, each tyre spins about fourteen times a second. "
          "And that's all that's holding you to the road.")
STYLE = ("Read as a confident, cinematic documentary narrator, brisk pace for a short video, no long pauses. "
         "Lean into 'size of your hand' and 'fourteen times a second'. Say the last sentence slower and quieter. Text: ")

if __name__ == "__main__":
    dst = Path(sys.argv[1])
    if dst.exists():
        sys.exit(f"cached: {dst}")
    body = {"contents": [{"parts": [{"text": STYLE + SCRIPT}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Orus"}}}}}
    r = subprocess.run(["curl", "-sS", "-m", "180", "-w", "\n%{http_code}", "-X", "POST", URL,
                        "-H", "Content-Type: application/json", "-H", "x-goog-api-key: placeholder",
                        "-d", json.dumps(body)], capture_output=True, text=True)
    text, code = r.stdout.rsplit("\n", 1)
    if code != "200":
        msg = text[:300]
        Path(str(dst) + ".error.txt").write_text(text)
        sys.exit(f"HTTP {code}: stopping (no retry). {msg}")
    part = json.loads(text)["candidates"][0]["content"]["parts"][0]["inlineData"]
    dst.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(dst), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(base64.b64decode(part["data"]))
    with wave.open(str(dst)) as w:
        print("ok", round(w.getnframes() / 24000, 2), "s")
