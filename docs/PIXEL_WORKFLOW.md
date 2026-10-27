# Pixel explainers with minimal context

## Start once

```bash
bash tools/setup.sh
source .venv/bin/activate
python tools/video.py doctor
```

Python 3.11+, FFmpeg/ffprobe and ripgrep must be available. Setup installs pinned
Pillow, NumPy and PocketSphinx into `.venv`. In local Claude Code it installs the
official `DietrichGebert/ponytail` plugin; restart Claude afterward. Project settings
select Sonnet, low effort, Ponytail lite and no automatic codebase map.
Use `/plugin` or `claude plugin list --json` to verify the runtime installation.

Hosted Claude Code cloud does not load plugins. A plugin enabled in this repo does
not prove it is active in a mobile/web session. The small root CLAUDE.md provides
lean coding rules there; it is not the official plugin. Cloud project threads may
ignore repository settings; select Sonnet/low in the host when settings do not apply.
Never claim a particular percentage saved. `/usage` and `/context` show real usage.

## Reuse these files

| Need | Read/edit |
|---|---|
| Character/outfit | `characters/main-guy/README.md`; `src/pix.py` |
| Spoken script and alignment | `src/align.py`; `src/words.json` |
| Scenes/captions/camera | `src/render.py` |
| Sound effects | `src/sfx.py` |
| Visual rules | `styles/explainer-style.md` |

Here `src` means `videos/new-car-trap/src`. New episodes belong in
`videos/<episode>/src`. Copy the source baseline once and change the script,
props, scene timings and cues; don't reread or rebuild the whole repository.
The preview helper defaults to the existing example. For another episode use
`python tools/video.py preview --src videos/<episode>/src --out out/<episode>`.
It reads that renderer's numeric `DUR` constant and samples six points across it.

## Produce the video

1. Write the hook and short script, then one compact scene/timing table.
2. Reuse the approved brown-skinned, glasses-wearing character and jointed poses.
   Keep crisp nearest-neighbour sprite scaling, physical arm/hand attachment,
   expressions and real actions. Use moving props to explain the spoken idea.
3. Reuse a supplied voiceover. Generate a new voice only when needed. Align once
   after the script/voice changes; reuse `words.json` otherwise. Do not invent times.
4. Use the existing white-background 1080x1920 style and 1–3 word captions.
   Readable captions and a visual change every 1–3 seconds; no placeholder slideshow.
5. Preview six stills, inspect the sheet, then check a short motion/audio export.
   Stills do not prove lip sync, transitions or sound work. Render the full cut once
   those pass, and verify the MP4 plays with audio.

```bash
python tools/video.py preview
python tools/video.py probe videos/new-car-trap/new_car_trap.mp4
# For the existing full example (run from repository root):
mkdir -p out
cd videos/new-car-trap/src
python ../../../tools/video.py run --log ../../../out/logs/render.log -- \
  python render.py video voiceover.mp3 ../../../out/new-car-trap.mp4
```

The renderer prefers Inter Black when installed. Set `PIXEL_FONT` to an exact
font path to lock typography; otherwise an available bold/default font is used.
The renderer's `mix.wav` is a local intermediate and is ignored by git.

## Keep context small

- Use `rg -n 'symbol' exact/path` then read the relevant range; avoid whole-tree dumps.
- Keep long command output in logs through `tools/video.py run`; read the full log
  only when the summary fails to explain a problem. Exit codes are never hidden.
- Inspect one contact sheet, then full-resolution frames only where needed.
- Reuse existing sprites and caches, don't embed binary/base64 assets in chat.
- Single agent by default. Don't install overlapping prose/context plugins or MCPs.
- Use `/clear` for a different episode after writing a short `out/HANDOFF.md`.
  Keep automatic compaction on; `/compact` should preserve decisions and source paths.
- Use low effort first; increase temporarily for a demonstrated hard bug. Never
  lower animation, timing or audio quality merely to shorten a response.

## Sources

- [Claude Code cost guidance](https://code.claude.com/docs/en/costs)
- [Cloud environment limits](https://code.claude.com/docs/en/cloud-environments)
- [Official Ponytail](https://github.com/DietrichGebert/ponytail)

Ponytail installation checked with Claude Code 2.1.311, plugin 5.3.2, upstream
commit `09c434ab73ca43761c5d8b0c5d341926c2fba710`. The marketplace remains the official
upstream source so a fresh installation receives its current release.
