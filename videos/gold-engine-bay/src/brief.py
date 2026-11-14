"""Gold engine bay - "mission brief" cut with the documentary voice.

Four visual layers under one brief layout (black, thin rules, data cards, yellow highlighter,
centred captions):  white wireframe (question) -> ASCII (V12) -> thermal (carbon + gold)
-> LiDAR (16 g) -> wireframe (your call). All times come from timing.json (aligned voice).

  python brief.py still OUTDIR T [T ...]
  python brief.py video OUT.mp4 VOICE.wav [START END]
"""
import math, subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

import combo
import pc
import render as R
import scene
import styles as ST
from render import B, DUR, FPS, W, H, WORDS, clamp, prog, io, oc, heat_i, foil_p

F32 = np.float32
INTER = "/usr/share/fonts/opentype/inter/Inter-"
JB = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-"
_F = {}
def sans(size, w="SemiBold"):
    k = ("s", size, w)
    if k not in _F: _F[k] = ImageFont.truetype(INTER + w + ".otf", int(size))
    return _F[k]
def mono(size, w="Medium"):
    k = ("m", size, w)
    if k not in _F: _F[k] = ImageFont.truetype(JB + w + ".ttf", int(size))
    return _F[k]

WHITE = (236, 236, 232); GREY = (138, 138, 136); DIM = (90, 90, 92); HL = (236, 212, 58); INK = (12, 12, 14)
X0, X1 = 64, R.SAFE_X1 - 10                     # text column
CAP_Y = 1060

def wstart(word, n=1):
    hits = [w for w in WORDS if w["w"].strip("?.,").lower() == word.lower()]
    return hits[n - 1]["s"]

# ---------- sections ----------
SECTIONS = [  # (visual, start, brief no., title)
    ("wire", 0.0, 1, "THE QUESTION"),
    ("ascii", B["reveal"] - 0.2, 2, "HEAT SOURCE"),
    ("thermal", wstart("and") - 0.2, 3, "THE PROBLEM"),
    ("lidar", B["lined"] - 0.1, 4, "THE FIX"),
    ("wire", B["question"] - 0.25, 5, "YOUR CALL"),
]
XF = 0.35                                          # crossfade


# ---------- white wireframe visual ----------
_PANEL = {}
def panel_grid():
    """Thin grid lines across the carbon panels (they turn gold as the foil wraps)."""
    if not _PANEL:
        A, Bv, wr = [], [], []
        for y in np.arange(0.1, 1.36, 0.1):
            A.append((-1.25, y, -0.58)); Bv.append((1.6, y, -0.58)); wr.append(0.30 + 0.70 * 0.0 + 0.05 * (y - 0.6))
            A.append((-0.76, y, -0.58)); Bv.append((-0.76, y, 0.02 if y < 1.1 else -0.58)); wr.append(0.0 + 0.05 * (y - 0.6))
        for x in np.arange(-1.2, 1.6, 0.1):
            A.append((x, 0.0, -0.58)); Bv.append((x, 1.36, -0.58))
            wr.append(float(scene.wrap_order(np.array([[x, 0.6, -0.58]]), np.array([False]))[0]))
        for z in np.arange(-0.55, 0.02, 0.1):
            A.append((-0.76, 0.0, z)); Bv.append((-0.76, 1.1, z))
            wr.append(float(scene.wrap_order(np.array([[-0.76, 0.6, z]]), np.array([True]))[0]))
        _PANEL.update(A=np.array(A, F32), B=np.array(Bv, F32), wrap=np.array(wr, F32))
    return _PANEL

def draw_segs(d, cam, A, Bv, cols, alphas, width):
    xa, ya, za = pc.proj(A, cam); xb, yb, zb = pc.proj(Bv, cam)
    for i in np.nonzero((za > 0.05) & (zb > 0.05))[0]:
        d.line((xa[i], ya[i], xb[i], yb[i]), fill=(*cols[i], int(255 * alphas[i])), width=width)

def wire_frame(t):
    cam = pc.camera(t)
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    for x in np.arange(-1.5, 1.81, 0.25):                                   # floor grid, very quiet
        ST.lines(d, cam, np.array([[x, 0, -0.58]], F32), np.array([[x, 0, 1.3]], F32), (70, 70, 74), 1, 0.6)
    for z_ in np.arange(-0.5, 1.31, 0.25):
        ST.lines(d, cam, np.array([[-1.6, 0, z_]], F32), np.array([[1.8, 0, z_]], F32), (70, 70, 74), 1, 0.6)
    pg = panel_grid(); fp = foil_p(t)
    gold = (fp - pg["wrap"]) > 0
    cols = np.where(gold[:, None], np.array([[226, 178, 60]]), np.array([[60, 60, 64]]))
    draw_segs(d, cam, pg["A"], pg["B"], cols, np.where(gold, 0.9, 0.7), 1)
    wv = ST.wire()
    mid = (wv["A"] + wv["B"]) / 2
    _, _, dz = pc.proj(mid, cam)
    alpha = np.clip(1.5 - dz / 4.2, 0.25, 1.0)
    cols = np.tile(np.array([[232, 232, 228]]), (len(dz), 1))
    hot = wv["mat"] == scene.HEADER
    cols[hot] = (255, 96, 60)
    cols[wv["mat"] == scene.CARBON] = (170, 170, 168)
    draw_segs(d, cam, wv["A"], wv["B"], cols, alpha, 2)
    for P_, u in ST.heat_paths(t, 500, lags=(0.0, 0.012, 0.024)):          # faint heat flow
        x, y, z_ = pc.proj(P_, cam); ok = z_ > 0.05
        for xi, yi, ui in zip(x[ok], y[ok], u[ok]):
            d.point((xi, yi), fill=(255, int(120 - 60 * ui), 70, int(150 * math.sin(math.pi * ui) * min(1.0, heat_i(t)))))
    base = Image.new("RGBA", (W, H), (6, 6, 7, 255))
    glow = lay.filter(ImageFilter.GaussianBlur(5))
    base.alpha_composite(glow); base.alpha_composite(lay)
    return base.convert("RGB")

GAIN = {"wire": 1.0, "ascii": 1.08, "thermal": 1.25, "lidar": 1.3}       # lift the murkier looks

def visual(name, t):
    im = _visual(name, t)
    if GAIN[name] == 1.0: return im
    a = np.asarray(im, F32) / 255
    a = 1 - (1 - np.clip(a * GAIN[name], 0, 1)) ** 1.08                    # brighten, soft shoulder
    return Image.fromarray(np.uint8(np.clip(a, 0, 1) * 255))

def _visual(name, t):
    if name == "wire": return wire_frame(t)
    if name == "ascii": return combo.ascii_frame(t, ())
    if name == "thermal": return combo.thermal_frame(t, labels=False)
    return pc.frame(t, text=False, tags=False)


# ---------- brief layout ----------
def text_w(f, s): return f.getlength(s)

def card(ov, x, y, rows, a, w=None):
    """rows: (kind, text[, extra]). kinds: title, meta, big, sub, hl, gap. Returns bottom y."""
    if a <= 0: return y
    spec = {"title": (sans(50), WHITE, 66), "meta": (mono(40), GREY, 54), "big": (mono(76, "SemiBold"), WHITE, 92),
            "sub": (sans(44, "Regular"), GREY, 58), "hl": (sans(44, "SemiBold"), INK, 62), "gap": (None, None, 18)}
    pad = 30
    h = pad * 2 + sum(spec[r[0]][2] for r in rows)
    if w is None:
        w = pad * 2 + max(text_w(spec[r[0]][0], r[1]) + (16 if r[0] == "hl" else 0) for r in rows if r[0] != "gap")
    assert x + w <= R.SAFE_X1 + 1 and y >= R.SAFE_Y0 and y + h <= R.SAFE_Y1, rows
    yo = 14 * (1 - oc(a))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(lay)
    d.rounded_rectangle((x, y + yo, x + w, y + h + yo), radius=12, fill=(14, 14, 16, 238), outline=(52, 52, 56, 255), width=2)
    cy = y + pad + yo
    for r in rows:
        kind, txt = r[0], r[1] if len(r) > 1 else ""
        f, col, lh = spec[kind]
        if kind == "hl":
            k = r[2] if len(r) > 2 else 1.0                                  # highlighter sweeps in
            tw = text_w(f, txt) + 16
            d.rectangle((x + pad - 4, cy + 4, x + pad - 4 + tw * k, cy + lh - 6), fill=(*HL, 255))
            if k > 0.05: d.text((x + pad + 4, cy + 6), txt, font=f, fill=(*INK, 255))
        elif f is not None:
            d.text((x + pad, cy), txt, font=f, fill=(*col, 255))
        cy += lh
    if a < 1: lay.putalpha(lay.getchannel("A").point(lambda v: int(v * a)))
    ov.alpha_composite(lay)
    return y + h

def cubes(ov, x, y, n, a):
    """Reference-style grid of small wireframe cubes (1 cube = 1 g)."""
    d = ImageDraw.Draw(ov)
    s, gap, dep = 36, 16, 11
    for i in range(16):
        if i >= n: break
        cx, cy = x + (i % 4) * (s + gap), y + (i // 4) * (s + gap)
        c = (*HL, int(255 * a)) if i == n - 1 and n < 16 else (226, 226, 222, int(255 * a))
        d.rectangle((cx, cy + dep, cx + s, cy + s + dep), outline=c, width=2)
        d.line((cx, cy + dep, cx + dep, cy, cx + s + dep, cy, cx + s, cy + dep), fill=c, width=2)
        d.line((cx + s + dep, cy, cx + s + dep, cy + s, cx + s, cy + s + dep), fill=c, width=2)

def captions(ov, t):
    """Centred sentence captions, split at punctuation, at most two lines."""
    segs, cur = [], []
    for w in WORDS:
        cur.append(w)
        if w["w"][-1] in ",.?": segs.append(cur); cur = []
    if cur: segs.append(cur)
    for i, sg in enumerate(segs):
        s0 = sg[0]["s"] - 0.12
        s1 = (segs[i + 1][0]["s"] - 0.12) if i + 1 < len(segs) else DUR
        s1 = min(s1, sg[-1]["e"] + 0.9)
        if not (s0 <= t < s1): continue
        a = min(prog(t, s0, 0.18), 1 - prog(t, s1 - 0.15, 0.15))
        f = sans(58, "Medium")
        words = [w["w"] for w in sg]; maxw = R.SAFE_X1 - 2 * X0
        if text_w(f, " ".join(words)) <= maxw:
            lines = [words]
        else:                                                         # two lines, balanced widths (no orphans)
            k = min(range(1, len(words)), key=lambda i: max(text_w(f, " ".join(words[:i])), text_w(f, " ".join(words[i:]))))
            lines = [words[:k], words[k:]]
        d = ImageDraw.Draw(ov)
        cx = (X0 + R.SAFE_X1 - X0) / 2 + 0
        for li, ln in enumerate(lines):
            txt = " ".join(ln)
            y = CAP_Y + li * 72 - (len(lines) - 1) * 36
            assert y >= R.SAFE_Y0 and y + 70 <= R.SAFE_Y1
            d.text((cx, y), txt, font=f, fill=(*WHITE, int(255 * a)), anchor="ma")

def brief(im, t, sec):
    ov = Image.new("RGBA", (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(ov)
    _, start, no, title = sec
    y = 290
    if no == 1:
        f = sans(92, "SemiBold")
        d.text((X0, y), "Why is there", font=f, fill=(*WHITE, 255))
        gw = text_w(f, "gold ")
        k = io(prog(t, wstart("gold") - 0.1, 0.35))                   # highlighter sweeps in on "gold"
        if k > 0: d.rectangle((X0 - 6, y + 112 + 8, X0 - 6 + (text_w(f, "gold") + 12) * k, y + 112 + 104), fill=(*HL, 255))
        d.text((X0, y + 112), "gold", font=f, fill=(*(INK if k > 0.5 else HL), 255))
        d.text((X0 + gw, y + 112), "in this engine?", font=f, fill=(*WHITE, 255))
        d.text((X0, y + 248), "McLaren F1 · engine bay", font=mono(40), fill=(*GREY, 255))
    elif no == 2:
        a = prog(t, B["v12"] - 0.2, 0.35)
        hl = io(prog(t, B["heat"] - 0.3, 0.4))
        rows = [("title", "Engine · BMW V12"), ("meta", "mid-mounted · behind the cabin"), ("gap",),
                ("big", "6.1 L"), ("sub", "about 618 hp")]
        if hl > 0: rows += [("gap",), ("hl", "huge heat", hl)]
        card(ov, X0, y, rows, a, w=640)
    elif no == 3:
        a = prog(t, B["carbon"] - 0.25, 0.35)
        hl = io(prog(t, B["protect"] - 0.1, 0.4))
        rows = [("title", "Body · carbon fibre"), ("meta", "monocoque and panels"), ("gap",),
                ("sub", "needs insulating from")]
        rows += [("hl", "engine heat", hl)] if hl > 0 else [("sub", "engine heat")]
        bot = card(ov, X0, y, rows, a, w=640)
        a2 = prog(t, B["gold"] - 0.2, 0.35)
        hl2 = io(prog(t, B["infrared"] - 0.05, 0.4))
        if a2 > 0:
            rows2 = [("title", "Gold"), ("sub", "reflects infrared well")] + ([("hl", "heat bounces back", hl2)] if hl2 > 0 else [])
            card(ov, X0 + 360, bot + 24, rows2, a2, w=480)
    elif no == 4:
        a = prog(t, B["lined"] - 0.05, 0.35)
        rows = [("title", "Lining · gold foil"), ("meta", "source · Robb Report, SlashGear"), ("gap",),
                ("big", "≈ 16 g" if t >= B["grams"] - 0.1 else "—"), ("sub", "1 cube = 1 g"), ("gap",), ("gap",)]
        bot = card(ov, X0, y, rows, a, w=R.SAFE_X1 - X0)
        n = int(clamp((t - B["grams"] + 0.1) / 0.07, 0, 16))
        if a > 0.5: cubes(ov, X0 + 520, y + 160, n, a)
    else:
        a = prog(t, B["question"] - 0.1, 0.35)
        f = sans(76, "SemiBold")
        lines = ["Would you line", "your car with gold?"]
        lay_y = y
        for ln in lines:
            d.text((X0, lay_y), ln, font=f, fill=(*WHITE, int(255 * a))); lay_y += 96
        for j, (lab, x0) in enumerate((("Yes", X0), ("No", X0 + 420))):
            wi = [i for i, w in enumerate(WORDS) if w["w"].strip("?").lower() == lab.lower()][-1]
            nxt = WORDS[wi + 2]["s"] - 0.05 if wi + 2 < len(WORDS) else DUR       # "Yes" holds until "no"
            on = WORDS[wi]["s"] - 0.05 <= t < nxt
            kb = prog(t, B["question"] + 0.3 + 0.12 * j, 0.3)
            yb = lay_y + 40
            if on: d.rectangle((x0, yb, x0 + 380, yb + 130), fill=(*HL, int(255 * kb)))
            for k_ in range(0, 380, 14):                                    # dashed outline like the reference
                d.line((x0 + k_, yb, x0 + min(380, k_ + 8), yb), fill=(200, 200, 196, int(255 * kb)), width=2)
                d.line((x0 + k_, yb + 130, x0 + min(380, k_ + 8), yb + 130), fill=(200, 200, 196, int(255 * kb)), width=2)
            for k_ in range(0, 130, 14):
                d.line((x0, yb + k_, x0, yb + min(130, k_ + 8)), fill=(200, 200, 196, int(255 * kb)), width=2)
                d.line((x0 + 380, yb + k_, x0 + 380, yb + min(130, k_ + 8)), fill=(200, 200, 196, int(255 * kb)), width=2)
            d.text((x0 + 190, yb + 65), lab, font=sans(64, "SemiBold"), fill=((*INK, 255) if on else (*WHITE, int(255 * kb))), anchor="mm")
            assert x0 + 380 <= R.SAFE_X1 and yb + 130 <= R.SAFE_Y1
    captions(ov, t)
    d.text((40, 52), "Yub", font=sans(30, "ExtraBold"), fill=(*WHITE, 210))
    if R.PREVIEW:
        tf = mono(22, "Bold"); pw = text_w(tf, "PREVIEW")
        d.rectangle((W - 60 - pw - 16, 92, W - 60, 124), outline=(220, 80, 60, 220), width=2)
        d.text((W - 68, 108), "PREVIEW", font=tf, fill=(220, 80, 60, 220), anchor="rm")
    base = im.convert("RGBA")
    # darken behind the text column so cards and captions sit on near-black, like the reference
    sc = np.zeros((H, 1), F32)
    yy = np.arange(H)
    sc[:, 0] = 0.55 * np.clip(1 - np.abs(yy - 520) / 360, 0, 1) ** 0.6 + 0.6 * np.exp(-((yy - CAP_Y - 30) / 110) ** 2)
    arr = np.asarray(base, F32); arr[..., :3] *= (1 - np.clip(sc, 0, 0.8))[..., None]
    base = Image.fromarray(np.uint8(arr))
    base.alpha_composite(ov)
    return base.convert("RGB")


def frame(t):
    t = clamp(t, 0, DUR - 1e-6)
    i = max(j for j, s in enumerate(SECTIONS) if t >= s[1])
    sec = SECTIONS[i]
    im = visual(sec[0], t)
    k = prog(t, sec[1], XF) if i > 0 else 1.0
    if k < 1:
        prev = visual(SECTIONS[i - 1][0], t)
        im = Image.blend(prev, im, io(k))
    a = np.asarray(im, F32) * 0.92                                           # slightly muted under the brief
    return brief(Image.fromarray(np.uint8(a)), t, sec)


# ---------- audio: voice + quiet bed ----------
def mix(voice, out, sfx=False):
    """Voice + sound design (engine bed, cues), SFX ducked under the voice. Also writes stems next to `out`."""
    import sound, wave
    sr = sound.SR
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(voice), "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"],
                         capture_output=True, check=True).stdout
    v = np.frombuffer(raw, np.int16).astype(F32) / 32768
    n = int(DUR * sr); v = np.pad(v, (0, max(0, n - len(v))))[:n]
    cards = [B["v12"] - 0.2, B["carbon"] - 0.25, B["gold"] - 0.2, B["lined"] - 0.05, B["question"] - 0.1]
    highlights = [wstart("gold") - 0.1, B["heat"] - 0.3, B["protect"] - 0.1, B["infrared"] - 0.05]
    fx = sound.sfx_track([(s[0], s[1]) for s in SECTIONS], cards, highlights, B["grams"] - 0.03) if sfx else np.zeros(n, F32)
    env = np.convolve(np.abs(v), np.ones(2400) / 2400, mode="same")
    duck = 1 - np.clip(env * 9, 0, 0.6)                                       # up to ~8 dB under speech
    fx = fx * np.convolve(duck, np.ones(4800) / 4800, mode="same")
    x = v + fx
    x = x / max(1.0, np.abs(x).max() / 0.95)
    def write(path, sig):
        with wave.open(str(path), "wb") as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(sr); f.writeframes((np.clip(sig, -1, 1) * 32767).astype("<i2").tobytes())
    write(out, x)
    stem = Path(out).with_suffix("")
    write(str(stem) + "_voice.wav", v); write(str(stem) + "_sfx.wav", fx)


def _job(i): return np.asarray(frame(i / FPS)).tobytes()

def video(out, voice, a=0.0, b=None, sfx=False):
    from multiprocessing import Pool
    pc.data(); combo.ascii_setup(); R.layers(); ST.wire(); panel_grid()
    b = DUR if b is None else b
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True); wav = out.parent / (out.stem + "_mix.wav")
    mix(voice, wav, sfx)
    n0, n1 = int(round(a * FPS)), int(round(b * FPS))
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-ss", str(a), "-t", str((n1 - n0) / FPS), "-i", str(wav), "-c:v", "libx264", "-preset", "medium",
           "-crf", "17", "-maxrate", "20M", "-bufsize", "40M", "-profile:v", "high", "-level", "4.2", "-g", "60",
           "-pix_fmt", "yuv420p", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709",
           "-af", "loudnorm=I=-14:TP=-1:LRA=7", "-c:a", "aac", "-b:a", "256k", "-ar", "48000", "-ac", "2",
           "-shortest", "-movflags", "+faststart", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for k, buf in enumerate(pool.imap(_job, range(n0, n1), chunksize=2)):
            p.stdin.write(buf)
            if k % 90 == 0: print(f"frame {n0 + k}/{n1}", flush=True)
    p.stdin.close()
    assert p.wait() == 0
    print(f"wrote {out} (+ {wav.name}, _voice / _sfx stems)")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "still":
        od = Path(sys.argv[2]); od.mkdir(parents=True, exist_ok=True)
        for s_ in sys.argv[3:]:
            frame(float(s_)).save(od / f"f_{s_}.png")
    elif cmd == "video":
        video(sys.argv[2], sys.argv[3], *(float(v) for v in sys.argv[4:6]))
