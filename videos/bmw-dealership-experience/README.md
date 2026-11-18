# BMW dealership experience — "Would you pay a monthly fee for heated seats?"

Vertical skit (1080x1920, 30 fps, ~70 s, 7 scenes). New series format: a whole-brand dealership walk. Same buyer
(Fenrir), same caption system, camera and mix chain as bmw-heated-seats; new BMW salesman (Orus): charcoal suit,
pale-blue shirt, BMW-blue tie, roundel lapel pin, silver hair, deadpan lids.

Real cars on one display platform (CC photos, background removed with rembg, see FACTS.md): M5 -> 3 Series (slides in
at scene 3) -> Z4 M40i (slides in on "Now,"). Pop-up props: Active Sound Design speaker, seat photo, $18/month tag, price
card + "SEATS: OFF" stamp, hardware/warmth chips, Z4 spec chips, Supra photo + same/same/same/different chips, SOLD
stamp. Hard cuts between wide/close framings in the showroom; whip pan to the front desk. No overlay before ~11 s;
the first label ("M5") pops at ~4.9 s.

Oddities (never mentioned, one per scene): penguin in a bow tie mopping; cactus in headphones bopping; pineapple in
sunglasses under a heat lamp; hamster wheel powering a floor lamp; giraffe head through a ceiling tile; octopus polishing
the platform with four cloths; goat in a headset at the front-desk computer.

`src/`: copied from bmw-heated-seats. `tts.py` skips the call if the WAV is cached; `align.py` adds model-name spellings
and a per-phone duration floor (30 ms per phone, the decoder's 3-frame minimum) for the plausibility score; `retime.py`
new holds; `render.py` new showroom/platform, cast, scenes, props, oddities, audio cues.

```bash
source .venv/bin/activate; cd videos/bmw-dealership-experience/src; C=~/.cache/bmw-dealership-experience
python tts.py $C/raw.wav                                       # one two-speaker Gemini call (Orus + Fenrir)
ffmpeg -i $C/raw.wav -ar 16000 -ac 1 -f s16le $C/raw16.raw && python align.py $C/raw16.raw $C/raw_words.json
python retime.py $C/raw.wav $C/raw_words.json $C/voice.wav words.json
python render.py meta ../../../out/bmw-dealership-experience/meta.json
python render.py video $C/voice.wav ../../../out/bmw-dealership-experience/bmw_dealership_experience.mp4
cd ../../..; python tools/preflight.py out/bmw-dealership-experience/bmw_dealership_experience.mp4 \
  --meta out/bmw-dealership-experience/meta.json --words videos/bmw-dealership-experience/src/words.json \
  --facts videos/bmw-dealership-experience/FACTS.md --align-pct 98.8
```
Alignment: 158/160 words plausible (98.8%) with the per-phone floor; 151/160 (94.4%) with the old fixed 60 ms floor —
the 9 extra flags were all one-phone "a"/"the" at 30–60 ms.

## v2 polish (after a weak first upload)
- Environment rebuilt (`bg_bmw`): glass window bays with a blurred city view and reflection streaks, graphite slatted
  feature wall with a backlit roundel and glowing lettering, ceiling LED strips and downlights, M-stripe and cove light
  along the wall base, glossy floor with the wall reflected in it and perspective tile joints, planters, a chrome-rim
  turntable with an animated LED chase ring, car reflections and contact shadows, periodic light sweeps over the cars.
  Front desk: glossy white counter with M-stripe and blue underglow, lit monitor.
- Editing: a cut per line to whoever is speaking (`SHOTS`), medium shot for prop moments, wide for car swaps, and a car
  close-up that rattles with the M5 rev. Pacing tightened in `retime.py` (63.3 s of dialogue, was 67.4 s).
- Engine: the user's M5 Competition exhaust recording replaces the synth rev (2.5 s clear beat after "Listen to that
  engine", ducked under the next line; a thin high-passed copy under "The volume is assisted"). The file stays outside
  git at `~/.cache/bmw-dealership-experience/m5_engine.opus`.
