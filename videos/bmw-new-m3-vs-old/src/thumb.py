"""Thumbnail (1080x1920 PNG): OLD M3 vs NEW M3, both real cars, buyer shouting, salesman deadpan.
Usage: python thumb.py OUT.png"""
import sys
from PIL import Image, ImageFilter
import render as R
from render import D, K, W, H, CX

img = R.bg_showroom().copy()
d = D(img)
d.rect(0, 0, W, 520, R.NAVY + (150,))                           # darken the top for the title
R.burst(d, 300, 1180, .15)                                       # shout burst behind the buyer
# two cars side by side, facing each other's way into the VS
for key, x, flip in (('e46', 275, False), ('g80', 805, False)):
    car = R.car_img(key)
    car = car.resize((int(car.width * .66), int(car.height * .66)), Image.LANCZOS)
    if flip: car = car.transpose(Image.FLIP_LEFT_RIGHT)
    gy = 860
    sh = Image.new('RGBA', img.size, (0, 0, 0, 0)); D(sh).ell(x, gy - 2, car.width / K * .48, 12, (0, 0, 0, 170))
    img.alpha_composite(sh.filter(ImageFilter.GaussianBlur(5 * K)))
    img.alpha_composite(car, (int(x * K - car.width / 2), int(gy * K - car.height + 3 * K)))
    pl = R.plaque(key)
    pl = pl.resize((int(pl.width * .85), int(pl.height * .85)), Image.LANCZOS)
    img.alpha_composite(pl, (int(x * K - pl.width / 2), int((gy - car.height / K - 70) * K - pl.height / 2)))
d = D(img)
d.ell(540, 770, 66, 66, (228, 30, 38), (255, 255, 255), 8)  # VS roundel between the cars
d.text(540, 772, 'VS', 58, (255, 255, 255), stroke=3, sc=(20, 10, 10))
# title
d.text(W / 2, 170, 'OLD M3', 170, (255, 214, 64), stroke=14, sc=(10, 10, 20))
d.text(W / 2, 360, 'or NEW M3?', 132, (255, 255, 255), stroke=12, sc=(10, 10, 20))
# characters, close and big
st = dict(lpose=R.POSES['up'], rpose=R.POSES['up'], mouth=0.9, look=1, brows='angry', eyes='wide', sweat=0.4, dy=0)
R.person(d, 300, 2230, R.BUYER, st)
st = dict(lpose=R.POSES['clasp'], rpose=R.POSES['clasp'], mouth=0.0, look=-1, brows='flat', dy=0)
R.person(d, 800, 2230, R.SALES, st)
d.rect(80, 1560, 1000, 1700, (255, 255, 255), r=28, ol=(10, 10, 20), w=8)
d.text(W / 2, 1632, 'NUMBERS vs FEELING', 78, R.NAVY)
img.convert('RGB').resize((W, H), Image.LANCZOS).save(sys.argv[1])
print('ok', sys.argv[1])
