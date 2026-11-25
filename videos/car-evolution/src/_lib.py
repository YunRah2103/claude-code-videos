"""Make lib/cine3d (renderer, engine, cars, props) and characters/yub-3d (Yub) importable from this video folder."""
import os, sys
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
for _p in (os.path.join(_ROOT, "lib", "cine3d"), os.path.join(_ROOT, "characters", "yub-3d")):
    if _p not in sys.path: sys.path.insert(0, _p)
