"""Generate one Gemini TTS (voice Fenrir) clip per script line: vo/line_NN.wav (24 kHz mono)."""
import base64, json, subprocess, sys, time, wave
from pathlib import Path

URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent"
STYLE = "Read this like an energetic, punchy explainer narrator, clear and confident: "

def synth(text, dst):
    body = {"contents": [{"parts": [{"text": STYLE + text}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": "Fenrir"}}}}}
    # the network proxy injects the real key; the header value here is a placeholder
    r = subprocess.run(["curl", "-sS", "-m", "120", "-X", "POST", URL, "-H", "Content-Type: application/json",
                        "-H", "x-goog-api-key: placeholder", "-d", json.dumps(body)], capture_output=True, text=True, check=True)
    d = json.loads(r.stdout)
    if "candidates" not in d:
        raise RuntimeError(d.get("error", {}).get("message", str(d)[:300]))
    part = d["candidates"][0]["content"]["parts"][0]["inlineData"]
    with wave.open(str(dst), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(base64.b64decode(part["data"]))

if __name__ == "__main__":
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    only = {int(a) for a in sys.argv[2:]}
    for i, line in enumerate(json.load(open(Path(__file__).with_name("script.json")))):
        dst = out / f"line_{i:02d}.wav"
        if (only and i not in only) or (not only and dst.exists()): continue
        for attempt in range(4):                      # transient rate limits: back off 5, 10, 20 s
            try:
                synth(line, dst); break
            except RuntimeError as e:
                print(i, "retry after:", e, file=sys.stderr); time.sleep(5 * 2 ** attempt)
        else:
            sys.exit(f"line {i} failed")
        with wave.open(str(dst)) as w: print(i, round(w.getnframes() / 24000, 2), "s")
