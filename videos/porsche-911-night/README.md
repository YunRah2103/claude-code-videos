# Night Run // 911

27.5 s vertical (1080x1920, 30 fps) pixel-art drive of a 2017 Porsche 911 (991.2 Carrera 4S)
through a rainy neon city, in the style of the supplied lo-fi pixel reference video.

Native canvas 360x640, nearest-neighbour 3x. Original synth soundtrack (96 bpm, cuts on bar lines)
with rain, thunder and a flat-six engine keyed to each shot.

| Time | Shot |
|---|---|
| 0–5 s | Teal dusk causeway: mega-tower, power lines, diner, flooded-road reflections |
| 5–10 s | Neon ramen street: hero shop, flickering signs, car cruises past |
| 10–15 s | Close tracking pan along the car, wing deploys, "CARRERA 4S" |
| 15–20 s | Blue overpass, lightning, traffic on the deck |
| 20–27.5 s | Rear chase down a neon canyon, car pulls away, "911" title |

```bash
cd videos/porsche-911-night/src
python ../../../tools/video.py preview --src . --out ../../../out/911/preview
python render.py video ../../../out/911/porsche_911_night_run.mp4
```

Car proportions: `car911.py` (metres; checked against Wikimedia Commons 991 photos).
