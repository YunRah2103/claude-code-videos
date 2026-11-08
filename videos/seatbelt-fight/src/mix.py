"""seatbelt-fight audio: voice on top, fight / car sfx under it (cue times from the scene's events.json, so hits land
on the impact frames), sfx ducked -7 dB under speech; whole mix -14 LUFS (measured gain), true peak <= -1 dB (oversampled limiter).
    python videos/seatbelt-fight/src/mix.py"""
import json, os, subprocess, sys, wave
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.join(HERE, '..', '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'shared', 'audio')); import sfx
OUT = os.path.join(ROOT, 'out', 'seatbelt-fight'); DUR = 18.0; SR = sfx.SR
ev = json.load(open(os.path.join(OUT, 'frames', 'events.json')))
HIT = {'block': ('block', .8), 'punch': ('punch', .9), 'punch_big': ('punch', 1.1), 'clash': ('boom', .9), 'crash': ('crash', 1.0)}
cues = []
for im in ev['impacts']:
    n, v = HIT[im['s']]; cues.append((im['t'], n, v))
    if im['s'] in ('punch_big', 'clash'): cues.append((im['t'], 'thump', .7))
    if im['s'] == 'crash': cues += [(im['t'], 'glass_crack', .55), (im['t'], 'clack', .6), (im['t'] + .02, 'thump', .9)]
cues += [(t - .12, 'whoosh', .55) for t in ev['whoosh']]
cues += [(t, 'thump', .35) for t in ev['land']]
cues += [(ev['screech'][0], 'screech', .45), (ev['screech'][1], 'screech', .6), (ev['click'], 'click', .6), (3.48, 'vroom', .5),
         (ev['scratch'], 'scratch', .8), (ev['airbag'], 'airbag_pop', .7), (17.5, 'boing', .25)]
fx = sfx.render(cues, DUR)
def load(p):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', p, '-ar', str(SR), '-ac', '1', '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.float32).astype(np.float64)
vo = load(os.path.join(OUT, 'vo_track.wav'))[:len(fx)]
vo = np.pad(vo, (0, len(fx) - len(vo)))
env = np.convolve(np.abs(vo), np.ones(SR // 10) / (SR // 10), 'same'); duck = np.where(env > 0.01, 10 ** (-7 / 20), 1.0)
duck = np.convolve(duck, np.ones(SR // 20) / (SR // 20), 'same')
fx = fx / (np.abs(fx).max() + 1e-9) * 0.5
mix = vo * 1.0 + fx * duck
mix /= max(1.0, np.abs(mix).max() / 0.95)
pre = os.path.join(OUT, 'mix_pre.wav')
with wave.open(pre, 'wb') as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype('<i2').tobytes())
def lufs(p):
    m = subprocess.run(['ffmpeg', '-v', 'info', '-i', p, '-af', 'ebur128=peak=true', '-f', 'null', '-'], capture_output=True, text=True).stderr
    return float(m[m.rindex('Summary:'):].split('I:')[1].split()[0])
gain = -14.0 - lufs(pre)
for _ in range(3):   # gain to -14 LUFS, look-ahead limiter keeps true peak under -1 dB; small correction passes
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', pre, '-af', f'volume={gain:.2f}dB,aresample=192000,alimiter=limit=0.80:level=disabled:attack=1:release=60,aresample=48000',
                    '-ar', '48000', '-ac', '2', os.path.join(OUT, 'mix.wav')], check=True)
    err = -14.0 - lufs(os.path.join(OUT, 'mix.wav'))
    if abs(err) < .3: break
    gain += err
print('cues', len(cues))
