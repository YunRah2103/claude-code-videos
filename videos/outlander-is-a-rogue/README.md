# Outlander is a Rogue — "Wait... my Mitsubishi is a Nissan?"

Vertical skit (1080x1920, 30 fps, ~44 s, 6 scenes) on the shared showroom engine `videos/showroom-kit/` (same buyer,
Fenrir/Orus voices, captions and mix chain as bmw-heated-seats). Mitsubishi showroom; the real Outlander and Rogue sit on a
glossy platform and slide out/in on each topic change. Hook: the car is already sliding on frame 1, the first word lands at
0.30 s, and nothing but captions is on screen before 3 s. `src/script.py` holds the lines, `src/show.py` the cars,
cards and gags. Background gags (never mentioned): a llama taking selfies, a dinosaur costume sipping tea,
a giraffe through the ceiling, a bear in a bathrobe, a chicken vending machine, a banana costume.

```bash
source .venv/bin/activate; K=videos/showroom-kit; C=~/.cache/outlander-is-a-rogue; O=out/outlander-is-a-rogue
python $K/prep_photos.py mitsubishi_outlander nissan_rogue                      # once: cut-outs -> ~/.cache/showroom/cars
cd videos/outlander-is-a-rogue/src
python ../../showroom-kit/tts.py $C/raw.wav                                   # ONE two-speaker Gemini call
ffmpeg -i $C/raw.wav -ar 16000 -ac 1 -f s16le $C/raw16.raw && python ../../showroom-kit/align.py $C/raw16.raw $C/raw_words.json
python ../../showroom-kit/retime.py $C/raw.wav $C/raw_words.json $C/voice.wav words.json
python render.py meta ../../../$O/meta.json
python render.py video $C/voice.wav ../../../$O/outlander_is_a_rogue.mp4
python render.py thumb ../../../$O/outlander_is_a_rogue_thumb.png
cd ../../..; python tools/preflight.py $O/outlander_is_a_rogue.mp4 --meta $O/meta.json \
  --words videos/outlander-is-a-rogue/src/words.json --facts videos/outlander-is-a-rogue/FACTS.md --align-pct 100
python $K/prep_photos.py credits $O/CREDITS.txt mitsubishi_outlander nissan_rogue
```
Alignment: 94/94 words plausible by `align.py`'s token-aware duration check (100%).
