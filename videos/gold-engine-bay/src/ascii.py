"""Gold engine bay, ASCII style: the LiDAR scene (true 3D camera) re-drawn as coloured monospace
characters. Block-letter titles decrypt in from random characters. Same timing.json beats.

  python ascii.py still OUTDIR T [T ...]
  python ascii.py video OUT.mp4 [START END]
"""
import subprocess, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import pc
import render as R
from render import B, FPS, W, H, clamp, prog

CW, CH = 9, 16                       # character cell (120 x 120 grid)
COLS, ROWS = W // CW, H // CH
JB = "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-Bold.ttf"
RAMP = " .,:;-~=+*cxoO#%@"
EDGE = {0: "-", 1: "/", 2: "|", 3: "\\"}
BG = np.array([0.02, 0.021, 0.025], np.float32)
GOLD = np.array([1.0, 0.78, 0.30], np.float32); WHITE = np.array([0.93, 0.94, 0.97], np.float32)
COPPER = np.array([1.0, 0.58, 0.32], np.float32); RED = np.array([1.0, 0.30, 0.18], np.float32)

_G = {}
def glyphs():
    if not _G:
        chars = sorted(set(RAMP + "-/|\\" + "#@%&$01ABCDEFGHIJKLMNOPQRSTUVWXYZ"))
        f = ImageFont.truetype(JB, 15)
        bank = np.zeros((len(chars), CH, CW), np.float32)
        for i, c in enumerate(chars):
            im = Image.new("L", (CW, CH), 0)
            ImageDraw.Draw(im).text((CW / 2, CH / 2), c, font=f, fill=255, anchor="mm")
            bank[i] = np.asarray(im, np.float32) / 255
        _G.update(chars=chars, bank=bank, idx={c: i for i, c in enumerate(chars)})
    return _G

def cells(img):
    """Average colour per character cell."""
    return img.reshape(ROWS, CH, COLS, CW, 3).mean((1, 3))

# block-letter titles: coverage masks on the character grid
TITLES = [  # key, items (x, y, text, font, size, colour, gold words), appear beat, leave beat
    ("headline", [(64, 238, "McLAREN F1 · ENGINE BAY", "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-ExtraBold.ttf", 60, COPPER, ()),
                  (64, 330, "WHY IS THERE", "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-ExtraBold.ttf", 104, WHITE, ()),
                  (64, 444, "GOLD IN THIS", "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-ExtraBold.ttf", 104, WHITE, ("GOLD",)),
                  (64, 558, "ENGINE?", "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-ExtraBold.ttf", 104, WHITE, ())], None, "reveal"),
    ("v12", [(64, 700, "V12 · 6.1 L", "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-ExtraBold.ttf", 84, COPPER, ())], "v12", None),
    ("ir", [(64, 430, "INFRARED HEAT", "/usr/share/fonts/truetype/jetbrains-mono/JetBrainsMono-ExtraBold.ttf", 84, RED, ())], "heat", None),
]
_T = {}
def title(key, items):
    if key not in _T:
        chars, cov = [], np.zeros((H, W), bool)
        rng = np.random.default_rng(len(key))
        n = sum(len(it[2]) for it in items); order = rng.permutation(n) / n * 0.97
        k = 0
        for x, y, text, fp, size, c, golds in items:
            f = ImageFont.truetype(fp, size); cx = x
            words = text.split(" "); wi = 0
            for chx in text:
                if chx == " ": wi += 1
                cc = GOLD if wi < len(words) and words[wi].strip("?") in golds else c
                wch = f.getlength(chx)
                chars.append((cx, y, chx, f, cc, order[k])); k += 1
                l, tp, r, b = f.getbbox(chx, anchor="la")
                cov[int(y + tp):int(y + b) + 1, int(cx):int(cx + wch) + 1] |= chx != " "
                cx += wch
        cc_ = cov.reshape(ROWS, CH, COLS, CW).any((1, 3))
        ys, xs = np.nonzero(cc_)
        assert (xs.max() + 1) * CW <= R.SAFE_X1 + CW and ys.min() * CH >= R.SAFE_Y0 and (ys.max() + 1) * CH <= R.SAFE_Y1, key
        halo = cc_.copy()
        for _ in range(2):
            h2 = halo.copy(); h2[1:] |= halo[:-1]; h2[:-1] |= halo[1:]; h2[:, 1:] |= halo[:, :-1]; h2[:, :-1] |= halo[:, 1:]; halo = h2
        _T[key] = (chars, halo)
    return _T[key]

def frame(t, tags=True):
    G = glyphs()
    src = np.asarray(pc.frame(t, text=False, tags=False), np.float32) / 255
    c = cells(src)
    lum = c @ np.array([0.3, 0.59, 0.11], np.float32)
    # characters: density ramp by brightness; edge characters where brightness changes sharply
    l2 = np.clip((lum - 0.03) / 0.75, 0, 1) ** 0.8
    ri = np.clip((l2 * (len(RAMP) - 1)).round().astype(int), 0, len(RAMP) - 1)
    ch = np.array([G["idx"][RAMP[i]] for i in range(len(RAMP))])[ri]
    gx = np.zeros_like(lum); gy = np.zeros_like(lum)
    gx[:, 1:-1] = lum[:, 2:] - lum[:, :-2]; gy[1:-1] = lum[2:] - lum[:-2]
    mag = np.hypot(gx, gy)
    ang = (np.round(((np.arctan2(gy, gx) + np.pi / 2) % np.pi) / (np.pi / 4)).astype(int)) % 4
    edge = (mag > 0.18) & (lum > 0.08)
    ech = np.array([G["idx"][EDGE[k]] for k in range(4)])[ang]
    ch = np.where(edge, ech, ch)
    # colour: hue of the cell pushed to full brightness, so characters glow on black
    colr = c / np.maximum(c.max(-1, keepdims=True), 1e-3)
    colr = colr * (0.55 + 0.75 * np.clip(l2 * 1.6, 0, 1))[..., None]
    bright = np.where(ri > 0, 1.0, 0.0) + edge
    # titles: decrypt in from random characters, scramble out
    rng = np.random.default_rng(int(t * FPS))
    rand_ch = rng.integers(0, len(G["chars"]), (ROWS, COLS))
    dim_mask = np.zeros((ROWS, COLS), np.float32)
    live = []
    for key, items, a0, a1 in TITLES:
        ta = 0.0 if a0 is None else B[a0]
        if t < ta or (a1 and t > B[a1] + 0.9): continue
        chars, halo = title(key, items)
        k_in = 1.0 if a0 is None else prog(t, ta, 0.7)
        k_out = 0.0 if a1 is None else prog(t, B[a1] - 0.1, 0.8)
        colr = colr * (1 - halo * (1 - k_out) * 0.92)[..., None]       # clear the scene behind the text
        live.append((chars, k_in, k_out))
    # rasterise: glyph bitmaps x cell colour
    g = G["bank"][ch]                                            # ROWS, COLS, CH, CW
    g = g * np.clip(bright, 0, 1)[..., None, None]
    img = (g[..., None] * colr[:, :, None, None, :]).transpose(0, 2, 1, 3, 4).reshape(H, W, 3)
    img = BG + img
    small = Image.fromarray(np.uint8(np.clip(img, 0, 1) * 255)).resize((W // 4, H // 4), Image.BILINEAR)
    from PIL import ImageFilter
    img += np.asarray(small.filter(ImageFilter.GaussianBlur(5)).resize((W, H), Image.BILINEAR), np.float32) / 255 * 0.55
    img *= (0.93 + 0.07 * ((np.arange(H) // 2) % 2))[:, None, None]     # faint CRT rows
    im = Image.fromarray(np.uint8(np.clip(img, 0, 1) * 255))
    d = ImageDraw.Draw(im)
    # terminal titles: each character decodes from random glyphs, then holds; scrambles out
    pool = "#@%&$/\\|<>*+=01ABCDEFGHJKLMNPRSTUVWXYZ"
    for chars, k_in, k_out in live:
        last = None
        for cx, cy, chx, f, cc, o in chars:
            if chx == " ": continue
            if o >= k_in + 0.18 or o < k_out - 0.18: continue
            settled = o < k_in and o >= k_out
            g_ = chx if settled else pool[rng.integers(len(pool))]
            col = tuple(int(255 * min(1, v * (1.0 if settled else 0.7))) for v in cc)
            d.text((cx, cy), g_, font=f, fill=col)
            last = (cx + f.getlength(chx), cy, f)
        if last and k_in < 1 and (int(t * 4) % 2 == 0):                 # blinking block cursor while typing
            x_, y_, f = last; l, tp, r, b = f.getbbox("M", anchor="la")
            d.rectangle((x_ + 4, y_ + tp, x_ + 4 + (r - l), y_ + b), fill=(240, 240, 240))
    if not tags: return im
    d.text((40, 52), "Yub", font=ImageFont.truetype(JB.replace("Bold", "ExtraBold"), 32), fill=(200, 200, 205))
    if R.PREVIEW:
        tf = ImageFont.truetype(JB, 24); tw = tf.getlength("PREVIEW")
        d.rectangle((W - 52 - tw, 50, W - 32, 86), outline=(255, 80, 60), width=2)
        d.text((W - 42 - tw, 68), "PREVIEW", font=tf, fill=(255, 80, 60), anchor="lm")
    return im


def _job(i): return np.asarray(frame(i / FPS)).tobytes()

def video(out, a=0.0, b=7.0):
    from multiprocessing import Pool
    pc.data(); glyphs()
    out = Path(out); out.parent.mkdir(parents=True, exist_ok=True); wav = out.with_suffix(".wav")
    R.audio(wav)
    n0, n1 = int(round(a * FPS)), int(round(b * FPS))
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-ss", str(a), "-t", str((n1 - n0) / FPS), "-i", str(wav), "-c:v", "libx264", "-preset", "medium",
           "-crf", "16", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", str(out)]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    with Pool(4) as pool:
        for k, buf in enumerate(pool.imap(_job, range(n0, n1), chunksize=2)):
            p.stdin.write(buf)
            if k % 60 == 0: print(f"frame {n0 + k}/{n1}", flush=True)
    p.stdin.close()
    assert p.wait() == 0
    wav.unlink(missing_ok=True)
    print(f"wrote {out}")


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "still":
        od = Path(sys.argv[2]); od.mkdir(parents=True, exist_ok=True)
        for s_ in sys.argv[3:]:
            frame(float(s_)).save(od / f"f_{s_}.png")
    elif cmd == "video":
        video(sys.argv[2], *(float(v) for v in sys.argv[3:5]))
