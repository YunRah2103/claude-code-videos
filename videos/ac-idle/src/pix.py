"""Pixel-art asset builders for the fuel myth explainer video."""
from functools import lru_cache
from PIL import Image

OUT = (26, 26, 46, 255)

def hexc(h):
    h = h.lstrip('#')
    return tuple(int(h[i:i+2], 16) for i in (0, 2, 4)) + (255,)

FONT = {
 '0': ["01110","10001","10011","10101","11001","10001","01110"],
 '1': ["00100","01100","00100","00100","00100","00100","01110"],
 '2': ["01110","10001","00001","00010","00100","01000","11111"],
 '3': ["11110","00001","00001","01110","00001","00001","11110"],
 '4': ["00010","00110","01010","10010","11111","00010","00010"],
 '5': ["11111","10000","11110","00001","00001","10001","01110"],
 '6': ["00110","01000","10000","11110","10001","10001","01110"],
 '7': ["11111","00001","00010","00100","01000","01000","01000"],
 '8': ["01110","10001","10001","01110","10001","10001","01110"],
 '9': ["01110","10001","10001","01111","00001","00010","01100"],
 '$': ["00100","01111","10100","01110","00101","11110","00100"],
 ',': ["00","00","00","00","00","01","10"],
 '.': ["0","0","0","0","0","0","1"],
 '-': ["000","000","000","111","000","000","000"],
 '+': ["00000","00100","00100","11111","00100","00100","00000"],
 '%': ["11001","11010","00010","00100","01000","01011","10011"],
 '?': ["01110","10001","00001","00010","00100","00000","00100"],
 '!': ["1","1","1","1","1","0","1"],
 ' ': ["000"]*7,
 'A': ["01110","10001","10001","11111","10001","10001","10001"],
 'B': ["11110","10001","10001","11110","10001","10001","11110"],
 'C': ["01110","10001","10000","10000","10000","10001","01110"],
 'D': ["11110","10001","10001","10001","10001","10001","11110"],
 'E': ["11111","10000","10000","11110","10000","10000","11111"],
 'F': ["11111","10000","10000","11110","10000","10000","10000"],
 'G': ["01110","10001","10000","10111","10001","10001","01111"],
 'H': ["10001","10001","10001","11111","10001","10001","10001"],
 'I': ["111","010","010","010","010","010","111"],
 'K': ["10001","10010","10100","11000","10100","10010","10001"],
 'L': ["10000"]*6 + ["11111"],
 'M': ["10001","11011","10101","10101","10001","10001","10001"],
 'N': ["10001","11001","10101","10011","10001","10001","10001"],
 'O': ["01110","10001","10001","10001","10001","10001","01110"],
 'P': ["11110","10001","10001","11110","10000","10000","10000"],
 'R': ["11110","10001","10001","11110","10100","10010","10001"],
 'S': ["01111","10000","10000","01110","00001","00001","11110"],
 'T': ["11111"] + ["00100"]*6,
 'U': ["10001"]*6 + ["01110"],
 'V': ["10001","10001","10001","10001","10001","01010","00100"],
 'W': ["10001","10001","10001","10101","10101","10101","01010"],
 'X': ["10001","10001","01010","00100","01010","10001","10001"],
 'Z': ["11111","00001","00010","00100","01000","10000","11111"],
 'Y': ["10001","10001","01010","00100","00100","00100","00100"],
}

def text_width(s):
    return sum(len(FONT[c][0]) for c in s) + len(s) - 1


class Grid:
    def __init__(self, w, h):
        self.w, self.h = w, h
        self.g = [[None]*w for _ in range(h)]

    def px(self, x, y, c):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.g[y][x] = hexc(c) if c else None

    def rect(self, x0, y0, x1, y1, c):
        for y in range(y0, y1+1):
            for x in range(x0, x1+1):
                self.px(x, y, c)

    def disc(self, cx, cy, r, c):
        for y in range(int(cy-r)-1, int(cy+r)+2):
            for x in range(int(cx-r)-1, int(cx+r)+2):
                if (x-cx)**2 + (y-cy)**2 <= r*r + 0.5:
                    self.px(x, y, c)

    def text(self, x, y, s, c):
        for ch in s:
            rows = FONT[ch]
            for j, row in enumerate(rows):
                for i, b in enumerate(row):
                    if b == '1':
                        self.px(x+i, y+j, c)
            x += len(rows[0]) + 1

    def image(self, outline=True, oc=OUT):
        g = self.g
        if outline:
            src = [row[:] for row in g]
            g = [row[:] for row in g]
            for y in range(self.h):
                for x in range(self.w):
                    if src[y][x] is None:
                        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                            nx, ny = x+dx, y+dy
                            if 0 <= nx < self.w and 0 <= ny < self.h and src[ny][nx] is not None:
                                g[y][x] = oc
                                break
        img = Image.new('RGBA', (self.w, self.h), (0, 0, 0, 0))
        img.putdata([c if c else (0, 0, 0, 0) for row in g for c in row])
        return img


def up(img, s):
    return img.resize((img.width*s, img.height*s), Image.NEAREST)

# ---------------------------------------------------------------- character

SKIN, SKINSH, MOUTH, EYE, WHITE = hexc('#c08862'), hexc('#a06b4b'), hexc('#6e2f33'), hexc('#12121c'), hexc('#ffffff')
INNER = hexc('#3a1418')
GP = {
 'hair': '#231a1c', 'hairhi': '#4f3d42', 'skin': '#c08862', 'skinsh': '#a06b4b', 'blush': '#d4917a',
 'mouth': '#6e2f33', 'eye': '#12121c', 'white': '#ffffff', 'frame': '#a9b0bb', 'framehi': '#d3d8e0',
 'framesh': '#7b8491', 'tee': '#f7f7fa', 'teesh': '#d6d9e2', 'jeans': '#2b2d33', 'jeansh': '#1f2025',
 'jeanhi': '#454852', 'waist': '#16171b', 'shoe': '#f4f4f6', 'shoesh': '#cfd2da', 'sole': '#b9bcc6',
}
OX = 6   # side padding so arms can reach outward; sprite is 48x60

# arm poses: (left, right), each ((elbow dx, dy), (hand dx, dy)) from the shoulder, dx positive = outward
_D = ((0, 6), (0, 11))
POSES = {
 'down': (_D, _D),
 'down2': (((1, 6), (1, 11)), ((1, 6), (1, 11))),
 'talkR': (_D, ((2, 6), (6, 2))),
 'talkL': (((2, 6), (6, 2)), _D),
 'talkB': (((2, 6), (5, 3)), ((2, 6), (5, 3))),
 'point': (_D, ((5, -1), (11, -2))),
 'pointup': (_D, ((5, -3), (9, -8))),
 'up1': (((3, -5), (5, -12)), ((3, -5), (5, -12))),
 'up2': (((4, -5), (7, -11)), ((4, -5), (7, -11))),
 'shrug': (((4, 4), (7, -1)), ((4, 4), (7, -1))),
 'wave1': (_D, ((4, -3), (5, -10))),
 'wave2': (_D, ((4, -3), (8, -9))),
 'shock': (((4, -1), (5, -7)), ((4, -1), (5, -7))),
 'sad': (((-1, 6), (-1, 11)), ((-1, 6), (-1, 11))),
 'hips': (((4, 4), (1, 8)), ((4, 4), (1, 8))),
 'flail1': (((4, -3), (8, -6)), ((4, 2), (8, 5))),
 'flail2': (((4, 2), (8, 5)), ((4, -3), (8, -6))),
 'thumb': (_D, ((4, 6), (7, 0))),
 'catch': (_D, ((3, 6), (8, 6))),
}

def _line(a, b):
    (x0, y0), (x1, y1) = a, b
    pts = []
    dx, dy = abs(x1 - x0), -abs(y1 - y0)
    sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
    err = dx + dy
    while True:
        pts.append((x0, y0))
        if (x0, y0) == (x1, y1): break
        e2 = 2 * err
        if e2 >= dy: err += dy; x0 += sx
        if e2 <= dx: err += dx; y0 += sy
    return pts

def _arm(g, sh, pose, side):
    (ex, ey), (hx, hy) = pose
    sgn = -1 if side == 'L' else 1
    s = sh
    e = (sh[0] + sgn * ex, sh[1] + ey)
    h = (sh[0] + sgn * hx, sh[1] + hy)
    pts = _line(s, e) + _line(e, h)[1:]
    for i, (x, y) in enumerate(pts):
        c = 'tee' if i < 3 else 'skin'
        g.rect(x - 1, y - 1, x + 1, y + 1, GP[c])
    if len(pts) > 3:
        x, y = pts[3]; g.rect(x - 1, y - 1, x + 1, y + 1, GP['teesh'])
        for x, y in pts[4:]:
            g.rect(x - 1, y - 1, x + 1, y + 1, GP['skin'])
    x, y = h
    if side == 'L': g.rect(x - 2, y - 1, x + 1, y + 2, GP['skin'])
    else: g.rect(x - 1, y - 1, x + 2, y + 2, GP['skin'])

@lru_cache(None)
def body(pose='down'):
    g = Grid(36 + 2 * OX, 60)
    def r(x0, y0, x1, y1, c): g.rect(x0 + OX, y0, x1 + OX, y1, GP[c] if c else None)
    def p(x, y, c): g.px(x + OX, y, GP[c] if c else None)
    r(14, 0, 14, 1, 'hair'); r(18, 0, 18, 1, 'hair')
    r(8, 2, 27, 12, 'hair')
    r(12, 3, 17, 4, 'hairhi'); r(20, 3, 24, 3, 'hairhi')
    r(9, 13, 9, 14, 'hair'); r(26, 13, 26, 14, 'hair')
    r(9, 9, 26, 25, 'skin')
    r(9, 9, 26, 10, 'hair'); r(13, 9, 18, 11, 'skin')
    r(10, 11, 12, 11, 'hair'); r(20, 10, 25, 11, 'hair')
    r(9, 11, 9, 12, 'hair'); r(26, 11, 26, 12, 'hair')
    r(8, 13, 8, 14, 'hair'); r(27, 13, 27, 14, 'hair')
    p(9, 25, None); p(26, 25, None); p(9, 24, 'skin'); p(26, 24, 'skin')
    r(7, 14, 8, 19, 'skin'); r(27, 14, 28, 19, 'skin')
    r(9, 14, 9, 20, 'skinsh'); r(26, 14, 26, 20, 'skinsh')
    r(11, 12, 15, 12, 'hair'); r(20, 12, 24, 12, 'hair')
    for (x0, x1) in ((10, 16), (19, 25)):
        r(x0, 13, x1, 19, 'frame'); r(x0 + 1, 14, x1 - 1, 18, 'skin')
        r(x0, 13, x1, 13, 'framehi'); r(x0, 19, x1, 19, 'framesh')
    r(17, 14, 18, 14, 'frame'); r(9, 14, 9, 15, 'frame'); r(26, 14, 26, 15, 'frame')
    for ex in (12, 21):
        r(ex + 1, 15, ex + 2, 16, 'eye'); p(ex, 15, 'white'); p(ex, 16, 'skin'); p(ex + 1, 15, 'white')
    r(17, 20, 18, 21, 'skinsh')
    r(11, 21, 12, 21, 'blush'); r(23, 21, 24, 21, 'blush')
    p(14, 22, 'mouth'); p(21, 22, 'mouth'); r(15, 23, 20, 23, 'mouth')
    # torso (arms are separate limbs)
    r(15, 26, 20, 29, 'skinsh')
    r(9, 28, 26, 31, 'tee')
    r(11, 28, 24, 43, 'tee')
    r(15, 28, 20, 29, 'skinsh'); r(16, 30, 19, 30, 'skinsh')
    r(14, 28, 14, 29, 'teesh'); r(21, 28, 21, 29, 'teesh'); p(15, 30, 'teesh'); p(20, 30, 'teesh')
    r(14, 31, 21, 31, 'teesh')
    r(11, 40, 14, 40, 'teesh'); r(22, 38, 24, 38, 'teesh')
    r(11, 34, 11, 43, 'teesh'); r(24, 34, 24, 43, 'teesh')
    # baggy black jeans
    r(10, 44, 25, 47, 'jeans'); r(10, 44, 25, 44, 'waist')
    r(9, 48, 26, 53, 'jeans'); r(8, 54, 27, 54, 'jeans')
    p(17, 48, None); r(17, 49, 18, 54, None); p(18, 48, None)
    r(10, 45, 10, 53, 'jeansh'); r(25, 45, 25, 53, 'jeansh')
    r(16, 45, 16, 53, 'jeansh'); r(19, 45, 19, 53, 'jeansh')
    r(12, 46, 13, 46, 'jeanhi'); r(22, 46, 23, 46, 'jeanhi')
    r(13, 49, 13, 52, 'jeanhi'); r(22, 49, 22, 52, 'jeanhi')
    r(9, 53, 15, 53, 'jeansh'); r(20, 53, 26, 53, 'jeansh')
    r(11, 50, 12, 50, 'jeansh'); r(23, 50, 24, 50, 'jeansh')
    p(11, 45, 'waist'); p(24, 45, 'waist')
    for (x0, x1) in ((8, 16), (19, 27)):
        r(x0, 55, x1, 57, 'shoe'); r(x0, 57, x1, 57, 'shoesh'); r(x0, 58, x1, 58, 'sole'); r(x0 + 1, 55, x0 + 3, 55, 'shoesh')
    L, R = POSES[pose]
    _arm(g, (9 + OX, 31), L, 'L')
    _arm(g, (26 + OX, 31), R, 'R')
    if pose == 'thumb':
        hx, hy = 26 + OX + 7, 31
        g.rect(hx, hy - 4, hx + 1, hy - 2, GP['skin'])
    return g.image()

def _recolor(img, mapping):
    m = {hexc(a): hexc(b) for a, b in mapping.items()}
    img = img.copy()
    img.putdata([m.get(p, p) for p in img.getdata()])
    return img

NPC_MAP = {'#f7f7fa': '#ff8a3d', '#d6d9e2': '#d9662a', '#c08862': '#f1c7a0', '#a06b4b': '#d6a37c',
           '#231a1c': '#e0a43a', '#4f3d42': '#f5cb6b', '#a9b0bb': '#f1c7a0', '#d3d8e0': '#f1c7a0',
           '#7b8491': '#f1c7a0', '#2b2d33': '#4a74ab', '#1f2025': '#37598a', '#454852': '#6490c6',
           '#16171b': '#2f4c78'}

@lru_cache(None)
def guy(expr='smile', npc=False, pose='down'):
    img = body(pose).copy()
    p = img.load()
    def put(x, y, c): p[x + OX, y] = c
    for y in range(22, 25):
        for x in range(14, 22):
            put(x, y, SKIN)
    if expr in ('smile', 'blink'):
        put(14, 22, MOUTH); put(21, 22, MOUTH)
        for x in range(15, 21): put(x, 23, MOUTH)
    elif expr == 'talk':
        for x in range(14, 22): put(x, 22, MOUTH)
        for x in range(15, 21): put(x, 23, INNER)
        for x in range(16, 20): put(x, 24, MOUTH)
    elif expr == 'sad':
        for x in range(15, 21): put(x, 22, MOUTH)
        put(14, 23, MOUTH); put(21, 23, MOUTH)
    elif expr == 'sadtalk':
        for x in range(15, 21): put(x, 22, MOUTH)
        for x in range(15, 21): put(x, 23, INNER)
        put(14, 24, MOUTH); put(21, 24, MOUTH)
    elif expr == 'shock':
        for x in range(16, 20): put(x, 22, MOUTH); put(x, 24, MOUTH)
        put(15, 23, MOUTH); put(20, 23, MOUTH)
        for x in range(16, 20): put(x, 23, INNER)
    if expr == 'blink':
        for ex in (12, 21):
            for x in range(ex, ex + 3):
                put(x, 15, SKIN); put(x, 16, EYE)
    if expr in ('sad', 'sadtalk'):
        put(11, 12, SKIN); put(15, 11, hexc('#231a1c')); put(24, 12, SKIN); put(20, 11, hexc('#231a1c'))
    if expr == 'shock':
        for ex in (12, 21):
            put(ex, 16, WHITE)
    if npc:
        img = _recolor(img, NPC_MAP)
    return img

# ---------------------------------------------------------------- car

CAR_COLORS = {
    'red':  ('#e8343f', '#b5222c', '#ff7a80'),
    'used': ('#a8585c', '#844246', '#c47a7d'),
    'blue': ('#3d7fd6', '#2b5fa8', '#7ab0f0'),
}

@lru_cache(None)
def car(color='red', phase=0):
    body, shade, hi = CAR_COLORS[color]
    g = Grid(52, 24)
    cab = [(16, 32), (15, 34), (14, 35), (13, 36), (12, 37), (11, 39), (10, 41)]
    for i, (a, b) in enumerate(cab):
        g.rect(a, 4+i, b, 4+i, body)
    g.rect(16, 4, 32, 4, hi)
    for y in range(6, 10):
        a, b = cab[y-4]
        g.rect(a+2, y, 25, y, '#bfe3f5')
        g.rect(28, y, b-2, y, '#bfe3f5')
    g.px(cab[2][0]+2, 6, '#ffffff'); g.px(29, 6, '#ffffff'); g.px(30, 6, '#ffffff')
    g.rect(4, 11, 47, 11, hi)
    g.rect(2, 12, 49, 16, body)
    g.rect(2, 16, 49, 16, shade)
    g.rect(2, 17, 49, 17, '#3a3b44')
    g.rect(47, 12, 49, 13, '#ffe27a')
    g.rect(2, 12, 3, 13, '#ffb03b')
    g.rect(27, 11, 27, 15, shade)
    g.rect(21, 13, 23, 13, shade); g.rect(31, 13, 33, 13, shade)
    for cx in (13, 40):
        for y in range(10, 19):
            for x in range(cx-6, cx+7):
                if (x-cx)**2 + (y-18)**2 <= 30:
                    g.px(x, y, None)
        g.disc(cx, 18, 4, '#26272e')
        g.disc(cx, 18, 2.2, '#a9b0bb')
        g.px(cx, 18, '#e2e5ea')
        if phase == 0:
            g.px(cx, 16, '#5d636e'); g.px(cx, 20, '#5d636e')
        else:
            g.px(cx-2, 18, '#5d636e'); g.px(cx+2, 18, '#5d636e')
    return g.image()

# ---------------------------------------------------------------- props

@lru_cache(None)
def tag(text, body='#fff6e0', ink='#d6303a', strike=False):
    tw = text_width(text)
    w, h = tw + 14, 15
    g = Grid(w, h)
    for y in range(1, h-1):
        g.rect(1 + max(0, 4 - min(y-1, h-2-y)), y, w-2, y, body)
    g.px(5, 7, '#1a1a2e')
    g.text(9, 4, text, ink)
    if strike:
        g.rect(7, 7, w-3, 7, '#1a1a2e')
    return g.image()

@lru_cache(None)
def stamp(text, col='#e0303a', fill=None):
    tw = text_width(text)
    w, h = tw + 10, 15
    g = Grid(w, h)
    if fill:
        g.rect(1, 1, w - 2, h - 2, fill)
    g.rect(1, 1, w-2, 2, col); g.rect(1, h-3, w-2, h-2, col)
    g.rect(1, 1, 2, h-2, col); g.rect(w-3, 1, w-2, h-2, col)
    g.text(5, 4, text, col)
    return g.image(outline=False)

@lru_cache(None)
def badge(text, body='#ffd23f', ink='#d6303a', shade='#e8b923'):
    tw = text_width(text)
    w, h = tw + 10, 13
    g = Grid(w, h)
    g.rect(2, 1, w-3, h-2, body); g.rect(1, 2, w-2, h-3, body)
    g.rect(2, h-3, w-3, h-2, shade)
    g.text(5, 3, text, ink)
    return g.image()

@lru_cache(None)
def label(text, col='#ffffff'):
    g = Grid(text_width(text) + 2, 9)
    g.text(1, 1, text, col)
    return g.image()

@lru_cache(None)
def bill():
    g = Grid(18, 11)
    g.rect(1, 1, 16, 9, '#79c25a')
    g.rect(3, 3, 14, 7, '#5aa543')
    g.disc(8.5, 5, 2, '#a6dd8a')
    g.px(8, 5, '#3d7a2c'); g.px(9, 5, '#3d7a2c')
    return g.image()

@lru_cache(None)
def coin():
    g = Grid(11, 11)
    g.disc(5, 5, 4, '#f0a81c')
    g.disc(5, 5, 3, '#ffcc33')
    g.rect(5, 3, 5, 7, '#f0a81c')
    g.px(3, 3, '#fff2a8')
    return g.image()

@lru_cache(None)
def freshener():
    g = Grid(20, 32)
    g.rect(9, 0, 10, 4, '#d9d9d9')
    g.rect(7, 5, 12, 7, '#ffffff')
    tiers = [(8, 13, 1, 4), (12, 19, 3, 7), (17, 25, 5, 9)]
    for y0, y1, w0, w1 in tiers:
        for y in range(y0, y1+1):
            hw = w0 + (w1-w0) * (y-y0) / (y1-y0)
            a, b = int(round(9.5-hw)), int(round(9.5+hw))
            g.rect(a, y, b, y, '#2fb35a')
            g.rect(int(round(9.5+hw*0.35)), y, b, y, '#1f8a43')
            g.px(a+1, y, '#6ee08f')
    g.rect(8, 26, 11, 29, '#1f8a43')
    return g.image()

@lru_cache(None)
def weight():
    g = Grid(34, 24)
    g.rect(12, 1, 21, 2, '#5d636e'); g.rect(11, 2, 12, 6, '#5d636e'); g.rect(21, 2, 22, 6, '#5d636e')
    for y in range(6, 23):
        inset = max(0, 3 - (y-6)) if y < 9 else 0
        g.rect(2 + inset, y, 31 - inset, y, '#d93a3a')
    g.rect(2, 20, 31, 22, '#a82828')
    g.rect(4, 7, 9, 7, '#ff7070')
    g.text(7, 10, '-20%', '#ffffff')
    return g.image()

@lru_cache(None)
def check():
    g = Grid(16, 13)
    pts = [(2, 6), (3, 7), (4, 8), (5, 9), (6, 8), (7, 7), (8, 6), (9, 5), (10, 4), (11, 3), (12, 2)]
    for x, y in pts:
        g.rect(x, y, x+1, y+2, '#3cc85a')
    return g.image()

@lru_cache(None)
def xmark():
    g = Grid(15, 15)
    for i in range(1, 13):
        g.rect(i, i, i+1, i+1, '#e0303a')
        g.rect(13-i, i, 14-i, i+1, '#e0303a')
    return g.image()

@lru_cache(None)
def glyph(ch, col):
    rows = FONT[ch]
    g = Grid(len(rows[0]) + 2, 9)
    g.text(1, 1, ch, col)
    return g.image()

@lru_cache(None)
def bubble(dots=3):
    g = Grid(32, 24)
    g.rect(2, 1, 29, 15, '#ffffff'); g.rect(1, 2, 30, 14, '#ffffff')
    for i in range(5):
        g.rect(6 - i // 2, 16 + i, 9 - i, 16 + i, '#ffffff')
    for i in range(dots):
        g.rect(8 + i*6, 7, 10 + i*6, 9, '#1a1a2e')
    return g.image()

@lru_cache(None)
def heart():
    g = Grid(11, 10)
    rows = ["0110110", "1111111", "1111111", "0111110", "0011100", "0001000"]
    for y, r in enumerate(rows):
        for x, b in enumerate(r):
            if b == '1': g.px(x+2, y+2, '#ff4d6d')
    g.px(3, 3, '#ffb3c1')
    return g.image()

@lru_cache(None)
def arrow():
    g = Grid(13, 14)
    g.rect(4, 1, 8, 6, '#ffd23f')
    for i in range(6):
        g.rect(1+i, 7+i, 11-i, 7+i, '#ffd23f')
    return g.image()

@lru_cache(None)
def star(col='#ffd23f'):
    g = Grid(7, 7)
    g.rect(3, 1, 3, 5, col); g.rect(1, 3, 5, 3, col)
    return g.image()

@lru_cache(None)
def sparkle(size=0):
    g = Grid(9, 9)
    if size == 0:
        g.px(4, 4, '#ffffff'); g.px(4, 3, '#fff6b0'); g.px(4, 5, '#fff6b0'); g.px(3, 4, '#fff6b0'); g.px(5, 4, '#fff6b0')
    else:
        g.rect(4, 1, 4, 7, '#fff6b0'); g.rect(1, 4, 7, 4, '#fff6b0'); g.rect(3, 3, 5, 5, '#ffffff')
    return g.image(oc=(255, 200, 60, 255))


# ---------------------------------------------------------------- fuel props

@lru_cache(None)
def pump(body='#ffd23f', shade='#e8b923', hi='#fff2a8', stripe='#1a1a2e'):
    g = Grid(34, 56)
    g.rect(2, 52, 31, 55, '#5d636e'); g.rect(2, 55, 31, 55, '#3a3b44')
    g.rect(4, 3, 27, 6, shade)
    g.rect(5, 6, 26, 51, body); g.rect(22, 6, 26, 51, shade); g.rect(7, 8, 8, 48, hi)
    g.rect(9, 10, 21, 20, '#1a1a2e'); g.rect(10, 11, 20, 19, '#16302a')
    g.text(13, 12, '$', '#7fe3a0')
    g.rect(10, 23, 12, 24, '#ff4d6d'); g.rect(14, 23, 16, 24, '#ffffff'); g.rect(18, 23, 20, 24, '#3d7fd6')
    g.rect(9, 29, 20, 45, '#ffffff'); g.rect(9, 34, 20, 39, stripe)
    g.rect(27, 18, 30, 21, '#2b2d33'); g.rect(28, 22, 30, 28, '#2b2d33'); g.rect(27, 22, 27, 24, '#5d636e')
    g.rect(29, 29, 30, 46, '#2b2d33'); g.rect(26, 46, 30, 47, '#2b2d33')
    return g.image()

@lru_cache(None)
def speedo(deg=180):
    import math
    g = Grid(44, 29)
    g.disc(22, 25, 21, '#2b2d33'); g.disc(22, 25, 19, '#ffffff')
    for a in range(180, -1, -2):
        col = '#3cc85a' if a > 120 else '#ffd23f' if a > 60 else '#e0303a'
        for r in (16.5, 17.5):
            g.px(int(round(22 + r * math.cos(math.radians(a)))), int(round(25 - r * math.sin(math.radians(a)))), col)
    g.rect(0, 26, 43, 28, None)
    g.rect(3, 25, 40, 27, '#2b2d33')
    tip = (int(round(22 + 14 * math.cos(math.radians(deg)))), int(round(25 - 14 * math.sin(math.radians(deg)))))
    for x, y in _line((22, 25), tip):
        g.rect(x, y - 1, x, y, '#e0303a')
    g.disc(22, 25, 2, '#1a1a2e')
    return g.image()

@lru_cache(None)
def engine():
    g = Grid(42, 31)
    g.rect(2, 27, 39, 29, '#2b2d33')
    g.rect(5, 10, 36, 27, '#8a909c'); g.rect(31, 10, 36, 27, '#6b717c')
    for x in (10, 16, 22, 28):
        g.rect(x, 13, x + 1, 24, '#a9b0bb')
    g.rect(7, 3, 34, 9, '#e0303a'); g.rect(9, 4, 31, 4, '#ff7a80'); g.rect(7, 8, 34, 9, '#b5222c')
    for x in (11, 18, 25):
        g.rect(x, 1, x + 2, 2, '#5d636e')
    g.disc(6, 19, 5, '#2b2d33'); g.disc(6, 19, 2.5, '#a9b0bb'); g.px(6, 19, '#e2e5ea')
    return g.image()

@lru_cache(None)
def textbubble(text, body='#ffffff', ink='#1a1a2e'):
    tw = text_width(text)
    w = tw + 12
    g = Grid(w, 22)
    g.rect(2, 1, w - 3, 15, body); g.rect(1, 2, w - 2, 14, body)
    for i in range(5):
        g.rect(6 - i // 2, 16 + i, 9 - i, 16 + i, body)
    g.text(6, 5, text, ink)
    return g.image()

@lru_cache(None)
def book_closed():
    g = Grid(46, 40)
    g.rect(1, 1, 42, 38, '#3d7fd6'); g.rect(1, 1, 4, 38, '#2b5fa8')
    g.rect(43, 3, 44, 37, '#f4f4f6')
    g.rect(6, 8, 40, 18, '#ffffff'); g.text(6, 10, 'MANUAL', '#1a1a2e')
    g.rect(8, 23, 38, 24, '#7ab0f0'); g.rect(8, 28, 30, 29, '#7ab0f0')
    g.rect(37, 30, 39, 34, '#ffd23f')
    return g.image()

@lru_cache(None)
def book_open(left='', right='CHECK', hl='#ffd23f'):
    g = Grid(102, 46)
    g.rect(1, 41, 100, 44, '#2b5fa8')
    g.rect(2, 2, 49, 41, '#fffdf5'); g.rect(52, 2, 99, 41, '#fffdf5'); g.rect(50, 1, 51, 42, '#cfd2da')
    for y in range(7, 38, 5):
        if not (left and 14 <= y <= 27):
            g.rect(7, y, 44, y + 1, '#d6d9e2')
        if not (14 <= y <= 27):
            g.rect(57, y, 94, y + 1, '#d6d9e2')
    if left:
        g.text(26 - text_width(left) // 2, 18, left, '#1a1a2e')
    g.rect(54, 15, 97, 27, hl)
    g.text(76 - text_width(right) // 2, 18, right, '#1a1a2e')
    return g.image()

@lru_cache(None)
def page():
    g = Grid(48, 40)
    g.rect(0, 0, 47, 39, '#fffdf5')
    for y in range(5, 36, 5):
        g.rect(5, y, 42, y + 1, '#d6d9e2')
    return g.image()

@lru_cache(None)
def bottle():
    g = Grid(40, 52)
    g.rect(13, 1, 26, 6, '#ffd23f'); g.rect(22, 1, 26, 6, '#e8b923')
    g.rect(14, 7, 25, 9, '#2b2d33'); g.rect(9, 10, 30, 13, '#2b2d33')
    g.rect(5, 14, 34, 50, '#2b2d33'); g.rect(28, 14, 34, 50, '#1f2025'); g.rect(8, 16, 9, 46, '#5d636e')
    return g.image()

# ---------------------------------------------------------------- parking brake props
import math as _m

DUSTY = {'#e0303a': '#b89a96', '#ff7a80': '#cbb7b4', '#26272e': '#6f707a', '#7b8491': '#9da2ab',
         '#3a3b44': '#80838c', '#5d636e': '#8f939c', '#16171b': '#5f626b'}

@lru_cache(None)
def handbrake(deg=0, dusty=False):
    """Red-and-black lever on a console; pivot right, grip reaching left. 64x44."""
    g = Grid(64, 44)
    g.rect(37, 27, 62, 43, '#3a3b44'); g.rect(36, 29, 63, 43, '#3a3b44')
    g.rect(38, 27, 61, 27, '#5d636e'); g.rect(36, 42, 63, 43, '#16171b')
    g.rect(42, 31, 58, 32, '#16171b')
    for x in range(48, 61):
        g.rect(x, 25 + abs(x - 54) // 2, x, 30, '#26272e')
    px, py, L = 54, 28, 44
    ca, sa = _m.cos(_m.radians(deg)), _m.sin(_m.radians(deg))
    i = 0.0
    while i <= L:
        x, y = px - ca * i, py - sa * i
        half = 1 if i < 25 else 2
        w = -half - 0.5
        while w <= half + 0.5:
            if i < 25:
                c = '#d3d8e0' if w < -0.6 else '#7b8491'
            else:
                c = '#e0303a' if (w > 1.4 or 33 <= i < 35) else '#26272e'
            g.px(int(round(x + w * sa)), int(round(y - w * ca)), c)
            w += 0.5
        i += 0.5
    tx, ty = px - ca * L, py - sa * L
    g.disc(tx, ty, 2.2, '#e0303a'); g.px(int(round(tx)) - 1, int(round(ty)) - 1, '#ff7a80')
    g.disc(px, py, 3.2, '#a9b0bb'); g.px(px, py, '#5d636e')
    img = g.image()
    if dusty:
        img = _recolor(img, DUSTY)
        pp = img.load()
        for (x, y) in ((40, 27), (45, 27), (52, 27), (58, 27), (60, 28), (38, 28), (49, 26)):
            pp[x, y] = hexc('#e6e1d3')
    return img

@lru_cache(None)
def drum():
    """Drum-brake backing plate with shoes, springs and hub. 48x48."""
    g = Grid(48, 48)
    c = 23.5
    g.disc(c, c, 22, '#5d636e'); g.disc(c, c, 21, '#7b8491')
    for y in range(48):
        for x in range(48):
            r = ((x - c) ** 2 + (y - c) ** 2) ** 0.5
            if abs(x - c) < 3.5: continue
            if 17.5 <= r <= 19.5: g.px(x, y, '#8a5a32')
            elif 13.5 <= r < 17.5: g.px(x, y, '#d6d9e2' if r > 16.5 else '#b9bcc6')
    g.rect(19, 3, 28, 6, '#d6303a'); g.rect(20, 3, 27, 3, '#ff7a80')
    for i, x in enumerate(range(15, 33, 2)):
        g.rect(x, 9 + (i % 2), x + 1, 9 + (i % 2), '#ffd23f')
    g.rect(17, 40, 30, 43, '#5d636e'); g.rect(18, 41, 29, 41, '#a9b0bb')
    g.disc(c, c, 6.5, '#a9b0bb'); g.disc(c, c, 3.2, '#5d636e')
    for dx, dy in ((0, -5), (5, 0), (0, 5), (-5, 0)):
        g.px(int(c + dx), int(c + dy), '#ffffff')
    return g.image()

@lru_cache(None)
def wheel(deg=0):
    """Tyre and alloy rim; spokes rotated by deg. 46x46."""
    g = Grid(46, 46)
    c = 22.5
    g.disc(c, c, 21.5, '#26272e')
    for k in range(24):
        a = _m.radians(k * 15 + deg)
        g.rect(int(round(c + 20 * _m.cos(a))), int(round(c + 20 * _m.sin(a))),
               int(round(c + 20 * _m.cos(a))), int(round(c + 20 * _m.sin(a))), '#4a4c56')
    g.disc(c, c, 14, '#3a3b44'); g.disc(c, c, 12.5, '#a9b0bb'); g.disc(c, c, 10.5, '#5d636e')
    for k in range(5):
        a = _m.radians(k * 72 + deg)
        for i in range(2, 12):
            x, y = c + i * _m.cos(a), c + i * _m.sin(a)
            g.rect(int(round(x)), int(round(y)), int(round(x)) + 1, int(round(y)), '#d3d8e0')
    g.disc(c, c, 3.5, '#d3d8e0'); g.disc(c, c, 1.5, '#7b8491')
    g.rect(14, 12, 15, 13, '#ffffff')
    return g.image()

@lru_cache(None)
def cobweb():
    g = Grid(16, 16)
    for a in (0, 22, 45, 68, 90):
        for i in range(15):
            g.px(int(round(i * _m.cos(_m.radians(a)))), int(round(i * _m.sin(_m.radians(a)))), '#c8ccd4')
    for r in (5, 10, 14):
        for k in range(30):
            a = _m.radians(k * 3)
            g.px(int(round(r * _m.cos(a))), int(round(r * _m.sin(a))), '#c8ccd4')
    return g.image(outline=False)


# ---------------------------------------------------------------- air con props

@lru_cache(None)
def tacho(deg=200):
    """Dashboard rev counter: dark face, white ticks, red zone, orange needle at deg (math degrees). 48x48."""
    g = Grid(48, 48)
    c = 23.5
    g.disc(c, c, 23, '#5d636e'); g.disc(c, c, 21.5, '#a9b0bb'); g.disc(c, c, 20, '#1a1a2e')
    g.disc(c, c, 18.5, '#22233a')
    for k in range(0, 271, 3):  # sweep 225 deg -> -45 deg clockwise
        a = _m.radians(225 - k)
        col = '#e0303a' if k > 210 else '#ffffff'
        for r in (16.5, 17.2):
            g.px(int(round(c + r * _m.cos(a))), int(round(c - r * _m.sin(a))), col)
    for k in range(0, 271, 30):
        a = _m.radians(225 - k)
        col = '#ff5a5a' if k > 210 else '#ffffff'
        for r in (13.5, 14.5, 15.5):
            g.px(int(round(c + r * _m.cos(a))), int(round(c - r * _m.sin(a))), col)
    g.text(15, 33, 'RPM', '#7b8491')
    a = _m.radians(deg)
    tip = (int(round(c + 15 * _m.cos(a))), int(round(c - 15 * _m.sin(a))))
    for x, y in _line((int(c), int(c)), tip):
        g.rect(x, y, x + 1, y + 1, '#ff8a3d')
    g.disc(c, c, 3, '#e0303a'); g.disc(c, c, 1.5, '#ff7a80')
    g.rect(14, 8, 17, 8, '#3a3c58')
    return g.image()

FLAKE = ["0001000", "0101010", "0011100", "1111111", "0011100", "0101010", "0001000"]
def _flake(g, cx, cy, col):
    for j, row in enumerate(FLAKE):
        for i, b in enumerate(row):
            if b == '1': g.px(cx - 3 + i, cy - 3 + j, col)

@lru_cache(None)
def snowflake(col='#7fd4ff'):
    g = Grid(11, 11)
    _flake(g, 5, 5, col)
    return g.image()

@lru_cache(None)
def acbtn(on=False):
    """Dash A/C button with snowflake; LED strip lights green when on. 30x22."""
    g = Grid(30, 22)
    g.rect(2, 1, 27, 20, '#3a3b44'); g.rect(1, 2, 28, 19, '#3a3b44')
    g.rect(3, 2, 26, 3, '#5d636e')
    g.rect(3, 17, 26, 19, '#26272e')
    _flake(g, 10, 10, '#7fd4ff' if on else '#a9b0bb')
    g.text(16, 7, 'AC', '#ffffff' if on else '#a9b0bb')
    g.rect(16, 14, 24, 15, '#3cc85a' if on else '#5d636e')
    if on: g.rect(17, 14, 18, 14, '#a6f5b8')
    return g.image()

@lru_cache(None)
def compressor(phase=0):
    """A/C compressor: finned body above a belt pulley whose spokes turn with phase. 30x34."""
    g = Grid(30, 34)
    g.rect(3, 2, 26, 17, '#5d8fc4'); g.rect(21, 2, 26, 17, '#41709f'); g.rect(4, 3, 25, 3, '#9cc6ee')
    for x in range(6, 20, 3):
        g.rect(x, 5, x, 15, '#41709f')
    g.rect(1, 6, 2, 12, '#a9b0bb'); g.rect(27, 6, 28, 12, '#a9b0bb')
    g.rect(12, 17, 17, 19, '#5d636e')
    _flake(g, 13, 10, '#ffffff')
    c = (14.5, 25.5)
    g.disc(*c, 7.5, '#26272e'); g.disc(*c, 5.5, '#a9b0bb'); g.disc(*c, 2, '#5d636e')
    for k in range(3):
        a = _m.radians(k * 120 + phase * 30)
        for i in range(2, 6):
            g.px(int(round(c[0] + i * _m.cos(a))), int(round(c[1] + i * _m.sin(a))), '#e2e5ea')
    return g.image()

@lru_cache(None)
def robot(blink=False):
    """Friendly ECU robot: chip body with pins, screen face, antenna light. 30x32."""
    g = Grid(30, 32)
    g.rect(14, 1, 15, 5, '#7b8491'); g.disc(14.5, 2, 2, '#e0303a'); g.px(14, 1, '#ff9aa0')
    g.rect(5, 6, 24, 19, '#d3d8e0'); g.rect(4, 7, 25, 18, '#d3d8e0'); g.rect(20, 7, 25, 18, '#a9b0bb')
    g.rect(7, 9, 22, 16, '#1a1a2e')
    for ex in (10, 17):
        if blink: g.rect(ex, 12, ex + 2, 12, '#3cc85a')
        else: g.rect(ex, 11, ex + 2, 13, '#3cc85a'); g.px(ex, 11, '#a6f5b8')
    g.rect(12, 15, 17, 15, '#3cc85a')
    g.rect(1, 10, 3, 14, '#a9b0bb'); g.rect(26, 10, 28, 14, '#a9b0bb')
    g.rect(4, 20, 25, 30, '#2b2d33'); g.rect(5, 21, 24, 21, '#5d636e')
    for y in (22, 25, 28):
        g.rect(1, y, 3, y, '#d3d8e0'); g.rect(26, y, 28, y, '#d3d8e0')
    g.text(7, 23, 'ECU', '#ffd23f')
    return g.image()
