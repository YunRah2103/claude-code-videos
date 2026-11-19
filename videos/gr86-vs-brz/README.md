# GR86 vs BRZ — "Wait... my Toyota was built by Subaru?"

Vertical skit (1080x1920, 30 fps, ~42 s, 6 scenes) on the shared showroom engine `videos/showroom-kit/` (same buyer,
Fenrir/Orus voices, captions and mix chain as bmw-heated-seats). Toyota showroom; the real GR86 and BRZ sit on a
glossy platform and slide out/in on each topic change. Hook: the car is already sliding on frame 1, the first word lands at
0.30 s, and nothing but captions is on screen before 3 s. `src/script.py` holds the lines, `src/show.py` the cars,
cards and gags. Background gags (never mentioned): two sheep on a filing cabinet, a penguin, a knight mopping,
a snail racing a tortoise, a marble bust that turns to watch, an octopus polishing the platform.

```bash
source .venv/bin/activate; K=videos/showroom-kit; C=~/.cache/gr86-vs-brz; O=out/gr86-vs-brz
python $K/prep_photos.py toyota_gr86 subaru_brz                      # once: cut-outs -> ~/.cache/showroom/cars
cd videos/gr86-vs-brz/src
python ../../showroom-kit/tts.py $C/raw.wav                                   # ONE two-speaker Gemini call
ffmpeg -i $C/raw.wav -ar 16000 -ac 1 -f s16le $C/raw16.raw && python ../../showroom-kit/align.py $C/raw16.raw $C/raw_words.json
python ../../showroom-kit/retime.py $C/raw.wav $C/raw_words.json $C/voice.wav words.json
python render.py meta ../../../$O/meta.json
python render.py video $C/voice.wav ../../../$O/gr86_vs_brz.mp4
python render.py thumb ../../../$O/gr86_vs_brz_thumb.png
cd ../../..; python tools/preflight.py $O/gr86_vs_brz.mp4 --meta $O/meta.json \
  --words videos/gr86-vs-brz/src/words.json --facts videos/gr86-vs-brz/FACTS.md --align-pct 100
python $K/prep_photos.py credits $O/CREDITS.txt toyota_gr86 subaru_brz
```
Alignment: 94/94 words plausible by `align.py`'s token-aware duration check (100%).
