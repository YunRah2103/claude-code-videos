"""Build the why-every-model-t-was-black sprites and backdrops into ../assets/ (PNG, not committed)."""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from PIL import Image, ImageDraw
from pixanim.guy import guy
from pixanim.car import car
from pixanim.sprites import tag, bubble, xmark
from backdrops.garage import Garage

ASSETS = os.path.join(HERE, '..', 'assets')
os.makedirs(ASSETS, exist_ok=True)
W, H = 1080, 1920


def up(img, s):
    return img.resize((img.width * s, img.height * s), Image.NEAREST)


def save(img, name):
    img.convert('RGBA').save(os.path.join(ASSETS, name))


def swatches():
    """Paint-chip sign: five colours in a row, one per cell. 50x12 grid, x8."""
    cols = [(214, 48, 58), (61, 127, 214), (255, 196, 40), (70, 180, 110), (235, 235, 240)]
    g = Image.new('RGBA', (50, 12), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    d.rectangle((0, 0, 49, 11), fill=(40, 42, 52, 255))
    for i, c in enumerate(cols):
        d.rectangle((2 + i * 10, 2, 9 + i * 10, 9), fill=c + (255,))
    return up(g, 8)


def calendar_years():
    """Year strip 1914-1925 with the black era as one solid block. 60x14 grid, x6."""
    g = Image.new('RGBA', (60, 14), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    d.rectangle((0, 0, 59, 13), fill=(250, 246, 236, 255), outline=(60, 60, 70, 255))
    d.rectangle((4, 4, 55, 9), fill=(26, 26, 30, 255))                # the black era
    for i in range(12):
        x = 4 + i * 4
        d.line([(x, 10), (x, 12)], fill=(60, 60, 70, 255))
    return up(g, 6)


def main():
    save(Garage(W, H, 1180, 9).frame(0), 'bg_garage.png')
    save(up(car('black'), 6), 'car_model_t_standin.png')   # generic body in black; not a Model T silhouette
    save(swatches(), 'swatch_sign.png')
    save(xmark(), 'xmark.png')
    save(calendar_years(), 'calendar_1914_1925.png')
    save(tag('1914 TO 1925'), 'tag_years.png')
    save(tag('THE BLACK ERA'), 'tag_black_era.png')
    save(tag('DRIED FASTER?'), 'tag_dried_faster.png')
    save(bubble(), 'bubble.png')
    save(up(guy('smirk', 'point'), 8), 'presenter_point.png')
    save(up(guy('think', 'talkR'), 8), 'presenter_think.png')


def preview(name):
    """3 preview stills (black car in garage, colour sign, dried-faster bubble) and a contact sheet in out/<name>/stills/."""
    out = os.path.join(HERE, '..', '..', '..', 'out', name, 'stills'); os.makedirs(out, exist_ok=True)
    A = lambda f: Image.open(os.path.join(ASSETS, f)).convert('RGBA')
    s1 = A('bg_garage.png'); s1.alpha_composite(A('car_model_t_standin.png'), (200, 1180)); s1.alpha_composite(A('presenter_point.png'), (640, 1000))
    s2 = A('bg_garage.png'); s2.alpha_composite(A('swatch_sign.png'), (120, 520)); s2.alpha_composite(A('xmark.png'), (700, 560)); s2.alpha_composite(A('presenter_point.png'), (560, 1000))
    s3 = A('bg_garage.png'); s3.alpha_composite(A('bubble.png'), (560, 480)); s3.alpha_composite(A('tag_dried_faster.png'), (600, 560)); s3.alpha_composite(A('presenter_think.png'), (120, 1000))
    stills = [s1, s2, s3]
    for i, s in enumerate(stills, 1): s.convert('RGB').save(os.path.join(out, f'preview_{i}.png'))
    sheet = Image.new('RGB', (360 * len(stills) + 10 * (len(stills) - 1), 640), (20, 20, 20))
    for i, s in enumerate(stills): sheet.paste(s.convert('RGB').resize((360, 640)), (i * 370, 0))
    sheet.save(os.path.join(out, 'sheet.png'))


if __name__ == '__main__':
    main()
    preview('why-every-model-t-was-black')
