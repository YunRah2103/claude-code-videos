"""List words in VIDEO_DIR's script that the PocketSphinx dictionary lacks (add them to cfg.DICT)."""
import re, sys
from pocketsphinx import Decoder
from cfgload import load
d = Decoder(bestpath=False)
for v in sys.argv[1:]:
    C = load(v); miss = set()
    for l in C.LINES:
        for w in l[1].split():
            core = re.sub(r"[^A-Za-z0-9']", "", w).lower()
            for tok in C.SPOKEN.get(core, core).split():
                if tok not in getattr(C, 'DICT', {}) and d.lookup_word(tok) is None: miss.add(tok)
    print(v, sorted(miss))
