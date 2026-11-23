# Car Ads vs Reality (long-form, 1920x1080 @30, plus 3 vertical Shorts)

The buyer (series rig, Fenrir voice) brings 8 car ads; a new deadpan salesman (silver quiff, moustache, bow tie,
burgundy suit; Gemini "Schedar") reads him the fine print. Each claim scene: a whip to an original parody-ad cutaway,
then a whip to a location where the real CC photo plays on a screen. `render.py` imports the cast rig, `D` and easing
from `bmw-heated-seats/src/render.py`. `tts.py`/`align.py`/`retime.py` are the bmw versions, changed to one
Gemini call per scene. Facts: `FACTS.md`. Deliverable texts: `deliver/`. Photos: `assets/` (Commons, see
`deliver/CREDITS.txt`). Music: `music/` (Kevin MacLeod, CC BY 4.0).

```bash
source .venv/bin/activate; cd videos/car-ads-reality/src; C=~/.cache/car-ads-reality; O=../../../out/car-ads-reality
for s in 0 1 2 3 4 5 6 7 8; do python tts.py $s $C/raw$s.wav || break; sleep 20; done   # stops on HTTP 429, no retry
for s in 0 1 2 3 4 5 6 7 8; do ffmpeg -v error -y -i $C/raw$s.wav -ar 16000 -ac 1 -f s16le $C/raw16_$s.raw && python align.py $s $C/raw16_$s.raw $C/words$s.json; done
python retime.py $C $C/voice.wav words.json           # uses every scene present from 0
python render.py sheet $O/sheet.png                   # contact sheet first
python render.py video $C/voice.wav $O/car_ads_vs_reality.mp4
for n in 1 2 3; do python render.py short $n $C/voice.wav $O/car_ads_vs_reality_mix.wav $O/short$n.mp4; done
python render.py thumb $O/thumbnail.png; for n in 1 2 3; do python render.py sthumb $n $O/short${n}_thumb.png; done
```
State: all 9 scenes voiced (the free-tier cap is 10 TTS requests per day, so the run spanned two days).

Music files are not committed. To fetch them: `for n in "Monkeys Spinning Monkeys" "Fluffing a Duck" "Pixel Peeker Polka - faster" "Sneaky Snitch" "Investigations" "Volatile Reaction" "Local Forecast - Elevator"; do curl -so "music/${n// /_}.mp3" "https://incompetech.com/music/royalty-free/mp3-royaltyfree/${n// /%20}.mp3"; done`
