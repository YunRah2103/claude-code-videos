# Yub cinematic low-poly shorts (ioniq_fake_gears, gm_carplay, jeep_wave)

Matched to the owner's "how matrix headlights work" reference: smooth-shaded low-poly 3D, soft sun shadows (PCF shadow map), SSAO, glossy paint
with fresnel sky reflections, bloom, additive light beams and glow sprites, depth of field, ACES tonemap. Pure numpy renderer (`src/render3d.py`)
at 810x1440, upscaled to 1080x1920 with crisp text drawn on top (`src/engine3d.py`: hook card, one-word captions, text-collision check, mix).
`src/yub.py` is the main character (white tee, black jeans, middle part, silver glasses, black LTN cap), `src/cars3d.py` the cars
(Ioniq 5 N, Blazer EV, Wrangler JL, Willys MB, Model 3), `src/props3d.py` the shared props. Facts and sources: `SUMMARY.md`.

```bash
source .venv/bin/activate; cd videos/yub-cine/src; C=~/.cache/yub3; n=ioniq   # or gm / jeep
python tts.py $n $C/${n}_raw.wav            # ONE Gemini call; exits on any HTTP error incl. 429
ffmpeg -i $C/${n}_raw.wav -ar 16000 -ac 1 -f s16le $C/${n}16.raw && python align.py $n $C/${n}16.raw $C/${n}_rw.json
python retime.py $n $C/${n}_raw.wav $C/${n}_rw.json $C/${n}_voice.wav ${n}_words.json   # first word 0.30 s, <=34 s
python $n.py sheet ../../../out/${n}_sheet.png; python $n.py check
python $n.py video $C/${n}_voice.wav ../../../out/yub3/music_full.wav ../../../out/yub3/<name>.mp4   # music: Hot Swing (incompetech), 48 kHz stereo wav
```
