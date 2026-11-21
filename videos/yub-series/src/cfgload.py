"""Load VIDEO_DIR/cfg.py (script lines, voices, direction) for tts/align/retime."""
import importlib.util, os
def load(vdir):
    spec = importlib.util.spec_from_file_location('cfg', os.path.join(os.path.abspath(vdir), 'cfg.py'))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
    return m
VOICES = {"B": ("Buyer", "Fenrir"), "S": ("Salesman", "Orus")}     # same cast voices as every earlier skit
def prompt(C):
    return C.DIRECTION + "\n\n" + "\n".join(f"{VOICES[l[0]][0]}: {l[1]}" for l in C.LINES) + "\n"
