---
description: Build a pixel explainer episode from a reference video, voiceover and script
argument-hint: <episode-name> <reference-video> <voiceover.mp3> "<script>"
---

Build a vertical 1080x1920, 60fps pixel-art explainer episode.

Inputs (from $ARGUMENTS, in order):
- episode name (lowercase, becomes `videos/<name>/`)
- reference video path
- voiceover mp3 path
- script, verbatim, in quotes

Rules:
- Use the existing character `characters/main-guy` through `videos/new-car-trap/src/pix.py`.
- Copy `videos/new-car-trap/src/{render,pix,sfx,align}.py` as the baseline. Change only the script, props, scene timings and cues.
- Get word timings by running `align.py` on the voiceover. Never invent times. Add any missing words to the dictionary in `align.py`.
- Match the reference's format: 1–3 word captions with a highlighted keyword, a visual change every 1–3 seconds, a two-line title and end card, camera punches and shake on beats.
- Make it eye-catching for retention: pop-ins, sparkles, confetti, stamps and a hook in the first 2 seconds.
- Keep renders and logs in `out/`. Never commit MP4s or generated frames.
- Steps: (1) report the reference's duration, scenes, caption style and motion in a short table, then wait for a go-ahead only if the reference is unclear; (2) `python tools/video.py doctor`, run `bash tools/setup.sh` if needed; (3) build props and scenes; (4) `python tools/video.py preview --src videos/<name>/src --out out/<name>` and inspect the sheet; (5) a short test export with `render.py video voiceover.mp3 <out> 0 6` and check motion and audio; (6) full render; (7) verify with `ffprobe` that the video is 1080x1920 at 60fps with an audio stream, and send the MP4 to the user.
- Write `out/HANDOFF.md`: goal, changed files, commands, verified results, next step.
- Commit the source only when the user asks. Do not put a model name in commits or PRs.

Episode request: $ARGUMENTS
