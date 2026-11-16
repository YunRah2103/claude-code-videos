"""Insert scene-change gaps, reveal holds and the final silence beat into the raw TTS.
Usage: python retime.py raw.wav raw_words.json voice.wav words.json"""
import sys, json, subprocess, numpy as np
SR = 48000
# (cut point in raw seconds, silence inserted). First entry = lead-in.
CUTS = [(0.0, 0.25), (6.24, 0.5), (9.34, 1.8), (12.84, 0.4), (14.55, 0.4), (18.23, 2.2), (22.17, 0.6), (24.46, 2.0), (25.94, 1.2)]
TAIL = 2.6
def shift(t):
    return t + sum(g for c, g in CUTS if t >= c)
if __name__ == '__main__':
    raw = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', sys.argv[1], '-ac', '1', '-ar', str(SR),
                        '-f', 'f32le', '-'], capture_output=True, check=True).stdout, np.float32)
    parts, prev = [], 0
    for c, g in CUTS:
        i = int(c * SR); parts += [raw[prev:i], np.zeros(int(g * SR), np.float32)]; prev = i
    parts += [raw[prev:], np.zeros(int(TAIL * SR), np.float32)]
    out = np.concatenate(parts)
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(SR), '-ac', '1', '-i', '-', sys.argv[3]],
                   input=out.tobytes(), check=True)
    W = json.load(open(sys.argv[2]))
    for w in W:
        w['s'], w['e'] = round(shift(w['s']), 2), round(shift(w['e']), 2)
    json.dump(W, open(sys.argv[4], 'w'))
    print('duration', round(len(out) / SR, 2), 'last word end', W[-1]['e'])
