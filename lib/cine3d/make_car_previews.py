"""Render the reusable car models into lib/cine3d/previews/cars.png.  python lib/cine3d/make_car_previews.py"""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
from PIL import Image, ImageDraw, ImageFont
from geo import Cam, tiles
from render3d import render, Env
import cars3d as C
OUT = os.path.join(HERE, "previews"); os.makedirs(OUT, exist_ok=True)
ENV = Env(sky_top=(150, 175, 215), sky_hor=(236, 236, 242), ground=(150, 150, 160), sun_dir=(-0.5, 0.7, 0.55), sun_i=1.9, amb_i=1.0, fog=None,
          exposure=0.95, bloom=0.4, sun_disc=False, sat=1.05, shadow_size=8, shadow_center=(0, 0, 0))
FLOOR = tiles(-8, -8, 8, 8, 0, 2.0, -1, (200, 200, 208))
CARS = [("Hyundai Ioniq 5 N  ioniq5n()", C.ioniq5n()), ("Chevrolet Blazer EV  blazer_ev()", C.blazer_ev()), ("Jeep Wrangler JL  wrangler()", C.wrangler()),
        ("Willys MB 1941  willys()", C.willys()), ("Tesla Model 3  model3()", C.model3())]
F = ImageFont.truetype("/usr/share/fonts/opentype/inter/Inter-Bold.otf", 26)
ims = [Image.fromarray(render([FLOOR, car], Cam((8.6, 2.6, 9.6), (0, 0.85, 0), 30), ENV)).resize((405, 720), Image.LANCZOS) for _, car in CARS]
s = Image.new("RGB", (405 * len(ims), 764), (250, 250, 252)); d = ImageDraw.Draw(s)
for i, (im, (lab, _)) in enumerate(zip(ims, CARS)):
    s.paste(im, (i * 405, 0)); d.text((i * 405 + 202, 742), lab, font=F, fill=(30, 30, 40), anchor="mm")
s.save(os.path.join(OUT, "cars.png")); print("wrote", os.path.join(OUT, "cars.png"))
