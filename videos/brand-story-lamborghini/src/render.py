"""brand-story-lamborghini: photo mini-documentary (no pixel engine). Layout, CLI and mixer follow videos/ac-idle;
the look comes from shared/assets/docstyle.py.
    python render.py still <dir> 0 0.5 1 ...        python render.py video <out.mp4> [t0 t1]
    python render.py check                          (safe-zone check over every 5th frame)
"""
import json, os, subprocess, sys, wave
from multiprocessing import Pool
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from audio import sfx
from assets import overlays as ov
from assets import docstyle as ds
from episode import W, H, RED, YEL, WHITE

ds.PHOTO_DIR = os.path.join(HERE, '..', 'assets')
OUT = os.path.join(HERE, '..', '..', '..', 'out', 'brand-story-lamborghini')
VO = os.path.join(OUT, 'voiceover.wav')
FPS = 60
WORDS = json.load(open(os.path.join(HERE, 'words.json')))
DUR = 41.2                       # voiceover 40.75 s + a short tail; the last 0.4 s blends back into frame 0
LOOP = 0.4


def at(i): return WORDS[i]['s']   # start time of word i


# ------------------------------------------------------------------ photo crops (fractions of each file; no people, no badges)
HERO = (0, 0, 1, 1)
HERO_FRONT = (0.36, 0.12, 1.0, 0.9)
TRACTOR = (0.06, 0.40, 0.94, 1.0)
F_FRONT = (0.0, 0.27, 1.0, 0.82)
F_REAR_CLOSE = (0.0, 0.36, 0.5, 0.8)
F_REAR = (0.0, 0.3, 0.84, 0.86)
FACTORY = (0.16, 0.3, 1.0, 0.78)
FACTORY_CLOSE = (0.34, 0.4, 0.92, 0.7)
GT = (0.0, 0.24, 0.92, 1.0)
GT_FRONT = (0.42, 0.42, 0.98, 0.86)
F_MOD_FRONT = (0.5, 0.18, 1.0, 0.94)

# ------------------------------------------------------------------ shots: (start, fn(t)) ; every shot <= 3.5 s
S = [0.0, 2.4, 4.6, 7.4, 9.6, 12.9, 15.6, 18.9, 22.0, 25.4, 28.4, 30.9, 32.5, 35.0, 36.4, 39.0, DUR]


def sh(i): return S[i], S[i + 1]


SHOTS = [
    lambda t: ds.shake(ds.parallax('hero', t, 0, 2.4, HERO, w=1000, cy=1090, z=(1.0, 1.3), pan=((.5, .5), (.62, .55)), drift=(1.4, 0.4)), t, 0, amp=26, decay=2.2),
    lambda t: ds.parallax('hero', t, *sh(1), HERO_FRONT, w=900, cy=1090, z=(1.12, 1.0), pan=((.7, .5), (.4, .5)), drift=(-1.0, 0.2)),
    lambda t: ds.parallax('tractor', t, *sh(2), TRACTOR, w=760, cy=1040, z=(1.0, 1.12), pan=((.5, .6), (.5, .45)), drift=(0.5, -0.6)),
    lambda t: ds.parallax('ferrari', t, *sh(3), F_FRONT, w=1000, cy=1010, z=(1.0, 1.12), pan=((.3, .5), (.7, .5)), drift=(-0.9, 0.2)),
    lambda t: ds.parallax('ferrari_rear', t, *sh(4), F_REAR_CLOSE, w=640, cy=1010, z=(1.0, 1.1), pan=((.3, .4), (.6, .6)), drift=(0.8, 0.3)),
    lambda t: ds.parallax('ferrari_rear', t, *sh(5), F_REAR, w=1000, cy=1010, z=(1.12, 1.0), pan=((.3, .5), (.5, .5)), drift=(-0.8, 0.2)),
    lambda t: ds.background('tractor', TRACTOR, t, *sh(6), drift=(0.6, 0.6), dark=0.32, z=(1.0, 1.12)),
    lambda t: ds.parallax('factory', t, *sh(7), FACTORY, w=1000, cy=1030, z=(1.0, 1.12), pan=((.3, .5), (.7, .5)), drift=(1.0, 0.2)),
    lambda t: ds.background('factory', FACTORY, t, *sh(8), drift=(-0.8, 0.0), dark=0.3, z=(1.0, 1.1)),
    lambda t: ds.parallax('factory', t, *sh(9), FACTORY_CLOSE, w=960, cy=1030, z=(1.05, 1.0), pan=((.7, .5), (.3, .5)), drift=(-0.8, 0.2)),
    lambda t: ds.parallax('gt350', t, *sh(10), GT, w=1000, cy=1030, z=(1.0, 1.15), pan=((.4, .5), (.6, .55)), drift=(0.9, 0.2)),
    lambda t: ds.parallax('gt350', t, *sh(11), GT_FRONT, w=740, cy=1030, z=(1.0, 1.06), pan=((.4, .5), (.7, .5)), drift=(-0.8, 0.3)),
    lambda t: ds.parallax('ferrari', t, *sh(12), F_FRONT, w=1000, cy=1010, z=(1.15, 1.0), pan=((.7, .5), (.4, .5)), drift=(0.8, 0.2), dark=0.35),
    lambda t: ds.shake(ds.background('tractor', TRACTOR, t, *sh(13), drift=(0.5, 0.3), dark=0.3, z=(1.05, 1.15)), t, 35.1, amp=14, decay=6),
    lambda t: ds.split(t, S[14], ('hero', HERO_FRONT, False), ('ferrari_modern', F_MOD_FRONT, True), cy=1000),
    lambda t: ds.background('hero', HERO, t, *sh(15), drift=(0.6, 0.3), dark=0.4, z=(1.0, 1.1)),
]
CHAPTERS = [0.0, 4.6, 9.6, 15.6, 19.9, 32.5, 39.0]


def picture(t):
    i = max(k for k in range(len(SHOTS)) if t >= S[k])
    img = SHOTS[i](t)
    if i > 0 and t - S[i] < 0.12 and i != 14:               # quick flash-cut on every new shot (no fades from black)
        img = Image.blend(img, Image.new('RGB', (W, H), (255, 255, 255)), 0.35 * (1 - (t - S[i]) / 0.12))
    return img


def overlay(cv, t):
    # cold open: headline on from frame 0, words kick as spoken
    ds.headline(cv, t, 0.0, 4.4, 'LAMBORGHINI EXISTS BECAUSE OF A BAD CLUTCH', hi={'BAD', 'CLUTCH'},
                beats=[(at(i), i) for i in range(7)], y=530, sz=94, maxw=780, settled=True)
    ds.name_chip(cv, t, at(7), 9.4, 'FERRUCCIO LAMBORGHINI', 440, 420)
    ds.pill(cv, t, at(10), 7.3, 'TRACTORS', 300, 560, col=YEL, sz=52)
    ds.pill(cv, t, at(14), 9.4, 'FERRARIS', 640, 560, col=RED, sz=52)
    ds.pill(cv, t, at(15), 12.8, 'REPORTEDLY', 300, 430, col=WHITE, sz=46)
    ds.pill(cv, t, at(18), 12.8, 'CLUTCH', 640, 600, col=RED, sz=64, fill=RED, tcol=(255, 255, 255), flash=3.0)
    ds.pill(cv, t, at(25), 15.5, 'ENZO FERRARI', 470, 470, col=RED, sz=52)
    ds.pill(cv, t, 15.6, 18.95, 'THE STORY SAYS', 330, 360, col=WHITE, sz=44)
    ds.speech(cv, t, 16.0, 18.95, ('STICK TO', 'TRACTORS'), hi='TRACTORS', y=640, k=0.86)
    ds.headline(cv, t, at(38), 21.9, 'HIS OWN SPORTS CAR COMPANY', hi={'OWN'},
                beats=[(at(41), 1), (at(42), 2), (at(43), 3), (at(44), 4)], y=440, sz=96)
    ds.timeline(cv, t, 23.0, 24.8, 1950, 1965, mark=1963, y=880, end=25.3)
    ds.year_counter(cv, t, 23.0, 24.8, 1950, 1963, y=620, end=25.3)
    ds.pill(cv, t, 25.4, 28.3, 'AUTOMOBILI LAMBORGHINI', 470, 420, col=YEL, sz=46)
    ds.pill(cv, t, 25.6, 28.3, '1963', 470, 540, col=WHITE, sz=58)
    ds.pill(cv, t, at(51), 32.4, 'FIRST PRODUCTION CAR', 470, 420, col=WHITE, sz=44)
    ds.pill(cv, t, at(56), 32.4, '350 GT', 470, 540, col=YEL, sz=72)
    ds.headline(cv, t, at(58), 34.9, 'DID THE INSULT REALLY HAPPEN?', hi={'INSULT'},
                beats=[(at(60), 2), (at(61), 3), (at(62), 4)], y=440, sz=92)
    ov.stamp(cv, t, 35.05, 36.3, ('STILL', 'DEBATED'), 470, 660, rot=-10, scale=0.72)
    ds.headline(cv, t, at(66), 38.9, 'BUT THE RIVALRY IS REAL', hi={'RIVALRY'}, beats=[(at(68), 2), (at(70), 4)], y=380, sz=92)
    ds.headline(cv, t, at(71), DUR + 1, 'DO YOU BELIEVE THE STORY?', hi={'BELIEVE'}, beats=[(at(73), 2)], y=380, sz=92)
    # poll: small sticker from ~18 s, grows big for the question
    if t >= 18.0:
        g = ds.ease((t - 38.9) / 0.5) if t > 38.9 else 0.0
        ov.poll(cv, t, 18.0, DUR + 1, 'Believe it?', 700 + (470 - 700) * g, 1100 + (820 - 1100) * g, 0.42 + 0.58 * g)


CREDIT_LINES = None


def credits(cv):
    global CREDIT_LINES
    if CREDIT_LINES is None:
        c = json.load(open(os.path.join(ds.PHOTO_DIR, 'credits.json'))); seen = []
        for x in c:
            s = f"{x['author'].replace('User:', '')} ({x['licence']})"
            if s not in seen: seen.append(s)
        CREDIT_LINES = ['Photos: Wikimedia Commons'] + [' · '.join(seen[i:i + 2]) for i in range(0, len(seen), 2)]
    for i, ln in enumerate(CREDIT_LINES):
        ov.credit(cv, ln, 1000 + 40 * i)


def compose(t):
    ov.reset()
    cv = picture(t)
    overlay(cv, t)
    ov.tag(cv)
    ds.progress(cv, t, DUR, CHAPTERS)
    return cv


def frame_img(n):
    t = n / FPS
    cv = ds.finish(compose(t), t)
    if t > DUR - LOOP:                                          # loop: blend into frame 0 so the last frame matches it
        f0 = ds.finish(compose(0.0), 0.0)
        cv = Image.blend(cv, f0, ds.ease((t - (DUR - LOOP)) / (LOOP - 1 / FPS)))
    if t >= DUR - 2.0: credits(cv)                               # small-print photo credits through the last frame
    return cv


def frame(n): return frame_img(n).tobytes()


# ------------------------------------------------------------------ audio
CUES = [(0.0, 'whoosh', 1.0), (0.05, 'thump', 0.6)] + [(S[i], 'whoosh', 0.35) for i in range(1, 15) if i not in (6, 8, 13)] + \
       [(at(7), 'pop', 0.5), (at(10), 'pop', 0.45), (at(14), 'pop', 0.45), (at(15), 'pop', 0.4), (at(18), 'buzzer', 0.35),
        (15.6, 'whoosh', 0.5), (16.0, 'pop', 0.5), (18.0, 'pop', 0.4), (35.05, 'stamp', 1.0), (S[14], 'whoosh', 0.7),
        (38.9, 'pop', 0.6), (25.4, 'whoosh', 0.4), (at(56), 'ding', 0.35)]


def tick_cues():
    out, last = [], None
    for n in range(int(22.8 * FPS), int(25.0 * FPS)):
        t = n / FPS; yr = round(1950 + 13 * ds.ease((t - 23.0) / 1.8)) if t >= 23.0 else 1950
        if yr != last and t >= 23.0: out.append((t, 'click', 0.55)); last = yr
    return out


def build_audio(out_wav):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', VO, '-ar', str(sfx.SR), '-ac', '1', '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    vo = np.frombuffer(raw, np.float32).astype(np.float64)
    n = int(sfx.SR * DUR); mix = np.zeros(n); m = min(n, len(vo)); mix[:m] = vo[:m]
    fx = sfx.render(CUES + tick_cues(), DUR)
    fx *= 0.3 * np.max(np.abs(vo)) / max(1e-9, np.max(np.abs(fx)))          # effects well under the voice
    mix += fx; mix /= max(1.0, np.max(np.abs(mix)) / 0.97)
    k = int(sfx.SR * 0.25); mix[-k:] *= np.linspace(1, 0, k) ** 2
    with wave.open(out_wav, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sfx.SR); w.writeframes((mix * 32767).astype('<i2').tobytes())


def main():
    mode = sys.argv[1]
    if mode == 'still':
        os.makedirs(sys.argv[2], exist_ok=True)
        for ts in sys.argv[3:]: frame_img(round(float(ts) * FPS)).save(f'{sys.argv[2]}/f_{ts}.png')
    elif mode == 'check':
        bad = set()
        for n in range(0, int(DUR * FPS), 5):
            compose(n / FPS); bad |= {(lab, round(n / FPS, 2)) for lab, _ in ov.violations()}
        print('safe-zone violations:', sorted(bad)[:20] or 'none', '| max photo upscale %.2fx' % ds.STATS['max_up'])
    elif mode == 'video':
        out = sys.argv[2]
        t0, t1 = (float(sys.argv[3]), float(sys.argv[4])) if len(sys.argv) > 4 else (0.0, DUR)
        mix = os.path.splitext(out)[0] + '_mix.wav'; build_audio(mix)
        F0, N = round(t0 * FPS), round(t1 * FPS)
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                               '-i', '-', '-ss', str(t0), '-t', str(t1 - t0), '-i', mix, '-c:v', 'libx264', '-preset', 'slow', '-crf', '17',
                               '-pix_fmt', 'yuv420p', '-aspect', '9:16', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '48000',
                               '-ac', '2', '-c:a', 'aac', '-b:a', '256k', '-movflags', '+faststart', '-shortest', out], stdin=subprocess.PIPE)
        with Pool(os.cpu_count() or 4) as pool:
            for i, b in enumerate(pool.imap(frame, range(F0, N), chunksize=4)):
                ff.stdin.write(b)
                if i % 300 == 0: print(f'{i}/{N - F0}', flush=True)
        ff.stdin.close(); ff.wait(); os.remove(mix)
        raise SystemExit(ff.returncode)


if __name__ == '__main__':
    main()
