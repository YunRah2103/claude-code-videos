"""Stops first: which hypercar stops first, 0-400-0 km/h? Vertical 1080x1920 @30fps, white blueprint line art.

Two original side-view hypercars (red "CHIRON", blue "NEVERA") on stacked lanes with clocks and speed counters.
Ink line art draws on over a speed-heat overlay that fades out in the first 2 s. All beats are anchored to the
user's voiceover via words.json (align.py). Audio = user's VO + user's music 18 dB under, -14 LUFS.
usage: python render.py still OUTDIR t1 t2 ... | python render.py video OUT.mp4 [END [START]] | python render.py scan
"""
import json, math, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / 'videos/new-car-trap/src'))
import sfx  # noqa: E402

DUR = 18.4                                   # voiceover (17.90 s) + 0.5 s
W, H, FPS, SR = 1080, 1920, 30, sfx.SR
OUT = ROOT / 'out/stops-first'
VO_WAV, MUSIC_WAV = OUT / 'vo.wav', OUT / 'music.wav'
WORDS = json.load(open(HERE / 'words.json'))[0]
INK = (18, 18, 22)
PAPER = (251, 251, 248)
RED, BLUE = (214, 48, 40), (36, 96, 214)
FONT = '/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf'
FONT_B = '/usr/share/fonts/opentype/inter/Inter-Bold.otf'
FONT_M = '/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf'
_F = {}


def font(path, size):
    if (path, size) not in _F:
        try: _F[path, size] = ImageFont.truetype(path, size)
        except OSError: _F[path, size] = ImageFont.truetype('/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf', size)
    return _F[path, size]


def ss(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def lerp(a, b, k): return a + (b - a) * k


def wt(prefix, nth=0):
    hits = [w for w in WORDS if ''.join(c for c in w['w'].lower() if c.isalnum()).startswith(prefix) and w['ok']]
    return hits[nth]['s']


def pop(t, t0, d=0.25):
    u = (t - t0) / d
    if u <= 0: return 0.0
    if u >= 1: return 1.0
    return 1 + 0.25 * math.sin(u * math.pi) * (1 - u) - (1 - u) ** 3


# ---------------------------------------------------------------- word anchors
T_GO = wt('same')                            # launch
T_400 = wt('hour') + 0.2                     # both counters reach 400
T_BRK = wt('then')                           # braking phase
T_CHIRON, T_42 = wt('chiron'), wt('42')
T_NEVERA, T_30 = wt('nevera'), wt('30')      # blue clock freezes, blue car stops
T_12 = wt('twelve')                          # red stops, gap marker
T_RACE, T_PARK = wt('race'), wt('parked')
T_Q, T_ONE = wt('would', 1), wt('one')
END_VO = max(w['e'] for w in WORDS)
assert END_VO + 0.45 <= DUR, END_VO
LOOP0 = DUR - 0.35                           # final dissolve back into frame 0

# total record times (FACTS.md); the accel/brake split of each clock is illustrative (75 % accel)
CARS = {'red': dict(name='CHIRON', col=RED, total=41.96, stop=T_12, y=1010, hy=610),
        'blue': dict(name='NEVERA', col=BLUE, total=29.93, stop=T_30, y=1480, hy=1066)}
SPLIT = 0.75


def speed(c, t):
    """km/h on the car's own record run, mapped onto the video clock."""
    if t < T_GO: return 0.0
    if t < T_400: u = (t - T_GO) / (T_400 - T_GO); return 400 * (1 - (1 - u) ** 2.2)
    if t < T_BRK: return 400.0
    u = (t - T_BRK) / (c['stop'] - T_BRK)
    return 0.0 if u >= 1 else 400 * (1 - u) ** 0.9


def clock(c, t):
    if t < T_GO: return 0.0
    a = c['total'] * SPLIT
    if t < T_BRK: return a * (t - T_GO) / (T_BRK - T_GO)
    return min(c['total'], a + (c['total'] - a) * (t - T_BRK) / (c['stop'] - T_BRK))


VMAX = 2600.0                                # ground scroll px/s at 400 km/h
_TS = np.arange(0, DUR + 1, 1 / 240)
for c in CARS.values():
    v = np.array([speed(c, x) for x in _TS]) / 400 * VMAX
    c['dist'] = np.concatenate([[0], np.cumsum(v[:-1]) / 240])


def dist(c, t): return float(np.interp(t, _TS, c['dist']))


# ---------------------------------------------------------------- 3D lanes (scene3d.py renders each car with its own camera)
import cars3d, scene3d  # noqa: E402
MODEL = {'red': cars3d.Car('chiron'), 'blue': cars3d.Car('nevera')}
PAINT = {'red': (0.62, 0.05, 0.04), 'blue': (0.07, 0.22, 0.75)}
VIEW = {'red': (600, 1060), 'blue': (1060, 1520)}            # viewport y ranges
MPS = 40.0                                                    # floor scroll m/s at 400 km/h (stylised)
for c in CARS.values():
    v = np.array([speed(c, x) for x in _TS]) / 400 * MPS
    c['dist_m'] = np.concatenate([[0], np.cumsum(v[:-1]) / 240])


def build_bg():
    img = Image.new('RGB', (W, H), PAPER); d = ImageDraw.Draw(img)
    for x in range(0, W, 30): d.line([x, 0, x, H], fill=(232, 238, 244) if x % 150 else (214, 224, 236), width=1)
    for y in range(0, H, 30): d.line([0, y, W, y], fill=(232, 238, 244) if y % 150 else (214, 224, 236), width=1)
    y = 1560
    d.line([60, y, 1020, y], fill=INK, width=3); d.line([60, y + 64, 1020, y + 64], fill=INK, width=1)
    for x in (60, 560, 1020): d.line([x, y, x, y + 64], fill=INK, width=1)
    d.text((76, y + 32), '0 → 400 → 0 KM/H', font=font(FONT_B, 28), fill=INK, anchor='lm')
    d.text((576, y + 32), 'MAKER-REPORTED TIMES', font=font(FONT_B, 24), fill=(110, 110, 120), anchor='lm')
    return img


def pitch(c, t):
    """Body pitch in degrees (+ = nose down): squat on launch, dive under braking, rebound at the stop."""
    sq = -1.0 * math.exp(-max(0, t - T_GO) * 2.5) * (t >= T_GO)
    dive = 1.3 * ss((t - T_BRK) / 0.35) * (t < c['stop'])
    reb = 0.0
    if t >= c['stop']:
        u = t - c['stop']; reb = 1.3 * math.exp(-u * 5) * math.cos(u * 16)
    return sq + dive + reb


def cam_yaw(t):
    """Slow orbit: front three-quarter on the line, swings toward the side at speed, back to the nose at the stop."""
    return 34 + 6 * math.sin(t * 0.9) * (t < T_GO) + 22 * ss((t - T_GO) / 2.5) - 18 * ss((t - T_BRK) / 6.5) + 8 * ss((t - T_RACE) / 2.5)


def lane_state(key, t):
    c = CARS[key]; m = MODEL[key]
    d = float(np.interp(t, _TS, c['dist_m'])); kmh = speed(c, t); mps = kmh / 400 * MPS
    R = m.s['R'][0]
    w = mps / R / FPS
    idle = 0.004 * math.sin(t * 70) if (t < T_GO or (key == 'red' and t > c['stop'] + 0.4)) else 0
    jit = 0.004 * math.sin(t * 157) * min(1, kmh / 300) if kmh > 60 else 0
    return dict(dist=d, kmh=kmh, mps=mps, pitch=pitch(c, t), heave=idle + jit - 0.01 * abs(pitch(c, t)), spin=d / R,
                yaw=cam_yaw(t), elev=8.5 + 2 * ss((t - T_BRK) / 6), cam_d=7.4 - 0.5 * ss((t - T_GO) / 2.5) + 0.3 * ss((t - T_BRK) / 6),
                fov=30, tx=0.15, heat=1 - ss((t - 0.5) / 1.5), ink=0.12 + 0.88 * ss(t / 1.5), colour=PAINT[key],
                blur=min(1, max(0, (w - 0.25) / 0.5)))


def draw_lane(img, key, t):
    y0, y1 = VIEW[key]
    a = scene3d.render_lane(MODEL[key], lane_state(key, t), W, y1 - y0)
    img.paste(Image.fromarray(a), (0, y0))


# ---------------------------------------------------------------- UI
BOXES = []
SAFE = (0, 0.12 * H, 0.85 * W, 0.62 * H)


def text(img, xy, s, f, col=INK, anchor='la', sc=1.0, box=True):
    if sc <= 0: return
    if sc != 1:
        f = font(f.path, max(4, int(f.size * sc)))
    d = ImageDraw.Draw(img); d.text(xy, s, font=f, fill=col, anchor=anchor)
    if box: BOXES.append(d.textbbox(xy, s, font=f, anchor=anchor))


def lane_header(img, c, t):
    hy = c['hy']; col = c['col']; d = ImageDraw.Draw(img)
    hi = pop(t, T_CHIRON if c['name'] == 'CHIRON' else T_NEVERA, 0.3) if t >= T_CHIRON - 0.01 else 0
    text(img, (60, hy), c['name'], font(FONT, 58), col)
    v = speed(c, t)
    text(img, (62, hy + 72), f'{int(round(v)):3d} KM/H', font(FONT_M, 40), (70, 70, 80))
    cl = clock(c, t); done = t >= c['stop']
    sc = 1 + 0.15 * math.sin(math.pi * (t - c['stop']) / 0.3) if done and t < c['stop'] + 0.3 else 1
    if done:
        bb = d.textbbox((900, hy + 4), f'{cl:05.2f} s', font=font(FONT_M, 76), anchor='ra')
        d.rectangle([bb[0] - 14, bb[1] - 10, bb[2] + 14, bb[3] + 12], fill=col)
        text(img, (900, hy + 4), f'{cl:05.2f} s', font(FONT_M, 76), PAPER, 'ra', sc)
    else:
        text(img, (900, hy + 4), f'{cl:05.2f} s', font(FONT_M, 76), INK, 'ra')
        if T_GO <= t < T_BRK:                                             # fast-forward marker while time is compressed
            x = 470
            for k in range(2): d.polygon([(x + k * 22, hy + 22), (x + k * 22 + 20, hy + 40), (x + k * 22, hy + 58)], fill=(150, 150, 160))
    if 0 < hi and t < (T_42 if c['name'] == 'CHIRON' else T_30) + 0.6:   # highlight while the voice names the car
        d.line([60, hy + 66, 60 + 250 * min(1, hi), hy + 66], fill=col, width=6)


PXS = 19.0                                   # timeline px per record second


def timeline(img, t, a):
    d = ImageDraw.Draw(img)
    for k, key in enumerate(('red', 'blue')):
        c = CARS[key]; y = 372 + k * 62
        d.rectangle([60, y, 60 + 42 * PXS + 6, y + 36], outline=(190, 196, 206), width=2)
        n = clock(c, t) * PXS
        if n > 1: d.rectangle([60, y, 60 + n, y + 36], fill=c['col'])
        text(img, (70 if n > 130 else 60 + n + 10, y + 18), c['name'], font(FONT_B, 24), PAPER if n > 130 else c['col'], 'lm')
    if t >= T_42:                                                         # the record named by the voice
        x = 60 + 41.96 * PXS; s = pop(t, T_42, 0.25)
        for y in range(352, 420, 12): d.line([x, y, x, y + 7], fill=INK, width=3)
        text(img, (x, 346), '≈42 s', font(FONT_B, 30), RED, 'rb', s)
    if t >= T_30:
        x = 60 + 29.93 * PXS; s = pop(t, T_30, 0.25)
        for y in range(434, 482, 12): d.line([x, y, x, y + 7], fill=INK, width=3)
        text(img, (x - 10, 497), '≈30 s', font(FONT_B, 30), BLUE, 'rt', s)
    if t >= T_12:                                                         # the 12 s gap, dimension-line style
        u = ss((t - T_12) / 0.3); xa, xb = 60 + 29.93 * PXS, 60 + 41.96 * PXS
        y = 520; xm = lerp(xa, xb, u)
        d.line([xa, 470, xa, y + 14], fill=INK, width=2); d.line([xb, 410, xb, y + 14], fill=INK, width=2)
        d.line([xa, y, xm, y], fill=INK, width=4)
        if u > 0.9:
            d.polygon([(xa, y), (xa + 16, y - 9), (xa + 16, y + 9)], fill=INK)
            d.polygon([(xb, y), (xb - 16, y - 9), (xb - 16, y + 9)], fill=INK)
        q = wt('quicker'); qs = 1 + 0.2 * math.sin(min(1, max(0, (t - q) / 0.5)) * math.pi)
        text(img, ((xa + xb) / 2, y + 12), '12 s', font(FONT, 52), INK, 'mt', pop(t, T_12 + 0.1, 0.3) * qs)


def panel(img, t):
    if t < T_GO:                                                          # hook: frame 1
        out = ss((t - (T_GO - 0.25)) / 0.25)
        dy = -int(60 * out)
        if out < 1:
            col = tuple(int(lerp(a, b, out)) for a, b in zip(INK, PAPER))
            text(img, (56, 268 + dy), 'WHICH STOPS', font(FONT, 114), col)
            text(img, (56, 396 + dy), 'FIRST?', font(FONT, 114), col)
            d = ImageDraw.Draw(img)
            if out == 0: d.line([60, 540 + dy, 60 + 420 * ss(t / 0.8), 540 + dy], fill=RED, width=10)
        return
    if t >= T_Q:                                                          # question + poll
        text(img, (60, 268), 'WOULD YOU TAKE', font(FONT, 74), INK, sc=pop(t, T_Q, 0.25))
        text(img, (60, 352), 'THE ELECTRIC ONE?', font(FONT, 74), BLUE, sc=pop(t, wt('electric'), 0.25))
        d = ImageDraw.Draw(img)
        for k, (lab, x, col) in enumerate((('YES', 60, BLUE), ('NO', 470, RED))):
            s = pop(t, wt('electric') + 0.12 * k, 0.25)
            if s <= 0: continue
            w, h = 380 * s, 110 * s; cx, cy = x + 190, 520
            d.rounded_rectangle([cx - w / 2 + 8, cy - h / 2 + 10, cx + w / 2 + 8, cy + h / 2 + 10], 18, fill=INK)
            d.rounded_rectangle([cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2], 18, fill=PAPER, outline=INK, width=6)
            BOXES.append((cx - w / 2, cy - h / 2, cx + w / 2 + 8, cy + h / 2 + 10))
            text(img, (cx, cy), lab, font(FONT, 64), col, 'mm', s)
        return
    a = ss((t - T_GO) / 0.25)
    lab = '0 → 400 KM/H' if t < T_BRK else '400 → 0  BRAKING' if t < T_12 + 0.4 else 'NEVERA STOPS FIRST'
    sw = max(T_GO, T_BRK if t >= T_BRK else 0, T_12 + 0.4 if t >= T_12 + 0.4 else 0)
    text(img, (60, 270), lab, font(FONT, 64), BLUE if 'NEVERA' in lab else INK, sc=pop(t, sw, 0.22) * a if a < 1 else pop(t, sw, 0.22))
    timeline(img, t, a)


def ui(img, t):
    BOXES.clear()
    panel(img, t)
    for c in CARS.values(): lane_header(img, c, t)
    if T_GO <= t < T_Q:
        text(img, (60, 540), 'separate record runs', font(FONT_B, 28), (110, 110, 120), sc=pop(t, T_GO + 0.2, 0.25))
    if t >= T_PARK:                                                       # "already parked"
        s = pop(t, T_PARK, 0.3); cx, cy = 455, 1112
        d = ImageDraw.Draw(img); r = 46 * s
        if r > 2:
            d.rounded_rectangle([cx - r, cy - r, cx + r, cy + r], 14, fill=BLUE, outline=INK, width=4)
            text(img, (cx, cy + 2), 'P', font(FONT, int(70)), PAPER, 'mm', s, box=False)
    text(img, (918, 236), 'Yub', font(FONT_B, 26), (120, 120, 130), 'rt')


# ---------------------------------------------------------------- frame
BG = None


def render(t):
    global BG
    if BG is None: BG = build_bg()
    img = BG.convert('RGBA')
    for key in CARS: draw_lane(img, key, t)
    ImageDraw.Draw(img).line([0, VIEW['red'][1], W, VIEW['red'][1]], fill=INK, width=3)
    ui(img, t)
    out = img.convert('RGB')
    sh = 0
    if T_GO <= t < T_GO + 0.5: sh = 6 * math.exp(-(t - T_GO) * 8) * math.sin(t * 95)
    for c in CARS.values():
        if c['stop'] <= t < c['stop'] + 0.3: sh += 5 * math.exp(-(t - c['stop']) * 12) * math.sin(t * 110)
    if sh:
        out = Image.fromarray(np.roll(np.asarray(out), int(sh), 0))
    return np.asarray(out)


F0 = None


def frame(t):
    global F0
    a = render(t)
    if t >= LOOP0:
        if F0 is None: F0 = render(0.0).astype(np.float32)
        k = ss((t - LOOP0) / (DUR - 1 / FPS - LOOP0))
        a = (a.astype(np.float32) * (1 - k) + F0 * k).astype(np.uint8)
    return a


# ---------------------------------------------------------------- audio
def read_wav(p):
    with wave.open(str(p)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        ch, sr = w.getnchannels(), w.getframerate()
    x = x.reshape(-1, ch).mean(1)
    return np.interp(np.arange(int(len(x) * SR / sr)) * sr / SR, np.arange(len(x)), x)


def lufs(x):
    """Integrated loudness (ITU-R BS.1770) via ffmpeg ebur128 on a mono float signal."""
    tmp = OUT / '_lufs.wav'; write_wav(tmp, x)
    r = subprocess.run(['ffmpeg', '-nostats', '-i', str(tmp), '-af', 'ebur128', '-f', 'null', '-'], capture_output=True, text=True).stderr
    tmp.unlink()
    return float(r.rsplit('I:', 1)[1].split('LUFS')[0])


def write_wav(p, x):
    pcm = (np.stack([x, x], 1).clip(-1, 1) * 32767).astype(np.int16)
    with wave.open(str(p), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


def add(buf, i, s):
    i = max(0, i); j = min(len(buf), i + len(s))
    if i < len(buf): buf[i:j] += s[:j - i]


def tick(): return sfx.fade(np.sign(np.sin(2 * np.pi * 1800 * sfx.T(0.02))) * 0.12)


def audio(path):
    n = int(DUR * SR)
    vo = np.zeros(n); add(vo, 0, read_wav(VO_WAV))
    mus = np.zeros(n); add(mus, 0, read_wav(MUSIC_WAV))
    L_vo, L_mu = lufs(vo), lufs(mus)
    mus *= 10 ** ((L_vo - 18 - L_mu) / 20)                                # music 18 dB under the voice
    fo = np.clip((DUR - np.arange(n) / SR) / 1.6, 0, 1); mus *= fo * fo   # fade the music out at the end
    mus *= np.clip(np.arange(n) / SR / 0.05, 0, 1)
    fx = np.zeros(n)
    ev = [(0.0, sfx.whoosh(0.4, 20) * .5), (T_GO - 0.05, sfx.vroom(1.2) * .9), (T_GO, sfx.whoosh(0.6, 8) * .6),
          (T_BRK, sfx.screech(0.6) * .35), (T_30, sfx.ding(1568, 0.5) * .5), (T_12, sfx.ding(1175, 0.6) * .5),
          (T_12 + 0.1, sfx.stamp() * .5), (T_42, sfx.pop() * .4), (T_PARK, sfx.pop() * .5),
          (T_Q, sfx.pop() * .4), (wt('electric'), sfx.pop() * .5), (wt('electric') + 0.12, sfx.pop() * .5), (LOOP0, sfx.whoosh(0.5, 16) * .4)]
    for k in range(10): ev.append((T_GO + k * 0.2, tick() * 0.6))
    for t0, s in ev: add(fx, int(t0 * SR), s)
    fx *= 10 ** ((L_vo - 12 - lufs(fx)) / 20)                             # effects sit 12 dB under the voice
    mix = vo + mus + fx
    g = 10 ** ((-13.4 - lufs(mix)) / 20); mix *= g                          # -14 LUFS after AAC (measured)
    pk = np.abs(mix).max()
    if pk > 0.89: mix = np.tanh(mix / 0.89) * 0.89                        # soft-limit peaks to about -1 dBFS
    write_wav(path, mix)
    print(f'audio: vo {L_vo:.1f} LUFS, music gain {L_vo - 18 - L_mu:+.1f} dB, mix gain {20 * math.log10(g):+.1f} dB')


def main():
    mode = sys.argv[1]
    if mode == 'still':
        out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
        for s in sys.argv[3:]: Image.fromarray(frame(float(s))).save(out / f'f_{s}.png')
        return
    if mode == 'scan':
        bad = []
        for i in range(int(DUR * FPS)):
            t = i / FPS
            img = Image.new('RGBA', (W, H)); ui(img, t)
            for k in CARS: lane_state(k, t)
            for b in BOXES:
                if b[0] < SAFE[0] or b[1] < SAFE[1] or b[2] > SAFE[2] or b[3] > SAFE[3]: bad.append((round(t, 2), b))
        print('anchors', {k: round(v, 2) for k, v in dict(go=T_GO, k400=T_400, brk=T_BRK, s30=T_30, s12=T_12, park=T_PARK,
                                                             q=T_Q, end_vo=END_VO).items()})
        print('safe-zone violations:', len(bad), bad[:5])
        return
    dst = Path(sys.argv[2]); dst.parent.mkdir(parents=True, exist_ok=True)
    t_end = float(sys.argv[3]) if len(sys.argv) > 3 else DUR
    t_start = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
    wav = dst.with_suffix('.wav'); audio(wav)
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                          '-i', '-', '-ss', str(t_start), '-i', str(wav), '-t', str(t_end - t_start), '-c:v', 'libx264', '-crf', '18',
                          '-pix_fmt', 'yuv420p', '-vf', 'setsar=1', '-ar', '48000', '-c:a', 'aac', '-b:a', '192k',
                          '-shortest', str(dst)], stdin=subprocess.PIPE)
    for i in range(int(round(t_start * FPS)), int(round(t_end * FPS))):
        p.stdin.write(frame(i / FPS).tobytes())
    p.stdin.close(); sys.exit(p.wait())


if __name__ == '__main__':
    main()
