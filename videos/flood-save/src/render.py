"""Pixel moment: 'Which car would you save from a flood?' (14.6 s, 9:16, calm ambient look of the pixel-moments preview).

Shots (timed to words.json, aligned on the shipped voiceover):
  1 flood    0.00  rainy flooded street at night: lit windows, lamps, the guy under a red umbrella, hatchback + SUV at the
                   kerb in the water; slow side pan. Headline 'Which car would you SAVE?' until 'A small car'.
                   5.26 'lower': the hatchback settles lower (thud) -> LOWER pill; 7.76 'sits higher' -> HIGHER pill
  2 depth    9.00  soft cut to the neutral water-depth graphic; headline 'HIGHER ISN'T ALWAYS SAFER'
  3 sunrise 11.20  rain clears, dissolve to the calm sunrise pier, both cars parked on it; HATCHBACK / SUV poll ~11.8
  loop     14.10  rain and the night street return to the exact first frame
Art is drawn at 216x384 (world 240 wide for the pan) and upscaled 5x nearest; text is sharp on top (safe zone checked).
"""
import json, math, os, sys, subprocess, wave
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared', 'assets'))
from pixanim.motion import prog, clamp, io, ob
from pixanim.fx import popin, popout
from audio import sfx
import overlays as ov
from episode import headline_img, YEL, WHITE
import ambient as am

W, H, FPS, K = 1080, 1920, 60, 5
NW, NH, WW = 216, 384, 240                     # native view, world width (pan room)
DUR = 14.6
LOOP = 0.5
WORDS = json.load(open(os.path.join(HERE, 'words.json')))
def at(word, n=0): return [w['s'] for w in WORDS if w['w'].strip('.,?!').lower() == word][n]

T_LOWER, T_HIGHER = at('lower'), at('sits', 1)
T_DEPTH, T_SUN, T_POLL = at('but') - 0.05, at('safer') + 0.75, at('save', 1)
END = DUR - LOOP
G, WL = 236, 229                                # car ground (under water) and water surface where the cars stand
HX, SX, GUYX = 40, 122, 14                      # world x of hatchback, SUV, guy
PAL_N = (0.62, 0.74, 0.8)                       # night tint for sprites


# ------------------------------------------------------------------ night street (static part)
@lru_cache(None)
def street_static():
    r = np.random.default_rng(4)
    a = am.vgrad(NH, WW, [(0, (9, 22, 28)), (0.22, (14, 36, 42)), (0.5, (22, 54, 60)), (0.56, (12, 32, 38)), (1, (7, 20, 26))])
    win = []
    x = -4
    while x < WW:                               # skyline: two depths of blocks with window grids
        bw, top = int(r.integers(16, 34)), int(r.integers(96, 160))
        far = r.random() < 0.45
        a[top:206, max(0, x):x + bw] = (16, 40, 46) if far else (13, 33, 39)
        if not far and r.random() < 0.4: a[top - 6:top, x + bw // 2:x + bw // 2 + 1] = (13, 33, 39)
        for wy in range(top + 5, 196, 6):
            for wx in range(x + 3, x + bw - 3, 5):
                if 0 <= wx < WW - 2:
                    a[wy:wy + 2, wx:wx + 2] = (24, 52, 58)
                    if r.random() < 0.22: win.append((wx, wy, r.random() < 0.7, r.uniform(0, 30)))
        x += bw + int(r.integers(0, 4))
    for y, s in ((58, 0.0), (64, 0.5)):        # overhead wires
        for xx in range(WW): a[int(y + 4 * math.sin(xx / WW * math.pi) + s), xx] = (30, 58, 62)
    a[200:212] = (28, 54, 58); a[200] = (44, 74, 76); a[212] = (70, 104, 104)          # pavement + kerb
    a[168:206, 180:182] = a[168:206, 234:236] = (44, 76, 78); a[166:169, 178:238] = (50, 84, 86)  # bus shelter
    a[170:200, 183:213] = a[170:200, 183:213] * 0.7 + np.array((40, 80, 84)) * 0.3
    a[176:200, 215:231] = (196, 232, 222); a[181:191, 219:227] = (214, 150, 140); a[193:195, 219:229] = (90, 120, 120)
    for lx in (30, 150):                        # lamp posts
        a[118:206, lx:lx + 2] = (22, 44, 48); a[114:118, lx - 3:lx + 5] = (30, 56, 60)
    return a, win


LAMPS = [(31, 118), (151, 118)]


def guy_on(a, x, y, t, tint, umb=True):
    blink = (t % 3.7) < 0.12
    if umb:
        c = am.umbrella()
        am.paste(a, c[:6], x - 6, y - 10, tint)
        a[y - 4:y + 14, x + 8] = np.array((60, 40, 44)) * np.array(tint)
    am.paste(a, am.mini_guy(blink), x, y, tint)


def flood(t, pan=None):
    """Native 216x384 night street at local time t (any t, also negative: used again for the loop)."""
    base, win = street_static()
    a = base.copy()
    for wx, wy, warm, ph in win:                # lit windows, a few switch on/off slowly
        on = math.sin(t * 0.7 + ph) > -0.85
        if on: a[wy:wy + 2, wx:wx + 2] = (238, 196, 116) if warm else (150, 214, 206)
    for lx, ly in LAMPS:
        f = 1 + 0.04 * math.sin(t * 13 + lx)
        a[118:121, lx - 2:lx + 4] = (255, 232, 160)
        am.glow(a, lx + 1, ly + 1, 15 * f, (255, 222, 140), 0.55)
        am.glow(a, lx + 1, 205, 26, (255, 210, 120), 0.35, ry=6)
    am.glow(a, 223, 188, 20, (170, 235, 220), 0.25)
    guy_on(a, GUYX, 184, t, PAL_N)
    # cars: bob gently; the hatchback settles lower on 'lower'
    sink = 2 * io(prog(t, T_LOWER - 0.1, 0.7)) if t < END else 0
    cars = [(am.hatchback(), HX, G + round(sink + 0.5 * math.sin(t * 1.6))), (am.suv(), SX, G + round(0.5 * math.sin(t * 1.4 + 2)))]
    for spr, x, gy in cars: am.paste(a, spr, x, gy - spr.shape[0], PAL_N)
    # water from the kerb down: reflections of the street, wobbling per row
    wat = am.vgrad(NH - 213, WW, [(0, (14, 40, 46)), (1, (6, 18, 24))])
    for i in range(NH - 213):
        y = 213 + i
        sy = 212 - int(i * 0.9)
        if sy < 60: break
        sh = int(round(1.2 * math.sin(i * 0.9 + t * 4.0)))
        wat[i] = wat[i] * 0.62 + np.roll(a[sy], sh, 0) * 0.38
    a[213:] = wat
    for lx, ly in LAMPS:                        # lamp reflection columns (dashed, shimmering)
        for y in range(215, 330, 3):
            w = 1 + int(2 * abs(math.sin(y * 0.7 + t * 5 + lx)))
            a[y, max(0, lx - w):lx + w + 2] += (np.array((255, 214, 130)) - a[y, max(0, lx - w):lx + w + 2]) * 0.5 * (1 - (y - 215) / 130)
    for spr, x, gy in cars:                     # re-draw cars above the waterline, submerged part tinted
        h = spr.shape[0]; top = gy - h
        am.paste(a, spr[:max(0, WL - top)], x, top, PAL_N)
        sub = spr[max(0, WL - top):].copy(); sub[..., :3] = sub[..., :3] * 0.25 + np.array((18, 52, 58)) * 0.75
        am.paste(a, sub, x, max(WL, top), (1, 1, 1), 0.85)
        for xx in range(x - 2, x + spr.shape[1] + 2):
            if 0 <= xx < WW and int(t * 6 + xx) % 4: a[WL, xx] = (110, 170, 172)
    for y in range(218, NH, 9):                 # drifting ripple dashes
        for j in range(3):
            xx = int((j * 83 + y * 7 + t * (10 + y % 7)) % WW)
            a[y, xx:xx + 4] += 18
    am.rain(a, t, **RAIN_FAR)                  # heavy two-layer rain: it carries the opening motion (score >= 6)
    am.rain(a, t, **RAIN_NEAR)
    p = pan_at(t) if pan is None else pan
    return a, p


RAIN_FAR = dict(seed=1, n=300, vy=240, ln=3, k=0.45, col=(140, 196, 204))
RAIN_NEAR = dict(seed=2, n=480, vy=340, ln=6, k=0.75, col=(178, 226, 232), water_y=216, splash=40)


def pan_at(t): return 0.0 if t < 0 else (WW - NW) * io(clamp(t / T_DEPTH))


# ------------------------------------------------------------------ sunrise pier
@lru_cache(None)
def cloud(seed, w, h):
    r = np.random.default_rng(seed); yy, xx = np.mgrid[0:h, 0:w]; m = np.zeros((h, w), bool)
    for _ in range(6):
        cx, cy, rr = r.uniform(w * 0.15, w * 0.85), r.uniform(h * 0.45, h * 0.8), r.uniform(h * 0.3, h * 0.55)
        m |= (xx - cx) ** 2 + ((yy - cy) * 1.2) ** 2 < rr ** 2
    m[int(h * 0.85):] = False
    s = np.zeros((h, w, 4), np.float32); s[m] = (238, 176, 184, 255)
    top = m & ~np.roll(m, 2, 0); s[top] = (255, 224, 214, 255)
    bot = m & ~np.roll(m, -2, 0); s[bot] = (206, 132, 158, 255)
    return s


CLOUDS = [(1, 30, 12, 10, 36, 4.0), (2, 44, 14, 120, 52, 3.0), (3, 26, 10, 60, 92, 5.0), (4, 36, 12, 170, 120, 3.6),
          (5, 22, 8, 20, 140, 4.4), (6, 30, 10, 140, 26, 2.6)]


@lru_cache(None)
def sun_static():
    a = am.vgrad(NH, NW, [(0, (56, 60, 110)), (0.16, (104, 82, 138)), (0.32, (196, 118, 148)), (0.45, (242, 160, 140)),
                           (0.535, (255, 202, 152)), (0.54, (150, 120, 162)), (0.7, (96, 88, 140)), (1, (52, 52, 96))])
    hz = 206
    for x in range(NW):                         # hills on the horizon
        h1 = 7 * math.exp(-((x - 160) / 30) ** 2) + 4 * math.exp(-((x - 205) / 14) ** 2)
        h2 = 3 * math.exp(-((x - 18) / 16) ** 2)
        hh = int(max(h1, h2))
        if hh: a[hz - hh:hz, x] = (126, 86, 124)
    yy, xx = np.mgrid[0:NH, 0:NW]
    disc = ((xx - 64) ** 2 + (yy - hz) ** 2 < 81) & (yy < hz)
    a[disc] = (255, 238, 196)
    am.glow(a, 64, hz - 2, 30, (255, 220, 170), 0.5)
    return a


def sunrise(t):
    a = sun_static().copy()
    for seed, w, h, x0, y0, sp in CLOUDS:       # drifting clouds
        am.paste(a, cloud(seed, w, h), (x0 + sp * t) % (NW + w) - w, y0)
    for i in range(3):                          # birds
        bx, by = (40 + i * 14 + 6 * t) % (NW + 20) - 10, 70 + i * 5 + round(math.sin(t * 2 + i))
        wing = int(t * 4 + i) % 2
        for dx, dy in ((-2, -wing), (-1, 0), (0, 1), (1, 0), (2, -wing)):
            if 0 <= bx + dx < NW: a[int(by + dy), int(bx + dx)] = (60, 44, 70)
    for y in range(207, NH, 2):                 # sun reflection column + sea sparkle
        k = (y - 207) / (NH - 207)
        w = 2 + int(14 * k * abs(math.sin(y * 1.7 + t * 2.2)))
        x = 64 + int(5 * k * math.sin(y * 0.5 + t * 1.3))
        if (y // 2 + int(t * 6)) % 3: a[y, max(0, x - w):x + w] = (255, 212, 160) if k < 0.4 else (236, 160, 150)
    for y in range(212, NH, 7):
        xx = int((y * 31 + t * 6) % NW); a[y, xx:xx + 5] += 14
    tint = (1.0, 0.86, 0.86)
    deck = 262                                  # pier: posts with reflections, deck, cars and the guy
    for px in range(100, NW, 15):
        a[deck + 3:deck + 60, px:px + 3] = (66, 40, 54)
        for y in range(deck + 62, deck + 100, 2): a[y, px + int(math.sin(y * 0.8 + t * 3)):px + 3] = (88, 66, 100)
    a[deck:deck + 4, 94:NW] = (92, 58, 66); a[deck, 94:NW] = (150, 100, 98); a[deck + 4, 94:NW] = (52, 34, 46)
    for spr, x in ((am.hatchback(), 112), (am.suv(), 160)):
        am.paste(a, spr, x, deck - spr.shape[0], tint)
    am.paste(a, am.mini_guy((t % 4.1) < 0.12), 98, deck - 23, tint)
    return a


# ------------------------------------------------------------------ composition
def to_img(a, pan=0.0, ww=None):
    ww = ww or a.shape[1]
    big = am.up(np.clip(a, 0, 255).astype(np.uint8), K)
    x0 = int(round(pan * K))
    return big[:, x0:x0 + W]


def picture(t):
    def F(tt):
        a, p = flood(tt); return to_img(a, p).astype(np.float32)
    if t >= END:                                # loop: the night street returns to frame 0
        e = io(prog(t, END, LOOP)); return am.blend(sunrise_img(t), F(t - DUR), e)
    if t < T_DEPTH: return F(t)
    if t < T_DEPTH + 0.3: return am.blend(F(t), depth_img(t), io(prog(t, T_DEPTH, 0.3)))
    if t < T_SUN: return depth_img(t)
    if t < T_SUN + 0.8: return am.blend(depth_img(t), sunrise_img(t), io(prog(t, T_SUN, 0.8)))
    return sunrise_img(t)


def depth_img(t):
    a = am.depth_graphic(t - T_DEPTH)
    rk = 1 - clamp((t - T_SUN) / 0.8)           # the rain clears as the sunrise dissolves in
    if rk > 0: am.rain(a, t, **dict(RAIN_NEAR, n=int(300 * rk), k=0.6 * rk, water_y=None))
    return to_img(a).astype(np.float32)


def sunrise_img(t): return to_img(sunrise(t)).astype(np.float32)


# ------------------------------------------------------------------ text (sharp, inside the safe zone)
HL1 = ((('Which car', None),), (('would you', None), ('SAVE?', YEL)))
HL2 = ((("HIGHER ISN'T", None),), (('ALWAYS', None), ('SAFER', YEL)))


def hl(cv, t, t0, t1, lines, y=440):
    if not (t0 <= t < t1 + 0.2): return
    img = headline_img(lines, 100)
    k = popin(t, t0, 0.3) * popout(t, t1, 0.2) * min(1, 820 / img.width)
    ov.place(cv, img, ov.SAFE_CX, y, k, -2.0, 'headline')


def pills(cv, t):
    p = pan_at(t)
    ov.chip(cv, t, T_LOWER, T_DEPTH - 0.1, 'LOWER', (HX + 20 - p) * K, 1050, col=(110, 200, 230), sz=58)
    ov.chip(cv, t, T_HIGHER, T_DEPTH - 0.1, 'HIGHER', (SX + 24 - p) * K, 1010, col=YEL, sz=58)


def poll(cv, t):
    if not (T_POLL <= t < END + 0.2): return
    grow = 0.78 + 0.2 * io(prog(t, T_POLL + 0.3, 1.6))
    ov.poll(cv, t, T_POLL, END, 'Which would you save?', ov.SAFE_CX, 760, grow,
            opts=(('HATCHBACK', (90, 200, 220)), ('SUV', YEL)), rot=-2.0)


def overlay(cv, t):
    ov.reset()
    hl(cv, t, -0.45, T_LOWER - 1.2, HL1)       # on screen from frame 0 (pops in during the loop tail)
    if t >= END: hl(cv, t - DUR, -0.45, 99, HL1)
    pills(cv, t)
    hl(cv, t, T_DEPTH + 0.1, T_SUN + 0.1, HL2)
    poll(cv, t)


def frame(n, check=True):
    t = n / FPS
    cv = Image.fromarray(np.clip(picture(t), 0, 255).astype(np.uint8)).convert('RGBA')
    overlay(cv, t)
    if check and ov.violations(): raise SystemExit(f'safe zone violation at {t:.2f}: {ov.violations()}')
    return cv.convert('RGB').tobytes()


# ------------------------------------------------------------------ audio
SR = sfx.SR


def _bp(x, lo, hi):
    X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / SR); X[(f < lo) | (f > hi)] = 0
    return np.fft.irfft(X, len(x))


def ambience(n):
    """Soft rain hiss + drops + low water lapping, rain fades out for the sunrise and returns for the loop."""
    r = np.random.default_rng(3); tt = np.arange(n) / SR
    rain = _bp(r.normal(0, 1, n), 900, 7000); rain /= np.abs(rain).max()
    drops = np.zeros(n); idx = r.integers(0, n - 400, 260)
    for i in idx: drops[i:i + 400] += r.uniform(0.2, 0.6) * np.exp(-np.arange(400) / 60) * np.sin(np.arange(400) * r.uniform(0.3, 0.6))
    lap = _bp(r.normal(0, 1, n), 60, 420); lap /= np.abs(lap).max(); lap *= 0.6 + 0.4 * np.sin(tt * 1.3) ** 2
    rk = np.interp(tt, [0, T_SUN, T_SUN + 1.0, END, DUR], [1, 1, 0.08, 0.08, 1])
    return rk * (0.8 * rain + 0.5 * drops) + 0.55 * lap


def build_audio(vo_path, out_wav):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', vo_path, '-ar', str(SR), '-ac', '1', '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    vo = np.frombuffer(raw, np.float32).astype(np.float64)
    n = int(SR * DUR); mix = np.zeros(n); m = min(n, len(vo)); mix[:m] = vo[:m]
    rms = lambda x: np.sqrt(np.mean(x[np.abs(x) > 1e-4] ** 2))
    amb = ambience(n); amb *= rms(vo) * 10 ** (-20 / 20) / rms(amb)     # ambience ~20 dB under the voice
    fx = sfx.render([(T_LOWER - 0.05, 'thump', 1.0), (T_LOWER, 'poof', 0.3), (T_DEPTH, 'whoosh', 0.25)], DUR)
    fx *= rms(vo) * 10 ** (-9 / 20) / rms(fx)
    mix += amb + fx
    mix /= max(1.0, np.max(np.abs(mix)) / 0.97)
    with wave.open(out_wav, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype('<i2').tobytes())


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'still':
        for ts in sys.argv[3:]:
            Image.frombytes('RGB', (W, H), frame(int(round(float(ts) * FPS)))).save(f'{sys.argv[2]}/f_{ts}.png')
    elif mode == 'video':
        vo, out = sys.argv[2], sys.argv[3]
        t0, t1 = (float(sys.argv[4]), float(sys.argv[5])) if len(sys.argv) > 5 else (0.0, DUR)
        mixp = os.path.join(os.path.dirname(os.path.abspath(out)), 'mix.wav'); build_audio(vo, mixp)
        F0, N = int(round(t0 * FPS)), int(round(t1 * FPS))
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                               '-i', '-', '-ss', str(t0), '-t', str(t1 - t0), '-i', mixp, '-c:v', 'libx264', '-preset', 'slow', '-crf', '17',
                               '-pix_fmt', 'yuv420p', '-vf', 'setsar=1', '-aspect', '9:16', '-c:a', 'aac', '-b:a', '192k',
                               '-movflags', '+faststart', '-shortest', out], stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for i, b in enumerate(pool.imap(frame, range(F0, N), chunksize=4)):
                ff.stdin.write(b)
        ff.stdin.close(); ff.wait(); print('done', ff.returncode); raise SystemExit(ff.returncode)
