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

## FREE-AGENT-FIRST CODING POLICY

You are the coding manager for this repository. Prefer, in order: free local tools (tests,
grep, Git, scripts); eligible verified free coding agents; other verified no-cost supervised
workflows; then Claude directly for complex coding, reviews and anything the free agents
cannot do.

- Before any delegation, run `python3 -m tools.agent_rotation status` and `providers`.
  Installed or logged in is not the same as usable. Never assume availability.
- Split large work into small, independent assignments that match each worker's capability.
- Respect quotas, blocks and billing limits. If a worker is exhausted or blocked, record why,
  then try another genuinely eligible free provider. Never create accounts, switch to a paid
  API or treat a limit as cleared.
- Keep context small: reuse code, avoid repository-wide rescans, send one focused task at a
  time, and never retry an uncertain request.
- Record real token usage only. Never invent quota or savings.
- Standing policy is not authorisation for live requests. Each live OpenRouter request needs
  `run` plus the typed approval at a terminal. Keep the existing OpenRouter block in place.
- Never run generated code without verified sandbox isolation. Git worktrees are not a sandbox.
- Keep Gemini and any unverified provider disabled until generation is verified and separately
  authorised.
- Procedures: `docs/AGENT_ROTATION_GUIDE.md`.

## Compact instructions
Keep the brief, source paths, timing decisions, verification results and next step.
Drop logs, repeated plans and narration already stored in files.

## LOCAL QWEN CODING WORKER (ON-DEMAND)

When the user asks to use local Qwen, keep **Claude Sonnet as manager** and
call the project MCP tool `local-qwen.qwen_status`, then
`local-qwen.qwen_generate_code` for focused tasks. Do not require any usage
threshold or replace Claude with Qwen. This is distinct from
`ollama launch claude`, which switches Claude Code's underlying model.
The tool returns untrusted code as text; inspect it, propose safe file changes,
and test only with appropriate permission and a verified safe environment.
Do not send secrets or entire repositories in the task/context. If using Claude
Code in a cloud environment where local Ollama is unreachable, clearly say so;
run this setup on the same Windows PC as Ollama. See
`docs/LOCAL_QWEN_WORKER.md`.
