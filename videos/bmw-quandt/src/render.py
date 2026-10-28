"""Renders 'BMW almost became part of Mercedes': the 1959 rescue story and Herbert Quandt. Generic cars only.

Word times come from the aligned voiceover (align.py). The video is 28 s to fit the spoken script.
One garage set, six beats (times are the spoken word starts):
  1 hook      0.00  two cars slam in and face off; the presenter stands between them; 'almost'
  2 paper     2.97  newspaper slides in; a red crack opens on 'serious trouble'
  3 stop      6.60  paper whips away; the silver car rolls at the small car; he raises a hand; suited silhouette + nameplate
  4 certs    14.90  share certificates pile over the small car; thumbs up on 'stayed'
  5 doubt    19.79  question bubbles; shrug on 'nobody agrees'; both cars drive off
  6 sign     23.10  NEXT EPISODE sign glows; he stands in front; 'Follow' card after the voice
"""
import json, math, os, sys, subprocess, wave
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..', 'shared'))
from backdrops.garage import Garage
from audio import sfx
from pixanim.motion import prog, lerp, clamp, ob, oc, ic, io, springs
from pixanim.camera import Camera
from pixanim.presenter import Presenter, Fn
from pixanim import fx
from pixanim.fx import blit, popin, popout
from pixanim.car import car, wheel_deg
from pixanim.dash import _gauge_face
from pixanim.grid import up

W, H, FPS, S = 1080, 1920, 60, 9
GROUND = 1180
DUR = 28.0
BG = (14, 15, 18)
NAVY = (26, 26, 46)
RED, YEL, GRN, WHITE = (255, 90, 90), (255, 217, 59), (90, 220, 120), (255, 255, 255)
GAR = Garage(W, H, GROUND, S)
WORDS = json.load(open('words.json'))

PX = 540                   # presenter centre
SMALL0, SMALL_S = 230, 3   # small car (the stand-in for BMW)
BIG0, BIG_S = 860, 4       # silver car (the stand-in for Mercedes)
BIG_STOP = 740
SIL_X = 900                # suited silhouette
END_T = 26.9               # speech ends here; the 'Follow' card takes over


def layer(): return Image.new('RGBA', (W, H), (0, 0, 0, 0))


def finish(img, fg, cam, t):
    """Composite a foreground layer (rim-lit) over the world image, then frame it with the shot camera."""
    fg = GAR.rim(fg)
    img = img.copy(); img.alpha_composite(fg)
    return cam.apply(img.convert('RGB'), t, BG)


# ------------------------------------------------------------------ presenter and camera
P = Presenter([
    (0.0, dict(path=Fn(lambda t: (PX, GROUND)), size=6, ground=GROUND, legs='stand', arms='wave', expr='grin')),
    (2.97, dict(arms='point', point=(540, 700), expr='smile')),
    (6.6, dict(arms='point', point=(760, 1000), expr='smirk')),        # raised hand toward the silver car
    (9.7, dict(squash=True, expr='shock')),
    (12.0, dict(arms='point', point=(SIL_X, 900), expr='wow', squash=True)),
    (14.9, dict(arms='talkB', expr='grin')),
    (17.33, dict(arms='thumb', expr='grin', squash=True)),
    (19.79, dict(arms='down', expr='think')),
    (20.7, dict(arms='shrug', expr='smirk', squash=True)),
    (23.1, dict(arms='cheer1', expr='grin', squash=True)),
], words=WORDS, base_size=6)

CAM = Camera(W, H, [(0.0, (540, 1010, 1.22)), (3.0, (540, 900, 1.25), 'io'), (6.6, (560, 1010, 1.18), 'io'),
                    (12.0, (600, 980, 1.15), 'io'), (14.9, (540, 1010, 1.12), 'io'), (19.8, (540, 960, 1.25), 'io'),
                    (21.6, (540, 960, 1.0), 'io'), (23.1, (540, 900, 1.12), 'io'), (DUR, (540, 900, 1.18))],
             kicks=[(0.0, 0.12, 540, 980), (0.45, 0.1, 540, 1050), (2.97, 0.1, 540, 700), (5.4, 0.1, 540, 760),
                    (10.75, 0.1, 760, 960), (12.0, 0.12, SIL_X, 900), (17.33, 0.08, 540, 900), (23.1, 0.1, 540, 640),
                    (25.84, 0.08, 540, 900)],
             shakes=[(5.4, 0.35, 14), (10.75, 0.3, 10), (12.0, 0.35, 10)])


# ------------------------------------------------------------------ world motion
def small_x(t):
    x = lerp(-260, SMALL0, oc(prog(t, 0.0, 0.45)))
    return lerp(x, -330, ic(prog(t, 21.6, 2.2)))


def big_x(t):
    x = lerp(1340, BIG0, oc(prog(t, 0.0, 0.45)))
    x = lerp(x, BIG_STOP, io(prog(t, 6.6, 3.8)))
    return lerp(x, 1500, ic(prog(t, 21.6, 2.2)))


def paper_xy(t):
    return 540 + 760 * ic(prog(t, 6.6, 0.4)), lerp(-420, 700, ob(prog(t, 2.97, 0.5)))


def rpm_deg(t):   # needle angle on the corner gauge: 225 is zero, lower is more revs
    return springs(t, 225, [(0.0, 150, 14, 6), (6.6, 175, 14, 6), (12.0, 130, 14, 6), (21.6, 105, 14, 6), (24.0, 225, 10, 5)])


# ------------------------------------------------------------------ props
@lru_cache(None)
def paper_img():
    img = Image.new('RGBA', (400, 500), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 399, 499), fill=(246, 244, 236, 255), outline=(40, 40, 52, 255), width=8)
    d.rectangle((24, 24, 376, 92), fill=(40, 40, 52, 255))                      # masthead
    f = font(54); d.text((200 - d.textlength('1959', font=f) / 2, 26), '1959', font=f, fill=YEL + (255,))
    for i, y in enumerate(range(130, 470, 36)):                                  # headline and body lines
        d.rectangle((30, y, 370 - 90 * (i % 3 == 2), y + 14), fill=(150, 150, 160, 255))
    return img


def paper_frame(t):
    img = paper_img().copy()
    k = prog(t, 5.4, 0.12)                                                       # crack opens on 'serious trouble'
    if k > 0:
        pts = [(200 + (14 if i % 2 else -14), 100 + i * 34) for i in range(11)]
        ImageDraw.Draw(img).line(pts[:max(2, int(len(pts) * k))], fill=(224, 48, 58, 255), width=9)
    return img


@lru_cache(None)
def suit_img():
    img = Image.new('RGBA', (220, 440), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    ink = (34, 36, 48, 255)
    d.ellipse((70, 0, 150, 84), fill=ink)                                         # head
    d.polygon([(30, 110), (190, 110), (206, 300), (14, 300)], fill=ink)          # shoulders and jacket
    d.polygon([(95, 112), (125, 112), (110, 200)], fill=(240, 240, 240, 255))    # shirt
    d.polygon([(104, 128), (116, 128), (121, 190), (110, 210), (99, 190)], fill=RED + (255,))  # tie
    d.rectangle((48, 290, 100, 440), fill=ink); d.rectangle((120, 290, 172, 440), fill=ink)     # legs
    return img


@lru_cache(None)
def cert_img():
    img = Image.new('RGBA', (150, 96), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, 149, 95), fill=(250, 244, 222, 255), outline=(60, 150, 90, 255), width=6)
    d.rectangle((14, 14, 136, 22), fill=(60, 150, 90, 255))
    for y in range(36, 80, 10):
        d.rectangle((20, y, 130 - (y % 20) * 2, y + 3), fill=(150, 150, 160, 255))
    d.ellipse((108, 62, 134, 88), fill=(224, 190, 60, 255))                      # seal
    return img


_rng = np.random.default_rng(11)
CERTS = [(_rng.uniform(-80, 80), _rng.uniform(-70, 40), _rng.uniform(-18, 18), 15.0 + i * 0.12) for i in range(18)]
QMARKS = [(PX - 110, 700, 19.79), (PX + 20, 640, 19.95), (PX - 40, 560, 20.1)]


@lru_cache(None)
def sign_img():
    img = Image.new('RGBA', (700, 150), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle((0, 0, 699, 149), 22, fill=(20, 22, 34, 255), outline=YEL + (255,), width=10)
    f = font(84); w = d.textlength('NEXT EPISODE', font=f)
    d.text((350 - w / 2, 30), 'NEXT EPISODE', font=f, fill=YEL + (255,), stroke_width=3, stroke_fill=(10, 10, 16, 255))
    return img


@lru_cache(None)
def gauge_img():
    img = Image.new('RGBA', (240, 240), (0, 0, 0, 0))
    _gauge_face(ImageDraw.Draw(img), 120, 120, 110, red_from=6, label='RPM')
    return img


def gauge(t):
    img = gauge_img().copy(); d = ImageDraw.Draw(img)
    a = math.radians(rpm_deg(t))
    d.line((120, 120, 120 + 84 * math.cos(a), 120 - 84 * math.sin(a)), fill=RED + (255,), width=6)
    d.ellipse((111, 111, 129, 129), fill=(200, 204, 212, 255))
    return img


# ------------------------------------------------------------------ frame
def picture(t):
    img = GAR.frame(t).convert('RGBA')
    fg = layer()
    sx, bx = small_x(t), big_x(t)
    fx.contact_shadow(fg, sx, GROUND, 300, s=S, alpha=120)
    fx.contact_shadow(fg, bx, GROUND, 400, s=S, alpha=120)
    if 0.45 <= t < 0.9:
        fx.dust(fg, t, 0.45, SMALL0, GROUND - 10, n=10, seed=43); fx.dust(fg, t, 0.45, BIG0, GROUND - 10, n=10, seed=45)
        fx.burst(fg, t, 0.45, PX, GROUND - 200, (224, 48, 58), n=12, seed=70)
    # suited silhouette stands behind the silver car
    k_sil = popin(t, 12.0, 0.3) * popout(t, 19.5, 0.2)
    if k_sil > 0.01:
        blit(fg, suit_img(), SIL_X, GROUND, k_sil, k_sil)
        blit(fg, fx.big('tag', 'HERBERT QUANDT', s=6), 650, 620, k_sil, k_sil, anchor='center')
    if 12.0 <= t < 12.6: fx.burst(fg, t, 12.0, SIL_X, GROUND - 300, (255, 210, 63), n=12, seed=72)
    # the cars
    blit(fg, up(car('red', wheel_deg(abs(sx - SMALL0), SMALL_S)), SMALL_S), sx, GROUND)
    blit(fg, up(car('silver', wheel_deg(abs(bx - BIG0), BIG_S)), BIG_S), bx, GROUND, flip=True)
    # share certificates pile over the small car and ride off with it
    for dx, dy, rot, t0 in CERTS:
        if t >= t0:
            yy = dy - 300 * (1 - oc(prog(t, t0, 0.22)))
            blit(fg, cert_img(), sx + dx, GROUND - 90 + yy, anchor='center', rot=rot)
    if 6.6 <= t < 7.0: fx.dust(fg, t, 6.6, 760, GROUND - 10, n=8, seed=44)
    if 15.0 <= t < 15.4: fx.poof(fg, t, 15.0, sx, GROUND - 120, seed=21, life=0.4, scale=0.5)
    if 17.33 <= t < 17.6: fx.gsparkles(fg, t, sx, GROUND - 120, 300, 200, n=8, seed=37)
    if 13.75 <= t < 14.3: fx.burst(fg, t, 13.75, 650, 620, (255, 210, 63), n=10, r0=70, r1=240, seed=73)
    if 10.75 <= t < 12.0:   # 'take it over'
        fx.stamp_at(fg, t, 10.75, 'TAKEOVER', BIG_STOP + 70, GROUND - 260, -8, 8)
        fx.burst(fg, t, 10.75, BIG_STOP, GROUND - 260, (224, 48, 58), seed=74)
    # newspaper: slides in, crack opens, whips away
    if 2.9 <= t < 7.0:
        px, py = paper_xy(t)
        blit(fg, paper_frame(t), px, py, anchor='center', rot=-4)
    # question bubbles over the presenter's head
    for qx, qy, t0 in QMARKS:
        if t0 <= t < 21.6:
            kq = popin(t, t0, 0.25)
            blit(fg, fx.big('glyph', '?', '#e0303a', s=10), qx, qy + 10 * math.sin(t * 7 + t0 * 9), kq, kq, 8 * math.sin(t * 5 + t0), anchor='center')
        fx.poof(fg, t, 21.6, qx, qy, seed=int(t0 * 10), life=0.4, scale=0.35)
    # NEXT EPISODE sign
    if t >= 23.1:
        fx.rays(fg, t, 23.1, 540, 690, (255, 210, 63), hold=True, r=460, n=8)
        k = ob(prog(t, 23.1, 0.35))
        blit(fg, sign_img(), 540, 690, k, k, anchor='center')
        fx.gsparkles(fg, t, 540, 690, 560, 160, n=8, seed=31)
    P.draw(fg, t)
    img = finish(img, fg, CAM, t)
    return img


# ------------------------------------------------------------------ captions
FONT_PATH = os.environ.get('PIXEL_FONT', '/usr/share/fonts/opentype/inter/Inter-Black.otf')

def font(size):
    if os.path.isfile(FONT_PATH):
        return ImageFont.truetype(FONT_PATH, size)
    try:
        return ImageFont.truetype('DejaVuSans-Bold.ttf', size)
    except OSError:
        return ImageFont.load_default(size=size)

FONT = font(104)
KEYCOL = {'almost': RED, 'trouble': YEL, 'herbert': YEL, 'quandt': YEL, 'stayed': GRN, 'nobody': RED, 'agrees': RED}


def make_chunks():
    sents, cur = [], []
    for i, w in enumerate(WORDS):
        cur.append(i)
        if w['w'][-1] in '.,?!':
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
        st = WORDS[c[0]]['s'] - 0.04
        nxt = WORDS[chunks[ci + 1][0]]['s'] - 0.04 if ci + 1 < len(chunks) else END_T
        out.append((st, min(nxt, WORDS[c[-1]]['e'] + 0.45), c))
    return out
CHUNKS = make_chunks()


def clean(w): return w.lower().strip('.,!')


@lru_cache(None)
def caption_img(ci):
    words = [WORDS[i]['w'] for i in CHUNKS[ci][2]]
    d0 = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    space = d0.textlength(' ', font=FONT)
    widths = [d0.textlength(w, font=FONT) for w in words]
    tw = sum(widths) + space * (len(words) - 1)
    pad = 40
    img = Image.new('RGBA', (int(tw + 2 * pad), 190), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    x = pad
    for w, wd in zip(words, widths):
        col = KEYCOL.get(clean(w), WHITE)                       # one highlighted keyword per caption
        d.text((x + 6, 30 + 8), w, font=FONT, fill=NAVY, stroke_width=14, stroke_fill=NAVY)
        d.text((x, 30), w, font=FONT, fill=col, stroke_width=13, stroke_fill=(10, 10, 16))
        x += wd + space
    if img.width > 1000:
        k = 1000 / img.width
        img = img.resize((1000, int(img.height * k)), Image.LANCZOS)
    return img


def _text_img(txt, col, sz):
    f = font(sz); d0 = ImageDraw.Draw(Image.new('RGB', (1, 1)))
    w = int(d0.textlength(txt, font=f)) + 60
    img = Image.new('RGBA', (w, int(sz * 1.5)), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.text((30 + 6, 8 + 8), txt, font=f, fill=NAVY, stroke_width=14, stroke_fill=NAVY)
    d.text((30, 8), txt, font=f, fill=col, stroke_width=13, stroke_fill=(10, 10, 16))
    return img


@lru_cache(None)
def follow_img(): return _text_img('Follow', YEL, 120)


def captions(cv, t):
    if t >= END_T:
        img = follow_img(); k = 0.72 + 0.28 * ob(prog(t, END_T, 0.16))
        img = img.resize((int(img.width * k), int(img.height * k)), Image.BILINEAR)
        cv.paste(img, (int(W / 2 - img.width / 2), int(1390 - img.height / 2)), img)
        return
    for ci, (st, en, idxs) in enumerate(CHUNKS):
        if st <= t < en:
            img = caption_img(ci)
            k = 0.72 + 0.28 * ob(prog(t, st, 0.16))
            dy = 18 * (1 - ob(prog(t, st, 0.2)))
            if k != 1:
                img = img.resize((int(img.width * k), int(img.height * k)), Image.BILINEAR)
            cv.paste(img, (int(W / 2 - img.width / 2), int(1390 + dy - img.height / 2)), img)
            return


# ------------------------------------------------------------------ progress bar
SCENES = [(0.0, 'hook'), (2.97, 'paper'), (6.6, 'stop'), (14.9, 'certs'), (19.79, 'doubt'), (23.1, 'sign')]


def progress(cv, t):
    p = clamp(t / DUR)
    d = ImageDraw.Draw(cv)
    x0, x1, y, h = 100, W - 100, 120, 4 * S
    d.rounded_rectangle((x0 - 7, y - 7, x1 + 7, y + h + 7), 22, fill=NAVY)
    d.rounded_rectangle((x0, y, x1, y + h), 16, fill=(236, 236, 242))
    xp = x0 + (x1 - x0) * p
    if xp > x0 + 32:
        d.rounded_rectangle((x0, y, xp, y + h), 16, fill=(255, 210, 63))
        d.rectangle((x0 + 16, y + 7, xp - 16, y + 13), fill=(255, 238, 160))
    for tc, _ in SCENES[1:]:
        xc = x0 + (x1 - x0) * tc / DUR; yc = y + h / 2
        on = t >= tc
        r = 12 * (1 + 0.6 * math.exp(-(t - tc) * 10) if on else 1)
        d.ellipse((xc - r - 6, yc - r - 6, xc + r + 6, yc + r + 6), fill=NAVY)
        d.ellipse((xc - r, yc - r, xc + r, yc + r), fill=(60, 200, 90) if on else (200, 204, 212))
    blit(cv, up(car('red', int(t * 300) % 360), 1), xp, y + 8 - S * (int(t * 8) % 2))


CONFETTI = [(26.9, 540, 700, 50, 3, 1.0)]


def frame(n):
    t = n / FPS
    cv = picture(t)
    for t0, x, y, k, seed, sp in CONFETTI:
        fx.confetti(cv, t, t0, x, y, n=k, seed=seed, spread=sp)
    GAR.vignette(cv)
    cv.paste(gauge(t), (60, 1640), gauge(t))
    captions(cv, t)
    progress(cv, t)
    return cv.tobytes()


# ------------------------------------------------------------------ audio
CUES = [
    (0.0, 'whoosh', 0.7), (0.0, 'pop', 0.5), (0.45, 'thump', 0.8), (0.5, 'sparkle', 0.5),
    (2.97, 'slide_down', 0.7), (3.45, 'thump', 0.5),
    (5.4, 'crash', 0.6), (5.42, 'boom', 0.3),
    (6.6, 'whoosh', 0.6), (6.67, 'vroom', 0.7), (9.7, 'screech', 0.5), (10.75, 'stamp', 0.9), (10.77, 'thump', 0.5),
    (12.0, 'stamp', 0.9), (12.02, 'thump', 0.6), (13.75, 'ding', 0.9), (13.78, 'sparkle', 0.7),
    (17.33, 'coin', 0.7), (17.36, 'ding', 0.6),
    (19.79, 'pop', 0.6), (19.95, 'pop', 0.6), (20.1, 'pop', 0.6),
    (21.6, 'vroom', 0.8), (22.08, 'click', 0.6),
    (23.1, 'slide_down', 0.4), (23.12, 'ding', 0.9), (23.14, 'sparkle', 0.8),
    (26.9, 'confetti', 0.9), (26.92, 'ding', 0.6),
] + [(15.0 + i * 0.12, 'pop', 0.4) for i in range(18)] + [(t, 'whoosh', 0.5) for t in (2.97, 6.6, 23.1)]


def build_audio(vo_path, out_wav):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', vo_path, '-ar', str(sfx.SR), '-ac', '1', '-f', 'f32le', '-'],
                         capture_output=True, check=True).stdout
    vo = np.frombuffer(raw, np.float32).astype(np.float64)
    n = int(sfx.SR * DUR)
    mix = np.zeros(n); m = min(n, len(vo)); mix[:m] = vo[:m]
    fxa = sfx.render(CUES, DUR)
    fxa *= 0.32 * np.max(np.abs(vo)) / max(1e-9, np.max(np.abs(fxa)))
    mix += fxa
    mix /= max(1.0, np.max(np.abs(mix)) / 0.97)
    pcm = (mix * 32767).astype('<i2')
    with wave.open(out_wav, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sfx.SR); w.writeframes(pcm.tobytes())


if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'still':
        for ts in sys.argv[3:]:
            t = float(ts); n = int(t * FPS)
            Image.frombytes('RGB', (W, H), frame(n)).save(f'{sys.argv[2]}/f_{ts}.png')
    elif mode == 'video':
        vo, out = sys.argv[2], sys.argv[3]
        t0, t1 = (float(sys.argv[4]), float(sys.argv[5])) if len(sys.argv) > 5 else (0.0, DUR)  # optional test range
        build_audio(vo, 'mix.wav')
        F0, N = int(t0 * FPS), int(t1 * FPS)
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                               '-i', '-', '-ss', str(t0), '-t', str(t1 - t0), '-i', 'mix.wav', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p',
                               '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', '-shortest', out], stdin=subprocess.PIPE)
        with Pool(4) as pool:
            for i, b in enumerate(pool.imap(frame, range(F0, N), chunksize=6)):
                ff.stdin.write(b)
                if i % 300 == 0: print(f'{i}/{N}', flush=True)
        ff.stdin.close(); ff.wait()
        print('done', ff.returncode)
        raise SystemExit(ff.returncode)
