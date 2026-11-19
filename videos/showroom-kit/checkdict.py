"""List script words missing from the CMU dictionary (add them to script.DICT or SPOKEN). Run from an episode src."""
import os, re, sys, pocketsphinx
sys.path.insert(0, os.getcwd()); import script
D = {l.split()[0] for l in open(os.path.join(os.path.dirname(pocketsphinx.__file__), 'model', 'en-us', 'cmudict-en-us.dict'))}
SP = {k.lower(): v for k, v in getattr(script, 'SPOKEN', {}).items()}; X = set(getattr(script, 'DICT', {}))
for _, text, *_ in script.LINES:
    for w in text.replace('...', '').split():
        core = re.sub(r"[^A-Za-z0-9'\-]", "", w.lstrip('*')).strip('-')
        for tok in SP.get(core.lower(), core.lower().replace('-', ' ')).split():
            if tok not in D and tok not in X: print('missing:', tok)
