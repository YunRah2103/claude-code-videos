"""Original 8.2s rainy neon pixel-art loop: 3 scenes, hard cuts, drift, rain, flicker, ambient audio.

Native canvas 180x180 -> nearest-neighbour x4 = 720x720 @ 30fps (matches the reference spec).
  python render.py still OUT_DIR T [T ...]     # preview PNGs at times (seconds)
  python render.py video OUT.mp4               # full render with synthesized audio
Needs: pillow, numpy, ffmpeg. Scenes are procedural and original (no traced art).
"""
import math, os, random, subprocess, sys, tempfile, wave
import numpy as np
from PIL import Image, ImageDraw

W = H = 180
SCALE = 4
FPS = 30
DUR = 8.2
CUTS = (2.5, 5.53)  # scene boundaries measured from the reference
START = (0, 30, 36)  # camera start x per scene
BIG = 240           # scene canvas width (wider than view so the camera can drift)


def hexc(s):
    return tuple(int(s[i:i + 2], 16) for i in (1, 3, 5))


def mix(a, b, k):
    return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))


def glyphs(d, x, y, n, col, seed, h=5, gap=2, w=4):
    """Fake neon lettering made of blocky strokes (original, not a real script)."""
    r = random.Random(seed)
    for i in range(n):
        gx = x + i * (w + gap)
        for _ in range(r.randint(2, 3)):
            if r.random() < .5:
                yy = y + r.randint(0, h - 1)
                d.line([gx, yy, gx + w - 1, yy], fill=col)
            else:
                xx = gx + r.randint(0, w - 1)
                d.line([xx, y, xx, y + h - 1], fill=col)


def gradient(d, w, h, top, bot):
    for y in range(h):
        d.line([0, y, w, y], fill=mix(top, bot, y / (h - 1)))


def windows(d, x0, y0, cols, rows, cw, ch, on, off, seed, p=.5):
    r = random.Random(seed)
    for i in range(cols):
        for j in range(rows):
            c = on if r.random() < p else off
            d.rectangle([x0 + i * (cw + 1), y0 + j * (ch + 1), x0 + i * (cw + 1) + cw - 1, y0 + j * (ch + 1) + ch - 1], fill=c)


def pole(d, x, ground, col):
    d.line([x, ground - 46, x, ground], fill=col)
    d.line([x - 6, ground - 40, x + 6, ground - 40], fill=col)
    d.line([x - 4, ground - 34, x + 4, ground - 34], fill=col)


def wires(d, x0, x1, y, col, sag=4):
    for k in range(3):
        for x in range(x0, x1):
            u = (x - x0) / (x1 - x0)
            d.point((x, int(y + k * 3 + math.sin(u * math.pi) * sag)), fill=col)


def flicker(t, seed, rate=9):
    """0.55..1 brightness with occasional dips, like a failing neon tube."""
    v = math.sin(t * rate + seed) * math.sin(t * 2.3 + seed * 2)
    return 1.0 if v > -0.6 else 0.55


def reflect(img, water_y, t, strength=.5, tint=(0, 12, 24)):
    a = np.asarray(img).astype(np.float32)
    out = a.copy()
    for y in range(water_y, a.shape[0]):
        src = water_y - (y - water_y) * 1 - 1
        if src < 0:
            break
        sh = int(round(math.sin(y * .9 + t * 2.5) * (1 + (y - water_y) / 18)))
        row = np.roll(a[src], sh, axis=0)
        k = max(0.0, strength - (y - water_y) / 90)
        out[y] = a[y] * (1 - k) + (row * .8 + np.array(tint)) * k
    return Image.fromarray(out.clip(0, 255).astype(np.uint8))


def rain(img, t, seed, n, col, speed=70, length=5, slant=1):
    d = ImageDraw.Draw(img)
    r = random.Random(seed)
    w, h = img.size
    for _ in range(n):
        x0, y0, v = r.uniform(0, w), r.uniform(0, h), r.uniform(.7, 1.3)
        y = (y0 + t * speed * v) % (h + length) - length
        x = (x0 + y * slant * .15) % w
        d.line([x, y, x + slant, y + length], fill=col)


# ---------------------------------------------------------------- scenes
def scene_roadside(t):
    """0-2.5s: teal dusk, huge tower with a red ring, wires, lit shop, car, wet road."""
    img = Image.new("RGB", (BIG, H)); d = ImageDraw.Draw(img)
    gradient(d, BIG, 112, hexc("#0e5a74"), hexc("#2f95a8"))
    d.polygon([(100, 112), (118, 24), (150, 8), (205, 24), (230, 112)], fill=hexc("#0a2e45"))   # tower
    d.polygon([(118, 24), (150, 8), (205, 24), (196, 24), (150, 14), (124, 28)], fill=hexc("#103e57"))
    for dx in range(0, 70, 2):                                                                 # red ring
        yy = 22 + int(math.sin(dx / 70 * math.pi) * -10) + 20
        d.point((135 + dx, yy), fill=hexc("#ff4a5a")); d.point((135 + dx, yy + 1), fill=hexc("#c01f3a"))
    r = random.Random(4)
    for _ in range(26):
        d.point((r.randint(120, 215), r.randint(26, 70)), fill=hexc("#e0b43c"))
    d.rectangle([0, 96, BIG, 112], fill=hexc("#0b3a4d"))                                         # tree line
    for x in range(0, BIG, 3):
        d.line([x, 96 - (x * 7 % 9), x, 100], fill=hexc("#082c3a"))
    pole(d, 30, 112, hexc("#0a2430")); pole(d, 120, 112, hexc("#0a2430"))
    wires(d, 0, 120, 78, hexc("#08202c")); wires(d, 30, BIG, 66, hexc("#08202c"), 6)
    d.rectangle([0, 112, BIG, H], fill=hexc("#0a3a4e"))                                          # ground
    d.rectangle([62, 94, 120, 112], fill=hexc("#0b2733"))                                        # shop
    d.rectangle([60, 92, 124, 95], fill=hexc("#12384a"))
    for x0, c in ((66, "#f2e3a1"), (84, "#f7e9ad"), (103, "#e9d98c")):
        d.rectangle([x0, 99, x0 + 10, 108], fill=hexc(c))
    d.rectangle([124, 98, 150, 112], fill=hexc("#0f3445"))
    d.rectangle([8, 104, 34, 112], fill=hexc("#7fa5b5")); d.rectangle([14, 98, 28, 104], fill=hexc("#5d8da0"))  # car
    d.rectangle([12, 110, 16, 113], fill=hexc("#0a1c26")); d.rectangle([26, 110, 30, 113], fill=hexc("#0a1c26"))
    img = reflect(img, 112, t)
    rain(img, t, 1, 90, hexc("#5fb3c4"))
    return img


def scene_izakaya(t):
    """2.5-5.53s: near-black blue, red disc + pill sign, vertical banner, awning, yellow window."""
    img = Image.new("RGB", (BIG, H)); d = ImageDraw.Draw(img)
    gradient(d, BIG, H, hexc("#06102a"), hexc("#02050f"))
    d.rectangle([40, 0, 204, 140], fill=hexc("#0a0f1f"))                                         # building
    d.polygon([(30, 74), (122, 56), (214, 74), (214, 80), (30, 80)], fill=hexc("#101830"))      # roof
    for y in range(8, 50, 6):
        d.rectangle([66, y, 120, y + 3], fill=hexc("#3a1019"))
    f = flicker(t, 1.3)
    red, deep = mix(hexc("#2a0508"), hexc("#ff1b1b"), f), mix(hexc("#2a0508"), hexc("#a80c18"), f)
    d.rounded_rectangle([86, 44, 158, 66], 10, outline=deep, width=2)                            # pill
    d.ellipse([60, 40, 92, 72], fill=red)                                                        # disc
    d.rectangle([68, 54, 84, 64], fill=hexc("#1a0408")); d.ellipse([66, 46, 74, 52], outline=hexc("#ffb0a0"))
    glyphs(d, 100, 48, 7, mix(hexc("#401018"), hexc("#ffe9e0"), f), 7)
    glyphs(d, 96, 60, 6, mix(hexc("#401018"), hexc("#ffd0c0"), f), 9, h=2, gap=3, w=3)
    d.rectangle([170, 0, 186, 44], fill=mix(hexc("#2a0508"), hexc("#e01420"), flicker(t, 4.1)))  # banner
    d.line([172, 22, 184, 22], fill=hexc("#ffd8c8"))
    for i in range(5):
        d.rectangle([84 + i * 9, 84, 87 + i * 9, 87], fill=hexc("#17bfd0"))                      # teal signage
    d.rectangle([62, 108, 160, 132], fill=hexc("#3b3414"))                                       # shop front
    for i in range(0, 100, 10):
        d.rectangle([60 + i, 98, 64 + i, 106], fill=hexc("#d8c030") if (i // 10) % 2 == 0 else hexc("#241c08"))
    d.rectangle([72, 108, 150, 132], fill=hexc("#f4e11c"))                                       # warm window
    d.rectangle([104, 114, 116, 132], fill=hexc("#16130a")); d.ellipse([105, 108, 115, 118], fill=hexc("#16130a"))  # silhouette
    for x in (166, 178):
        d.ellipse([x, 106, x + 7, 114], fill=hexc("#ff2a2a"))                                    # lanterns
    d.rectangle([0, 140, BIG, H], fill=hexc("#03060f"))
    img = reflect(img, 140, t, .35, (4, 6, 16))
    rain(img, t, 2, 55, hexc("#2c4066"), 80)
    return img


def scene_bridge(t):
    """5.53-8.2s: deep blue night, tower with number, slanted gantry, green neon, truck, shop."""
    img = Image.new("RGB", (BIG, H)); d = ImageDraw.Draw(img)
    gradient(d, BIG, 130, hexc("#07204a"), hexc("#0b2c52"))
    d.rectangle([140, 8, 206, 118], fill=hexc("#0c2a4e"))                                        # tower
    windows(d, 144, 18, 14, 14, 3, 5, hexc("#134a70"), hexc("#0a2442"), 5, .25)
    d.rectangle([150, 16, 200, 30], fill=hexc("#0e3158"))
    glyphs(d, 156, 20, 4, hexc("#4aa0d8"), 3, h=6, gap=3, w=5)                                   # "-07-" style tag (own glyphs)
    d.polygon([(20, 70), (130, 58), (200, 90), (200, 98), (130, 70), (20, 80)], fill=hexc("#0a1838"))  # gantry
    for x in (36, 66, 96):
        d.line([x, 78, x - 10, 124], fill=hexc("#06122a"), width=2)
    for x in range(10, 60, 8):
        d.rectangle([x, 96, x + 5, 118], fill=hexc("#081832"))
    f = flicker(t, 2.2, 6)
    g = mix(hexc("#0a2a10"), hexc("#9cff2a"), f)
    d.ellipse([136, 82, 152, 98], outline=g, width=2); d.line([144, 85, 144, 95], fill=g)         # green sign
    glyphs(d, 156, 86, 4, g, 11, h=6, gap=3, w=4)
    d.rectangle([0, 124, BIG, H], fill=hexc("#05122a"))                                          # ground
    d.rectangle([90, 108, 128, 124], fill=hexc("#0a1830")); d.rectangle([118, 112, 130, 124], fill=hexc("#cfd6df"))  # truck
    d.rectangle([121, 116, 127, 120], fill=hexc("#ff6a3c"))
    for i in range(4):
        c = mix(hexc("#0a3a40"), hexc("#7af0e0"), flicker(t, 3 + i, 5))
        d.rectangle([154 + i * 12, 112, 162 + i * 12, 122], fill=c)                              # cyan stalls
    d.rectangle([150, 106, 206, 112], fill=hexc("#0c2a40"))
    d.rectangle([40, 116, 44, 124], fill=hexc("#3b8fd0"))                                        # lone lamp
    img = reflect(img, 124, t, .45, (0, 10, 30))
    rain(img, t, 3, 70, hexc("#3f6fa8"), 75)
    return img


def frame(t):
    s = 0 if t < CUTS[0] else 1 if t < CUTS[1] else 2
    t0 = (0, *CUTS)[s]
    img = (scene_roadside, scene_izakaya, scene_bridge)[s](t)
    off = min(START[s] + int((t - t0) * 6), BIG - W)         # slow horizontal camera drift
    img = img.crop((off, 0, off + W, H))
    a = np.asarray(img).astype(np.float32)
    yy, xx = np.mgrid[0:H, 0:W]
    v = 1 - .35 * (((xx - W / 2) / (W / 2)) ** 2 + ((yy - H / 2) / (H / 2)) ** 2) / 2          # vignette
    a *= v[..., None]
    a[::2] *= .96                                             # faint scanlines
    return Image.fromarray(a.clip(0, 255).astype(np.uint8)).resize((W * SCALE, H * SCALE), Image.NEAREST)


# ---------------------------------------------------------------- audio
def audio(path, sr=44100):
    n = int(DUR * sr); t = np.arange(n) / sr
    rng = np.random.default_rng(1)
    noise = rng.standard_normal(n)
    k = 40
    rainb = np.convolve(noise, np.ones(k) / k, mode="same") * 1.6 * (.8 + .2 * np.sin(t * .7))   # soft rain
    chords = [(220, 261.6, 329.6, 493.9), (196, 246.9, 293.7, 440), (174.6, 220, 261.6, 392)]     # Am9, G, Fmaj7-ish
    pad = np.zeros(n)
    seg = DUR / 3
    for i, ch in enumerate(chords):
        m = (t >= i * seg) & (t < (i + 1) * seg)
        env = np.clip(np.minimum((t - i * seg) / .5, ((i + 1) * seg - t) / .6), 0, 1) * m
        for f in ch:
            pad += env * np.sin(2 * np.pi * f * t + .3 * np.sin(2 * np.pi * 5 * t)) / len(ch)
    arp = np.zeros(n)
    notes = [440, 523.3, 659.3, 523.3, 392, 493.9, 587.3, 493.9]
    for i in range(int(DUR / .4)):                                                                  # soft pluck arp
        s0 = int(i * .4 * sr); ln = int(.38 * sr)
        tt = np.arange(min(ln, n - s0)) / sr
        arp[s0:s0 + len(tt)] += np.sin(2 * np.pi * notes[i % 8] * tt) * np.exp(-tt * 7) * .5
    crack = (rng.random(n) > .9996) * rng.standard_normal(n) * .6                                   # vinyl crackle
    mono = .55 * pad + .35 * arp + .18 * rainb + .3 * crack
    fade = np.clip(np.minimum(t / .4, (DUR - t) / .6), 0, 1)
    mono *= fade / max(1e-6, np.abs(mono).max()) * .8
    left, right = mono, np.roll(mono, 90)                                                           # tiny stereo widening
    pcm = (np.stack([left, right], 1) * 32767).astype("<i2")
    with wave.open(path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(sr); w.writeframes(pcm.tobytes())


def video(out):
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        wav = os.path.join(tmp, "a.wav"); audio(wav)
        cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W*SCALE}x{H*SCALE}",
               "-r", str(FPS), "-i", "-", "-i", wav, "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18",
               "-c:a", "aac", "-b:a", "128k", "-t", str(DUR), "-movflags", "+faststart", out]
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
        for i in range(int(round(DUR * FPS))):
            p.stdin.write(frame(i / FPS).tobytes())
        p.stdin.close()
        if p.wait():
            sys.exit("ffmpeg failed")


if __name__ == "__main__":
    if len(sys.argv) >= 4 and sys.argv[1] == "still":
        os.makedirs(sys.argv[2], exist_ok=True)
        for s in sys.argv[3:]:
            frame(float(s)).save(os.path.join(sys.argv[2], f"t{float(s):.2f}.png"))
    elif len(sys.argv) == 3 and sys.argv[1] == "video":
        video(sys.argv[2])
    else:
        sys.exit(__doc__)
