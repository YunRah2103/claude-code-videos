"""Build the the-mascot-with-a-secret sprites and backdrops into ../assets/ (PNG, not committed)."""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from PIL import Image, ImageDraw
from pixanim.guy import guy
from pixanim.car import car
from backdrops.garage import Garage
from pixanim.sprites import tag, sparkle
from pixanim.street import Street

ASSETS = os.path.join(HERE, '..', 'assets')
os.makedirs(ASSETS, exist_ok=True)
W, H = 1080, 1920


def up(img, s):
    return img.resize((img.width * s, img.height * s), Image.NEAREST)


def save(img, name):
    img.convert('RGBA').save(os.path.join(ASSETS, name))


def mascot():
    """Pixel Spirit of Ecstasy: head, flowing dress, outstretched wings. 16x26 grid, x6. Generic figure only."""
    g = Image.new('RGBA', (16, 26), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    silver, shade = (214, 220, 230, 255), (120, 128, 142, 255)
    d.polygon([(8, 9), (3, 24), (13, 24)], fill=silver, outline=shade)           # dress
    d.polygon([(8, 10), (0, 3), (3, 13)], fill=silver, outline=shade)            # wing
    d.polygon([(8, 10), (16, 3), (13, 13)], fill=silver, outline=shade)          # wing
    d.ellipse((5, 2, 11, 8), fill=silver, outline=shade)                         # head
    d.rectangle((3, 24, 13, 25), fill=shade)                                     # base
    return up(g, 6)


def ship():
    """Torpedoed passenger ship, side view: 60x20 grid, x6."""
    g = Image.new('RGBA', (60, 20), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    d.polygon([(4, 12), (56, 12), (50, 19), (10, 19)], fill=(40, 44, 58, 255), outline=(150, 156, 170, 255))
    d.rectangle((14, 6, 38, 12), fill=(210, 214, 224, 255))
    for x in range(18, 38, 4):
        d.rectangle((x, 8, x + 1, 9), fill=(40, 44, 58, 255))
    d.rectangle((30, 2, 33, 6), fill=(190, 190, 200, 255))
    return up(g, 6)


def torpedo_streak():
    """Thin white wake with a fading tail, 90x6 grid, x6."""
    g = Image.new('RGBA', (90, 6), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    for x in range(90):
        a = int(255 * x / 89)
        d.point((x, 3), fill=(235, 240, 255, a))
    return up(g, 6)


def calendar():
    """1911 calendar page: red binder band, white grid, page tag. 40x30 grid, x6."""
    g = Image.new('RGBA', (40, 30), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    d.rectangle((0, 0, 39, 29), fill=(250, 246, 236, 255), outline=(60, 60, 70, 255))
    d.rectangle((0, 0, 39, 6), fill=(214, 48, 58, 255))
    for r in range(3):
        for c in range(6):
            d.rectangle((3 + c * 6, 10 + r * 6, 5 + c * 6, 12 + r * 6), fill=(190, 194, 204, 255))
    return up(g, 6)


def main():
    save(Garage(W, H, 1180, 9).frame(0), 'bg_workshop.png')
    save(up(car('silver'), 6), 'car_bonnet_standin.png')
    save(mascot(), 'mascot_spirit.png')
    save(ship(), 'ship_torpedoed.png')
    save(torpedo_streak(), 'torpedo_streak.png')
    save(calendar(), 'calendar_1911.png')
    save(tag('SINCE 1911'), 'tag_since_1911.png')
    save(tag('THE COMPANY SAYS'), 'tag_company_says.png')   # on-screen brand names are not allowed; see report
    save(sparkle(), 'sparkle.png')
    save(up(guy('think', 'point'), 8), 'presenter_study.png')
    save(up(guy('smirk', 'pointup'), 8), 'presenter_point.png')
    save(up(guy('sad', 'down'), 8), 'presenter_sad.png')


def preview(name):
    """3 preview stills (workshop study, bonnet in rain, ship at night) and a contact sheet in out/<name>/stills/."""
    out = os.path.join(HERE, '..', '..', '..', 'out', name, 'stills'); os.makedirs(out, exist_ok=True)
    A = lambda f: Image.open(os.path.join(ASSETS, f)).convert('RGBA')
    s1 = A('bg_workshop.png'); s1.alpha_composite(A('presenter_study.png'), (560, 1000))
    s1.alpha_composite(A('tag_since_1911.png'), (60, 480))
    s2 = A('bg_workshop.png'); s2.alpha_composite(A('car_bonnet_standin.png'), (200, 1180))
    s2.alpha_composite(A('mascot_spirit.png'), (420, 880)); s2.alpha_composite(A('sparkle.png'), (420, 760))
    s3 = Street(seed=5).frame(0, 0); s3.alpha_composite(A('ship_torpedoed.png'), (200, 1150)); s3.alpha_composite(A('torpedo_streak.png'), (120, 1210))
    stills = [s1, s2, s3]
    for i, s in enumerate(stills, 1): s.convert('RGB').save(os.path.join(out, f'preview_{i}.png'))
    sheet = Image.new('RGB', (360 * len(stills) + 10 * (len(stills) - 1), 640), (20, 20, 20))
    for i, s in enumerate(stills): sheet.paste(s.convert('RGB').resize((360, 640)), (i * 370, 0))
    sheet.save(os.path.join(out, 'sheet.png'))


if __name__ == '__main__':
    main()
    preview('the-mascot-with-a-secret')
