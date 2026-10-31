"""Stage 2 pixel assets for the Mirai episode -> out/mirai-five-minutes/assets/ (not committed).

Garage backdrop, presenter poses, a pixel Mirai (generic EV saloon from pixanim.autos), a fuel pump with a
five-minute stopwatch, a US map with station dots (California clustered), a dashboard frame and preview stills.
Run:  python videos/mirai-five-minutes/src/assets.py
"""
import math, os, sys, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', '..', 'shared'))
from PIL import Image, ImageDraw
from backdrops.garage import Garage
from pixanim.guy import guy
from pixanim.autos import ev
from pixanim.props import stopwatch
from pixanim.dash import Dashboard
from pixanim.fx import contact_shadow
from pixanim.grid import up
from mirai_props import pump, map_base, DOTS, proj

W, H, GROUND, S = 1080, 1920, 1180, 9
OUT = os.path.join(HERE, '..', '..', '..', 'out', 'mirai-five-minutes', 'assets')
os.makedirs(OUT, exist_ok=True)
save = lambda img, name: (img.save(os.path.join(OUT, name)), print(name, img.size))

# 1. garage backdrop (no foreground)
GAR = Garage(W, H, GROUND, S)
save(GAR.frame(0).convert('RGB'), 'garage.png')

# 2. presenter poses (48x60 rig, x9)
POSES = {'point': ('smile', 'point', 'stand'), 'cheer': ('grin', 'cheer1', 'stand'), 'shrug': ('smirk', 'shrug', 'stand'),
         'think': ('think', 'think', 'stand'), 'present': ('talk', 'present', 'stand'), 'wow': ('wow', 'up1', 'stand')}
for k, (ex, arms, legs) in POSES.items():
    save(up(guy(ex, arms, legs), S), f'pose_{k}.png')

# 3. pixel Mirai: generic electric saloon (no badges, no logos)
MIRAI = up(ev('air'), S)
save(MIRAI, 'mirai.png')

# 4. fuel pump with a five-minute timer
save(up(pump(), S), 'pump.png')

# five-minute timer: stopwatch sprite at four points of the five minutes (1, 2, 3, 5 minutes)
for m in (1, 2, 3, 5):
    save(up(stopwatch(m / 5.0), S), f'timer_{m}min.png')

# 5. US map (lower 48, approximate outline) with 59 station dots, California clustered
m, dots = map_base(), DOTS
big = m.resize((m.width * S, m.height * S), Image.NEAREST)
dd = ImageDraw.Draw(big)
for lat, lon, ca in dots:
    x, y = proj(lon, lat); x, y = x * S, y * S
    col = (255, 77, 109, 255) if ca else (255, 210, 63, 255)
    dd.ellipse((x - 9, y - 9, x + 9, y + 9), fill=(26, 26, 46, 255)); dd.ellipse((x - 7, y - 7, x + 7, y + 7), fill=col)
save(big, 'map_us.png')
print('dots', len(dots), 'california', sum(1 for d in dots if d[2]))

# 6. dashboard frame (car interior close-up, rev counter + speedometer)
dash = Dashboard().frame(0)
save(dash.convert('RGBA') if dash.mode != 'RGBA' else dash, 'dash.png')

# 7. preview stills (garage + sprite), checked by eye
def still(name, parts):
    img = GAR.frame(0).convert('RGBA')
    for im, cx, gy in parts:
        contact_shadow(img, cx, gy, im.width, k=1.0, s=S)
        img.paste(im, (int(cx - im.width / 2), int(gy - im.height)), im)
    img = GAR.rim(img); 
    save(img.convert('RGB'), name)
still('preview_1_car_point.png', [(MIRAI, 400, GROUND), (up(guy('smile', 'point', 'stand'), S), 880, GROUND)])
still('preview_2_pump_timer.png', [(up(pump(), S), 300, GROUND), (up(stopwatch(0.6), S), 800, GROUND - 400)])
still('preview_3_map.png', [(big, 540, 1100)])
still('preview_4_dash.png', [(dash.convert('RGBA'), 540, 1920)])
