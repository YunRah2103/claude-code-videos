# Car stuff, explained: tyre wear bars

"Your tyres have hidden bars that tell you when to replace them." 13.0 s, 1080x1920, 30 fps,
H.264 + AAC 192k. Native art 135x240 (32-colour indexed, raised from 16 at your request),
upscaled x8 nearest-neighbour only.

Visuals: the presenter drives a pixel hatchback along a lively daytime town street. Parallax
layers move in whole-pixel steps: clouds, far blocks, shops/trees/lamps, pedestrians, birds, the
road and the front pavement with a dog-walker and planters. The car stops at a red light and the
front tyre's wear bar lights up. A HUD scan analyses the car, punches in x2/x4 and cuts to the tread
close-up. The NEW/WORN analysis panel sits over the live street. The car pulls away on green as
the NEXT EPISODE card slides in.

## Commands (from `videos/tyre-wear-bars/src`)

```bash
O=../../../out/tyre-wear-bars
python3 tts.py                 # Gemini TTS, voice Fenrir: 1 cached request (cache/script_*.wav)
python3 tts.py --alt           # shorter line-4 candidates: 1 cached request (cache/alt4_*.wav)
python3 audio.py               # trim, fit to slots (max +8% tempo), SFX, build/mix.wav + timing.json
python ../../../tools/video.py preview --src . --out $O/preview      # stills sheet
python3 render.py video $O     # master_silent_yuv444.mp4 (lossless) + final.mp4
python3 verify.py $O           # verify_report.md, zoom4x_tyre.png, zoom4x_bar.png
```

`tts.py` never re-requests a cached take (the cache key is model + voice + full prompt). It
retries 429/5xx with exponential backoff and respects Retry-After. It stops with a clear message
when the quota is exhausted. The key comes from `GEMINI_API_KEY` and is never printed. Put your
shared style prompt in `src/style_prompt.txt`. Changing it makes one new request.

## Files

| File | Role |
|---|---|
| `src/render.py` | palette, street parallax, car + presenter, tyre (RotSprite 16 angles), HUD scenes, encode |
| `src/audio.py` | VO fitting, square-wave SFX (ping 1.5 s, click 7.97 s, blip 11.0 s), mix |
| `src/tts.py` | Gemini TTS with cache and backoff |
| `src/verify.py` | pass/fail checks |
| `src/fonts/` | Press Start 2P (OFL, licence included) |
| `src/cache/` | raw TTS takes (24 kHz WAV). Split lines are rebuilt from these without requests. |

## VO timing (slot / start / fit)

| Line | Slot | Start | Fit |
|---|---|---|---|
| 1 "Look in the grooves of your tyre. There's a hidden wear bar." | 0-3 | 0.00 | pause shortened, x1.066 tempo |
| 2 "Every tyre has them. The sidewall mark shows where." | 3-6 | 3.12 | pause shortened, x1.007 |
| 3 "When the tread is level with the bar, you're at the limit." | 6-9 | 6.04 | as is |
| 4 **DRAFT** "Find TWI. Check the groove." | 9-11 | 9.03 | as is |
| 5 "Have you ever looked for yours?" | 11-13 | 11.04 | as is |

Line 4 as written ("Find TWI, look in the groove. Ten seconds. Don't wait until it's flush.")
is 4.3 s of speech for a 2.0 s slot. That would need about 2.2x speed, so it was not used.
The render uses the first two sentences of a cached alternative take. This needs approval.
