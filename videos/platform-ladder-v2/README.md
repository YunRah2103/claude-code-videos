# Platform ladder v2 — new hook

Partial redo of `videos/platform-ladder` (~42 s, 1080x1920, 30 fps). Only the opening changes: the buyer's first line now
carries the price shock ("...with a two-hundred-thousand-dollar Lamborghini?!"), the first word lands by 0.3 s, and the
scene-1 photo cards, "SAME PLATFORM: MLB EVO" chip and "THE CHEAP ONE" stamp wait until the hook has landed (>= 3 s).
Everything else (cast, showrooms, five background oddities, cards, ladder, captions, SFX, mix) is v1.

Changes vs v1: `script.py` line 0 (+ direction for an instant first line); `align.py` splits the compound into two
caption words; `retime.py` trims the raw lead-in (first word at 0.27 s); `render.py` gates scene-1 overlays at
`T_HOOK` and reads photos from `../platform-ladder/assets`. `tts.py`, `sfx.py` unchanged.

```bash
source .venv/bin/activate; cd videos/platform-ladder-v2/src; C=~/.cache/platform-ladder-v2
python tts.py $C/raw.wav
ffmpeg -i $C/raw.wav -ar 16000 -ac 1 -f s16le $C/raw16.raw && python align.py $C/raw16.raw $C/raw_words.json
python retime.py $C/raw.wav $C/raw_words.json $C/voice.wav words.json
python render.py meta ../../../out/platform-ladder-v2/meta.json
python render.py video $C/voice.wav ../../../out/platform-ladder-v2/platform_ladder_v2.mp4
cd ../../..; python tools/preflight.py out/platform-ladder-v2/platform_ladder_v2.mp4 --meta out/platform-ladder-v2/meta.json \
  --words videos/platform-ladder-v2/src/words.json --facts videos/platform-ladder-v2/FACTS.md --align-pct 95.9
```
`--align-pct 95.9`: all 73 words force-aligned in order; 70/73 pass the 60 ms–1.2 s duration check in `align.py`.
