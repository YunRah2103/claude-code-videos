"""Build the the-car-that-stayed-level sprites and backdrops into ../assets/ (PNG, not committed)."""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from PIL import Image, ImageDraw
from pixanim.guy import guy
from pixanim.car import car
from pixanim.dash import Dashboard
from pixanim.street import Street
from pixanim.sprites import sparkle, star, tag

ASSETS = os.path.join(HERE, '..', 'assets')
os.makedirs(ASSETS, exist_ok=True)
W, H = 1080, 1920


def up(img, s):
    return img.resize((img.width * s, img.height * s), Image.NEAREST)


def save(img, name):
    img.convert('RGBA').save(os.path.join(ASSETS, name))


def motorcycle():
    """Bodyguard motorbike, side view: 40x24 grid, x5."""
    g = Image.new('RGBA', (40, 24), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    for cx in (8, 32):
        d.ellipse((cx - 6, 12, cx + 6, 24), fill=(20, 20, 28, 255), outline=(150, 150, 160, 255))
        d.ellipse((cx - 2, 16, cx + 2, 20), fill=(120, 124, 134, 255))
    d.polygon([(8, 14), (18, 10), (28, 10), (32, 14), (20, 14)], fill=(60, 64, 78, 255))
    d.line([(26, 10), (30, 2)], fill=(200, 200, 210, 255), width=1)     # handlebar
    return up(g, 5)


def suspension():
    """Hydropneumatic diagram: DS body on four spheres, arrows show the level correction. 60x36 grid, x6."""
    g = Image.new('RGBA', (60, 36), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    d.rounded_rectangle((6, 8, 54, 20), radius=3, fill=(70, 130, 220, 255), outline=(180, 210, 255, 255))
    d.polygon([(18, 8), (24, 3), (40, 3), (46, 8)], fill=(90, 150, 240, 255))   # cabin
    for x in (14, 46):
        d.line([(x, 20), (x, 26)], fill=(200, 200, 210, 255))
        d.ellipse((x - 4, 26, x + 4, 34), fill=(255, 210, 63, 255), outline=(160, 106, 10, 255))  # sphere
        d.ellipse((x - 6, 30, x + 6, 36), fill=(20, 20, 28, 255))                      # tyre
    d.line([(30, 2), (30, 6)], fill=(90, 230, 150, 255))
    d.polygon([(27, 6), (33, 6), (30, 10)], fill=(90, 230, 150, 255))                # level-up arrow
    return up(g, 6)


def runway():
    """Calm airport runway at dusk: sky, runway, centre dashes, approach lights."""
    img = Image.new('RGBA', (W, H), (28, 34, 52, 255)); d = ImageDraw.Draw(img)
    d.rectangle((0, 0, W, 900), fill=(20, 24, 40, 255))
    d.polygon([(380, 900), (700, 900), (1000, H), (80, H)], fill=(58, 60, 70, 255))
    for i in range(8):
        y = 960 + i * 110
        d.rectangle((536, y, 544, y + 50), fill=(235, 235, 240, 255))
    for i in range(7):
        y = 900 + i * 150
        for x in (400, 680):
            d.rectangle((x - 3, y, x + 3, y + 6), fill=(255, 210, 63, 255))
    return img


def main():
    save(Street(seed=3).frame(0, 0), 'bg_road_night.png')
    save(runway(), 'bg_runway_dusk.png')

    save(up(car('black'), 5), 'car_ds_standin.png')
    save(motorcycle(), 'bike_bodyguard.png')
    save(suspension(), 'diagram_suspension.png')

    save(up(guy('shock', 'shock'), 8), 'presenter_shock.png')
    save(up(guy('sad', 'down2'), 8), 'presenter_serious.png')
    save(up(guy('smile', 'talkR'), 8), 'presenter_talk.png')

    save(sparkle(), 'sparkle.png')
    save(star('#ff4a4a'), 'spark_red.png')
    save(tag('TYRES PUNCTURED'), 'tag_caption.png')

    save(Dashboard().frame(0, rpm_deg=225), 'dash_idle.png')


def preview(name):
    """3 preview stills (road with bodyguard, DS levelling, runway arrival) plus a contact sheet in out/<name>/stills/."""
    out = os.path.join(HERE, '..', '..', '..', 'out', name, 'stills'); os.makedirs(out, exist_ok=True)
    A = lambda f: Image.open(os.path.join(ASSETS, f)).convert('RGBA')
    s1 = A('bg_road_night.png'); s1.alpha_composite(A('car_ds_standin.png'), (300, 1180))
    s1.alpha_composite(A('bike_bodyguard.png'), (560, 1260)); s1.alpha_composite(A('presenter_shock.png'), (60, 1000))
    s2 = A('bg_road_night.png'); s2.alpha_composite(A('diagram_suspension.png'), (200, 760)); s2.alpha_composite(A('presenter_talk.png'), (700, 1040))
    s3 = A('bg_runway_dusk.png'); s3.alpha_composite(A('car_ds_standin.png'), (300, 1200)); s3.alpha_composite(A('sparkle.png'), (520, 1000))
    stills = [s1, s2, s3]
    for i, s in enumerate(stills, 1): s.convert('RGB').save(os.path.join(out, f'preview_{i}.png'))
    sheet = Image.new('RGB', (360 * len(stills) + 10 * (len(stills) - 1), 640), (20, 20, 20))
    for i, s in enumerate(stills): sheet.paste(s.convert('RGB').resize((360, 640)), (i * 370, 0))
    sheet.save(os.path.join(out, 'sheet.png'))


if __name__ == '__main__':
    main()
    preview('the-car-that-stayed-level')
