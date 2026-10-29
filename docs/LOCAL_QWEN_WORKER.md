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
