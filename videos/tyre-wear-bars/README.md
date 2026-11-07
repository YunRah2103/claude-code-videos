# Car stuff, explained: tyre wear bars

"Your tyres have hidden bars that tell you when to replace them." 13.0 s, 1080x1920, 30 fps,
H.264 + AAC 192k. Native art 135x240 (32-colour indexed, raised from 16 at your request),
upscaled x8 nearest-neighbour only.

Visuals (timeline):
- 0-3 s hook: side-on hero tyre (~60% of frame width) with the bar already lit in the top groove,
  presenter crouched beside it, "HIDDEN" / "BAR" stacked headline, hazy street behind.
- 3-5 s zoom: stepped clean re-draws of the tyre (82 -> 124 -> 176 -> 248 -> 330 px), never upscales.
  Navy outline, one rim-light colour (GLH), flat shadows, no speckle. Sipes and raised sidewall
  lettering, TWI mark blinking from 4.4 s.
- 5-6 s tread cross-section: chipped irregular blocks, grooves lighter than blocks, wear bar 30 px
  tall (was 14) with a 2-step palette pulse, the brightest colour in frame.
- 6-9 s fresh vs worn: two side-on tyres over the hazy street (no dark panel). The worn tyre wears
  down to the bar. One white frame plus the click lands at 7.70 s (frame 231), on "bar" in "level
  with the bar". That time is the syllable onset before the 7.95 s pause, measured from the VO
  waveform.
- 9-13 s: payoff strip and poll with the presenter in the car, big YES/NO buttons, NEXT EPISODE
  card for the final second (pops in whole, no empty plates).

Street life: one string of fluttering bunting, drifting leaves, pecking pigeons, a cyclist (9-12.6 s), exhaust puffs (idling at the light), a stepped-ray sun behind the rooftops.

Background art: ragged parapets, chimneys, vents, aerials, dishes and rooftop signs; uneven windows
with shutters, curtains, blinds and flower boxes; clustered brick courses, peeling paint, cracks and
damp patches; drainpipes and sagging wires. Walls use a 3-tone ramp with hue shift (brick SK/BRK/BRKS,
cream CRM/CRMS/R2, teal CYAN/TEAL/GLS). `chip_edges()` gives every background layer a 1 px chip
before any straight edge passes 19 px. `verify.py` renders the street alone, with open sky masked
and the car, UI and tyre close-ups excluded. It fails on any straight edge over 20 px or any
single-colour 13x13 area. The NEW/WORN analysis panel sits over the live street. The car pulls away on green as
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
