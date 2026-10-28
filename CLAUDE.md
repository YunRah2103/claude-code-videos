# Claude Code Videos

Default: Sonnet, low effort. Minimise tokens while completing the requested video.
Use one agent. No automatic teams, extra MCP servers, long plans or repeated audits.
Reply briefly; do not print source, base64, word timings or full logs into chat.

Reuse first: `characters/main-guy/`, `styles/explainer-style.md`, and
`videos/new-car-trap/src/{render,pix,sfx,align}.py`. Read only files needed for the
change. Use `rg -n` and small line ranges; skip generated files and dependencies.
Read `docs/PIXEL_WORKFLOW.md` only when producing or changing a video.

Ponytail lite is enabled locally. Hosted cloud does not load plugins, so use these
fallback rules: inspect affected callers, reuse existing code or stdlib, make the
smallest complete change, avoid speculative features and new dependencies. Keep
validation and visual quality. Test changed nontrivial logic; report real limits.

Run `python tools/video.py doctor` once. If dependencies are missing, run
`bash tools/setup.sh`. Use `python tools/video.py run --log out/logs/task.log --
COMMAND ...` for noisy commands: full output stays on disk and failures stay failures.
Create preview frames before a full render with `python tools/video.py preview`.
Inspect the sheet, then check motion/audio in a short video before the full export.
Reuse unchanged sprites, voiceover and alignment. Never simplify art to save tokens.

Keep renders/logs in `out/`; don't commit new MP4s, audio mixes or generated frames.
Before changing topics, save a short `out/HANDOFF.md`: goal, changed files, commands,
verified results, next step. Use `/clear` between unrelated tasks, `/usage` to inspect
usage. Only raise effort for a concrete unresolved problem, then return to low.

## OpenCode
When asked to "use opencode", delegate the work to OpenCode with a free model only.
Install if missing: `npm install -g opencode-ai@1.19.5` (OpenCode 2 is not released).
Use free models only (`opencode models`, ids ending in `-free` or `opencode/big-pickle`).
Run: `opencode run -m opencode/<free-model> "<task>"`, and cap runs with `timeout 240`.
Before real work, test with a hello prompt. If it reports "Free usage limit reached",
stop, report it, and do not subscribe, buy credits or switch to a paid model.
Never change project files or settings unless the user asked for that change.

## Compact instructions
Keep the brief, source paths, timing decisions, verification results and next step.
Drop logs, repeated plans and narration already stored in files.
