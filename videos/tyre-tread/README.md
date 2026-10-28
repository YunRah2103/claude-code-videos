# Why Tyres Have Tread

TikTok explainer (16.2s, 1080x1920, 60fps): tread grooves push water out so the tyre grips;
bald tyres hydroplane; legal minimum 1.6 mm; check with a coin (on-screen end card).

Built from the `new-car-trap` baseline. New in `src/pix.py`: side-view `tyre`, front `tread`,
`cloud`, `drop`. New in `src/sfx.py`: `splash`, `rain`, `thunder`, `skid`.
`src/voiceover.mp3` is the supplied voiceover (it ends at "1.6 millimetres").

```bash
cd videos/tyre-tread/src
ffmpeg -i voiceover.mp3 -ar 16000 -ac 1 -f s16le vo16k.raw
python align.py vo16k.raw words.json           # only if the voiceover changes
python render.py still ../../../out/tyre-tread 4.6 9.9
python render.py video voiceover.mp3 ../../../out/tyre-tread/tyre_tread.mp4
```
