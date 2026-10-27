# claude-code-videos

TikTok explainer videos made with Claude Code.

- `characters/main-guy/` - approved reusable character sprite (see its README)
- `styles/explainer-style.md` - format and style guide for the videos
- `videos/new-car-trap/` - "The New Car Trap" video and its source (render pipeline reusable for future videos)

## Low-token setup

Run `bash tools/setup.sh`, then `source .venv/bin/activate`.
Shared Claude settings select Sonnet + low effort and official Ponytail lite for
local sessions. Hosted cloud uses the short coding rules in `CLAUDE.md` because
plugins do not load there. Restart/open a fresh session after pulling these changes.

```bash
python tools/video.py doctor             # dependency/plugin status
python tools/video.py preview            # six stills + one compact sheet
python tools/video.py probe path/to.mp4   # short media metadata
python tools/video.py run --log out/task.log -- COMMAND ARGUMENTS
python -m unittest discover -s tests -q
```

Full workflow: [docs/PIXEL_WORKFLOW.md](docs/PIXEL_WORKFLOW.md).
Logs and new renders stay in ignored `out/`. Existing character and example assets
are reused; no extra MCP servers or overlapping always-on plugins are installed.
