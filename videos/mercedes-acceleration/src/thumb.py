"""Thumbnail: the stalled EQE with the EXPIRED HUD, panicking buyer, headline. Usage: python thumb.py OUT.png"""
import sys
import render as r
r.load_mouth(r.VOICE_CACHE)
t = r.T_STOP + .15
img = r.shoot(t)
ov = r.overlays(t).convert('RGBa').resize((r.W, r.H)).convert('RGBA'); img.alpha_composite(ov)
d = r.D(img, k=1)
d.rect(40, 1000, 1040, 1300, (12, 14, 20, 225), r=34)
d.text(540, 1080, 'MERCEDES PAYWALLED', 76, r.TAG, stroke=4, sc=(10, 10, 16))
d.text(540, 1200, '+61 HP: $1,200/YEAR', 84, (255, 255, 255), stroke=4, sc=(10, 10, 16))
img.convert('RGB').save(sys.argv[1])
