"""Documentary narration with Gemini TTS: the whole script as ONE clip (natural pacing).

  python3 tts.py OUT_DIR [VOICE]       -> OUT_DIR/vo_<VOICE>.wav (24 kHz mono)
"""
import base64, json, subprocess, sys, time, wave
from pathlib import Path

import timing

MODELS = ["gemini-2.5-pro-preview-tts", "gemini-2.5-flash-preview-tts"]
STYLE = ("Narrate this like a premium documentary: calm, measured and authoritative, with quiet gravitas. "
         "Unhurried but not slow, crisp consonants, short natural pauses between sentences, no hype. "
         "Say 'V12' as 'vee twelve' and 'F1' as 'eff one'. Read exactly this:\n\n")

def synth(text, dst, voice, model):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    body = {"contents": [{"parts": [{"text": STYLE + text}]}],
            "generationConfig": {"responseModalities": ["AUDIO"],
                                 "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": voice}}}}}
    # the network proxy injects the real key; the header value here is a placeholder
    r = subprocess.run(["curl", "-sS", "-m", "180", "-X", "POST", url, "-H", "Content-Type: application/json",
                        "-H", "x-goog-api-key: placeholder", "-d", json.dumps(body)], capture_output=True, text=True, check=True)
    d = json.loads(r.stdout)
    if "candidates" not in d:
        raise RuntimeError(d.get("error", {}).get("message", str(d)[:300]))
    part = d["candidates"][0]["content"]["parts"][0]["inlineData"]
    with wave.open(str(dst), "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(base64.b64decode(part["data"]))

if __name__ == "__main__":
    out = Path(sys.argv[1]); out.mkdir(parents=True, exist_ok=True)
    voice = sys.argv[2] if len(sys.argv) > 2 else "Charon"
    dst = out / f"vo_{voice}.wav"
    for model in MODELS:
        for attempt in range(3):
            try:
                synth(timing.SCRIPT, dst, voice, model)
                with wave.open(str(dst)) as w: print(voice, model, round(w.getnframes() / 24000, 2), "s ->", dst)
                sys.exit(0)
            except RuntimeError as e:
                print(model, "attempt", attempt, "failed:", e, file=sys.stderr); time.sleep(8 * 2 ** attempt)
    sys.exit("TTS failed on every model")
