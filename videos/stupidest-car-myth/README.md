# Stupidest Car Myth

TikTok explainer (18.0s, 1080x1920, 60fps): you don't need to warm your car up for five minutes.
Built from the `new-car-trap` baseline; same character, caption and camera system.

- `src/voiceover.mp3` - supplied voiceover (16.75s).
- `src/align.py` / `src/words.json` - script recovered with pocketsphinx recognition, then force-aligned.
  "That's" start set to 3.01s (recogniser time) because the aligner absorbed the pause before it.
- `src/pix.py` - adds dash clock, vintage car, choke knob, stopwatch, thermometer, fuel pump, drop, `thumb` pose.
- `src/render.py` - scenes: hook clock + X (0-2.9), old car/OLD/choke, modern car, stopwatch 5:00->0:30,
  gentle drive + thermometer, fuel waste + WASTED, thumbs-up / 30 SEC finale.
  `render.py video voiceover.mp3 out.mp4 [t0 t1]` renders an optional test range.
