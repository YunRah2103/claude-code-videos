# Supra / Z4 — "Is it still a real Supra?"

Vertical skit (1080x1920, 30 fps, ~41 s). Same cast, captions, camera and mix chain as tesla-locked / aston-cygnet /
urus-rsq8; `src/render.py` is built on `urus-rsq8/src/render.py` (branch `ccr-39b55cd6-nh196m`) with new scenes:
Toyota showroom (user photos of the GR Supra and BMW Z4), parts counter, Graz factory line, back to the showroom.
Background gag (never mentioned): a cat on the top shelf paws boxes onto the parts clerk.

```bash
cd videos/supra-z4/src
python tts.py ~/.cache/supra-z4/raw.wav                      # one two-speaker Gemini call (Orus + Fenrir)
ffmpeg -i ~/.cache/supra-z4/raw.wav -ar 16000 -ac 1 -f s16le raw16.raw && python align.py raw16.raw raw_words.json
python retime.py ~/.cache/supra-z4/raw.wav raw_words.json ~/.cache/supra-z4/voice.wav words.json
python render.py meta ../../../out/supra-z4/meta.json
python render.py video ~/.cache/supra-z4/voice.wav ../../../out/supra-z4/supra_z4.mp4
python ../../../tools/preflight.py ../../../out/supra-z4/supra_z4.mp4 --meta ../../../out/supra-z4/meta.json \
  --words words.json --facts ../FACTS.md --align-pct 96.5
```
