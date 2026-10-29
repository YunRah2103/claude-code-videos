"""Episode kit: the caption, progress-bar, photo-card, end-card, audio-mixer and CLI code from
videos/jaguar-rise-fall/src/render.py (itself from ac-idle), lifted here so new episodes stop copying it.

An episode sets up its shots, then calls:
    kit.setup(HERE, dur=..., end_t=..., shots=SHOTS, trans=TRANS, cues=CUES, keycol={...}, overlay=fn)
    kit.main()
The corner RPM gauge was dropped on purpose (removed from the format on request).
"""
import json, math, os, subprocess, sys, wave
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from audio import sfx
from pixanim.motion import prog, clamp, ob, io
from pixanim import fx, transitions as T
from pixanim.fx import blit, popin, popout
from pixanim.car import car
from pixanim.grid import up
from pixanim.car import wheel_deg
from pixanim.camera import Camera
from pixanim.presenter import Presenter
from pixanim.motion import Track, oc
from pixanim.props import sheet
from pixanim import diagram as dg
from backdrops.garage import Garage

W, H, FPS, S = 1080, 1920, 60, 9
NAVY = (26, 26, 46)
GLOW = (255, 210, 63)
RED, YEL, GRN, WHITE = (255, 90, 90), (255, 217, 59), (90, 220, 120), (255, 255, 255)
CAP_Y = 1390
GROUND = 1180
GAR = Garage(W, H, GROUND, S)
E = {}   # episode state, filled by setup(); forked render workers inherit it


def setup(here, words, dur, end_t, shots, trans, cues, keycol, overlay=None, bar_car='red'):
    E.update(here=here, words=words, dur=dur, end_t=end_t, shots=shots, trans=trans, cues=cues, keycol=keycol, overlay=overlay,
             bar_car=bar_car, photo_dir=os.path.join(here, '..', 'assets'))
    E['chunks'] = make_chunks()
    cr = os.path.join(E['photo_dir'], 'credits.json')
    E['credits'] = json.load(open(cr)) if os.path.isfile(cr) else []


def load_words(here, name='words.json'): return json.load(open(os.path.join(here, name)))


# ------------------------------------------------------------------ scene helpers (as in the reference episodes)
def layer(): return Image.new('RGBA', (W, H), (0, 0, 0, 0))


def finish(img, fg, cam, t, rim=True):
    """Composite a foreground layer (rim-lit) over the world image, then frame it with the shot camera."""
    if rim: fg = GAR.rim(fg)
    img = img.copy(); img.alpha_composite(fg)
    return cam.apply(img.convert('RGB'), t, (14, 15, 18))


def draw_car(cv, col, x, s, y=GROUND, flip=False, dist=0.0, lights=False, brake=False, sx=1.0, sy=1.0, rot=0.0):
    blit(cv, up(car(col, wheel_deg(dist, s), lights, brake), s), x, y, sx, sy, rot, flip=flip)


def teaser(t0, words, sheet_x=660, sign_at=(560, 520)):
    """Shared ending: NEXT EPISODE label over a dust sheet; he lifts it, confetti, 'Follow' card (from jaguar shot 7)."""
    lift_t, end = t0 + 0.55, t0 + 0.75
    P = Presenter([
        (t0 - 0.05, dict(path=Track([(t0 - 0.05, (-200, 500)), (t0 + 0.35, (250, GROUND), 'oc')]), size=8, legs='auto', arms='fly',
                         expr='grin', face=1, ground=None)),
        (t0 + 0.35, dict(ground=GROUND, squash=True, arms='point', point=(sheet_x, GROUND - 200), look=(sheet_x, GROUND - 200))),
        (lift_t, dict(arms=('aim', 30), expr='wow', squash=True)),
        (end + 0.2, dict(arms='thumb', point=None, look=None, look_camera=True, expr='grin', squash=True)),
    ], words=words, base_size=8)
    cam = Camera(W, H, [(t0, (560, 900, 1.2)), (lift_t, (600, 960, 1.28), 'io'), (end + 0.3, (560, 920, 1.18), 'io'), (t0 + 6, (560, 920, 1.24))],
                 kicks=[(t0 + 0.2, 0.06, *sign_at), (lift_t, 0.12, sheet_x, GROUND - 200), (end + 0.2, 0.08, 250, 900)])

    def shot(t):
        img = GAR.frame(t).convert('RGBA'); fg = layer()
        lift = oc(prog(t, lift_t, 0.35)) * 0.85
        fx.rays(fg, t, t0 + 0.15, sheet_x, GROUND - 200, GLOW, hold=True, r=560)
        blit(fg, up(sheet(round(lift * 20) / 20), 8).transpose(Image.FLIP_LEFT_RIGHT), sheet_x, GROUND)
        if lift > 0.3: fx.sparkles(fg, t * 1.6, sheet_x - 170, GROUND - 60, 160, 100, n=8, seed=58)
        dg.label(fg, t, t0 + 0.15, 'NEXT EPISODE', (sheet_x, GROUND - 330), sign_at, '#ffd23f', '#1a1a2e', '#e8b923', s=8)
        fx.sparkles(fg, t, *sign_at, 560, 140, n=6, seed=31)
        if t >= lift_t:
            kq = popin(t, lift_t, 0.25) * (1 + 0.1 * math.sin(t * 9))
            blit(fg, fx.big('glyph', '?', '#e0303a', s=16), sheet_x + 40, GROUND - 330, kq, kq, 8 * math.sin(t * 6), anchor='center')
            fx.burst(fg, t, lift_t, sheet_x + 40, GROUND - 330, seed=81)
        fx.confetti(fg, t, end, 540, 700, n=50, seed=3)
        P.draw(fg, t)
        GAR.reflect(img, fg)
        return finish(img, fg, cam, t)
    cues = [(t0 + 0.35, 'thump', 0.5), (t0 + 0.2, 'pop', 0.7), (t0 + 0.22, 'sparkle', 0.6), (lift_t, 'creak', 0.6),
            (lift_t + 0.02, 'boom', 0.35), (lift_t + 0.04, 'sparkle', 0.8), (end, 'confetti', 1.0), (end + 0.02, 'ding', 0.7)]
    return shot, cues


# ------------------------------------------------------------------ fonts and text
FONT_PATH = os.environ.get('PIXEL_FONT', '/usr/share/fonts/opentype/inter/Inter-Black.otf')


@lru_cache(None)
def font(size):
    if os.path.isfile(FONT_PATH):
        return ImageFont.truetype(FONT_PATH, size)
    try:
        return ImageFont.truetype('DejaVuSans-Bold.ttf', size)
    except OSError:
        return ImageFont.load_default(size=size)


@lru_cache(None)
def text_img(txt, col, sz):
    f = font(sz); d0 = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    w = int(d0.textlength(txt, font=f)) + 60
    img = Image.new('RGBA', (w, int(sz * 1.5)), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.text((30 + 6, 8 + 8), txt, font=f, fill=NAVY, stroke_width=14, stroke_fill=NAVY)
    d.text((30, 8), txt, font=f, fill=col, stroke_width=13, stroke_fill=(10, 10, 16))
    return img


def title(cv, t, t0, t1, txt, col, y, sz=110, rot=0.0):
    """Big outlined title that pops in at t0 and out at t1 (hook captions like 'Tractors vs. Ferraris')."""
    if not (t0 <= t < t1 + 0.2): return
    k = popin(t, t0, 0.3) * popout(t, t1, 0.2) * (1 + 0.025 * math.sin(t * 8))
    img = text_img(txt, col, sz)
    if img.width > 1020: k *= 1020 / img.width
    blit(cv, img, W / 2, y, k, k, rot + 1.5 * math.sin(t * 3), anchor='center')


# ------------------------------------------------------------------ real photos in framed cards
@lru_cache(None)
def _src(name): return Image.open(os.path.join(E['photo_dir'], name + '.jpg')).convert('RGB')


@lru_cache(None)
def _frame(w, h, label):
    img = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, w - 1, h - 1), 12, fill=(248, 246, 238, 255), outline=NAVY + (255,), width=6)
    if label:
        f = font(34)
        while d.textlength(label, font=f) > w - 30 and f.size > 18: f = font(f.size - 2)
        tw = d.textlength(label, font=f)
        d.text((w / 2 - tw / 2, h - 54), label, font=f, fill=NAVY + (255,))
    return img


@lru_cache(None)
def _shadow(w, h):
    sh = Image.new('RGBA', (w, h), (0, 0, 0, 255))
    sh.putalpha(_frame(w, h, '').getchannel('A').point(lambda a: a * 120 // 255))
    return sh


def cover(name, iw, ih, focus=(0.5, 0.5), zoom=0.0, k=0.0):
    src = _src(name); sw, sh = src.size
    sc = max(iw / sw, ih / sh) * (1 + zoom + 0.12 * k)
    cw, ch = iw / sc, ih / sc
    cx = min(max(focus[0] * sw, cw / 2), sw - cw / 2); cy = min(max(focus[1] * sh, ch / 2), sh - ch / 2)
    return src.crop((int(cx - cw / 2), int(cy - ch / 2), int(cx + cw / 2), int(cy + ch / 2))).resize((iw, ih), Image.BILINEAR)


def photo_card(name, w, h, label='', k=0.0, focus=(0.5, 0.5), zoom=0.0):
    b = 16; iw, ih = w - 2 * b, h - b - 64
    img = _frame(w, h, label).copy(); img.paste(cover(name, iw, ih, focus, zoom, round(k * 30) / 30), (b, b))
    return img


def photo(fg, t, t0, t1, name, x, y, w, h, rot=0.0, label='', focus=(0.5, 0.5), zoom=0.0):
    """Pop a real photo card in at t0, sway and push in slowly, pop it out at t1."""
    if not (t0 <= t < t1 + 0.25): return
    k = popin(t, t0, 0.3) * popout(t, t1, 0.2)
    if k <= 0.01: return
    r = rot + 2.5 * math.sin(t * 2.2 + x)
    blit(fg, _shadow(w, h), x + 14, y + 18, k, k, r, anchor='center')
    blit(fg, photo_card(name, w, h, label, clamp((t - t0) / 3), focus, zoom), x, y, k, k, r, anchor='center')
    fx.burst(fg, t, t0, x, y, GLOW, n=8, r0=90, r1=260, seed=int(x) % 90)


# ------------------------------------------------------------------ captions: chunks of <=3 words, one highlighted keyword
def make_chunks():
    words = E['words']
    sents, cur = [], []
    for i, w in enumerate(words):
        cur.append(i)
        if w['w'][-1] in '.,?!:':
            sents.append(cur); cur = []
    if cur: sents.append(cur)
    chunks = []
    for s in sents:
        k = math.ceil(len(s) / 3)
        base, extra = divmod(len(s), k)
        j = 0
        for c in range(k):
            n = base + (1 if c < extra else 0)
            chunks.append(s[j:j + n]); j += n
    out = []
    for ci, c in enumerate(chunks):
        st = words[c[0]]['s'] - 0.04
        nxt = words[chunks[ci + 1][0]]['s'] - 0.04 if ci + 1 < len(chunks) else E['end_t']
        out.append((st, min(nxt, words[c[-1]]['e'] + 0.45), c))
    return out


def clean(w): return w.lower().strip('.,!:?')


@lru_cache(None)
def caption_img(ci):
    words = [E['words'][i]['w'] for i in E['chunks'][ci][2]]
    f = font(104); d0 = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    space = d0.textlength(' ', font=f)
    widths = [d0.textlength(w, font=f) for w in words]
    pad = 40
    img = Image.new('RGBA', (int(sum(widths) + space * (len(words) - 1) + 2 * pad), 190), (0, 0, 0, 0))
    d = ImageDraw.Draw(img); x = pad
    for w, wd in zip(words, widths):
        col = E['keycol'].get(clean(w), WHITE)
        d.text((x + 6, 38), w, font=f, fill=NAVY, stroke_width=14, stroke_fill=NAVY)
        d.text((x, 30), w, font=f, fill=col, stroke_width=13, stroke_fill=(10, 10, 16))
        x += wd + space
    if img.width > 1000:
        img = img.resize((1000, int(img.height * 1000 / img.width)), Image.LANCZOS)
    return img


def captions(cv, t):
    if t >= E['end_t']:
        img = text_img('Follow for the next one', YEL, 92); k = 0.72 + 0.28 * ob(prog(t, E['end_t'], 0.16)) + 0.03 * math.sin(t * 8)
        img = img.resize((int(img.width * k), int(img.height * k)), Image.BILINEAR)
        cv.paste(img, (int(W / 2 - img.width / 2), int(CAP_Y - img.height / 2)), img)
        return
    for ci, (st, en, _) in enumerate(E['chunks']):
        if st <= t < en:
            img = caption_img(ci)
            k = 0.72 + 0.28 * ob(prog(t, st, 0.16)); dy = 18 * (1 - ob(prog(t, st, 0.2)))
            if k != 1: img = img.resize((int(img.width * k), int(img.height * k)), Image.BILINEAR)
            cv.paste(img, (int(W / 2 - img.width / 2), int(CAP_Y + dy - img.height / 2)), img)
            return


@lru_cache(None)
def credit_img():
    """Small photo credits for the end card, built from ../assets/credits.json."""
    if not E['credits']: return None
    by = {}
    for c in E['credits']: by.setdefault(c['licence'], []).append(c['author'][:40])
    lines = ['Photos: Wikimedia Commons'] + [f"{', '.join(a)} ({lic})" for lic, a in by.items()]
    f = font(22); d0 = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    img = Image.new('RGBA', (1040, 30 * len(lines) + 10), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    for i, ln in enumerate(lines):
        while d0.textlength(ln, font=f) > 1020: ln = ln[:-4] + '...'
        d.text((520 - d0.textlength(ln, font=f) / 2, 4 + 30 * i), ln, font=f, fill=(200, 204, 214, 230))
    return img


# ------------------------------------------------------------------ progress bar (pixel car rides along the top)
def progress(cv, t):
    dur = E['dur']; p = clamp(t / dur); d = ImageDraw.Draw(cv)
    x0, x1, y, h = 100, W - 100, 120, 4 * S
    d.rounded_rectangle((x0 - 7, y - 7, x1 + 7, y + h + 7), 22, fill=NAVY)
    d.rounded_rectangle((x0, y, x1, y + h), 16, fill=(236, 236, 242))
    xp = x0 + (x1 - x0) * p
    if xp > x0 + 32:
        d.rounded_rectangle((x0, y, xp, y + h), 16, fill=GLOW)
        d.rectangle((x0 + 16, y + 7, xp - 16, y + 13), fill=(255, 238, 160))
    for tc, _ in E['shots'][1:]:
        xc = x0 + (x1 - x0) * tc / dur; yc = y + h / 2; on = t >= tc
        r = 12 * (1 + 0.6 * math.exp(-(t - tc) * 10) if on else 1)
        d.ellipse((xc - r - 6, yc - r - 6, xc + r + 6, yc + r + 6), fill=NAVY)
        d.ellipse((xc - r, yc - r, xc + r, yc + r), fill=(60, 200, 90) if on else (200, 204, 212))
    blit(cv, up(car(E['bar_car'], int(t * 300) % 360), 1), xp, y + 8 - S * (int(t * 8) % 2))


# ------------------------------------------------------------------ shots, frame, audio, CLI
def picture(t):
    shots = E['shots']
    idx = max(i for i, (s, _) in enumerate(shots) if t >= s)
    if idx in E['trans']:
        t0, t1, kind, opt = E['trans'][idx]
        if t < t1:
            e = io(prog(t, t0, t1 - t0)); a, b = shots[idx - 1][1](t), shots[idx][1](t)
            if kind == 'whip': return T.whip(a, b, e, **opt)
            if kind == 'push': return T.push(a, b, e, dx=opt or -1)
            if kind == 'iris': return T.iris(a, b, e, *opt)
    return shots[idx][1](t)


def frame(n):
    t = n / FPS
    cv = picture(t)
    if t < 0.12:                                    # white flash on frame 0 for the hook
        cv = Image.blend(cv, Image.new('RGB', (W, H), (255, 255, 255)), 0.7 * (1 - t / 0.12))
    if E['overlay']: E['overlay'](cv, t)
    GAR.vignette(cv)
    captions(cv, t)
    if t >= E['end_t'] - 0.3 and credit_img():
        c = credit_img(); cv.paste(c, (int(W / 2 - c.width / 2), H - c.height - 14), c)
    progress(cv, t)
    return cv.tobytes()


def build_audio(vo_path, out_wav):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', vo_path, '-ar', str(sfx.SR), '-ac', '1', '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    vo = np.frombuffer(raw, np.float32).astype(np.float64)
    n = int(sfx.SR * E['dur'])
    mix = np.zeros(n); m = min(n, len(vo)); mix[:m] = vo[:m]
    cues = E['cues'] + [(t, 'whoosh', 0.6) for t, _ in E['shots'][1:]]
    fxa = sfx.render(cues, E['dur'])
    fxa *= 0.32 * np.max(np.abs(vo)) / max(1e-9, np.max(np.abs(fxa)))
    mix += fxa
    mix /= max(1.0, np.max(np.abs(mix)) / 0.97)
    with wave.open(out_wav, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sfx.SR); w.writeframes((mix * 32767).astype('<i2').tobytes())


def main():
    """still <dir> t... | video <voiceover> <out.mp4> [t0 t1]"""
    mode = sys.argv[1]
    if mode == 'still':
        os.makedirs(sys.argv[2], exist_ok=True)
        for ts in sys.argv[3:]:
            Image.frombytes('RGB', (W, H), frame(int(float(ts) * FPS))).save(f'{sys.argv[2]}/f_{ts}.png')
    elif mode == 'video':
        vo, out = sys.argv[2], sys.argv[3]
        t0, t1 = (float(sys.argv[4]), float(sys.argv[5])) if len(sys.argv) > 5 else (0.0, E['dur'])
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        mix = os.path.splitext(out)[0] + '_mix.wav'
        build_audio(vo, mix)
        F0, N = int(t0 * FPS), int(t1 * FPS)
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                               '-i', '-', '-ss', str(t0), '-t', str(t1 - t0), '-i', mix, '-c:v', 'libx264', '-preset', 'medium', '-crf', '18',
                               '-maxrate', '8M', '-bufsize', '12M', '-pix_fmt', 'yuv420p',
                               '-c:a', 'aac', '-b:a', '160k', '-movflags', '+faststart', '-shortest', out], stdin=subprocess.PIPE)
        with Pool(os.cpu_count() or 4) as pool:
            for i, b in enumerate(pool.imap(frame, range(F0, N), chunksize=6)):
                ff.stdin.write(b)
                if i % 300 == 0: print(f'{i}/{N - F0}', flush=True)
        ff.stdin.close(); ff.wait()
        os.remove(mix)
        print('done', ff.returncode)
        raise SystemExit(ff.returncode)
