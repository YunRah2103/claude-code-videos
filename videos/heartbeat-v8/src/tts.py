"""ONE Gemini TTS generation (voice Orus) -> out/heartbeat-v8/vo.wav. No retry loop: on HTTP 429 it stops."""
import base64, json, subprocess, sys, wave
from pathlib import Path

import os
MODEL = os.environ.get("TTS_MODEL", "gemini-2.5-flash-preview-tts")
URL = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent"
SCRIPT = ("A heart beats about once a second. This engine fires about 560 times a second. "
          "Every piston flips direction roughly 280 times a second. It's a BMW M3, built to scream like a race car. "
          "Loud petrol V8 or silent electric? Pick one.")
STYLE = ("Read as a fast, clear, intense documentary narrator. Punch the numbers five hundred sixty and two hundred "
         "eighty. Drop your pitch on the word scream. Sound curious on the final question. Text: ")

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
