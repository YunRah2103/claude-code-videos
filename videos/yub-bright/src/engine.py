"""Shared runner for the bright Yub low-poly shorts.
Screen layout (1080x1920), fixed so text never collides:
  TOP zone    y 120-560  : the hook title (frame 0 until the hook line is spoken) and, later, short labels (TOPS).
  CAPTION band y 1310-1470: 1-3 word caption chunks, active word in yellow, auto-shrunk to fit 940 px. Never moves.
  The 3D shots keep in-world text out of the caption band (checked on the contact sheet).
Each video module defines: NAME, HOOK, SHOTS [(t, fn(u, t, dt) -> dict, what)], HOT, SFX [(t, name, vol)], TOPS
[(t0, t1, text)], ONSCREEN, ODDITY.
python <video>.py sheet out.png | still T out.png | meta out.json | video voice.wav music.wav out.mp4 [t0 t1]"""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from lowpoly import render, finish, Cam, sky
import sfx

FPS, OW, OH = 30, 1080, 1920
FONT = "/usr/share/fonts/opentype/inter/Inter-Black.otf"
def F(size): return ImageFont.truetype(FONT, size)
CAP_Y, CAP_SIZE, CAP_MAXW, CAP_STROKE = 1390, 104, 940, 10
TOP_Y0, TOP_Y1, TOP_MAXW = 130, 560, 960
SAFE_X = 50
MUSIC_OFFSET = 11.5            # Hot Swing: start where the full band is playing
BPM, BEAT0 = 144.0, 0.0225     # measured from the track (onset grid), snare on beats 2 and 4

SKY_BG = sky((70, 150, 245), (196, 228, 255))
DEF_FOG = (30, 70, (196, 228, 255))
SUN = (-0.35, 0.85, 0.55)

def ease(u): return u * u * (3 - 2 * u)
def lerp(a, b, u): return tuple(x + (y - x) * u for x, y in zip(a, b))
def shake(t, amt, f=23.0): return (amt * math.sin(t * f * 6.1), amt * math.sin(t * f * 4.3 + 1), amt * math.sin(t * f * 5.2 + 2))

def fit_lines(text, size, maxw, maxlines=3, minsize=48):
    """Greedy word-wrap; shrink the font until it fits maxw in <= maxlines lines."""
    while size >= minsize:
        f = F(size); words = text.split(); lines = [words[0]]
        for w in words[1:]:
            if f.getlength(lines[-1] + " " + w) <= maxw: lines[-1] += " " + w
            else: lines.append(w)
        if len(lines) <= maxlines and all(f.getlength(l) <= maxw for l in lines): return f, lines
        size -= 4
    return F(minsize), [text]

class Video:
    def __init__(s, mod):
        s.m = mod
        here = os.path.dirname(os.path.abspath(__file__))
        s.words = json.load(open(os.path.join(here, f"{mod.NAME}_words.json")))
        s.dur = round(min(25.0, s.words[-1]["e"] + 0.7), 2)
        s.hook_end = max(o["e"] for o in s.words if o["line"] == 0) + 0.35
        s.chunks = s._chunks()

    def ws(s, line, i=0): return [o for o in s.words if o["line"] == line][i]["s"]
    def we(s, line, i=-1): return [o for o in s.words if o["line"] == line][i]["e"]

    def _chunks(s):
        """1-3 word caption chunks inside a line, breaking after punctuation. Hook line excluded (it is the title)."""
        out = []
        for li in sorted({o["line"] for o in s.words}):
            if li == 0: continue
            ws = [k for k, o in enumerate(s.words) if o["line"] == li]; cur = []
            for k in ws:
                cur.append(k)
                if len(cur) == 3 or s.words[k]["w"][-1] in ",.?!:" or k == ws[-1]: out.append(cur); cur = []
        res = []
        for i, c in enumerate(out):
            t0 = s.words[c[0]]["s"]; t1 = out[i + 1] and s.words[out[i + 1][0]]["s"] if i + 1 < len(out) else s.dur
            t1 = min(t1, s.words[c[-1]]["e"] + 0.6)
            res.append((max(t0, s.hook_end), t1, c))
        return res

    def shot_at(s, t):
        S = s.m.SHOTS
        i = max(k for k, x in enumerate(S) if x[0] <= t)
        t0 = S[i][0]; t1 = S[i + 1][0] if i + 1 < len(S) else s.dur
        return i, min(1.0, (t - t0) / (t1 - t0)), t - t0

    def lowres(s, t):
        i, u, dt = s.shot_at(t)
        d = s.m.SHOTS[i][1](u, t, dt)
        if i and dt < 0.15: d["cam"].fov *= 1 + 0.18 * (1 - dt / 0.15) ** 2      # zoom punch on every cut
        return render(d["scene"], d["cam"], d.get("bg", SKY_BG), fog=d.get("fog", DEF_FOG), amb=d.get("amb", 0.62), dif=d.get("dif", 0.55),
                      light=d.get("light", SUN), points=d.get("points", ()))

    # ------------------------------------------------------------------ 2D text layers
    def draw_title(s, im, text, t, y0=TOP_Y0):
        """Hook / label: black text on a yellow card with a thick dark border, centred in the TOP zone."""
        d = ImageDraw.Draw(im)
        f, lines = fit_lines(text, 112, TOP_MAXW - 80, 3)
        lh = int(f.size * 1.08); h = lh * len(lines) + 60; w = max(f.getlength(l) for l in lines) + 80
        x0 = (OW - w) / 2; box = (x0, y0, x0 + w, y0 + h)
        d.rounded_rectangle((box[0] + 10, box[1] + 12, box[2] + 10, box[3] + 12), 28, fill=(20, 20, 30))
        d.rounded_rectangle(box, 28, fill=(255, 214, 40), outline=(20, 20, 30), width=8)
        for i, l in enumerate(lines):
            d.text((OW / 2, y0 + 30 + lh * (i + 0.5)), l, font=f, fill=(20, 20, 30), anchor="mm")
        return tuple(int(v) for v in (box[0], box[1], box[2] + 10, box[3] + 12))

    def draw_caption(s, im, chunk, t):
        d = ImageDraw.Draw(im); ws = [s.words[k] for k in chunk]
        text = " ".join(o["w"] for o in ws); size = CAP_SIZE
        while F(size).getlength(text) + 2 * CAP_STROKE > CAP_MAXW and size > 56: size -= 4
        f = F(size); x = (OW - f.getlength(text)) / 2
        bb = d.textbbox((x, CAP_Y), text, font=f, anchor="lm", stroke_width=CAP_STROKE)
        for o in ws:
            on = o["s"] <= t + 0.02
            col = (255, 214, 40) if on and o["w"].strip(".,?!:").lower() in s.m.HOT else (255, 255, 255) if on else (235, 235, 240)
            d.text((x, CAP_Y), o["w"], font=f, fill=col, anchor="lm", stroke_width=CAP_STROKE, stroke_fill=(16, 16, 24))
            x += f.getlength(o["w"] + " ")
        return bb

    def overlays(s, t):
        """[(kind, payload)] active at t."""
        out = []
        if t < s.hook_end: out.append(("title", s.m.HOOK.upper()))
        else:
            for a, b, txt in s.m.TOPS:
                if a <= t < b: out.append(("title", txt)); break
            for a, b, c in s.chunks:
                if a <= t < b: out.append(("cap", c)); break
        return out

    def frame(s, n):
        t = n / FPS
        im = Image.fromarray(finish(s.lowres(t), seed=n % 7))
        for kind, p in s.overlays(t):
            if kind == "title": s.draw_title(im, p, t)
            else: s.draw_caption(im, p, t)
        return np.asarray(im)

    def check_text(s):
        """Every text box must sit inside the frame margins and the TOP / caption zones must never intersect."""
        bad = []; probe = Image.new("RGB", (OW, OH))
        for n in range(int(s.dur * FPS)):
            t = n / FPS; boxes = []
            for kind, p in s.overlays(t):
                boxes.append(s.draw_title(probe, p, t) if kind == "title" else s.draw_caption(probe, p, t))
            for b in boxes:
                if b[0] < SAFE_X - 15 or b[2] > OW - SAFE_X + 15 or b[1] < 60 or b[3] > OH - 300: bad.append((round(t, 2), "clip", b))
            if len(boxes) == 2 and not (boxes[0][3] < boxes[1][1] or boxes[1][3] < boxes[0][1]): bad.append((round(t, 2), "overlap", boxes))
        return bad

    def sheet(s, path, times=None):
        times = times or [x[0] + 0.25 for x in s.m.SHOTS]
        th = [Image.fromarray(s.frame(int(t * FPS))).resize((270, 480)) for t in times]
        cols = 8; rows = (len(th) + cols - 1) // cols
        sh = Image.new("RGB", (cols * 270, rows * 480))
        for i, im in enumerate(th):
            sh.paste(im, ((i % cols) * 270, (i // cols) * 480))
            ImageDraw.Draw(sh).text(((i % cols) * 270 + 6, (i // cols) * 480 + 4), f"{i} {times[i]:.1f}", fill=(255, 0, 255))
        sh.save(path)

    def meta(s, path):
        probe = Image.new("RGB", (OW, OH))
        caps = [dict(text=" ".join(s.words[k]["w"] for k in c), t0=round(a, 2), t1=round(b, 2), box=s.draw_caption(probe, c, b)) for a, b, c in s.chunks]
        json.dump(dict(size=[OW, OH], fps=FPS, duration=s.dur, hook=s.m.HOOK, hook_until=round(s.hook_end, 2), first_word=s.words[0]["s"],
                       tops=s.m.TOPS, captions=caps, text_problems=s.check_text(), onscreen=s.m.ONSCREEN, oddity=s.m.ODDITY,
                       shots=[dict(t=round(x[0], 2), what=x[2]) for x in s.m.SHOTS]), open(path, "w"), indent=1)

    # ------------------------------------------------------------------ audio
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
        mixwav = out + ".mix.wav"; s.mix(voice, music, mixwav, t0); print("levels", s.levels)
        n0, n1 = int(t0 * FPS), int(t1 * FPS)
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-",
               "-i", mixwav, "-c:v", "libx264", "-preset", "slow", "-crf", "20", "-maxrate", "2.9M", "-bufsize", "5.8M", "-pix_fmt", "yuv420p",
               "-af", f"loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=out:st={max(0, t1 - t0 - 0.3):.2f}:d=0.25", "-ar", "48000", "-c:a", "aac", "-b:a", "160k",
               "-movflags", "+faststart", "-t", f"{t1 - t0:.3f}", out]
        ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        with Pool(os.cpu_count(), initializer=_init, initargs=(s.m.NAME,)) as pool:
            for k, fr in enumerate(pool.imap(_frame, range(n0, n1), chunksize=4)):
                ff.stdin.write(fr.tobytes())
                if k % 150 == 0: print("frame", n0 + k, flush=True)
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
