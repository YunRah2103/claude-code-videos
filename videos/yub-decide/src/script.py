"""Episode selector: YUB_EP=cybertruck|range_rover|civic_golf picks the dialogue module."""
import importlib, os
_m = importlib.import_module('ep_' + os.environ.get('YUB_EP', 'cybertruck'))
LINES, DIRECTION, SPOKEN, SLUG = _m.LINES, _m.DIRECTION, _m.SPOKEN, _m.SLUG
VOICES = {"B": ("Buyer", "Fenrir"), "S": ("Salesman", "Orus")}
def prompt():
    return DIRECTION + "\n".join(f"{VOICES[s][0]}: {t}" for s, t, _ in LINES) + "\n"
HOLD = getattr(_m, "HOLD", {})
GAPS = getattr(_m, "GAPS", (0.2, 0.5, 0.9))
