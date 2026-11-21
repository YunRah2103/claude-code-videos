# The real [Brand] dealership experience (series)

~100 s dialogue skits. `src/engine.py` is the shared renderer (cast, poses, lip sync, captions, camera, whip pans, cutaways,
music bed + SFX mix), lifted from `videos/bmw-heated-seats/src/render.py`. Each episode folder holds `script.py` (dialogue,
voices, holds, SPOKEN map), `scenes.py` (sets, photo displays, gags, overlays, cues), `words.json`, `assets/` (Wikimedia
Commons photos) and FACTS / CREDITS / script / captions.

```bash
source .venv/bin/activate; cd videos/real-dealership/src; E=tesla; C=~/.cache/real-dealership/$E; M=path/to/music.mp3
python tts.py ../$E $C/raw.wav                         # ONE two-speaker Gemini call; stops on any HTTP error
ffmpeg -i $C/raw.wav -ar 16000 -ac 1 -f s16le $C/raw16.raw && python align.py ../$E $C/raw16.raw $C/raw_words.json
python retime.py ../$E $C/raw.wav $C/raw_words.json $C/voice.wav ../$E/words.json
EPDIR=../$E python render.py sheet /tmp/sheet.png 1,10,20,30            # preview stills
EPDIR=../$E python render.py clip $C/voice.wav $M out.mp4 40 55         # short motion/audio check
EPDIR=../$E python render.py video $C/voice.wav $M ../../../out/real-dealership/$E.mp4
EPDIR=../$E python render.py thumb 22 thumb.png; EPDIR=../$E python render.py meta meta.json
python credits.py ../$E 'local.jpg=Commons file name' ...               # CREDITS.txt from the file pages
```
