"""One two-speaker Gemini TTS call per episode -> 24 kHz mono WAV. No retries: stop on any HTTP error (429 included).
Usage: python tts.py EPISODE_DIR OUT.wav"""
import base64, json, os, subprocess, sys, wave
sys.path.insert(0, os.path.abspath(sys.argv[1]))
from script import prompt, VOICES
URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent"
cfg = [{"speaker": n, "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": v}}} for n, v in VOICES.values()]
body = {"contents": [{"parts": [{"text": prompt()}]}],
        "generationConfig": {"responseModalities": ["AUDIO"],
                             "speechConfig": {"multiSpeakerVoiceConfig": {"speakerVoiceConfigs": cfg}}}}
# the network proxy injects the real key; the header value is a placeholder
r = subprocess.run(["curl", "-sS", "-m", "400", "-w", "\n%{http_code}", "-X", "POST", URL, "-H", "Content-Type: application/json",
                    "-H", "x-goog-api-key: placeholder", "-d", json.dumps(body)], capture_output=True, text=True)
out, code = r.stdout.rsplit("\n", 1)
if code != "200": sys.exit(f"HTTP {code}: {out[:300]}")
data = json.loads(out)["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
with wave.open(sys.argv[2], "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(base64.b64decode(data))
print("ok", sys.argv[2])
