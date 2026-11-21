"""One two-speaker Gemini TTS call per scene (Buyer=Fenrir, Salesman=Schedar) -> 24 kHz mono WAV.
Usage: python tts.py SCENE OUT.wav. No retries: stop on any HTTP error (429 included)."""
import base64, json, subprocess, sys, wave
from script import prompt, VOICES
URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-tts:generateContent"
cfg = [{"speaker": n, "voiceConfig": {"prebuiltVoiceConfig": {"voiceName": v}}} for n, v in VOICES.values()]
body = {"contents": [{"parts": [{"text": prompt(int(sys.argv[1]))}]}],
        "generationConfig": {"responseModalities": ["AUDIO"],
                             "speechConfig": {"multiSpeakerVoiceConfig": {"speakerVoiceConfigs": cfg}}}}
# the network proxy injects the real key; the header value is a placeholder
r = subprocess.run(["curl", "-sS", "-m", "240", "-w", "\n%{http_code}", "-X", "POST", URL, "-H", "Content-Type: application/json",
                    "-H", "x-goog-api-key: placeholder", "-d", json.dumps(body)], capture_output=True, text=True)
out, code = r.stdout.rsplit("\n", 1)
if code != "200": sys.exit(f"HTTP {code}: {out[:300]}")
data = json.loads(out)["candidates"][0]["content"]["parts"][0]["inlineData"]["data"]
with wave.open(sys.argv[2], "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(24000); w.writeframes(base64.b64decode(data))
print("ok", sys.argv[2])
