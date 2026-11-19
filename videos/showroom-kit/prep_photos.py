"""Cut the Commons car photos out cleanly (rembg isnet-general-use), remove stray background objects, level them to a
common exposure and write ~/.cache/showroom/cars/<key>.png. Downloads go to ~/.cache/photos (not committed).
Usage: python prep_photos.py KEY [KEY ...] | python prep_photos.py credits OUT.txt KEY [KEY ...]   (needs `pip install "rembg[cpu]"`, which brings scipy)"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageEnhance


SRC, OUT = os.path.expanduser('~/.cache/photos'), os.path.expanduser('~/.cache/showroom/cars')
# key: (Commons file name, polygons to erase in first-cut bbox coordinates, fade-left fraction)
PHOTOS = {
    'honda_prologue': ("2024 Honda Prologue Touring, front 7.11.25.jpg", [], 0),
    'chevy_blazer_ev': ("2024 Chevrolet Blazer EV RS AWD in Summit White, front left, 2024-03-31.jpg",
                        [[(330, 180), (472, 180), (445, 240), (415, 282), (330, 300)]], 0),
    'tesla_model_y': ("2024 Tesla Model Y Long Range, front left, 07-28-2024.jpg", [], 0),
    'toyota_gr86': ("2022 Toyota GR86 Premium in Halo, Front Right, 04-10-2022.jpg",
                    [[(330, 0), (1000, 0), (1000, 150), (700, 146), (420, 158), (330, 186)]], 0),
    'subaru_brz': ("2022 Subaru BRZ Limited in Crystal Black Silica, front right (NYIAS 2022).jpg", [], 0),
    'mitsubishi_outlander': ("2022 Mitsubishi Outlander SE Launch Edition (United States) front view 03.jpg", [], 0),
    'nissan_rogue': ("2021 Nissan Rogue (T33) front view (United States).png", [], .10),
}
# photographer and licence, read from each file page (wikitext) on 2026-11-19
CREDIT = {
    'honda_prologue': ('Kevauto', 'CC BY-SA 4.0'),
    'chevy_blazer_ev': ('Elise240SX', 'CC BY-SA 4.0'),
    'tesla_model_y': ('Ethan Llamas', 'CC BY-SA 4.0'),
    'toyota_gr86': ('Elise240SX', 'CC BY-SA 4.0'),
    'subaru_brz': ('Mr.choppers', 'CC BY-SA 3.0 / GFDL'),
    'mitsubishi_outlander': ('Gold Pony (YouTube, via Commons)', 'CC BY 3.0 (YouTube CC BY)'),
    'nissan_rogue': ('North Island Nissan (YouTube, via Commons)', 'CC BY 3.0 (YouTube CC BY)'),
}
def write_credits(keys, out):
    with open(out, 'w') as f:
        f.write('Car photos from Wikimedia Commons (cut out from their backgrounds, levelled and resized for this video).\n\n')
        for k in keys:
            name = PHOTOS[k][0]; who, lic = CREDIT[k]
            f.write(f'- "{name}" by {who}, {lic}\n  https://commons.wikimedia.org/wiki/File:{name.replace(" ", "_")}\n')
        f.write('\nModified: background removed, exposure levelled, resized. Showroom, characters and gags are original drawings.\n')
    print('credits', out)

def local(name): return os.path.join(SRC, name.translate(str.maketrans(' ,()', '____')))

def prep(key, session):
    name, erase, fade = PHOTOS[key]
    from rembg import remove
    from scipy import ndimage
    orig = Image.open(local(name)).convert('RGB')
    mask = remove(orig, session=session, only_mask=True, post_process_mask=True)
    bb = mask.point(lambda v: 255 if v > 40 else 0).getbbox()
    rgb, m = orig.crop(bb), mask.crop(bb)
    md = ImageDraw.Draw(m)
    for poly in erase: md.polygon(poly, fill=0)
    a = np.array(m)
    lab, n = ndimage.label(a > 100)
    keep = lab == 1 + int(np.argmax(ndimage.sum(np.ones_like(a), lab, range(1, n + 1))))
    keep = ndimage.binary_fill_holes(ndimage.binary_dilation(keep, iterations=3))
    a = np.where(keep, np.maximum(a, 255 * ndimage.binary_fill_holes(a > 100)), 0).astype(np.float32)   # glass holes back in
    if fade:
        w = a.shape[1]; ramp = np.clip(np.arange(w) / (fade * w), 0, 1) ** 1.5; a *= ramp[None, :]
    px = np.asarray(rgb).astype(np.float32)
    lum = px @ np.array([.299, .587, .114]); sel = lum[a > 200]
    lo, hi = np.percentile(sel, 1.5), np.percentile(sel, 98.5)
    px = np.clip((px - lo) * (240 / max(1, hi - lo)) + 8, 0, 255)
    im = Image.fromarray(px.astype(np.uint8)); im = ImageEnhance.Color(im).enhance(1.1)
    im.putalpha(Image.fromarray(a.astype(np.uint8)))
    im = im.crop(im.getchannel('A').point(lambda v: 255 if v > 40 else 0).getbbox())
    if im.width > 1400: im = im.resize((1400, int(im.height * 1400 / im.width)), Image.LANCZOS)
    os.makedirs(OUT, exist_ok=True); im.save(os.path.join(OUT, key + '.png')); print(key, im.size)

if __name__ == '__main__':
    if sys.argv[1:2] == ['credits']:
        write_credits(sys.argv[3:], sys.argv[2]); sys.exit()
    from rembg import new_session
    s = new_session('isnet-general-use')
    for k in sys.argv[1:] or PHOTOS: prep(k, s)
