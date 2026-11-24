"""Shared runner for the Yub low-poly shorts: frames, small word-by-word captions (none before 3 s), contact sheet, meta,
and the final mix (voice + quiet jazz bed + synthesised SFX).
Each video module defines: NAME, SHOTS [(t, fn(u, t, dt) -> dict, what)], HOT words, SFX cues [(t, name, vol)], ONSCREEN, ODDITY.
python <video>.py sheet out.png | still T out.png | meta out.json | video voice.wav music.wav out.mp4 [t0 t1]"""
import json, math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from lowpoly import render, finish, Cam, sky
import sfx

FPS, OW, OH = 30, 1080, 1920
CAP_FONT = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 66)
CAP_Y = int(0.555 * OH)
NO_OVERLAY_UNTIL = 3.0
MUSIC_GAIN_DB = -1.0           # music bed: loud, a few dB under the speech after loudnorm
MUSIC_OFFSET = 9.0             # start into "Hep Cats" where the full band is playing

DEF_BG = sky((10, 10, 14), (26, 24, 30))
DEF_FOG = (11, 30, (16, 14, 18))
DEF_POINTS = [((x, 4.6, z), (255, 236, 214), 8.0) for x in (-3.5, 3.5) for z in (-1.5, 2.5)]

def ease(u): return u * u * (3 - 2 * u)
def lerp(a, b, u): return tuple(x + (y - x) * u for x, y in zip(a, b))
def shake(t, amt, f=23.0): return (amt * math.sin(t * f * 6.1), amt * math.sin(t * f * 4.3 + 1), amt * math.sin(t * f * 5.2 + 2))

class Video:
    def __init__(s, mod):
        s.m = mod
        here = os.path.dirname(os.path.abspath(__file__))
        s.words = json.load(open(os.path.join(here, f"{mod.NAME}_words.json")))
        s.dur = round(min(25.0, s.words[-1]["e"] + 0.75), 2)

    def ws(s, line, i=0): return [o for o in s.words if o["line"] == line][i]["s"]

    def shot_at(s, t):
        S = s.m.SHOTS
        i = max(k for k, x in enumerate(S) if x[0] <= t)
        t0 = S[i][0]; t1 = S[i + 1][0] if i + 1 < len(S) else s.dur
        return i, min(1.0, (t - t0) / (t1 - t0)), t - t0

    def lowres(s, t):
        i, u, dt = s.shot_at(t)
        d = s.m.SHOTS[i][1](u, t, dt)
        if i and dt < 0.18: d["cam"].fov *= 1 + 0.22 * (1 - dt / 0.18) ** 2      # zoom punch on every cut
        return render(d["scene"], d["cam"], d.get("bg", DEF_BG), fog=d.get("fog", DEF_FOG), amb=d.get("amb", 0.34), dif=d.get("dif", 0.6),
                      light=d.get("light", (-0.4, 0.8, 0.45)), points=d.get("points", DEF_POINTS))

    def caption_at(s, t):
        if t < NO_OVERLAY_UNTIL: return None, None
        W = s.words
        for k, o in enumerate(W):
            nxt = W[k + 1]["s"] if k + 1 < len(W) else s.dur
            if max(o["s"], NO_OVERLAY_UNTIL) <= t < min(nxt, o["e"] + 0.35): return k, o["w"]
        return None, None

    def draw_caption(s, im, word, pop=0.0):
        d = ImageDraw.Draw(im)
        col = (255, 214, 40) if word.strip(".,?!:").lower() in s.m.HOT else (255, 255, 255)
        y = CAP_Y - int(10 * pop)
        d.text((OW // 2, y), word, font=CAP_FONT, fill=col, anchor="mm", stroke_width=5, stroke_fill=(0, 0, 0))
        return d.textbbox((OW // 2, y), word, font=CAP_FONT, anchor="mm", stroke_width=5)

    def frame(s, n):
        t = n / FPS
        im = Image.fromarray(finish(s.lowres(t), seed=n % 7))
        k, w = s.caption_at(t)
        if w: im = im.copy(); s.draw_caption(im, w, max(0, 1 - (t - max(NO_OVERLAY_UNTIL, s.words[k]["s"])) / 0.08))
        return np.asarray(im)

    def sheet(s, path, times=None):
        times = times or [x[0] + 0.3 for x in s.m.SHOTS]
        th = [Image.fromarray(s.frame(int(t * FPS))).resize((216, 384)) for t in times]
        cols = 8; rows = (len(th) + cols - 1) // cols
        sh = Image.new("RGB", (cols * 216, rows * 384))
        for i, im in enumerate(th):
            sh.paste(im, ((i % cols) * 216, (i // cols) * 384))
            ImageDraw.Draw(sh).text(((i % cols) * 216 + 6, (i // cols) * 384 + 4), f"{i} {times[i]:.1f}", fill=(255, 255, 0))
        sh.save(path)

    def meta(s, path):
        caps = []; capH = CAP_FONT.getbbox("H")[3] - CAP_FONT.getbbox("H")[1]
        for o in s.words:
            if o["e"] + 0.35 <= NO_OVERLAY_UNTIL: continue
            x0, y0, x1, y1 = s.draw_caption(Image.new("RGB", (OW, OH)), o["w"])
            caps.append(dict(text=o["w"], t=max(o["s"], NO_OVERLAY_UNTIL), x0=x0, y0=y0 - 10, x1=x1, y1=y1, cap_height=capH))
        json.dump(dict(size=[OW, OH], fps=FPS, duration=s.dur, captions=caps, onscreen=s.m.ONSCREEN, oddity=s.m.ODDITY,
                       shots=[dict(t=round(x[0], 2), what=x[2]) for x in s.m.SHOTS]), open(path, "w"), indent=1)

    def mix(s, voice, music, out, t0=0.0):
        sr = sfx.SR; n = int(s.dur * sr)
        def load(p, ch):
            tmp = out + ".tmp.raw"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", p, "-ar", str(sr), "-ac", str(ch), "-f", "f32le", tmp], check=True)
            a = np.fromfile(tmp, np.float32); os.remove(tmp); return a.reshape(-1, ch)
        v = load(voice, 1)[:, 0]; v = np.pad(v, (0, max(0, n - len(v))))[:n]
        mu = load(music, 2)[int(MUSIC_OFFSET * sr):][:n]
        g = 10 ** (MUSIC_GAIN_DB / 20)
        # gentle ducking: music dips another ~2 dB while the narrator talks
        env = np.convolve(np.abs(v), np.ones(int(0.05 * sr)) / int(0.05 * sr), "same")
        talk = np.clip(env / (0.25 * env.max() + 1e-9), 0, 1)
        talk = np.convolve(talk, np.ones(int(0.25 * sr)) / int(0.25 * sr), "same")
        mg = g * (1 - 0.2 * talk)
        fi = np.minimum(1, np.arange(n) / (0.4 * sr)); fo = np.clip((s.dur - np.arange(n) / sr) / 0.6, 0, 1)
        mu = mu * (mg * fi * fo)[:, None]
        fx = sfx.render(s.m.SFX, s.dur) * 0.5
        y = mu + (v + fx)[:, None]
        y = y[int(t0 * sr):]
        y /= max(1.0, np.abs(y).max() / 0.95)
        with wave.open(out, "wb") as w:
            w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes((y * 32767).astype(np.int16).tobytes())

    def video(s, voice, music, out, t0=0.0, t1=None):
        from multiprocessing import Pool
        t1 = s.dur if t1 is None else t1
        mixwav = out + ".mix.wav"; s.mix(voice, music, mixwav, t0)
        n0, n1 = int(t0 * FPS), int(t1 * FPS)
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{OW}x{OH}", "-r", str(FPS), "-i", "-",
               "-i", mixwav, "-c:v", "libx264", "-preset", "medium", "-crf", "21", "-maxrate", "12M", "-bufsize", "24M", "-pix_fmt", "yuv420p",
               "-af", f"loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=out:st={max(0, t1 - t0 - 0.3):.2f}:d=0.25", "-ar", "48000", "-c:a", "aac", "-b:a", "192k",
               "-movflags", "+faststart", "-t", f"{t1 - t0:.3f}", out]
        ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        with Pool(os.cpu_count(), initializer=_init, initargs=(s.m.NAME,)) as pool:
            for k, fr in enumerate(pool.imap(_frame, range(n0, n1), chunksize=4)):
                ff.stdin.write(fr.tobytes())
                if k % 150 == 0: print("frame", n0 + k, flush=True)
        ff.stdin.close(); ff.wait(); os.remove(mixwav)
        if ff.returncode: sys.exit("ffmpeg failed")
        print("ok", out)

def _remux(s, voice, music, src, out):
    """Re-mix the audio only and put it on an existing render's video stream (no re-render of frames)."""
    mixwav = out + ".mix.wav"; s.mix(voice, music, mixwav)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", src, "-i", mixwav, "-map", "0:v", "-map", "1:a", "-c:v", "copy",
                    "-af", f"loudnorm=I=-14:TP=-1.5:LRA=11,afade=t=out:st={s.dur - 0.3:.2f}:d=0.25", "-ar", "48000", "-c:a", "aac",
                    "-b:a", "192k", "-movflags", "+faststart", "-t", f"{s.dur:.3f}", out], check=True)
    os.remove(mixwav); print("ok", out)
Video.remux = _remux

_V = None
def _init(name):
    global _V
    import importlib; _V = importlib.import_module(name).V
def _frame(n): return _V.frame(n)

def main(V):
    cmd = sys.argv[1]
    if cmd == "still": Image.fromarray(V.frame(int(float(sys.argv[2]) * FPS))).save(sys.argv[3])
    elif cmd == "sheet": V.sheet(sys.argv[2])
    elif cmd == "meta": V.meta(sys.argv[2])
    elif cmd == "remux": V.remux(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    elif cmd == "video": V.video(sys.argv[2], sys.argv[3], sys.argv[4], *[float(x) for x in sys.argv[5:7]])
