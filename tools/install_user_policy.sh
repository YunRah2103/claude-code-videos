#!/usr/bin/env bash
# Install or refresh the Free-Agent-First policy in the user-level Claude instructions.
# Idempotent: rewrites only the marked block. Set CLAUDE_USER_DIR to test elsewhere.
# Note: user-level files may not persist across Claude Code Cloud sessions; add this command to the
# environment's setup script to reinstall it for each new session.
set -euo pipefail
repo="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
target="${CLAUDE_USER_DIR:-$HOME/.claude}/CLAUDE.md"
mkdir -p "$(dirname "$target")"
section="$(awk '/^## FREE-AGENT-FIRST CODING POLICY/{f=1} /^## Compact instructions/{f=0} f' "$repo/CLAUDE.md")"
if [ -z "$section" ]; then
  echo "error: policy section not found in $repo/CLAUDE.md" >&2
  exit 1
fi
python3 - "$target" "$section" <<'PY'
import sys
from pathlib import Path
target, section = Path(sys.argv[1]), sys.argv[2]
begin, end = "<!-- BEGIN free-agent-first policy -->", "<!-- END free-agent-first policy -->"
block = f"{begin}\n{section.strip()}\n{end}\n"
text = target.read_text(encoding="utf-8") if target.exists() else ""
if begin in text and end in text:
    head, rest = text.split(begin, 1)
    tail = rest.split(end, 1)[1]
    text = head + block + tail.lstrip("\n")
else:
    text = (text.rstrip() + "\n\n" if text.strip() else "") + block
target.write_text(text, encoding="utf-8")
print(f"installed Free-Agent-First policy in {target}")
PY
