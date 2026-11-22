"""Thumbnail (1080x1920): the store-screen shout ('A YEAR?!') with a bold headline and the real EQE photo.
Usage: python thumb.py VOICE.wav OUT.png"""
import sys
from PIL import Image
import render as R

R.load_mouth(sys.argv[1])
t = R.T_YEAR2 + .25
img = R.shoot(t)
ov = Image.new('RGBA', (R.W * R.K, R.H * R.K), (0, 0, 0, 0)); d = R.D(ov)
R.put(ov, R.photo_card('eqe_front.jpg', 'EQE 350 4MATIC', (18, 20, 26), (255, 255, 255), 420), 790, 1500, 1.0, 1.0, rot=6)
d = R.D(ov)
d.rect(30, 1180, 1050, 1420, (12, 14, 20, 235), r=34)
d.text(540, 1250, '$1,200 A YEAR', 120, R.TAG, stroke=6, sc=(10, 10, 16))
d.text(540, 1360, 'for power it already has', 64, (255, 255, 255), stroke=4, sc=(10, 10, 16))
ov = ov.convert('RGBa').resize((R.W, R.H), Image.LANCZOS).convert('RGBA')
img.alpha_composite(ov)
img.convert('RGB').save(sys.argv[2])
print('ok', sys.argv[2])
