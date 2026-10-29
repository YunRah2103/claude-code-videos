"""Build the rotary-le-mans sprites and backdrop into ../assets/ (PNG, not committed)."""
import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from PIL import Image, ImageDraw
from pixanim.guy import guy
from pixanim.car import car
from pixanim.dash import Dashboard
from pixanim.street import Street

ASSETS = os.path.join(HERE, '..', 'assets')
os.makedirs(ASSETS, exist_ok=True)


def up(img, s):
    return img.resize((img.width * s, img.height * s), Image.NEAREST)


def save(img, name):
    img.convert('RGBA').save(os.path.join(ASSETS, name))


def wankel():
    """Pixel Wankel: oval housing, rounded-triangle rotor, spark plugs. 80x60 grid, upscaled x6."""
    g = Image.new('RGBA', (80, 60), (0, 0, 0, 0)); d = ImageDraw.Draw(g)
    d.ellipse((4, 10, 75, 49), fill=(70, 74, 86, 255), outline=(200, 206, 220, 255))
    d.ellipse((12, 17, 67, 42), fill=(26, 26, 46, 255))
    tri = [(40, 14), (60, 40), (20, 40)]                      # rotor, rounded by the inner ring
    d.polygon(tri, fill=(232, 52, 63, 255), outline=(255, 122, 128, 255))
    d.ellipse((36, 26, 44, 34), fill=(255, 210, 63, 255))     # eccentric shaft
    for x in (12, 68):
        d.rectangle((x, 4, x + 3, 9), fill=(255, 210, 63, 255))  # spark plugs
    return up(g, 6)


def main():
    # backdrop: night track with the Street parallax set
    save(Street(seed=11).frame(0, 0), 'bg_track_night.png')

    # presenter poses (48x60 base, x8)
    save(up(guy('grin', 'pointup'), 8), 'presenter_point.png')
    save(up(guy('happy', 'up2'), 8), 'presenter_cheer.png')
    save(up(guy('shock', 'shock'), 8), 'presenter_shock.png')

    # stand-in for the 787B: generic race colour, no livery text or logos
    save(up(car('red'), 5), 'car_787b_standin.png')

    save(wankel(), 'rotary_wankel.png')

    # dashboard: idle and redline sweeps
    save(Dashboard().frame(0, rpm_deg=225), 'dash_idle.png')
    save(Dashboard().frame(0, rpm_deg=40), 'dash_redline.png')


def preview(name):
    """3 preview stills (track, dash + presenter, wankel) and one contact sheet in out/<name>/stills/."""
    out = os.path.join(HERE, '..', '..', '..', 'out', name, 'stills'); os.makedirs(out, exist_ok=True)
    A = lambda f: Image.open(os.path.join(ASSETS, f)).convert('RGBA')
    bg = A('bg_track_night.png')
    s1 = bg.copy(); s1.alpha_composite(A('car_787b_standin.png'), (315, 1180)); s1.alpha_composite(A('presenter_point.png'), (80, 1000))
    s2 = A('dash_redline.png'); s2.alpha_composite(A('presenter_cheer.png'), (60, 1040))
    s3 = bg.copy(); s3.alpha_composite(A('rotary_wankel.png'), (300, 900)); s3.alpha_composite(A('presenter_shock.png'), (600, 1000))
    stills = [s1, s2, s3]
    for i, s in enumerate(stills, 1): s.convert('RGB').save(os.path.join(out, f'preview_{i}.png'))
    sheet = Image.new('RGB', (360 * len(stills) + 10 * (len(stills) - 1), 640), (20, 20, 20))
    for i, s in enumerate(stills): sheet.paste(s.convert('RGB').resize((360, 640)), (i * 370, 0))
    sheet.save(os.path.join(out, 'sheet.png'))


if __name__ == '__main__':
    main()
    preview('rotary-le-mans')
