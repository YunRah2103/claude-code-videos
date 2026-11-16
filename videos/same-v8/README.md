# same-v8

Urus vs RS Q8 ASCII short: 1080x1920, 30 fps, 18.0 s loop. Same ASCII style as `ascii-terminal-test` / `heartbeat-v8`
(the glyph atlas, Matcher, scanlines and bloom are imported unchanged from `videos/ascii-terminal-test/src`).
Cars come from the user's reference sheet `assets/sheet_src.png` (right-facing side views, same crop scale and slots).

```bash
python3 src/tts.py ../../out/same-v8/vo.wav                     # ONE Gemini Orus call, cached outside git; stops on 429
../../.venv/bin/python src/align.py ../../out/same-v8/vo.wav    # -> src/words.json (56/56 words)
../../.venv/bin/python src/render.py video ../../out/same-v8/same-v8_silent.mp4
../../.venv/bin/python src/audio.py ../../out/same-v8/vo.wav ../../out/same-v8/same-v8_silent.mp4 ../../out/same-v8/same-v8.mp4
../../.venv/bin/python src/checks.py ../../out/same-v8/same-v8.mp4 ../../out/same-v8/same-v8_silent.frames.json
bash snippets/check.sh                                           # runs/compiles every on-screen snippet
```

Timeline (all anchored to `words.json` via `wt()`): hook with prices ticking -> V8s overlap ("same V8") -> platform
x-ray ("same platform") -> prices land ("230,000", "121,000") -> cover jump ("covers ... fit") -> gap +$108,399
("extra money") -> DIFFERENT badge / hp / tune (each on its word) -> poll `input("Pay $108k extra? ")` -> cascade to frame 1.
Facts and sources: `FACTS.md`.
