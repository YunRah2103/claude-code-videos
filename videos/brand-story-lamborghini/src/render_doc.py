"""brand-story-lamborghini v2: documentary cut. Real footage (S25 phone clips, out/.../footage/clip-NNN.mp4) and
full-bleed stills, one grade, restrained serif titles, sentence subtitles, low synthesised score under the Charon read.
    python render_doc.py shots            # cut/crop every shot to 1080x1920 60 fps intermediates (out/.../doc/shots)
    python render_doc.py still <dir> t..  # composited stills
    python render_doc.py video <out.mp4>
Footage is private reference material (rights unverified): keep it and the render out of git and off public pages.
"""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from audio import sfx

OUT = os.path.abspath(os.path.join(HERE, '..', '..', '..', 'out', 'brand-story-lamborghini'))
FOOT, HQ, DOC = (os.path.join(OUT, d) for d in ('footage', 'stills_hq', 'doc'))
VO = os.path.join(OUT, 'voiceover_v2.wav')
WORDS = json.load(open(os.path.join(HERE, 'words_v2.json')))
W, H, FPS = 1080, 1920, 60
DUR = 50.4
LOOP = 0.45
SERIF = '/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf'
SERIF_I = '/usr/share/fonts/truetype/liberation/LiberationSerif-Italic.ttf'
SANS = '/usr/share/fonts/opentype/inter/InterDisplay-Medium.otf'
SANS_L = '/usr/share/fonts/opentype/inter/InterDisplay-Light.otf'


def at(i): return WORDS[i]['s']


# ------------------------------------------------------------------ shot list: (start, kind, source, params)
# clip params: src time, crop centre x (0-1 of the 16:9 frame), zoom from->to (slow push), drift in x
# still params: crop box (fractions), zoom from->to, centre from->to
SHOTS = [
    (0.0,  'clip', 306, dict(src=193.4, cx=0.36, z=(1.10, 1.0))),     # Revuelto sweeps through the light tunnel
    (2.0,  'clip', 306, dict(src=219.5, cx=0.50, z=(1.0, 1.08))),     # chasing it down the straight
    (4.0,  'clip', 306, dict(src=222.0, cx=0.50, z=(1.0, 1.06))),     # over the engine cover, on track
    (6.0,  'still', 'tractor2241', dict(box=(0.0, 0.34, 1.0, 1.0), z=(1.0, 1.08), c=((.5, .6), (.5, .45)))),
    (9.0,  'still', 'f250gte', dict(box=(0.12, 0.2, 0.9, 0.85), z=(1.0, 1.1), c=((.25, .5), (.65, .5)))),
    (12.0, 'still', 'f250int', dict(z=(1.15, 1.35), c=((.5, .62), (.5, .7)))),
    (14.4, 'still', 'f250gte', dict(box=(0.12, 0.2, 0.9, 0.85), z=(1.12, 1.0), c=((.75, .55), (.6, .55)))),
    (16.5, 'still', 'f250lusso', dict(z=(1.0, 1.1), c=((.35, .55), (.6, .5)))),
    (19.7, 'still', 'tractor', dict(box=(0.06, 0.40, 0.94, 1.0), z=(1.0, 1.06), c=((.5, .55), (.5, .5)), dark=0.55)),
    (22.4, 'still', 'tractor2241', dict(box=(0.0, 0.34, 1.0, 1.0), z=(1.0, 1.0), c=((.3, .4), (.7, .45)), dark=0.6)),
    (24.9, 'clip', 306, dict(src=245.2, cx=0.30, z=(1.0, 1.06))),     # Sant'Agata from the air
    (27.4, 'clip', 306, dict(src=58.4, cx=0.35, z=(1.06, 1.0))),      # finished-car bay
    (29.7, 'clip', 306, dict(src=247.5, cx=0.35, z=(1.08, 1.0))),     # aerial, wider (date card)
    (32.4, 'clip', 306, dict(src=251.0, cx=0.62, z=(1.0, 1.06))),     # assembly
    (35.2, 'clip', 305, dict(src=10.0, cx=0.30, z=(1.0, 1.05))),      # 350 GT by the lake
    (37.6, 'clip', 305, dict(src=190.0, cx=0.40, z=(1.08, 1.0))),     # 350 GT front three-quarter
    (40.3, 'clip', 305, dict(src=160.0, cx=0.30, z=(1.0, 1.06))),     # wood wheel, dash
    (42.6, 'clip', 305, dict(src=172.0, cx=0.18, z=(1.05, 1.12))),    # gear lever
    (44.7, 'clip', 306, dict(src=235.0, cx=0.45, z=(1.0, 1.08))),     # the rivalry: Revuelto at full commitment
    (47.7, 'clip', 305, dict(src=270.0, cx=0.35, z=(1.0, 1.06))),     # 350 GT, last look
    (DUR, None, None, None),
]

# ------------------------------------------------------------------ grade (one look for footage and stills)
def grade(a):
    """uint8 HxWx3 -> graded uint8: gentle S-curve, muted colour, teal shadows / warm highlights, lifted blacks."""
    x = a.astype(np.float32) / 255
    x = x + 0.08 * (x - 0.5) * (1 - np.abs(2 * x - 1))           # soft S-curve
    l = x.mean(2, keepdims=True); x = l + (x - l) * 0.82          # desaturate a touch
    x = x + (1 - l) ** 2 * np.array([-0.02, 0.006, 0.03]) + l ** 2 * np.array([0.03, 0.01, -0.025])
    x = 0.025 + x * 0.965                                          # lifted blacks, rolled highlights
    return (np.clip(x, 0, 1) * 255).astype(np.uint8)


# ------------------------------------------------------------------ shot intermediates
def shot_bounds(i): return SHOTS[i][0], SHOTS[i + 1][0]


def ease(u): u = min(max(u, 0), 1); return u * u * (3 - 2 * u)


def cut_clip(i, path):
    """Fixed 9:16 window of the 16:9 clip, decoded at 60 fps, then an eased push in/out (Lanczos) to 1080x1920."""
    t0, t1 = shot_bounds(i); d = t1 - t0; p = SHOTS[i][3]; n = round(d * FPS)
    cw = round(1080 * 9 / 16); x0 = round(min(max(p['cx'] * 1920 - cw / 2, 0), 1920 - cw))
    dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', str(p['src']), '-i', os.path.join(FOOT, f'clip-{SHOTS[i][2]}.mp4'),
                            '-vf', f'crop={cw}:1080:{x0}:0,fps={FPS}', '-frames:v', str(n), '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'],
                           stdout=subprocess.PIPE)
    enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                            '-i', '-', '-c:v', 'libx264', '-crf', '12', '-preset', 'fast', '-pix_fmt', 'yuv420p', path], stdin=subprocess.PIPE)
    sz = cw * 1080 * 3; last = None
    for k in range(n):
        b = dec.stdout.read(sz)
        if len(b) == sz: last = Image.frombytes('RGB', (cw, 1080), b)
        u = ease(k / max(1, n - 1)); z = p['z'][0] + (p['z'][1] - p['z'][0]) * u
        w, h = cw / z, 1080 / z
        enc.stdin.write(last.resize((W, H), Image.LANCZOS, box=((cw - w) / 2, (1080 - h) / 2, (cw + w) / 2, (1080 + h) / 2)).tobytes())
    dec.stdout.close(); dec.wait(); enc.stdin.close(); enc.wait()
    return H / 1080 * max(p['z'])


def still_src(name):
    import glob
    if name == 'tractor': return Image.open(os.path.join(HERE, '..', 'assets', 'tractor_original.jpg')).convert('RGB')
    return Image.open(glob.glob(os.path.join(HQ, name + '_original.jpg'))[0]).convert('RGB')


def cut_still(i, path):
    t0, t1 = shot_bounds(i); d = t1 - t0; p = SHOTS[i][3]
    im = still_src(SHOTS[i][2])
    if 'box' in p:
        b = p['box']; im = im.crop((round(b[0] * im.width), round(b[1] * im.height), round(b[2] * im.width), round(b[3] * im.height)))
    ar = W / H; iw, ih = (im.width, im.width / ar) if im.width / im.height < ar else (im.height * ar, im.height)
    n = round(d * FPS); dark = p.get('dark', 1.0); up = 0
    ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                           '-i', '-', '-c:v', 'libx264', '-crf', '12', '-preset', 'fast', '-pix_fmt', 'yuv420p', path], stdin=subprocess.PIPE)
    for k in range(n):
        u = ease(k / max(1, n - 1)); z = p['z'][0] + (p['z'][1] - p['z'][0]) * u
        c = [p['c'][0][j] + (p['c'][1][j] - p['c'][0][j]) * u for j in (0, 1)]
        w, h = iw / z, ih / z
        cx = min(max(c[0] * im.width, w / 2), im.width - w / 2); cy = min(max(c[1] * im.height, h / 2), im.height - h / 2)
        up = max(up, W / w)
        fr = im.resize((W, H), Image.LANCZOS, box=(cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2))
        if dark != 1.0: fr = Image.eval(fr, lambda v: int(v * dark))
        ff.stdin.write(fr.tobytes())
    ff.stdin.close(); ff.wait()
    return up


def make_shots():
    os.makedirs(os.path.join(DOC, 'shots'), exist_ok=True); report = []
    for i in range(len(SHOTS) - 1):
        path = os.path.join(DOC, 'shots', f'{i:02d}.mp4')
        if SHOTS[i][1] == 'clip': report.append((i, 'clip', round(cut_clip(i, path), 2)))
        else: report.append((i, SHOTS[i][2], round(cut_still(i, path), 2)))
    with open(os.path.join(DOC, 'concat.txt'), 'w') as f:
        for i in range(len(SHOTS) - 1): f.write(f"file 'shots/{i:02d}.mp4'\n")
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', os.path.join(DOC, 'concat.txt'),
                    '-c', 'copy', os.path.join(DOC, 'picture.mp4')], check=True)
    print('upscale per shot:', report)


# ------------------------------------------------------------------ text
def fnt(path, sz): return ImageFont.truetype(path, sz)


def tracked(d, xy, txt, f, fill, track=0.0, anchor_center=True):
    """Draw text with letter spacing (track = fraction of the font size); returns width."""
    sz = f.size; ws = [d.textlength(ch, font=f) + track * sz for ch in txt]; tw = sum(ws) - track * sz
    x = xy[0] - tw / 2 if anchor_center else xy[0]
    for ch, w in zip(txt, ws): d.text((x, xy[1]), ch, font=f, fill=fill); x += w
    return tw


def shadowed(layer, blur=10, alpha=170):
    a = layer.getchannel('A').filter(ImageFilter.GaussianBlur(blur)).point(lambda v: v * alpha // 255)
    sh = Image.new('RGBA', layer.size, (0, 0, 0, 0)); sh.putalpha(a)
    return Image.alpha_composite(sh, layer)


def fade(t, t0, t1, a=0.35, b=0.35):
    return min(1.0, max(0.0, (t - t0) / a), max(0.0, (t1 - t) / b)) if t0 <= t <= t1 else 0.0


CACHE = {}


def card(key, draw_fn):
    if key not in CACHE:
        lay = Image.new('RGBA', (W, H), (0, 0, 0, 0)); draw_fn(ImageDraw.Draw(lay)); CACHE[key] = shadowed(lay)
    return CACHE[key]


def lower_third(d, title, sub, y=850):
    d.line((90, y, 90 + 70, y), fill=(232, 200, 120, 255), width=3)
    tracked(d, (90, y + 22), title, fnt(SERIF, 54), (245, 242, 235, 255), 0.08, False)
    tracked(d, (92, y + 92), sub.upper(), fnt(SANS_L, 28), (225, 222, 214, 235), 0.28, False)


def quote(d):
    tracked(d, (W * 0.42, 560), '“Stick to', fnt(SERIF_I, 104), (246, 243, 236, 255), 0.0)
    tracked(d, (W * 0.42, 690), 'tractors.”', fnt(SERIF_I, 104), (246, 243, 236, 255), 0.0)
    tracked(d, (W * 0.42, 850), 'AS THE STORY GOES', fnt(SANS_L, 28), (232, 200, 120, 255), 0.35)


def date_card(d):
    tracked(d, (W * 0.42, 560), '1963', fnt(SERIF, 190), (246, 243, 236, 255), 0.06)
    d.line((W * 0.42 - 60, 800, W * 0.42 + 60, 800), fill=(232, 200, 120, 255), width=3)
    tracked(d, (W * 0.42, 830), "SANT'AGATA BOLOGNESE", fnt(SANS_L, 30), (235, 232, 224, 255), 0.32)
    tracked(d, (W * 0.42, 878), 'ITALY', fnt(SANS_L, 26), (210, 206, 198, 230), 0.32)


def title_card(d):
    tracked(d, (W * 0.42, 600), 'THE BAD CLUTCH', fnt(SERIF, 74), (246, 243, 236, 255), 0.16)
    tracked(d, (W * 0.42, 700), 'HOW LAMBORGHINI BEGAN', fnt(SANS_L, 28), (232, 200, 120, 255), 0.32)


CARDS = [  # (t0, t1, key, draw) -- subtitles hide while a card repeats the line
    (-0.4, 5.7, 'title', title_card),
    (6.3, 11.6, 'lt_ferruccio', lambda d: lower_third(d, 'Ferruccio Lamborghini', 'Tractor maker, Ferrari owner')),
    (20.0, 24.6, 'quote', quote),
    (29.7, 34.8, 'date', date_card),
    (35.5, 40.0, 'lt_350', lambda d: lower_third(d, 'Lamborghini 350 GT', 'The first production car')),
]
HIDE_SUBS = ((20.0, 24.6),)

SENTENCES = []                                     # (start, end, text) from the aligned words
_cur = []
for i, w in enumerate(WORDS):
    _cur.append(i)
    if w['w'].endswith(('.', '?')):
        SENTENCES.append((WORDS[_cur[0]]['s'], WORDS[_cur[-1]]['e'], ' '.join(WORDS[k]['w'] for k in _cur))); _cur = []


def sub_img(txt):
    key = 'sub:' + txt
    if key not in CACHE:
        f = fnt(SANS, 44); lay = Image.new('RGBA', (W, 260), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
        words, lines, cur = txt.split(), [], ''
        for wd in words:
            if cur and d.textlength(cur + ' ' + wd, font=f) > 860: lines.append(cur); cur = wd
            else: cur = (cur + ' ' + wd).strip()
        lines.append(cur)
        for k, ln in enumerate(lines):
            tw = d.textlength(ln, font=f); d.text((W * 0.42 - tw / 2 + 20, 20 + k * 60), ln, font=f, fill=(250, 248, 242, 255))
        CACHE[key] = (shadowed(lay, 8, 210), len(lines))
    return CACHE[key]


def tag_img():
    return card('tag', lambda d: tracked(d, (60, 236), 'CAR STUFF, EXPLAINED', fnt(SANS, 26), (240, 238, 232, 200), 0.22, False))


def overlay(cv, t):
    """cv: RGBA frame. Titles fade; subtitles for the spoken sentence sit at ~57-62 % of the height (safe zone)."""
    cv.alpha_composite(tag_img())
    for t0, t1, key, fn in CARDS:
        a = fade(t, t0, t1)
        if a > 0:
            c = card(key, fn); dy = round(14 * (1 - a))
            if a < 1: c = c.copy(); c.putalpha(c.getchannel('A').point(lambda v: int(v * a)))
            cv.alpha_composite(c, (0, dy))
    if any(a <= t <= b for a, b in HIDE_SUBS): return
    for s, e, txt in SENTENCES:
        if s - 0.05 <= t <= e + 0.25:
            img, n = sub_img(txt); a = fade(t, s - 0.05, e + 0.25, 0.12, 0.2)
            if a < 1: img = img.copy(); img.putalpha(img.getchannel('A').point(lambda v: int(v * a)))
            cv.alpha_composite(img, (0, 1190 - 60 * n - 30))
            return


# ------------------------------------------------------------------ finish
_yy, _xx = np.mgrid[0:H, 0:W].astype(np.float32)
VIG = (1 - 0.55 * np.clip(np.sqrt(((_xx - W / 2) / (W * 0.6)) ** 2 + ((_yy - H / 2) / (H * 0.58)) ** 2) - 0.5, 0, 1) ** 1.5)[..., None]
GRAIN = [np.repeat(np.repeat(np.random.default_rng(7 + i).normal(0, 1, (H // 2, W // 2)).astype(np.float32), 2, 0), 2, 1)[..., None] for i in range(8)]


def finish(rgb, t):
    a = grade(rgb).astype(np.float32) * VIG + GRAIN[int(t * FPS / 2) % 8] * 6.0
    return np.clip(a, 0, 255).astype(np.uint8)


def compose(rgb, t):
    cv = Image.fromarray(finish(rgb, t)).convert('RGBA')
    overlay(cv, t)
    return np.asarray(cv.convert('RGB'))


def raw_frames(start=0):
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-ss', str(start), '-i', os.path.join(DOC, 'picture.mp4'), '-f', 'rawvideo',
                          '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
    n, sz = round(start * FPS), W * H * 3
    while True:
        b = p.stdout.read(sz)
        if len(b) < sz: break
        yield n, b; n += 1


FIRST = None


def render_frame(item):
    """Composite one frame; the last LOOP seconds dissolve back into frame 0 so the video loops."""
    global FIRST
    n, b = item; t = n / FPS
    out = compose(np.frombuffer(b, np.uint8).reshape(H, W, 3), t)
    if t > DUR - LOOP:
        if FIRST is None: FIRST = compose(np.frombuffer(next(raw_frames())[1], np.uint8).reshape(H, W, 3), 0.0)
        k = ease((t - (DUR - LOOP)) / (LOOP - 1 / FPS)); out = (out * (1 - k) + FIRST * k).astype(np.uint8)
    return n, out.tobytes()


# ------------------------------------------------------------------ audio: voice on top, quiet score, few accents
def score(dur, sr):
    t = np.arange(int(dur * sr)) / sr
    env = np.clip(t / 3.0, 0, 1) * np.clip((dur - t) / 1.5, 0, 1)
    sw = 0.75 + 0.25 * np.sin(2 * np.pi * t / 12.5 - 1.2)               # slow swell
    bed = sum(a * np.sin(2 * np.pi * f * t + ph) for f, a, ph in ((55, .5, 0), (82.4, .32, 1), (110.3, .22, 2), (164.8, .12, .5), (220.6, .06, 1.7)))
    n = np.random.default_rng(3).normal(0, 1, len(t)); k = int(sr / 300)
    air = np.convolve(n, np.ones(k) / k, 'same') * 0.6
    pulse = np.zeros_like(t)
    for b in np.arange(24.9, 35.2, 60 / 72):                              # soft heartbeat under the founding section
        i = int(b * sr); m = min(len(t) - i, int(0.35 * sr))
        if m > 0: pulse[i:i + m] += np.sin(2 * np.pi * 48 * t[:m]) * np.exp(-t[:m] * 14) * 0.9
    return (bed * sw + air * 0.25 + pulse) * env


def build_audio(path):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', VO, '-ar', str(sfx.SR), '-ac', '1', '-f', 'f32le', '-'], capture_output=True, check=True).stdout
    vo = np.frombuffer(raw, np.float32).astype(np.float64); n = int(DUR * sfx.SR)
    mix = np.zeros(n); m = min(n, len(vo)); mix[:m] = vo[:m]
    rms = lambda x: np.sqrt(np.mean(x ** 2) + 1e-12)
    bed = score(DUR, sfx.SR); bed *= rms(vo[vo != 0]) / rms(bed) * 10 ** (-22 / 20)          # ~22 dB under the voice
    fx = sfx.render([(0.0, 'boom', 0.8), (6.0, 'whoosh', 0.25), (19.7, 'thump', 0.6), (24.9, 'boom', 0.55), (29.7, 'boom', 0.7),
                     (44.7, 'whoosh', 0.35), (46.3, 'whoosh', 0.3)], DUR)
    fx *= 0.18 * np.max(np.abs(vo)) / max(1e-9, np.max(np.abs(fx)))
    mix += bed + fx; mix /= max(1.0, np.max(np.abs(mix)) / 0.97)
    k = int(sfx.SR * 0.3); mix[-k:] *= np.linspace(1, 0, k) ** 2
    with wave.open(path, 'wb') as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(sfx.SR); w.writeframes((mix * 32767).astype('<i2').tobytes())


def main():
    mode = sys.argv[1]
    if mode == 'shots': make_shots()
    elif mode == 'still':
        os.makedirs(sys.argv[2], exist_ok=True)
        for x in sys.argv[3:]:
            n, b = next(raw_frames(float(x)))
            Image.frombytes('RGB', (W, H), render_frame((round(float(x) * FPS), b))[1]).save(f'{sys.argv[2]}/d_{x}.png')
    elif mode == 'video':
        out = sys.argv[2]; mix = os.path.splitext(out)[0] + '_mix.wav'; build_audio(mix)
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-',
                               '-i', mix, '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', '-aspect', '9:16',
                               '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', '48000', '-ac', '2', '-c:a', 'aac', '-b:a', '256k',
                               '-movflags', '+faststart', '-shortest', out], stdin=subprocess.PIPE)
        from multiprocessing import Pool
        with Pool(os.cpu_count() or 4) as pool:
            for n, fr in pool.imap(render_frame, raw_frames(), chunksize=4):
                ff.stdin.write(fr)
                if n % 600 == 0: print(n, flush=True)
        ff.stdin.close(); ff.wait(); os.remove(mix); raise SystemExit(ff.returncode)


if __name__ == '__main__':
    main()
