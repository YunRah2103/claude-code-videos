# BMW heated seats (Yub) — "Would you pay monthly for something already in your car?"

Vertical skit (1080x1920, 30 fps, ~45 s, 6 scenes). Same buyer (Fenrir), captions, camera, whip pans and mix chain as
bmw-heated-seats / platform-ladder; new BMW salesman (Charon, silver hair, light-grey suit). Real 2023 BMW X1 photos and
the real BMW roundel from Wikimedia Commons (`assets/`, credits in out/bmw-heated-seats-yub/CREDITS.txt). Background music
is the user-supplied track (path via `MUSIC`, default `~/.cache/bmw-yub/music.mp3`, starts at `MUSIC_START`=1.0 s), ducked
under the dialogue. Oddity: penguin under a heat lamp in every set. Gag: the seat padlock (snaps on, pops open, hops to the
bonnet on "Remote start").

```bash
source .venv/bin/activate; cd videos/bmw-heated-seats-yub/src; C=~/.cache/bmw-yub
python tts.py $C/raw.wav                                       # one two-speaker Gemini call (Charon + Fenrir)
ffmpeg -i $C/raw.wav -ar 16000 -ac 1 -f s16le $C/raw16.raw && python align.py $C/raw16.raw $C/raw_words.json
python retime.py $C/raw.wav $C/raw_words.json $C/voice.wav words.json
python render.py meta ../../../out/bmw-heated-seats-yub/meta.json
python render.py video $C/voice.wav ../../../out/bmw-heated-seats-yub/bmw_heated_seats.mp4
```
Alignment: 114 words, 110 plausible by align.py's duration check (the 4 others are short "a"/"I").
