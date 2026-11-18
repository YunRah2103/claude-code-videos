"""Cut real photos out of their backgrounds (rembg isnet), blank number plates, grade them to one look and resample
them to one display resolution so every exhibit in a video has the same sharpness.
Usage: python cutout.py VIDEO_DIR OUT_DIR   (reads EXHIBITS from VIDEO_DIR/src/script.py)"""
import os, sys, importlib.util
import numpy as np
from PIL import Image, ImageEnhance, ImageFilter, ImageOps
from rembg import remove, new_session

DISP_W, DISP_H, K = 600, 330, 2            # display box (design px) on the platform; K = supersampling

def load_script(vdir):
    spec = importlib.util.spec_from_file_location('script', os.path.join(vdir, 'src', 'script.py'))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def cut(path, ex, sess):
    im = Image.open(path).convert('RGB')
    w, h = im.size
    for (x0, y0, x1, y1) in ex.get('plates', ()):        # blank plates (fractions of the photo)
        box = (int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h))
        reg = np.array(im.crop(box)).reshape(-1, 3)
        col = tuple(int(c) for c in np.percentile(reg, 85, axis=0)) if ex.get('plate_col') is None else ex['plate_col']
        im.paste(col, box)
    cx0, cy0, cx1, cy1 = ex.get('crop', (0, 0, 1, 1))
    im = im.crop((int(cx0 * w), int(cy0 * h), int(cx1 * w), int(cy1 * h)))
    rgba = remove(im, session=sess, post_process_mask=True)
    a = np.array(rgba.getchannel('A')).astype(np.float32)
    def loc(b):                                          # original-photo fractions -> crop pixels
        return (int(b[0] * w) - int(cx0 * w), int(b[1] * h) - int(cy0 * h), int(b[2] * w) - int(cx0 * w), int(b[3] * h) - int(cy0 * h))
    for b in ex.get('erase', ()):                        # manual mask fixes: boxes to drop...
        x0, y0, x1, y1 = loc(b); a[max(0, y0):max(0, y1), max(0, x0):max(0, x1)] = 0
    a = np.where(a > 40, a, 0)
    from scipy import ndimage                            # keep the main object only
    lab, n = ndimage.label(a > 128)
    if n > 1:
        sizes = ndimage.sum(np.ones_like(a), lab, range(1, n + 1)); keep = np.argmax(sizes) + 1
        big = ndimage.binary_dilation(lab == keep, iterations=6)
        a = a * big
    if ex.get('keep'):                                   # ...and ellipses rembg missed (dark tyres on dark floors)
        from PIL import ImageDraw
        m = Image.new('L', (a.shape[1], a.shape[0]), 0)
        for b in ex['keep']: ImageDraw.Draw(m).ellipse(loc(b), fill=255)
        a = np.maximum(a, np.array(m, np.float32))
    rgba = im.convert('RGBA'); rgba.putalpha(Image.fromarray(a.astype(np.uint8)))   # photo colour, rembg alpha
    rgba = rgba.crop(rgba.getchannel('A').getbbox())
    if ex.get('flip'): rgba = ImageOps.mirror(rgba)
    for (x0, y0, x1, y1) in ex.get('erase_out', ()):     # boxes in final (flipped) fractions
        al = rgba.getchannel('A'); al.paste(0, (int(x0 * rgba.width), int(y0 * rgba.height), int(x1 * rgba.width), int(y1 * rgba.height)))
        rgba.putalpha(al)
    rgba = rgba.crop(rgba.getchannel('A').getbbox())
    # one look: autocontrast, warm showroom grade, saturation, then same resolution for all
    rgb = ImageOps.autocontrast(rgba.convert('RGB'), cutoff=0.5)
    rgb = ImageEnhance.Color(rgb).enhance(ex.get('sat', 1.18))
    rgb = ImageEnhance.Contrast(rgb).enhance(1.08)
    out = rgb.convert('RGBA'); out.putalpha(rgba.getchannel('A'))
    s = min(DISP_W * ex.get('scale', 1.0) / out.width, DISP_H * ex.get('scale', 1.0) / out.height)
    dw, dh = max(1, round(out.width * s)), max(1, round(out.height * s))
    out = out.resize((dw, dh), Image.LANCZOS)                   # common display resolution (1x)...
    out = out.resize((dw * K, dh * K), Image.BICUBIC)             # ...then the same upsample for every exhibit
    rgb = out.convert('RGB').filter(ImageFilter.UnsharpMask(2.2, 70, 2))
    alpha = out.getchannel('A').filter(ImageFilter.GaussianBlur(0.8))
    rgb.putalpha(alpha); return rgb

if __name__ == '__main__':
    vdir, odir = sys.argv[1:3]; os.makedirs(odir, exist_ok=True)
    S = load_script(vdir); sess = new_session('isnet-general-use')
    for key, ex in S.EXHIBITS.items():
        cut(os.path.join(vdir, 'assets', ex['file']), ex, sess).save(os.path.join(odir, key + '.png'))
        print('cut', key)
