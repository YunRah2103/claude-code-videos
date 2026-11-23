"""Hand-composed YouTube thumbnail for Car Ads vs Reality: big screaming buyer, deadpan salesman pointing at a real car
photo stamped with a giant asterisk, split AD / REALITY background, 3-word title. Usage: python thumb.py OUT.png"""
import math, sys
import numpy as np
from PIL import Image, ImageFilter
import render as r
from render import D, DS, K, W, H, TAG, RED, INK, asterisk, fine_lines, photo, person, sales_extras, POSES, OL

def st_for(lp, rp, **kw):
    s = dict(lpose=list(POSES[lp]), rpose=list(POSES[rp]), mouth=0.0, look=0, dy=0, blink=False,
             out_lpose=lp in r.OUTBEND, out_rpose=rp in r.OUTBEND)
    s.update(kw); return s

def main(out):
    img = Image.new('RGBA', (W * K, H * K)); d = D(img)
    # split background: hot AD side (left) vs cold REALITY side (right), diagonal seam
    img.paste(r.grad(W * K, H * K, (255, 196, 40), (255, 120, 30)), (0, 0))
    right = r.grad(W * K, H * K, (40, 52, 86), (14, 18, 34))
    mask = Image.new('L', (W * K, H * K), 0); __import__('PIL.ImageDraw').ImageDraw.Draw(mask).polygon([(1080 * K, 0), (W * K, 0), (W * K, H * K), (780 * K, H * K)], fill=255)
    img.paste(right, (0, 0), mask); d = D(img)
    for i in range(14):                                          # sunburst on the AD side only
        a = i * math.pi / 7
        d.poly([(420, 560), (420 + 1500 * math.cos(a), 560 + 1500 * math.sin(a)), (420 + 1500 * math.cos(a + .14), 560 + 1500 * math.sin(a + .14))],
               (255, 255, 255, 40))
    img.paste(right, (0, 0), mask); d = D(img)
    d.line([(1080, 0), (780, H)], (255, 255, 255), 14)
    # the real car, as a tilted photo card, stamped with a giant asterisk
    pw, ph = 760, 470
    card = Image.new('RGBA', ((pw + 36) * K, (ph + 36) * K), (255, 255, 255, 255))
    card.paste(photo('charger', pw, ph).crop((0, 0, pw * K, ph * K)), (18 * K, 18 * K))
    cd = D(card); cd.rect(18, ph - 40, pw + 18, ph + 18, (255, 255, 255, 235))
    fine_lines(cd, 30, ph - 34, pw + 6, ph + 12, 230, 11, 4)
    sh = Image.new('RGBA', card.size, (0, 0, 0, 120)).filter(ImageFilter.GaussianBlur(12))
    for im, off in ((sh, 18), (card, 0)):
        rot = im.rotate(5, resample=Image.BICUBIC, expand=True)
        img.alpha_composite(rot, (int((960 + off) * K - rot.width / 2), int((560 + off) * K - rot.height / 2)))
    d = D(img)
    asterisk(d, 1290, 330, 170, 0.4, rot=.25)                   # the asterisk with a face, peeking over the card
    # cast, big: screaming buyer left, deadpan salesman right
    buyer = st_for('up', 'up', mouth=1.0, brows='angry', eyes='wide', look=1)
    ds = DS(img, 1.32, 330, 440 + 905 * 1.32); person(ds, 0, 0, r.BUYER, buyer)
    sales = st_for('offer', 'clasp', brows='flat', look=-1)
    ds = DS(img, 1.18, 1650, 470 + 905 * 1.18); person(ds, 0, 0, r.SALES, sales); sales_extras(ds, 0, 0, sales)
    d = D(img)
    hx, hy = 330, 440                               # shock lines around the buyer's head
    for a_ in (-2.7, -2.3, -0.85, -0.45):
        d.line([(hx + 135 * math.cos(a_), hy + 135 * math.sin(a_)), (hx + 185 * math.cos(a_), hy + 185 * math.sin(a_))], INK, 12)
    # title: three words, huge, with a heavy outline
    d.text(560, 110, 'CAR ADS', 150, (255, 255, 255), stroke=16, sc=INK)
    d.rect(1180, 30, 1880, 190, RED, r=26, ol=(255, 255, 255), w=8)
    d.text(1530, 112, 'vs REALITY', 112, (255, 255, 255), stroke=8, sc=INK)
    # a red arrow from the asterisk to the fine print strip
    d.rect(1220, 880, 1880, 1040, (255, 255, 255), r=24, ol=INK, w=8)
    d.text(1550, 960, '*READ THIS', 92, INK)
    img = img.resize((W, H), Image.LANCZOS).convert('RGB')
    img.save(out, optimize=True)
    img.resize((1280, 720), Image.LANCZOS).save(out.replace('.png', '_1280.png'), optimize=True)

if __name__ == '__main__':
    main(sys.argv[1])
