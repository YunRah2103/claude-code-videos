"""Forced alignment (PocketSphinx) of the single narration clip -> words.json (flat {w, s, e} list).

  ../../../.venv/bin/python align.py VO.wav OUT_WORDS.json
"""
import json, re, subprocess, sys
from pocketsphinx import Decoder

import timing

NUM = {"V12": "v twelve", "16": "sixteen", "F1's": "f ones"}

def align(wav, text):
    disp = text.split()
    norm = [NUM.get(w.strip("?.,"), re.sub(r"[^a-z']", "", w.lower())) for w in disp]
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(wav), "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    d = Decoder(samprate=16000, bestpath=False)
    d.set_align_text(" ".join(norm))
    d.start_utt(); d.process_raw(raw, full_utt=True); d.end_utt()
    segs = [(s.word, s.start_frame / 100, (s.end_frame + 1) / 100) for s in d.seg()]
    segs = [s for s in segs if s[0] not in ("<s>", "</s>", "<sil>", "[NOISE]")]
    out, k = [], 0
    for w, n in zip(disp, norm):
        parts = len(n.split())
        out.append(dict(w=w, s=round(segs[k][1], 2), e=round(segs[k + parts - 1][2], 2))); k += parts
    assert k == len(segs), (k, len(segs))
    return out

if __name__ == "__main__":
    words = align(sys.argv[1], timing.SCRIPT)
    json.dump(words, open(sys.argv[2], "w"), indent=0)
    print(len(words), "words; first", words[0], "last", words[-1])
