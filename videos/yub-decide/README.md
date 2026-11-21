# yub-decide: "pick a side" skits (Cybertruck / used Range Rover / Civic Type R vs Golf R)

These are vertical skits (1080x1920, 30 fps, about 41–45 s, 6 scenes). They reuse the bmw-heated-seats cast, captions, camera, whip pans and mix chain. `src/base.py` is lifted from bmw-heated-seats/src/render.py. `render.py` adds:
- ten environments: showroom, drag strip, desert highway, workshop, rainy night street, used lot (day/dusk), country lane, finance office, race track, snowy mountain road
- cartoon Cybertruck, Range Rover L405, Civic Type R and Golf R
- three background oddities, one per episode
- Commons photo cards and logos
- the channel's music bed, ducked under the dialogue

`YUB_EP=cybertruck|range_rover|civic_golf` picks `src/ep_<EP>.py`, which holds the dialogue and the scene/overlay/cue data. Anchors such as `'11:fall'` and `'E3+.2'` are resolved against `src/words_<EP>.json`.

```bash
source .venv/bin/activate; cd videos/yub-decide/src; E=cybertruck; C=~/.cache/yub/$E; M=path/to/music.mp3; O=../../../out/yub/01_cybertruck
YUB_EP=$E python tts.py $C/raw.wav                         # ONE two-speaker Gemini call (Fenrir buyer, Orus salesman)
ffmpeg -i $C/raw.wav -ar 16000 -ac 1 -f s16le $C/raw16.raw && YUB_EP=$E python align.py $C/raw16.raw $C/raw_words.json
YUB_EP=$E python retime.py $C/raw.wav $C/raw_words.json $C/voice.wav words_$E.json   # first word at 0.30 s
YUB_EP=$E python render.py sheet $C/voice.wav $O/sheet.png  # 12-still contact sheet
YUB_EP=$E python render.py video $C/voice.wav $M $O/cybertruck.mp4 [SECONDS]
YUB_EP=$E python render.py thumb $O/cybertruck_thumb.png $C/voice.wav; YUB_EP=$E python render.py meta $O/meta.json
```
Facts and allowed numbers: `FACTS_<EP>.md`. Photo/logo sources: `assets/SOURCES.txt`.
