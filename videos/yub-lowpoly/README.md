# Yub low-poly shorts (Toyota key fob, Tesla Acceleration Boost, Veyron tyres)

Three vertical shorts (1080x1920, 30 fps, about 24.5 s each) in the PS1 low-poly narrated style of `ferrari-purrari`
and `rolls-royce-pinstripe`. The renderer `src/lowpoly.py`, plus `models.py`, `fmodels.py` and `sfx.py`, is copied
unchanged from `ferrari-purrari`. New files:
`ymodels.py` (RAV4, Model 3, Veyron, logos, props and the oddities), `engine.py` (shots, captions, sheet, meta, mix),
`toyota.py` / `tesla.py` / `veyron.py` (shots, captions, SFX cues), `script.py` (the three narrations), `tts.py`,
`align.py` and `retime.py`, the last three generalised to take a video NAME. Facts, sources and the music credit are
in `SUMMARY.md`.

```bash
source .venv/bin/activate; cd videos/yub-lowpoly/src; C=~/.cache/yub; n=toyota   # or tesla / veyron
python tts.py $n $C/${n}_raw.wav            # ONE Gemini call; exits on any HTTP error incl. 429 (no retry)
ffmpeg -i $C/${n}_raw.wav -ar 16000 -ac 1 -f s16le $C/${n}16.raw && python align.py $n $C/${n}16.raw $C/${n}_rw.json
python retime.py $n $C/${n}_raw.wav $C/${n}_rw.json $C/${n}_voice.wav ${n}_words.json   # <=24.5 s, first word 0.33 s
python $n.py sheet ../../../out/yub/${n}_sheet.png       # preview: one frame per shot
# music bed: Kevin MacLeod "Hep Cats" (CC BY 4.0) from incompetech.com -> out/yub/music.wav (48 kHz stereo)
../render_all.sh                                          # renders all three into out/yub/
```
Captions start at 3.0 s, so nothing is drawn over the picture in the first 3 seconds.
