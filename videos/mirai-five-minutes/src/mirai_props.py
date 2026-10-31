"""Episode props for the Mirai episode: hydrogen pump and a pixel US map with station dots.

pump(hose, cap) 26x40 grid pump (blue cap = hydrogen, red = petrol); hose=False when the scene draws the hose to the car.
map_base()      100x58 grid lower-48 silhouette (approximate outline), outlined; scale with up(img, S).
DOTS            59 (lat, lon, in_california) station dots: 47 clustered round California metros, 12 spread elsewhere.
                The total and 'most in California' follow the script (2023 count); positions are illustrative.
proj(lon, lat)  map grid coordinates of a point.
"""
import random
from functools import lru_cache
from PIL import Image, ImageDraw
from pixanim.grid import outline

US = [(-124.7, 48.4), (-123.0, 49.0), (-95.2, 49.0), (-95.2, 49.4), (-89.6, 48.0), (-84.5, 46.5), (-82.4, 45.3), (-82.5, 43.0),
      (-79.0, 43.3), (-76.5, 44.2), (-74.7, 45.0), (-71.5, 45.0), (-70.0, 46.7), (-67.8, 47.1), (-67.0, 44.9), (-70.2, 43.6),
      (-70.7, 42.0), (-70.0, 41.7), (-73.9, 40.6), (-74.0, 39.5), (-75.5, 38.8), (-75.9, 37.2), (-76.0, 36.9), (-75.5, 35.2),
      (-78.0, 33.9), (-79.2, 33.2), (-81.0, 32.0), (-81.4, 30.6), (-80.0, 27.0), (-80.4, 25.2), (-81.1, 25.1), (-82.7, 27.5),
      (-82.8, 29.2), (-84.0, 30.0), (-85.4, 29.7), (-88.0, 30.4), (-89.6, 30.2), (-89.4, 29.2), (-91.0, 29.2), (-93.8, 29.7),
      (-96.5, 28.3), (-97.4, 27.0), (-97.2, 25.9), (-99.1, 26.4), (-100.0, 28.0), (-101.4, 29.8), (-102.7, 29.7), (-103.1, 29.0),
      (-104.5, 29.6), (-106.5, 31.8), (-108.2, 31.8), (-108.2, 31.3), (-111.1, 31.3), (-114.8, 32.5), (-117.1, 32.5), (-118.4, 33.8),
      (-120.6, 34.5), (-121.9, 36.6), (-122.5, 37.8), (-123.8, 39.5), (-124.2, 41.9), (-124.5, 43.0), (-124.1, 46.3)]
CA_CITIES = [(34.05, -118.24), (37.77, -122.42), (38.58, -121.49), (32.72, -117.16), (36.74, -119.79), (34.42, -119.7),
             (33.68, -117.83), (37.34, -121.89), (36.6, -121.9), (39.1, -120.9), (40.8, -124.1), (35.37, -119.02)]
OTHER = [(45.5, -122.7), (47.6, -122.3), (39.7, -105.0), (33.4, -112.1), (36.2, -115.1), (34.0, -81.0), (33.7, -84.4),
         (29.8, -95.4), (32.8, -96.8), (40.7, -74.0), (42.4, -71.1), (42.3, -83.0)]


def proj(lon, lat): return ((lon + 125) * 0.79 * 2 + 3, (50 - lat) * 2 + 3)   # 2 cells per degree, cos(38N) squash


def _dots(seed=7):
    rnd = random.Random(seed)
    ca = []
    for _ in range(47):
        lat, lon = rnd.choice(CA_CITIES); ca.append((lat + rnd.uniform(-0.6, 0.6), lon + rnd.uniform(-0.6, 0.6), True))
    dots = ca + [(lat, lon, False) for lat, lon in OTHER]
    rnd.shuffle(dots)          # pop-in order: California fills up while the odd dot lands elsewhere
    return dots


DOTS = _dots()
CA_N = 47


@lru_cache(None)
def map_base():
    m = Image.new('RGBA', (100, 58), (0, 0, 0, 0)); d = ImageDraw.Draw(m)
    d.polygon([proj(*p) for p in US], fill=(70, 78, 96, 255), outline=(170, 180, 200, 255))
    return outline(m, (26, 26, 46, 255))


@lru_cache(None)
def pump(hose=True, cap=(61, 127, 214)):
    img = Image.new('RGBA', (26, 40), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    d.rectangle((2, 36, 23, 39), fill=(120, 126, 140))            # base plate
    d.rectangle((4, 4, 21, 35), fill=(236, 238, 244))             # body
    d.rectangle((4, 4, 21, 7), fill=cap)                          # cap: blue = hydrogen, red = petrol
    d.rectangle((6, 9, 19, 17), fill=(18, 24, 36))                # display
    d.rectangle((7, 11, 18, 15), fill=(110, 240, 150))            # green readout
    d.rectangle((7, 20, 18, 26), fill=(170, 176, 190))            # nozzle holder
    if hose:
        d.line((18, 26, 24, 31, 24, 36), fill=(30, 30, 40), width=2)
        d.rectangle((21, 27, 25, 30), fill=(30, 30, 40))          # nozzle
    return outline(img)
