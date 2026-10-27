"""Generates the base explainer character sprite (front view, 36x60 grid)."""
import sys
from PIL import Image

W, H = 36, 60
OUT = (26, 26, 46, 255)
P = {
 'hair': '#231a1c', 'hairhi': '#4f3d42',
 'skin': '#c08862', 'skinsh': '#a06b4b', 'blush': '#d4917a',
 'mouth': '#6e2f33', 'eye': '#12121c', 'white': '#ffffff',
 'frame': '#a9b0bb', 'framehi': '#d3d8e0', 'framesh': '#7b8491',
 'tee': '#f7f7fa', 'teesh': '#d6d9e2',
 'jeans': '#2b2d33', 'jeansh': '#1f2025', 'jeanhi': '#454852', 'waist': '#16171b',
 'shoe': '#f4f4f6', 'shoesh': '#cfd2da', 'sole': '#b9bcc6',
}
def rgba(h): h = h.lstrip('#'); return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (255,)

g = [[None]*W for _ in range(H)]
def px(x, y, c):
    if 0 <= x < W and 0 <= y < H: g[y][x] = rgba(P[c]) if c else None
def rect(x0, y0, x1, y1, c):
    for y in range(y0, y1+1):
        for x in range(x0, x1+1): px(x, y, c)

# ---- hair + head
rect(14, 0, 14, 1, 'hair'); rect(18, 0, 18, 1, 'hair')
rect(8, 2, 27, 12, 'hair')
rect(12, 3, 17, 4, 'hairhi'); rect(20, 3, 24, 3, 'hairhi')
rect(9, 13, 9, 14, 'hair'); rect(26, 13, 26, 14, 'hair')   # sideburns
rect(9, 9, 26, 25, 'skin')
rect(9, 9, 26, 10, 'hair')                                   # fringe
rect(13, 9, 18, 11, 'skin')                                  # forehead notch
rect(10, 11, 12, 11, 'hair'); rect(20, 10, 25, 11, 'hair')
rect(9, 11, 9, 12, 'hair'); rect(26, 11, 26, 12, 'hair')
rect(8, 13, 8, 14, 'hair'); rect(27, 13, 27, 14, 'hair')
# chin taper
for x in (9, 26): px(x, 25, None)
for x in (9, 26): px(x, 24, 'skin')
# ears
rect(7, 14, 8, 19, 'skin'); rect(27, 14, 28, 19, 'skin')
rect(9, 14, 9, 20, 'skinsh'); rect(26, 14, 26, 20, 'skinsh')
# eyebrows
rect(11, 12, 15, 12, 'hair'); rect(20, 12, 24, 12, 'hair')
# ---- silver glasses
for (x0, x1) in ((10, 16), (19, 25)):
    rect(x0, 13, x1, 19, 'frame')
    rect(x0+1, 14, x1-1, 18, 'skin')
    rect(x0, 13, x1, 13, 'framehi')            # top highlight
    rect(x0, 19, x1, 19, 'framesh')            # bottom shade
rect(17, 14, 18, 14, 'frame')                  # bridge
rect(9, 14, 9, 15, 'frame'); rect(26, 14, 26, 15, 'frame')  # arms to ears
# eyes (looking down-right, white glint)
for ex in (12, 21):
    rect(ex+1, 15, ex+2, 16, 'eye')
    px(ex, 15, 'white'); px(ex, 16, 'skin'); px(ex+1, 15, 'white')
# nose, cheeks, mouth
rect(17, 20, 18, 21, 'skinsh')
rect(11, 21, 12, 21, 'blush'); rect(23, 21, 24, 21, 'blush')
px(14, 22, 'mouth'); px(21, 22, 'mouth'); rect(15, 23, 20, 23, 'mouth')

# ---- neck + tee
rect(15, 26, 20, 29, 'skinsh')
rect(8, 28, 27, 31, 'tee')
rect(11, 28, 24, 43, 'tee')
rect(15, 28, 20, 29, 'skinsh'); rect(16, 30, 19, 30, 'skinsh')
rect(14, 28, 14, 29, 'teesh'); rect(21, 28, 21, 29, 'teesh'); rect(15, 30, 15, 30, 'teesh'); rect(20, 30, 20, 30, 'teesh')
rect(14, 31, 21, 31, 'teesh')
rect(8, 32, 10, 34, 'tee'); rect(25, 32, 27, 34, 'tee')           # sleeves
rect(8, 34, 10, 34, 'teesh'); rect(25, 34, 27, 34, 'teesh')       # sleeve hem
rect(11, 40, 14, 40, 'teesh'); rect(22, 38, 24, 38, 'teesh')      # fold lines
rect(11, 34, 11, 43, 'teesh'); rect(24, 34, 24, 43, 'teesh')      # side shade
# arms
rect(8, 35, 10, 42, 'skin'); rect(25, 35, 27, 42, 'skin')
rect(8, 35, 8, 41, 'skinsh'); rect(27, 35, 27, 41, 'skinsh')
rect(7, 41, 10, 44, 'skin'); rect(25, 41, 28, 44, 'skin')         # hands

# ---- baggy jeans
rect(10, 44, 25, 47, 'jeans')
rect(10, 44, 25, 44, 'waist')
rect(9, 48, 26, 53, 'jeans')
rect(8, 54, 27, 54, 'jeans')
px(17, 48, None); rect(17, 49, 18, 54, None)                       # leg gap
px(18, 48, None)
# folds / shading
rect(10, 45, 10, 53, 'jeansh'); rect(25, 45, 25, 53, 'jeansh')
rect(16, 45, 16, 53, 'jeansh'); rect(19, 45, 19, 53, 'jeansh')
rect(12, 46, 13, 46, 'jeanhi'); rect(22, 46, 23, 46, 'jeanhi')
rect(13, 49, 13, 52, 'jeanhi'); rect(22, 49, 22, 52, 'jeanhi')
rect(9, 53, 15, 53, 'jeansh'); rect(20, 53, 26, 53, 'jeansh')       # ankle bunching
rect(11, 50, 12, 50, 'jeansh'); rect(23, 50, 24, 50, 'jeansh')
rect(11, 45, 11, 45, 'waist'); rect(24, 45, 24, 45, 'waist')       # belt loops

# ---- white sneakers
for (x0, x1) in ((8, 16), (19, 27)):
    rect(x0, 55, x1, 57, 'shoe')
    rect(x0, 57, x1, 57, 'shoesh')
    rect(x0, 58, x1, 58, 'sole')
    rect(x0+1, 55, x0+3, 55, 'shoesh')

# ---- auto outline
src = [row[:] for row in g]
for y in range(H):
    for x in range(W):
        if src[y][x] is None:
            for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                nx, ny = x+dx, y+dy
                if 0 <= nx < W and 0 <= ny < H and src[ny][nx] is not None:
                    g[y][x] = OUT; break

img = Image.new('RGBA', (W, H), (0, 0, 0, 0))
for y in range(H):
    for x in range(W):
        if g[y][x]: img.putpixel((x, y), g[y][x])
out = sys.argv[1]
img.save(f'{out}/sprite_1x.png')
img.resize((W*16, H*16), Image.NEAREST).save(f'{out}/sprite_16x.png')
bg = Image.new('RGBA', (W*16, H*16), (255, 255, 255, 255))
bg.alpha_composite(img.resize((W*16, H*16), Image.NEAREST))
bg.convert('RGB').save(f'{out}/preview.png')
