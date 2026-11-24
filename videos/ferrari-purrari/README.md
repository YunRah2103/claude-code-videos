# Ferrari "Purrari": PS1 low-poly style test 2

A vertical short (1080x1920, 30 fps, 28.0 s) in the same PS1 low-poly narrated style as `rolls-royce-pinstripe`.
The renderer (`lowpoly.py`, `models.py`) and the TTS, alignment and retime scripts are reused from that video.
New in this one: `fmodels.py` (Ferrari 458, shield, rainbow-cat wrap, props), `render.py` (23 shots), and `mix.py`
(the first video's mix.py was never committed). Facts and sources are in `SUMMARY.md`.

```bash
cd videos/ferrari-purrari/src; C=~/.cache/fp
python tts.py $C/raw.wav                       # one Gemini call; stops on any HTTP error incl. 429
ffmpeg -i $C/raw.wav -ar 16000 -ac 1 -f s16le $C/raw16.raw && python align.py $C/raw16.raw $C/raw_words.json
# set raw_words.json[0].s = 0.17 (the aligner puts the first word at 0.0; the real onset is about 0.17 s)
python retime.py $C/raw.wav $C/raw_words.json $C/voice.wav words.json   # tempo 1.156 to 28 s, first word 0.33 s
python render.py sheet ../../../out/fp/sheet.png; python render.py meta ../../../out/fp/meta.json
python render.py thumb ../../../out/fp/thumbnail.png
python render.py video $C/voice.wav ../../../out/fp/ferrari_purrari.mp4
cd ../../..; python tools/preflight.py out/fp/ferrari_purrari.mp4 --meta out/fp/meta.json \
  --words videos/ferrari-purrari/src/words.json --facts videos/ferrari-purrari/SUMMARY.md --align-pct 94.6
```
Preflight: 11 of 12 pass. Alignment is 94.6% against a 95% gate: all 5 short words are "a", which the
fast read clips to 30–50 ms.
