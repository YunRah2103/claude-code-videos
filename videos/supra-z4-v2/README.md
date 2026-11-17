# Supra / Z4 v2 — new hook

Partial redo of `videos/supra-z4` (~41 s, 1080x1920, 30 fps). Only the opening changes: the buyer's first line is a
first-person problem ("I bought a Toyota Supra and it has a BMW engine?!"), the first word lands by 0.3 s, and the
Supra/Z4 photo cards, "=" chip, "BMW B58" label and "BMW?!" stamp wait until the hook has landed (`T_HOOK`, >= 3 s).
Everything else (cast, showroom, parts counter with the cat gag, Graz line, cards, captions, SFX, mix) is v1.

Changes vs v1: `script.py` line 0 (+ direction for an instant first line); `retime.py` trims the raw lead-in;
`render.py` gates scene-1 overlays at `T_HOOK` and reads photos from `../supra-z4/assets`. `tts.py`, `align.py`,
`sfx.py` unchanged.

```bash
source .venv/bin/activate; cd videos/supra-z4-v2/src; C=~/.cache/supra-z4-v2
python tts.py $C/raw.wav
ffmpeg -i $C/raw.wav -ar 16000 -ac 1 -f s16le $C/raw16.raw && python align.py $C/raw16.raw $C/raw_words.json
python retime.py $C/raw.wav $C/raw_words.json $C/voice.wav words.json
python render.py meta ../../../out/supra-z4-v2/meta.json
python render.py video $C/voice.wav ../../../out/supra-z4-v2/supra_z4_v2.mp4
cd ../../..; python tools/preflight.py out/supra-z4-v2/supra_z4_v2.mp4 --meta out/supra-z4-v2/meta.json \
  --words videos/supra-z4-v2/src/words.json --facts videos/supra-z4-v2/FACTS.md --align-pct 100
```
`--align-pct 100`: all 87 words force-aligned in order and every aligned span is voiced. The stricter duration
heuristic in `align.py` reports 93.1% (six reduced "a"/"the" at 40–60 ms, below its 60 ms floor), as in platform-ladder v1.
