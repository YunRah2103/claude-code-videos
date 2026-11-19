# Tesla FSD subscription — "I can't BUY Full Self-Driving anymore?"

Vertical skit (1080x1920, 30 fps, ~45 s, 6 scenes) on the shared showroom engine `videos/showroom-kit/` (same buyer,
Fenrir/Orus voices, captions and mix chain as bmw-heated-seats). Tesla showroom; the real Model Y sits on a
glossy platform and slides out/in on each topic change. Hook: the car is already sliding on frame 1, the first word lands at
0.30 s, and nothing but captions is on screen before 3 s. `src/script.py` holds the lines, `src/show.py` the cars,
cards and gags. Background gags (never mentioned): flamingo on a robot vacuum, goat on the roof chewing a brochure,
scuba diver reading a magazine, potted plant tiptoeing out, hot-air balloon with a cat, cow on a treadmill.

```bash
source .venv/bin/activate; K=videos/showroom-kit; C=~/.cache/tesla-fsd-subscription; O=out/tesla-fsd-subscription
python $K/prep_photos.py tesla_model_y                      # once: cut-outs -> ~/.cache/showroom/cars
cd videos/tesla-fsd-subscription/src
python ../../showroom-kit/tts.py $C/raw.wav                                   # ONE two-speaker Gemini call
ffmpeg -i $C/raw.wav -ar 16000 -ac 1 -f s16le $C/raw16.raw && python ../../showroom-kit/align.py $C/raw16.raw $C/raw_words.json
python ../../showroom-kit/retime.py $C/raw.wav $C/raw_words.json $C/voice.wav words.json
python render.py meta ../../../$O/meta.json
python render.py video $C/voice.wav ../../../$O/tesla_fsd_subscription.mp4
python render.py thumb ../../../$O/tesla_fsd_subscription_thumb.png
cd ../../..; python tools/preflight.py $O/tesla_fsd_subscription.mp4 --meta $O/meta.json \
  --words videos/tesla-fsd-subscription/src/words.json --facts videos/tesla-fsd-subscription/FACTS.md --align-pct 98.1
python $K/prep_photos.py credits $O/CREDITS.txt tesla_model_y
```
Alignment: 103/105 words plausible by `align.py`'s token-aware duration check (98.1%).
