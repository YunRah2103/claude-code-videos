"""Runner for the cinematic Yub shorts: renders shots with render3d, draws the hook title and reference-style captions
(one bold white word at a time, large, centred, fixed position), checks every frame for clipped/overlapping text,
and mixes voice + upbeat jazz bed (Hot Swing) + rock backbeat + SFX.
Layout (1080x1920): TOP zone y 120-600 for the hook / short labels; CAPTION centred at y 1250 (one word, <= 960 px wide).
Module API: NAME, HOOK, SHOTS [(t, fn(u, t, dt) -> dict(scene, cam, env, glow, sprites, center)), what)], TOPS, SFX, ONSCREEN, ODDITY.
python <video>.py sheet out.png [t...] | still T out.png | meta out.json | check | video voice.wav music.wav out.mp4 [t0 t1]"""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from render3d import render, Env
OW, OH = 1080, 1920
import sfx

FPS = 30
FONT_B = "/usr/share/fonts/opentype/inter/Inter-Black.otf"; FONT_X = "/usr/share/fonts/opentype/inter/Inter-ExtraBold.otf"
def F(size, f=FONT_X): return ImageFont.truetype(f, size)
CAP_Y, CAP_SIZE, CAP_MAXW = 1250, 132, 960
TOP_Y0, TOP_MAXW = 130, 980
SAFE = 40
MUSIC_OFFSET = 11.5
BPM, BEAT0 = 144.0, 0.0225

def ease(u): return u * u * (3 - 2 * u)
def lerp(a, b, u): return tuple(x + (y - x) * u for x, y in zip(a, b))
def shake(t, amt, f=23.0): return (amt * math.sin(t * f * 6.1), amt * math.sin(t * f * 4.3 + 1), amt * math.sin(t * f * 5.2 + 2))

def fit_lines(text, size, maxw, maxlines=3, minsize=50, font=FONT_B):
    while size >= minsize:
        f = F(size, font); words = text.split(); lines = [words[0]]
        for w in words[1:]:
            if f.getlength(lines[-1] + " " + w) <= maxw: lines[-1] += " " + w
            else: lines.append(w)
        if len(lines) <= maxlines and all(f.getlength(l) <= maxw for l in lines): return f, lines
        size -= 4
    return F(minsize, font), [text]

def _shadow_text(im, xy, text, f, fill, anchor, blur=10, off=(0, 6), stroke=0):
    """White text with a soft dark drop shadow (reference style)."""
    sh = Image.new("L", im.size, 0); ImageDraw.Draw(sh).text((xy[0] + off[0], xy[1] + off[1]), text, font=f, fill=200, anchor=anchor, stroke_width=stroke + 4)
    sh = sh.filter(ImageFilter.GaussianBlur(blur))
    im.paste(Image.new("RGB", im.size, (8, 8, 14)), (0, 0), sh)
    d = ImageDraw.Draw(im)
    d.text(xy, text, font=f, fill=fill, anchor=anchor, stroke_width=stroke, stroke_fill=(20, 20, 28))
    return d.textbbox(xy, text, font=f, anchor=anchor, stroke_width=stroke)

class Video:
    def __init__(s, mod):
        s.m = mod
        here = os.path.dirname(os.path.abspath(mod.__file__))       # words.json lives next to the video module
        s.words = json.load(open(os.path.join(here, f"{mod.NAME}_words.json")))
        s.dur = round(min(getattr(mod, "MAXDUR", 35.0), s.words[-1]["e"] + 0.8), 2)
        s.hook_end = max(o["e"] for o in s.words if o["line"] == 0) + 0.3

    def ws(s, line, i=0): return [o for o in s.words if o["line"] == line][i]["s"]
    def we(s, line, i=-1): return [o for o in s.words if o["line"] == line][i]["e"]

    def shot_at(s, t):
        S = s.m.SHOTS
        i = max(k for k, x in enumerate(S) if x[0] <= t)
        t0 = S[i][0]; t1 = S[i + 1][0] if i + 1 < len(S) else s.dur
        return i, min(1.0, (t - t0) / (t1 - t0)), t - t0

    def render_t(s, t):
        i, u, dt = s.shot_at(t)
        d = s.m.SHOTS[i][1](u, t, dt)
        return render(d["scene"], d["cam"], d.get("env") or s.m.ENV, glow=d.get("glow", ()), sprites=d.get("sprites", ()),
                      shadow_center=d.get("center"))

    def word_at(s, t):
        if t < s.hook_end: return None
        W = s.words
        for k, o in enumerate(W):
            if o["line"] == 0: continue
            nxt = W[k + 1]["s"] if k + 1 < len(W) else s.dur
            if o["s"] - 0.02 <= t < max(min(nxt, o["e"] + 0.45), o["s"] + 0.18): return k
        return None

    def draw_title(s, im, text, small=False):
        f, lines = fit_lines(text, 96 if small else 118, TOP_MAXW - 60, 3)
        lh = int(f.size * 1.1); y0 = TOP_Y0 + (30 if small else 0); boxes = []
        for i, l in enumerate(lines):
            boxes.append(_shadow_text(im, (OW // 2, y0 + lh * (i + 0.5)), l, f, (255, 255, 255), "mm", 12, (0, 7), 3))
        # accent underline
        bx0 = min(b[0] for b in boxes); bx1 = max(b[2] for b in boxes); by = max(b[3] for b in boxes) + 14
        ImageDraw.Draw(im).rounded_rectangle(((OW - 160) // 2, by, (OW + 160) // 2, by + 12), 6, fill=s.m.ACCENT)
        return (bx0, min(b[1] for b in boxes), bx1, by + 12)

    def draw_word(s, im, k, t):
        o = s.words[k]; text = o["w"].strip(",.:;").replace("...", "")
        if not text: text = o["w"]
        size = CAP_SIZE
        while F(size).getlength(text) * 1.06 > CAP_MAXW and size > 60: size -= 4      # room for the pop-in scale
        pop = max(0.0, 1 - (t - o["s"]) / 0.09)
        f = F(int(size * (1 + 0.06 * pop)))
        hot = text.strip("?!").lower() in s.m.HOT
        return _shadow_text(im, (OW // 2, CAP_Y), text, f, (255, 226, 70) if hot else (255, 255, 255), "mm", 9, (0, 6), 3)

    def overlays(s, t):
        out = []
        if t < s.hook_end: out.append(("title", s.m.HOOK))
        else:
            for a, b, txt in s.m.TOPS:
                if a <= t < b: out.append(("label", txt)); break
            k = s.word_at(t)
            if k is not None: out.append(("word", k))
        return out

    def paint(s, im, t):
        boxes = []
        for kind, p in s.overlays(t):
            if kind == "title": boxes.append(s.draw_title(im, p))
            elif kind == "label": boxes.append(s.draw_title(im, p, small=True))
            else: boxes.append(s.draw_word(im, p, t))
        return boxes

    def frame(s, n):
        t = n / FPS
        im = Image.fromarray(s.render_t(t)).resize((OW, OH), Image.LANCZOS)
        s.paint(im, t)
        return np.asarray(im)

    def check_text(s):
        bad = []; probe = Image.new("RGB", (OW, OH))
        for n in range(int(s.dur * FPS)):
            t = n / FPS; boxes = s.paint(probe, t)
            for b in boxes:
                if b[0] < SAFE or b[2] > OW - SAFE or b[1] < 60 or b[3] > OH - 320: bad.append((round(t, 2), "clip", b))
            for i in range(len(boxes)):
                for j in range(i + 1, len(boxes)):
                    a, b = boxes[i], boxes[j]
                    if not (a[3] < b[1] or b[3] < a[1] or a[2] < b[0] or b[2] < a[0]): bad.append((round(t, 2), "overlap"))
        return bad

    def sheet(s, path, times=None):
        times = times or [x[0] + 0.3 for x in s.m.SHOTS]
        th = [Image.fromarray(s.frame(int(t * FPS))).resize((270, 480)) for t in times]
        cols = 8; rows = (len(th) + cols - 1) // cols
        sh = Image.new("RGB", (cols * 270, rows * 480))
        for i, im in enumerate(th):
            sh.paste(im, ((i % cols) * 270, (i // cols) * 480))
            ImageDraw.Draw(sh).text(((i % cols) * 270 + 6, (i // cols) * 480 + 4), f"{i} {times[i]:.1f}", fill=(255, 0, 255))
        sh.save(path)

    def meta(s, path):
        json.dump(dict(size=[OW, OH], fps=FPS, duration=s.dur, hook=s.m.HOOK, hook_until=round(s.hook_end, 2), first_word=s.words[0]["s"],
                       tops=s.m.TOPS, text_problems=s.check_text(), onscreen=s.m.ONSCREEN, oddity=s.m.ODDITY,
                       shots=[dict(t=round(x[0], 2), what=x[2]) for x in s.m.SHOTS]), open(path, "w"), indent=1)

    def drums(s, n, sr):
        """Rock backbeat on the music's own grid: kick on 1 and 3 (+ the 'and' of 3), snare on 2 and 4, crash on the hook."""
        y = np.zeros(n + sr); P = 60 / BPM; k0 = math.ceil((MUSIC_OFFSET - BEAT0) / P)
        K, S, C = sfx.kick(), sfx.snare(), sfx.cymbal()
        def put(x, t, g):
            i = int(t * sr)
            if 0 <= i < n: y[i:i + len(x)] += g * x[:len(y) - i]
        k = k0
        while True:
            t = BEAT0 + k * P - MUSIC_OFFSET
            if t > s.dur: break
            if k % 2 == 0: put(K, t, 0.9)
            else: put(S, t, 0.55)
            if k % 4 == 2: put(K, t + P / 2, 0.6)
            k += 1
        put(C, 0.0, 0.5)
        for t in getattr(s.m, "CRASH", []): put(C, t, 0.45)
        return y[:n]

    def mix(s, voice, music, out, t0=0.0):
        sr = sfx.SR; n = int(s.dur * sr)
        def load(p, ch):
            tmp = out + ".tmp.raw"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", p, "-ar", str(sr), "-ac", str(ch), "-f", "f32le", tmp], check=True)
            a = np.fromfile(tmp, np.float32); os.remove(tmp); return a.reshape(-1, ch)
        v = load(voice, 1)[:, 0]; v = np.pad(v, (0, max(0, n - len(v))))[:n]
        mu = load(music, 2)[int(MUSIC_OFFSET * sr):][:n].astype(np.float64)
        dr = s.drums(n, sr)[:, None] * 0.32
        mu = mu + dr
        # carve 1.2-4 kHz out of the music by ~5 dB so the voice sits on top without burying the band
        for c in range(2):
            X = np.fft.rfft(mu[:, c]); f = np.fft.rfftfreq(n, 1 / sr)
            X *= 1 - 0.45 * np.exp(-((np.log(f + 1) - np.log(2200)) / 0.55) ** 2); mu[:, c] = np.fft.irfft(X, n)
        talk_rms = np.sqrt(np.mean(v[np.abs(v) > 0.02 * np.abs(v).max()] ** 2))
        mus_rms = np.sqrt(np.mean(mu ** 2))
        g = talk_rms / mus_rms * 10 ** (-s.m.__dict__.get("MUSIC_UNDER_DB", 6.0) / 20)
        env = np.convolve(np.abs(v), np.ones(int(0.05 * sr)) / int(0.05 * sr), "same")
        talk = np.clip(env / (0.25 * env.max() + 1e-9), 0, 1)
        talk = np.convolve(talk, np.ones(int(0.25 * sr)) / int(0.25 * sr), "same")
        mg = g * (1 - 0.18 * talk)                                  # light ducking (~1.7 dB) while the narrator talks
        fo = np.clip((s.dur - np.arange(n) / sr) / 0.5, 0, 1)
        mu = mu * (mg * fo)[:, None]
        fx = sfx.render(s.m.SFX, s.dur) * 0.55
        y = mu + (v + fx)[:, None]
        y = y[int(t0 * sr):]
        y = np.tanh(y / 0.9) * 0.9                                   # soft limiter
        s.levels = dict(music_under_voice_db=round(20 * math.log10(talk_rms / (mus_rms * g)), 1))
        with wave.open(out, "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes((np.clip(y, -1, 1) * 32767).astype(np.int16).tobytes())

    def video(s, voice, music, out, t0=0.0, t1=None):
        from multiprocessing import Pool
        t1 = s.dur if t1 is None else t1
        mixwav = out + ".mix.wav"; s.mix(voice, music, mixwav, t0); print("levels", s.levels, flush=True)
        n0, n1 = int(t0 * FPS), int(t1 * FPS)
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-",
               "-i", mixwav, "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-maxrate", "2.3M", "-bufsize", "4.6M", "-pix_fmt", "yuv420p",
               "-af", f"loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=out:st={max(0, t1 - t0 - 0.3):.2f}:d=0.25", "-ar", "48000", "-c:a", "aac", "-b:a", "160k",
               "-movflags", "+faststart", "-t", f"{t1 - t0:.3f}", out]
        ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        with Pool(os.cpu_count(), initializer=_init, initargs=(s.m.NAME,)) as pool:
            for k, fr in enumerate(pool.imap(_frame, range(n0, n1), chunksize=2)):
                ff.stdin.write(fr.tobytes())
                if k % 60 == 0: print("frame", n0 + k, flush=True)
        ff.stdin.close(); ff.wait(); os.remove(mixwav)
        if ff.returncode: sys.exit("ffmpeg failed")
        print("ok", out)

_V = None
def _init(name):
    global _V
    import importlib; _V = importlib.import_module(name).V
def _frame(n): return _V.frame(n)

def main(V):
    cmd = sys.argv[1]
    if cmd == "still": Image.fromarray(V.frame(int(float(sys.argv[2]) * FPS))).save(sys.argv[3])
    elif cmd == "sheet": V.sheet(sys.argv[2], [float(x) for x in sys.argv[3:]] or None)
    elif cmd == "meta": V.meta(sys.argv[2])
    elif cmd == "check": print(V.check_text() or "text ok")
    elif cmd == "video": V.video(sys.argv[2], sys.argv[3], sys.argv[4], *[float(x) for x in sys.argv[5:7]])
