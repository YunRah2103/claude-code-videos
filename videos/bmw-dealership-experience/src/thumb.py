"""Thumbnail: python thumb.py OUT.png [VOICE]. Buyer's 'A month?!' moment, the 3 Series, big hook text."""
import sys
from PIL import Image
import render as R
R.load_mouth(sys.argv[2] if len(sys.argv) > 2 else R.VOICE_CACHE)
t = R.T_MONTH + .25
R.shot_at = lambda t_: ('M', 0.0)                       # medium two-shot so the car shows
img = R.shoot(t)
ov = Image.new('RGBA', (R.W * R.K, R.H * R.K), (0, 0, 0, 0)); d = R.D(ov)
d.rect(40, 110, 878, 430, (12, 14, 20, 235), r=34)
d.text(R.CX, 200, 'BMW DEALERSHIP', 84, (255, 255, 255), stroke=5, sc=(10, 10, 16))
d.text(R.CX, 330, 'EXPERIENCE', 104, R.TAG, stroke=6, sc=(10, 10, 16))
R.put(ov, R.price_tag('$18/month', 'HEATED SEATS', R.TAG), R.CX + 170, 740, .95, 1.0, rot=-6)
d = R.D(ov)
d.rect(60, 1530, 858, 1690, (12, 14, 20, 235), r=30)
d.text(R.CX, 1612, 'FOR SEATS?!', 104, (255, 255, 255), stroke=7, sc=(16, 16, 28))
ov = ov.convert('RGBa').resize((R.W, R.H), Image.LANCZOS).convert('RGBA')
img.alpha_composite(ov); img.convert('RGB').save(sys.argv[1]); print('ok', sys.argv[1])
