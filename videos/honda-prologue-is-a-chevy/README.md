# Honda Prologue is a Chevy — "Wait... my Honda is a Chevy?"

Vertical skit (1080x1920, 30 fps, ~45 s, 6 scenes) on the shared showroom engine `videos/showroom-kit/` (same buyer,
Fenrir/Orus voices, captions and mix chain as bmw-heated-seats). Honda showroom; the real Prologue and Blazer EV sit on a
glossy platform and slide out/in on each topic change. Hook: the car is already sliding on frame 1, the first word lands at
0.30 s, and nothing but captions is on screen before 3 s. `src/script.py` holds the lines, `src/show.py` the cars,
cards and gags. Background gags (never mentioned): shark fin in the floor, mime in an invisible box, UFO beaming up a
traffic cone, pigeon in a hard hat with a clipboard, a lone disco dancer, a snowman in a hot tub.

```bash
source .venv/bin/activate; K=videos/showroom-kit; C=~/.cache/honda-prologue-is-a-chevy; O=out/honda-prologue-is-a-chevy
python $K/prep_photos.py honda_prologue chevy_blazer_ev                      # once: cut-outs -> ~/.cache/showroom/cars
cd videos/honda-prologue-is-a-chevy/src
python ../../showroom-kit/tts.py $C/raw.wav                                   # ONE two-speaker Gemini call
ffmpeg -i $C/raw.wav -ar 16000 -ac 1 -f s16le $C/raw16.raw && python ../../showroom-kit/align.py $C/raw16.raw $C/raw_words.json
python ../../showroom-kit/retime.py $C/raw.wav $C/raw_words.json $C/voice.wav words.json
python render.py meta ../../../$O/meta.json
python render.py video $C/voice.wav ../../../$O/honda_prologue_is_a_chevy.mp4
python render.py thumb ../../../$O/honda_prologue_is_a_chevy_thumb.png
cd ../../..; python tools/preflight.py $O/honda_prologue_is_a_chevy.mp4 --meta $O/meta.json \
  --words videos/honda-prologue-is-a-chevy/src/words.json --facts videos/honda-prologue-is-a-chevy/FACTS.md --align-pct 98.1
python $K/prep_photos.py credits $O/CREDITS.txt honda_prologue chevy_blazer_ev
```
Alignment: 103/105 words plausible by `align.py`'s duration check (98.1%).
