"""Entry point: python -m tools.agent_rotation <command>. See docs/AGENT_ROTATION_GUIDE.md."""
import sys

from .cli import main

if __name__ == '__main__':
    sys.exit(main())
