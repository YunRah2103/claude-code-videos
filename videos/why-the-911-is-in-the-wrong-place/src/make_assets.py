"""Build the why-the-911-is-in-the-wrong-place sprites and backdrops into ../assets/ (PNG, not committed)."""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from PIL import Image
from pixanim.guy import guy
from pixanim.car import car
from pixanim.engine import Engine
from pixanim.street import Street
from pixanim.sprites import tag, snowflake, sparkle

ASSETS = os.path.join(HERE, '..', 'assets')
os.makedirs(ASSETS, exist_ok=True)


def up(img, s):
    return img.resize((img.width * s, img.height * s), Image.NEAREST)


def save(img, name):
    img.convert('RGBA').save(os.path.join(ASSETS, name))


def main():
    save(Street(seed=7).frame(0, 0), 'bg_winter_street.png')       # night street; snow is added in the scene
    save(up(car('silver'), 6), 'car_911_standin.png')              # generic body; not a 911 silhouette
    save(Engine().frame(0), 'engine_cutaway.png')

    # eight generation stand-ins, one per tile, in a row of generic colours
    palette = ['silver', 'red', 'blue', 'yellow', 'used', 'black', 'silver', 'red']
    for i, c in enumerate(palette, 1):
        save(up(car(c), 3), f'car_gen_{i}.png')
        save(tag(f'GEN {i}'), f'tag_gen_{i}.png')

    save(snowflake(), 'snowflake.png')
    save(sparkle(), 'sparkle.png')
    save(up(guy('grin', 'up2'), 8), 'presenter_punch.png')
    save(up(guy('happy', 'up1'), 8), 'presenter_cheer.png')
    save(tag('WRONG PLACE, ON PURPOSE'), 'tag_caption.png')


def preview(name):
    """3 preview stills (911 on snowy road, engine cutaway, eight generations) and a contact sheet in out/<name>/stills/."""
    out = os.path.join(HERE, '..', '..', '..', 'out', name, 'stills'); os.makedirs(out, exist_ok=True)
    A = lambda f: Image.open(os.path.join(ASSETS, f)).convert('RGBA')
    s1 = A('bg_winter_street.png'); s1.alpha_composite(A('car_911_standin.png'), (300, 1180)); s1.alpha_composite(A('presenter_punch.png'), (620, 1000)); s1.alpha_composite(A('sparkle.png'), (700, 760))
    s2 = A('bg_winter_street.png'); s2.alpha_composite(A('engine_cutaway.png'), (0, 0)); s2.alpha_composite(A('presenter_cheer.png'), (60, 1000))
    s3 = A('bg_winter_street.png')
    for i in range(8):
        x = 20 + i * 130
        s3.alpha_composite(A(f'car_gen_{i + 1}.png'), (x, 1150)); s3.alpha_composite(A(f'tag_gen_{i + 1}.png'), (x, 1000))
    stills = [s1, s2, s3]
    for i, s in enumerate(stills, 1): s.convert('RGB').save(os.path.join(out, f'preview_{i}.png'))
    sheet = Image.new('RGB', (360 * len(stills) + 10 * (len(stills) - 1), 640), (20, 20, 20))
    for i, s in enumerate(stills): sheet.paste(s.convert('RGB').resize((360, 640)), (i * 370, 0))
    sheet.save(os.path.join(out, 'sheet.png'))


if __name__ == '__main__':
    main()
    preview('why-the-911-is-in-the-wrong-place')
