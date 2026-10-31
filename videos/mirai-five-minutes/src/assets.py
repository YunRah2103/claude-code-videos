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
from pixanim.grid import up, outline

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

# 4. fuel pump (26x40 grid) with a five-minute timer
def pump():
    img = Image.new('RGBA', (26, 40), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((2, 36, 23, 39), fill=(120, 126, 140))            # base plate
    d.rectangle((4, 4, 21, 35), fill=(236, 238, 244))             # body
    d.rectangle((4, 4, 21, 7), fill=(61, 127, 214))               # blue cap, hydrogen livery
    d.rectangle((6, 9, 19, 17), fill=(18, 24, 36))                # display
    d.rectangle((7, 11, 18, 15), fill=(110, 240, 150))            # green readout bar (5:00 countdown)
    d.rectangle((7, 20, 18, 26), fill=(170, 176, 190))            # nozzle holder
    d.line((18, 26, 24, 31, 24, 36), fill=(30, 30, 40), width=2)  # hose
    d.rectangle((21, 27, 25, 30), fill=(30, 30, 40))              # nozzle
    return outline(img)
save(up(pump(), S), 'pump.png')

# five-minute timer: stopwatch sprite at four points of the five minutes (1, 2, 3, 5 minutes)
for m in (1, 2, 3, 5):
    save(up(stopwatch(m / 5.0), S), f'timer_{m}min.png')

# 5. US map (lower 48, approximate outline) with 59 station dots, California clustered
US = [(-124.7,48.4),(-123.0,49.0),(-95.2,49.0),(-95.2,49.4),(-89.6,48.0),(-84.5,46.5),(-82.4,45.3),(-82.5,43.0),
      (-79.0,43.3),(-76.5,44.2),(-74.7,45.0),(-71.5,45.0),(-70.0,46.7),(-67.8,47.1),(-67.0,44.9),(-70.2,43.6),
      (-70.7,42.0),(-70.0,41.7),(-73.9,40.6),(-74.0,39.5),(-75.5,38.8),(-75.9,37.2),(-76.0,36.9),(-75.5,35.2),
      (-78.0,33.9),(-79.2,33.2),(-81.0,32.0),(-81.4,30.6),(-80.0,27.0),(-80.4,25.2),(-81.1,25.1),(-82.7,27.5),
      (-82.8,29.2),(-84.0,30.0),(-85.4,29.7),(-88.0,30.4),(-89.6,30.2),(-89.4,29.2),(-91.0,29.2),(-93.8,29.7),
      (-96.5,28.3),(-97.4,27.0),(-97.2,25.9),(-99.1,26.4),(-100.0,28.0),(-101.4,29.8),(-102.7,29.7),(-103.1,29.0),
      (-104.5,29.6),(-106.5,31.8),(-108.2,31.8),(-108.2,31.3),(-111.1,31.3),(-114.8,32.5),(-117.1,32.5),(-118.4,33.8),
      (-120.6,34.5),(-121.9,36.6),(-122.5,37.8),(-123.8,39.5),(-124.2,41.9),(-124.5,43.0),(-124.1,46.3)]
def proj(lon, lat): return ((lon + 125) * 0.79 * 2 + 3, (50 - lat) * 2 + 3)   # 2 cells per degree, cos(38N) squash
def map_art(seed=7):
    rnd = random.Random(seed)
    m = Image.new('RGBA', (100, 58), (0, 0, 0, 0)); d = ImageDraw.Draw(m)
    d.polygon([proj(*p) for p in US], fill=(70, 78, 96, 255), outline=(170, 180, 200, 255))
    m = outline(m, (26, 26, 46, 255))
    cities = {'CA': [(34.05,-118.24),(37.77,-122.42),(38.58,-121.49),(32.72,-117.16),(36.74,-119.79),(34.42,-119.7),
                     (33.68,-117.83),(37.34,-121.89),(36.6,-121.9),(39.1,-120.9),(40.8,-124.1),(35.37,-119.02)],
              'other': [(45.5,-122.7),(47.6,-122.3),(39.7,-105.0),(33.4,-112.1),(36.2,-115.1),(34.0,-81.0),(33.7,-84.4),
                        (29.8,-95.4),(32.8,-96.8),(40.7,-74.0),(42.4,-71.1),(42.3,-83.0)]}
    dots = []
    for i in range(47):   # 47 CA dots, clustered around the metro areas
        lat, lon = rnd.choice(cities['CA']); dots.append((lat + rnd.uniform(-0.6, 0.6), lon + rnd.uniform(-0.6, 0.6)))
    dots += [(lat, lon) for lat, lon in cities['other']]   # 12 spread across the rest
    return m, dots   # 59 dots total (illustrative positions; count and 'most in California' from the brief)
m, dots = map_art()
big = m.resize((m.width * S, m.height * S), Image.NEAREST)
dd = ImageDraw.Draw(big)
for lat, lon in dots:
    x, y = proj(lon, lat); x, y = x * S, y * S
    col = (255, 77, 109, 255) if 0 < x < 1000 and lon < -114 else (255, 210, 63, 255)
    dd.ellipse((x - 9, y - 9, x + 9, y + 9), fill=(26, 26, 46, 255)); dd.ellipse((x - 7, y - 7, x + 7, y + 7), fill=col)
save(big, 'map_us.png')
print('dots', len(dots), 'CA-region', sum(1 for la, lo in dots if lo < -114 and la > 32 and lo > -125))

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
