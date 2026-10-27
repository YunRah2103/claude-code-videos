#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python3 -m venv .venv
python3 tools/video.py run --log out/logs/setup.log -- \
  .venv/bin/python -m pip install --disable-pip-version-check -q -r requirements.txt
if command -v claude >/dev/null && [[ "${CLAUDE_CODE_REMOTE:-}" != "true" ]]; then
  python3 tools/video.py run --log out/logs/marketplace.log -- \
    claude plugin marketplace add DietrichGebert/ponytail --scope project
  python3 tools/video.py run --log out/logs/ponytail-install.log -- \
    claude plugin install ponytail@ponytail --scope project --config ledger=false --config sendNames=false
else
  echo 'Ponytail: use CLAUDE.md fallback in hosted cloud; local install needs the claude CLI.'
fi
.venv/bin/python tools/video.py doctor
echo 'Next: source .venv/bin/activate'
