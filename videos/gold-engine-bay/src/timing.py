"""Build timing.json: word times + word-anchored beats (the only timing source for render.py).

  python timing.py estimate                 # phase 1: ~2.7 words/s from the script
  python timing.py from-words WORDS.json    # phase 2: real aligned times ({w,s,e}, flat list
                                            #   or align.py's list-of-lines for ONE concatenated clip)
Beats are anchored to words, so only "words" changes between phases.
"""
import json, re, sys
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "timing.json"
SCRIPT = ("Why is there real gold inside a McLaren F1's engine bay? Not for show. "
          "The V12 makes huge heat, and the car's body is carbon fibre, which needs protecting from it. "
          "Gold reflects infrared heat, so McLaren lined the bay with about 16 grams of it. "
          "Would you line your car with gold? Yes or no?")
WPS, LEAD, TAIL = 2.7, 0.25, 0.55
SPOKEN = {"v12": "vee twelve", "16": "sixteen", "f1's": "eff ones"}

# beat id -> (anchor word, occurrence, offset s). "end" is always DUR.
BEATS = {
    "open": ("why", 1, -LEAD), "push": ("inside", 1, 0.0), "reveal": ("not", 1, -0.05),
    "v12": ("v12", 1, -0.1), "heat": ("heat", 1, -0.1), "carbon": ("carbon", 1, -0.1),
    "protect": ("protecting", 1, -0.1), "gold": ("gold", 2, -0.1), "infrared": ("infrared", 1, 0.0),
    "lined": ("lined", 1, -0.15), "about": ("about", 1, 0.0), "grams": ("16", 1, -0.1),
    "question": ("would", 1, -0.15), "poll": ("yes", 1, -0.1), "outro": ("no", 1, 0.3),
}

def key(w): return re.sub(r"[^a-z0-9']", "", w.lower())

def estimate():
    toks = SCRIPT.split()
    weight = [0.6 + 0.075 * len(re.sub(r"[^a-z]", "", SPOKEN.get(key(w), key(w)))) for w in toks]
    pause = [0.28 if w[-1] in ".?!" else 0.12 if w[-1] == "," else 0.0 for w in toks]
    span = len(toks) / WPS                      # whole speech span keeps the 2.7 w/s average
    k = (span - sum(pause[:-1])) / sum(weight)
    t, words = LEAD, []
    for w, g, p in zip(toks, weight, pause):
        words.append({"w": w, "s": round(t, 3), "e": round(t + g * k, 3)})
        t += g * k + p
    return words, "estimate 2.7 wps"

def from_words(path):
    data = json.load(open(path))
    flat = [w for line in data for w in line] if data and isinstance(data[0], list) else data
    return [{"w": w["w"], "s": float(w["s"]), "e": float(w["e"])} for w in flat], f"aligned {path}"

def build(words, source):
    ks = [key(w["w"]) for w in words]
    assert ks == [key(w) for w in SCRIPT.split()], "word list does not match SCRIPT"
    dur = round(words[-1]["e"] + TAIL, 2)
    beats = {}
    for b, (w, n, off) in BEATS.items():
        i = [j for j, x in enumerate(ks) if x == w][n - 1]
        beats[b] = round(max(0.0, words[i]["s"] + off), 3)
    beats["open"], beats["end"] = 0.0, dur
    json.dump({"source": source, "fps": 30, "dur": dur, "script": SCRIPT,
               "beats": beats, "anchors": {b: list(v) for b, v in BEATS.items()},
               "words": words}, open(OUT, "w"), indent=1)
    print(f"{OUT.name}: {len(words)} words, dur {dur}s ({source})")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "estimate"
    build(*(estimate() if cmd == "estimate" else from_words(sys.argv[2])))
