"""Cut real car photos out and give them a flat, vivid look that sits in the cartoon showroom.
Usage: python prep_cars.py RAW_DIR   (RAW_DIR holds e46.jpg e92.jpg g80_side.jpg g80_front.jpg; kept outside git)
Writes ../assets/<name>.png (RGBA). Steps: rembg cut-out -> tight crop -> mild edge-preserving flatten (median) ->
saturation/contrast boost -> clean alpha edge -> thin dark outline like the drawn characters."""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter
from scipy import ndimage
from rembg import remove, new_session
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', 'assets')
OL = (26, 26, 46)
PLATES = {'g80_front': [(212, 601), (492, 629), (490, 699), (212, 673)]}   # measured on this output
sess = new_session('isnet-general-use')
for name in ('e46', 'e92', 'g80_side', 'g80_front'):
    src = next(os.path.join(sys.argv[1], f) for f in os.listdir(sys.argv[1]) if f.startswith(name + '.'))
    im = Image.open(src).convert('RGB')
    if im.width > 2400: im = im.resize((2400, int(im.height * 2400 / im.width)), Image.LANCZOS)
    cut = remove(im, session=sess, post_process_mask=True)
    a = cut.getchannel('A')
    a = a.point(lambda v: 0 if v < 40 else 255 if v > 215 else int((v - 40) * 255 / 175))
    lab, n = ndimage.label(np.array(a) > 60)                          # keep only the car: drop stray fragments
    if n > 1:
        big = 1 + int(np.argmax(ndimage.sum(np.ones_like(lab), lab, range(1, n + 1))))
        a = Image.fromarray((np.array(a) * (lab == big)).astype(np.uint8))
    bb = a.getbbox(); rgb = im.crop(bb); a = a.crop(bb)
    rgb = rgb.filter(ImageFilter.MedianFilter(5))                       # flatten texture/noise, keep edges
    rgb = ImageEnhance.Color(rgb).enhance(1.45)
    rgb = ImageEnhance.Contrast(rgb).enhance(1.12)
    rgb = ImageEnhance.Brightness(rgb).enhance(1.04)
    a = a.filter(ImageFilter.GaussianBlur(1.2)).point(lambda v: 0 if v < 100 else 255 if v > 160 else int((v - 100) * 255 / 60))
    edge = a.filter(ImageFilter.MaxFilter(7))                            # outline ring
    pad = 8
    out = Image.new('RGBA', (rgb.width + 2 * pad, rgb.height + 2 * pad), (0, 0, 0, 0))
    ring = Image.new('RGBA', out.size, OL + (0,)); ring.putalpha(Image.new('L', out.size, 0))
    e2 = Image.new('L', out.size, 0); e2.paste(edge, (pad, pad)); e2 = e2.filter(ImageFilter.MaxFilter(5))
    ring.putalpha(e2); out.alpha_composite(ring)
    body = rgb.convert('RGBA'); body.putalpha(a)
    out.alpha_composite(body, (pad, pad))
    if name in PLATES:                                                  # replace the real number plate with a blank one
        q = PLATES[name]; d = ImageDraw.Draw(out)
        d.polygon(q, fill=(246, 246, 242), outline=(30, 30, 34), width=4)
        (x0, y0), (x3, y3) = q[0], q[3]
        d.polygon([q[0], (x0 + 26, y0 + 3), (x3 + 26, y3), q[3]], fill=(20, 60, 170))
    out.save(os.path.join(OUT, name + '.png'), optimize=True)
    print(name, out.size)
