"""One single-voice Gemini TTS call -> 24 kHz mono WAV. No retries: stop on any HTTP error (incl. 429).
python tts.py NAME out.wav"""
import base64, json, subprocess, sys, wave
from script import prompt, VOICE
URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent"
body = {"contents": [{"parts": [{"text": prompt(sys.argv[1])}]}],
        "generationConfig": {"responseModalities": ["AUDIO"],
                             "speechConfig": {"voiceConfig": {"prebuiltVoiceConfig": {"voiceName": VOICE}}}}}
# the network proxy injects the real key; the header value is a placeholder
r = subprocess.run(["curl", "-sS", "-m", "240", "-w", "\n%{http_code}", "-X", "POST", URL, "-H", "Content-Type: application/json",
                    "-H", "x-goog-api-key: placeholder", "-d", json.dumps(body)], capture_output=True, text=True)
out, code = r.stdout.rsplit("\n", 1)
if code != "200": sys.exit(f"HTTP {code}: {out[:300]}")
data = json.loads(out)["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
with wave.open(sys.argv[2], "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(base64.b64decode(data))
print("ok", sys.argv[2])
