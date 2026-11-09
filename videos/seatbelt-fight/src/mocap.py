"""Shim: the ASF/AMC reader lives in shared/assets/mocapmoves/amc.py."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '../../../shared/assets/mocapmoves'))
from amc import joints, parse_asf, parse_amc  # noqa: E402,F401
