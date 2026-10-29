# Local Qwen worker — optional Claude Code integration

This integration keeps **Claude Sonnet as the manager** and adds your existing
**Qwen3.8 27B** model as a separate, optional coding worker.

It is *not* the same as **Ollama → Apps → Claude Code** /
`ollama launch claude`, which starts Claude Code using Qwen *instead of* Sonnet.

## Windows setup (one-time)

1. Start Ollama on the same Windows PC, and confirm the installed model:

   ```powershell
   ollama list
   ```

2. Open PowerShell and enter your existing cloned project:

   ```powershell
   cd $HOME\claude-code-videos
   git pull
   claude
   ```

3. Claude Code may request approval for the project's `.mcp.json` server.
   Review the local script and approve it. Type `/mcp` inside Claude Code
   to inspect the connection. **Keep Claude Sonnet selected normally**.

4. In Claude Code, ask:

   > Check local Qwen status, then delegate a small Python wheel-rotation
   > function to Qwen. Review its output without executing it.

## Important behaviour

- Delegate **on demand**, whenever the user requests local Qwen.
- Qwen receives only the task and explicitly provided source excerpts.
  Never include credentials, secrets, private environment variables, or large logs.
- Tool `qwen_generate_code` only returns generated text. It does not write files,
  execute code or run FFmpeg; Claude separately reviews proposed changes and
  handles any permitted edits and tests.
- This is a Windows-PC-local integration using `127.0.0.1:11434`.
  Claude Code running in a **cloud container cannot reach your home Ollama server**
  through localhost. Start Claude Code on your own Windows PC.
- If Python isn't in PATH, install Python, then reopen PowerShell and check
  `python --version`.
- Do not expose Ollama's unauthenticated local API on a public network.
- Nothing is sent to a paid Qwen API; local requests have no provider fee,
  but consume your PC's electricity.
- If Qwen is unavailable, tell the user. Do not silently switch models
  or retry paid requests.

## Output length and reasoning

- The local worker requests `num_predict=-1`, so there is **no artificial
  2,500-token generation cap**. Ollama's model configuration, available VRAM,
  context window and finite tool/API response size still impose practical limits.
- By default the worker sends `think: false` for **code-first output**,
  preventing long reasoning from consuming the entire response. For particularly
  difficult assignments Claude can pass `deep_thinking: true` to enable
  Qwen's extra reasoning, which will be slower.
- The connector no longer overrides the model's `num_ctx`. The installed
  `Q3_K_M` model currently configures approximately 24K context for 16GB VRAM.
  This is context, not the generated-answer token cap.
- A single synchronous Ollama request still has a **one-hour network timeout**;
  it does not run indefinitely. For projects longer than that, delegate
  successive focused tasks and save each reviewed result.
- Long returned code consumes Claude's **own** context/usage when it reviews
  the answer. Avoid asking for thousands of unrelated lines in one tool call.
- If Ollama reports a `length` stop, treat the code as incomplete and report
  that honestly rather than assuming it passed.
