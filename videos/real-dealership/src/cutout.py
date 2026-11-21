"""Cut a car out of a real photo: a hand-traced outline (percent coords) gives a trimap; a colour model (k-means
centres for car vs background, sampled from the sure regions) decides the uncertain band; result is a soft-edged RGBA PNG
cropped to the car. Pure PIL + numpy. Usage: python cutout.py EPISODE_DIR  (reads CUTS in EPISODE_DIR/cutouts.py)"""
import os, sys, importlib.util
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

def blur(a, r):
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
    return np.asarray(im.filter(ImageFilter.BoxBlur(r)), np.float32) / 255

def kmeans(x, k, it=12, seed=0):
    rng = np.random.default_rng(seed); c = x[rng.choice(len(x), k, replace=False)]
    for _ in range(it):
        lab = np.argmin(((x[:, None, :] - c[None]) ** 2).sum(-1), 1)
        c = np.array([x[lab == j].mean(0) if np.any(lab == j) else c[j] for j in range(k)])
    return c

def nearest(x, c):
    out = np.full(len(x), np.inf, np.float32)
    for j in range(len(c)): out = np.minimum(out, ((x - c[j]) ** 2).sum(-1))
    return out

def cut(src, poly, band=0.007, k=8, bias=0.0, out=None):
    im = Image.open(src).convert('RGB'); W, H = im.size
    a = np.asarray(im, np.float32)
    m = Image.new('L', (W, H), 0); ImageDraw.Draw(m).polygon([(x * W / 100, y * H / 100) for x, y in poly], fill=255)
    M = np.asarray(m, np.float32) / 255
    r = max(4, int(band * W))
    prior = blur(blur(M, r), r // 2)
    fg, bg = prior > .97, prior < .03
    near_bg = bg & (blur(M, 3 * r) > .01)
    rng = np.random.default_rng(1)
    def samp(mask, n=25000):
        p = a[mask]; return p[rng.choice(len(p), min(n, len(p)), replace=False)]
    cf, cb = kmeans(samp(fg), k), kmeans(samp(near_bg), k)
    unk = ~(fg | bg)
    x = a[unk]
    df, db = nearest(x, cf), nearest(x, cb)
    p = np.zeros((H, W), np.float32); p[fg] = 1
    p[unk] = db / (df + db + 1e-6)
    p = blur(p, 2)
    p[unk] = 0.55 * p[unk] + 0.45 * prior[unk] + bias
    alpha = np.clip((p - 0.42) / 0.16, 0, 1); alpha[fg] = 1; alpha[bg] = 0
    alpha = blur(alpha, 1)
    ys, xs = np.nonzero(alpha > .02)
    box = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
    rgba = Image.fromarray(np.dstack([a, alpha * 255]).astype(np.uint8), 'RGBA').crop(box)
    if out: rgba.save(out)
    return rgba

if __name__ == '__main__':
    ep = os.path.abspath(sys.argv[1])
    spec = importlib.util.spec_from_file_location('cutouts', os.path.join(ep, 'cutouts.py')); C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)
    only = sys.argv[2:] or list(C.CUTS)
    for name in only:
        src, poly, kw = C.CUTS[name]
        r = cut(os.path.join(ep, 'assets', src), poly, out=os.path.join(ep, 'assets', f'cut_{name}.png'), **kw)
        print(name, r.size)
