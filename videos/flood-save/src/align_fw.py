"""Word timings from the real voiceover with faster-whisper (word_timestamps), mapped onto the script words.
    python align_fw.py voiceover.wav words.json"""
import json, re, subprocess, sys
import numpy as np
from faster_whisper import WhisperModel
sys.path.insert(0, __file__.rsplit('/', 1)[0]); from make_voiceover import SCRIPT

def norm(w): return re.sub(r"[^a-z]", '', w.lower())

def pcm16k(p):   # decode with ffmpeg (the bundled PyAV build here cannot open files)
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-ar', '16000', '-ac', '1', '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32)

segs, _ = WhisperModel('base.en', device='cpu', compute_type='int8').transcribe(pcm16k(sys.argv[1]), word_timestamps=True, initial_prompt=SCRIPT)
heard = [w for s in segs for w in s.words]
script = SCRIPT.split()
assert [norm(w.word) for w in heard] == [norm(w) for w in script], [w.word for w in heard]
json.dump([dict(w=s, s=round(h.start, 3), e=round(h.end, 3)) for s, h in zip(script, heard)], open(sys.argv[2], 'w'), indent=0)
print('aligned', len(script), 'words; last ends', heard[-1].end)
