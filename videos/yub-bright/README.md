# Yub bright low-poly shorts (jeep_wave, ioniq_fake_gears, gm_carplay)

Bright daytime low-poly 3D shorts at 1080x1920, 30 fps and under 25 s. They star Yub, the skit character rebuilt in 3D in `src/hero.py`: a rounded superellipsoid head, a middle-part curtain fringe, 3D glasses, nose and ears, and an anti-aliased 256 px face with 11 expressions.
The renderer `src/lowpoly.py` comes from yub-lowpoly. It now renders at full output resolution and uses a bright grade with no vignette. `src/engine.py` adds a hook card from frame 0, fixed large captions with a text-collision check, and a louder music bed. The bed is Hot Swing with a rock backbeat locked to its 144 BPM grid. `src/cars.py` holds the Wrangler, Willys MB, Ioniq 5 N, Equinox EV, the logos and the oddities. Facts and sources are in `SUMMARY.md`.

```bash
source .venv/bin/activate; cd videos/yub-bright/src; C=~/.cache/yub2; n=jeep   # or ioniq / gm
python tts.py $n $C/${n}_raw.wav            # ONE Gemini call; exits on any HTTP error incl. 429 (no retry)
ffmpeg -i $C/${n}_raw.wav -ar 16000 -ac 1 -f s16le $C/${n}16.raw && python align.py $n $C/${n}16.raw $C/${n}_rw.json
python retime.py $n $C/${n}_raw.wav $C/${n}_rw.json $C/${n}_voice.wav ${n}_words.json   # first word at 0.30 s, <=24.8 s
python $n.py sheet ../../../out/yub2/${n}_sheet.png; python $n.py check                 # preview + text overlap/clip check
# music: incompetech.com "Hot Swing" mp3 -> ffmpeg -ar 48000 -ac 2 out/yub2/music_full.wav
python $n.py video $C/${n}_voice.wav ../../../out/yub2/music_full.wav ../../../out/yub2/<name>.mp4
```
