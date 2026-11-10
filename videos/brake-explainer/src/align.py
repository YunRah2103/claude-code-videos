"""Word timings for each voiceover line with PocketSphinx forced alignment -> words.json."""
import json, re, subprocess, sys
from pathlib import Path
from pocketsphinx import Decoder

NUM = {"ABS": "a b s"}

def align(wav, text):
    disp = text.split()
    norm = [" ".join(NUM.get(re.sub(r"[^A-Za-z']", "", w), re.sub(r"[^a-z']", "", w.lower())).split()) for w in disp]
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(wav), "-ac", "1", "-ar", "16000", "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    d = Decoder(samprate=16000, bestpath=False)
    d.set_align_text(" ".join(norm))
    d.start_utt(); d.process_raw(raw, full_utt=True); d.end_utt()
    segs = [(s.word, s.start_frame / 100, (s.end_frame + 1) / 100) for s in d.seg()]
    segs = [s for s in segs if s[0] not in ('<s>', '</s>', '<sil>', '[NOISE]')]
    out, k = [], 0
    for w, n in zip(disp, norm):                      # multi-token words (e.g. "a b s") span several segments
        parts = len(n.split())
        st, en = segs[k][1], segs[k + parts - 1][2]; k += parts
        out.append(dict(w=w, s=round(st, 2), e=round(en, 2)))
    assert k == len(segs), (wav, k, len(segs))
    return out

if __name__ == "__main__":
    vo = Path(sys.argv[1])
    lines = json.load(open(Path(__file__).with_name("script.json")))
    res = [align(vo / f"line_{i:02d}.wav", t) for i, t in enumerate(lines)]
    json.dump(res, open(Path(__file__).with_name("words.json"), "w"))
    for i, r in enumerate(res): print(i, len(r), "words, last ends", r[-1]["e"])
