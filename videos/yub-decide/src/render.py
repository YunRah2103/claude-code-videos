"""Yub "pick a side" skits (Cybertruck / used Range Rover / Civic Type R vs Golf R). Six scenes each, same buyer cast and
voice as tesla-locked .. bmw-heated-seats, deadpan salesman, word-by-word captions, whip pans, real Commons photos/logos.
YUB_EP=cybertruck|range_rover|civic_golf selects ep_<EP>.py (dialogue + scene/overlay/cue data) and words_<EP>.json.
Usage: python render.py video VOICE.wav MUSIC OUT.mp4 | still T OUT.png VOICE | sheet VOICE OUT.png | thumb OUT.png VOICE
       | meta OUT.json"""
import importlib
from base import *

EPN = os.environ.get('YUB_EP', 'cybertruck')
E = importlib.import_module('ep_' + EPN)
WORDS = json.load(open(os.path.join(HERE, f'words_{EPN}.json')))
DUR = round(WORDS[-1]['e'] + 2.3, 2)
LINES = {}
for w in WORDS:
    LINES.setdefault(w['line'], []).append(w)
LS = {k: v[0]['s'] for k, v in LINES.items()}
LE = {k: v[-1]['e'] for k, v in LINES.items()}
NL = len(LINES)
SCN_OF = [sc for _, _, sc in E.LINES]
SCENES = [0.0] + [LS[SCN_OF.index(k)] - 0.5 for k in range(2, max(SCN_OF) + 1)]
def scene_at(t): return max(i for i, s in enumerate(SCENES) if t >= s)
T_FINAL = LS[NL - 1]
T_CARD = LE[NL - 1] + 0.3
BEAT = (LE[NL - 2], T_FINAL)

def A(s):
    """Anchor -> time. 'L3' line start, 'E3' line end, '3:word' / '3:word#1' word start, 'S2' scene start, 'CARD';
    optional +/-offset, e.g. 'E3+.2'."""
    if isinstance(s, (int, float)): return float(s)
    off = 0.0
    for sign in ('+', '-'):
        i = s.rfind(sign)
        if i > 0:
            off = float(s[i:]); s = s[:i]; break
    if s == 'CARD': t = T_CARD
    elif s[0] == 'L': t = LS[int(s[1:])]
    elif s[0] == 'E': t = LE[int(s[1:])]
    elif s[0] == 'S': t = SCENES[int(s[1:])]
    else:
        li, wd = s.split(':'); nth = 0
        if '#' in wd: wd, nth = wd.split('#'); nth = int(nth)
        t = [w['s'] for w in LINES[int(li)] if wd.lower() in w['w'].lower()][nth]
    return t + off

# ================================================================ cars (side profile, front to the left)
STEEL = ((222, 226, 230), (150, 154, 160), (96, 100, 106))
def _wheel(d, wx, wy, r, rim, cal, n=5, cover=False, spin=0.0):
    d.ell(wx, wy, r, r, (18, 18, 22))
    d.ell(wx, wy, r * .9, r * .9, None, (40, 40, 46), max(2, r * .06))
    if cover:                                            # Cybertruck aero cover: flat dark disc with angular facets
        d.ell(wx, wy, r * .72, r * .72, (40, 42, 46))
        for a in range(6):
            ra = math.radians(a * 60 + spin)
            d.line([(wx + r * .2 * math.cos(ra), wy + r * .2 * math.sin(ra)), (wx + r * .68 * math.cos(ra + .3), wy + r * .68 * math.sin(ra + .3))],
                   (70, 72, 78), max(2, r * .07))
        d.ell(wx, wy, r * .16, r * .16, (24, 24, 28), (90, 92, 98), 2)
        return
    d.ell(wx, wy, r * .7, r * .7, (66, 68, 74))
    d.chord(wx, wy, r * .62, r * .62, 200, 290, cal)
    d.ell(wx, wy, r * .7, r * .7, None, rim, max(3, r * .1))
    for a in range(n):
        ra = math.radians(a * 360 / n + 18 + spin)
        for off in (-.1, .1):
            d.line([(wx + r * .13 * math.cos(ra + off), wy + r * .13 * math.sin(ra + off)),
                    (wx + r * .66 * math.cos(ra + off * 1.4), wy + r * .66 * math.sin(ra + off * 1.4))], rim, max(2, r * .08))
    d.ell(wx, wy, r * .16, r * .16, rim, (90, 94, 102), 2)

def cybertruck(d, x0, g, L):
    Hh = L * .42
    def P(u, v): return (x0 + u * L, g - v * Hh)
    d.ell(x0 + L * .5, g + 4, L * .58, 15, (0, 0, 0, 100))
    body = [P(.0, .22), P(-.005, .44), P(.47, .80), P(1.0, .585), P(1.0, .25), P(.98, .18), P(.02, .18)]
    shade(d, body, STEEL[0], STEEL[2], g - .8 * Hh, g - .18 * Hh)
    d.poly([P(.03, .47), P(.47, .785), P(.62, .72), P(.20, .50)], (255, 255, 255, 40))          # sky reflection
    for u in (.12, .3, .5, .7, .88):                                                             # brushed grain
        d.line([P(u, .22), P(u + .02, .5)], (255, 255, 255, 18), 3)
    d.poly([P(.0, .18), P(1.0, .18), P(1.0, .27), P(.0, .27)], (34, 34, 38))                   # lower cladding
    r = Hh * .21
    for u in (.17, .80):                                                                         # angular black arches
        d.poly([P(u - .125, .18), P(u - .10, .43), P(u - .05, .47), P(u + .05, .47), P(u + .10, .43), P(u + .125, .18)], (26, 26, 30))
    d.poly(body, None, (40, 42, 48), 5)
    gl = [P(.17, .58), P(.455, .785), P(.70, .69), P(.70, .575)]
    shade(d, gl, (90, 104, 120), (18, 22, 30), g - .78 * Hh, g - .57 * Hh)
    d.poly(gl, None, (30, 32, 38), 3)
    d.line([P(.455, .785), P(.45, .575)], (22, 22, 26), 9)                                       # B pillar
    d.line([P(.70, .69), P(.70, .26)], (110, 114, 120), 3)                                       # bed / door cuts
    d.line([P(.19, .56), P(.19, .27)], (110, 114, 120), 3); d.line([P(.45, .57), P(.45, .27)], (110, 114, 120), 3)
    d.line([P(.70, .69), P(1.0, .585)], (120, 124, 130), 3)                                      # tonneau seam
    d.line([P(-.004, .44), P(.06, .487)], (255, 255, 255), 6)                                    # front light bar
    d.line([P(-.004, .44), P(.06, .487)], (220, 240, 255, 90), 16)
    d.line([P(.995, .58), P(.995, .55)], (240, 30, 40), 7)                                       # rear light bar edge
    d.rect(*P(.165, .60), *P(.19, .575), (30, 30, 34), r=3)                                      # mirror
    for u in (.17, .80):
        _wheel(d, P(u, 0)[0], g - r, r, (60, 62, 68), (40, 40, 44), cover=True)

RR_CTRL = [(.012, .17), (0.0, .30), (.003, .50), (.04, .565), (.20, .59), (.31, .61), (.41, .865), (.56, .885), (.82, .88),
           (.965, .855), (1.0, .79), (1.0, .45), (.99, .19), (.86, .155), (.5, .165), (.14, .155)]
def rangerover(d, x0, g, L, sag=0.0):
    Hh = L * .42
    def P(u, v): return (x0 + u * L, g - v * Hh + (sag * u * 26))
    base, hi, lo = (176, 180, 184), (232, 234, 236), (104, 108, 114)
    d.ell(x0 + L * .5, g + 4, L * .58, 15, (0, 0, 0, 100))
    body = spline([P(u, v) for u, v in RR_CTRL], 8)
    shade(d, body, hi, lo, g - .9 * Hh, g - .18 * Hh)
    shade(d, spline([P(.02, .17), P(.5, .18), P(.98, .17), P(.99, .27), P(.5, .25), P(.01, .26)], 6), (60, 62, 66), (30, 30, 34),
          g - .27 * Hh, g - .16 * Hh)
    d.line([P(.03, .52), P(.5, .555), P(.97, .57)], hi + (220,), 3)                               # waistline highlight
    d.line([P(.04, .33), P(.96, .35)], (220, 224, 228), 4)                                       # lower bright strip
    r = Hh * .215
    for u in (.17, .80):
        wx, wy = P(u, 0)[0], P(u, 0)[1] - r
        d.chord(wx, wy, r * 1.2, r * 1.2, 180, 360, (14, 14, 16))
        d.arc(wx, wy, r * 1.24, r * 1.24, 190, 350, (60, 62, 66), 6)
    d.poly(body, None, (40, 42, 48), 5)
    gh = [P(.33, .64), P(.41, .84), P(.93, .835), P(.955, .66)]                                   # long glasshouse
    shade(d, gh, (70, 84, 100), (14, 16, 22), g - .84 * Hh, g - .64 * Hh)
    for u in (.36, .56, .76, .935):                                                              # floating-roof black pillars
        d.line([P(u, .645), P(u + (.035 if u < .4 else .0), .835)], (16, 16, 18), 10)
    d.poly([P(.40, .66), P(.43, .66), P(.48, .82), P(.45, .82)], (255, 255, 255, 45))
    d.line([P(.33, .64), P(.955, .655)], (20, 20, 24), 4)
    for v in (.47, .43):                                                                         # side vent gills
        d.line([P(.25, v), P(.31, v + .005)], (226, 230, 236), 5)
    d.line([P(.56, .62), P(.565, .22)], lo, 3); d.line([P(.33, .62), P(.32, .22)], lo, 3); d.line([P(.78, .63), P(.79, .22)], lo, 3)
    d.rect(*P(.50, .55), *P(.54, .53), (200, 204, 210), r=3)
    d.poly(spline([P(.34, .69), P(.39, .71), P(.39, .76), P(.345, .76)], 4), (30, 30, 34), (24, 26, 34), 3)
    d.poly([P(-.002, .36), P(.035, .37), P(.04, .5), P(.0, .5)], (40, 42, 46), (200, 204, 210), 4)   # mesh grille
    for i in range(4):
        d.line([P(.004, .385 + i * .03), P(.034, .39 + i * .03)], (120, 124, 130), 2)
    d.poly([P(.01, .51), P(.10, .545), P(.11, .52), P(.02, .495)], (236, 240, 246), (30, 30, 36), 3)   # slim lamp
    d.poly([P(.985, .56), P(1.0, .56), P(1.0, .76), P(.987, .75)], (200, 26, 32))
    for u in (.17, .80):
        wx, wy = P(u, 0)[0], P(u, 0)[1] - r
        _wheel(d, wx, wy, r, (196, 200, 206), (60, 60, 66), n=7)

HATCH = {
    'civic': dict(ctrl=[(.012, .18), (0.0, .33), (.01, .43), (.08, .49), (.30, .555), (.46, .735), (.60, .745), (.80, .63),
                        (.95, .56), (1.0, .53), (1.0, .37), (.99, .19), (.86, .155), (.5, .165), (.14, .155)],
                  gh=[(.33, .565), (.465, .715), (.60, .725), (.78, .62), (.80, .57)], col=((70, 164, 222), (150, 210, 244), (26, 88, 140)),
                  rim=(30, 30, 34), cal=(214, 30, 36)),
    'golf': dict(ctrl=[(.012, .18), (0.0, .35), (.015, .46), (.10, .51), (.30, .565), (.45, .78), (.60, .80), (.76, .785),
                       (.90, .70), (.975, .62), (1.0, .50), (.99, .19), (.86, .155), (.5, .165), (.14, .155)],
                 gh=[(.33, .58), (.455, .76), (.60, .78), (.75, .765), (.86, .67), (.84, .585)], col=((34, 76, 176), (110, 150, 230), (12, 30, 84)),
                 rim=(200, 204, 212), cal=(30, 90, 200)),
}
def hatch(d, x0, g, L, kind):
    S = HATCH[kind]; Hh = L * .42
    def P(u, v): return (x0 + u * L, g - v * Hh)
    base, hi, lo = S['col']
    d.ell(x0 + L * .5, g + 4, L * .58, 15, (0, 0, 0, 100))
    body = spline([P(u, v) for u, v in S['ctrl']], 8)
    shade(d, body, hi, lo, g - .8 * Hh, g - .18 * Hh)
    shade(d, spline([P(.02, .18), P(.5, .185), P(.98, .18), P(.99, .26), P(.5, .245), P(.01, .25)], 6), (36, 36, 40), (16, 16, 18),
          g - .26 * Hh, g - .17 * Hh)
    d.line(spline([P(.05, .46), P(.40, .50), P(.95, .52)], 6, closed=False), hi + (220,), 3)
    r = Hh * .215
    for u in (.17, .80):
        wx, wy = P(u, 0)[0], g - r
        d.chord(wx, wy, r * 1.2, r * 1.2, 180, 360, (14, 14, 16))
        d.arc(wx, wy, r * 1.24, r * 1.24, 190, 350, (30, 30, 34), 7)
    d.poly(body, None, (24, 26, 34), 5)
    gh = spline([P(u, v) for u, v in S['gh']], 5)
    shade(d, gh, (86, 106, 130), (16, 20, 30), g - .8 * Hh, g - .56 * Hh)
    d.poly(gh, None, (20, 22, 28), 4)
    d.line([P(.60, .58), P(.60, .72 if kind == 'civic' else .79)], (20, 20, 24), 8)
    d.poly([P(.38, .59), P(.41, .59), P(.47, .70), P(.44, .70)], (255, 255, 255, 50))
    d.line([P(.34, .55), P(.32, .22)], lo, 3); d.line([P(.60, .56), P(.61, .21)], lo, 3)
    d.rect(*P(.50, .50), *P(.545, .48), (24, 24, 28), r=3)
    d.poly(spline([P(.335, .59), P(.39, .61), P(.39, .66), P(.34, .66)], 4), (24, 24, 28), (24, 26, 34), 3)
    d.poly([P(-.004, .20), P(.09, .22), P(.07, .34), P(0, .36)], (16, 16, 20))                  # lower intake
    d.poly([P(.02, .43), P(.13, .475), P(.14, .45), P(.04, .415)], (236, 240, 248), (24, 26, 34), 3)
    if kind == 'civic':
        d.poly([P(.84, .62), P(.85, .70), P(.87, .70), P(.87, .60)], (20, 20, 24))                 # wing stalk
        d.poly([P(.80, .70), P(1.02, .71), P(1.02, .745), P(.80, .725)], (22, 22, 26), (10, 10, 12), 3)   # big rear wing
        d.line([P(.02, .26), P(.30, .27)], (214, 30, 36), 4)                                    # red accent
        d.rect(*P(.97, .30), *P(1.01, .26), (60, 60, 66), r=4)                                  # triple exhaust
        d.poly([P(.93, .52), P(1.0, .50), P(1.0, .46), P(.94, .48)], (210, 24, 30))
        d.ell(*P(.012, .40), 7, 6, (214, 30, 36))                                               # red H badge
    else:
        d.poly([P(.80, .785), P(.90, .73), P(.89, .71), P(.80, .765)], (12, 26, 70))             # roof spoiler
        d.line([P(.02, .40), P(.12, .43)], (220, 224, 232), 3)                                  # light strip
        d.poly([P(.95, .58), P(1.0, .57), P(1.0, .52), P(.96, .53)], (210, 24, 30))
        for dx in (0, .03): d.ell(*P(.93 + dx, .21), 6, 5, (180, 184, 190))                      # quad tips
        d.text(*P(.015, .44), 'R', 16, (220, 224, 232))
    for u in (.17, .80):
        _wheel(d, P(u, 0)[0], g - r, r, S['rim'], S['cal'])

@lru_cache(None)
def car_img(kind, L, sag=0.0):
    img = Image.new('RGBA', (int(L * 1.25) * K, int(L * .62) * K), (0, 0, 0, 0))
    d = D(img, ox=-L * .1, oy=-L * .56)
    if kind == 'cybertruck': cybertruck(d, 0, 0, L)
    elif kind == 'rangerover': rangerover(d, 0, 0, L, sag)
    else: hatch(d, 0, 0, L, kind)
    return img
def paste_car(img, kind, x0, g, L, rot=0.0, sag=0.0, flip=False):
    c = car_img(kind, L, round(sag, 2))
    if flip: c = c.transpose(Image.FLIP_LEFT_RIGHT)
    if rot: c = c.rotate(rot, resample=Image.BICUBIC, center=(c.width // 2, int(L * .56) * K))
    img.paste(c, (int((x0 - L * .1) * K), int((g - L * .56) * K)), c)

@lru_cache(None)
def trailer_img():
    """Flatbed trailer with a speedboat, for 'it tows'."""
    w, h = 560, 260
    img = Image.new('RGBA', (w * K, h * K), (0, 0, 0, 0)); d = D(img)
    d.rect(20, 190, 520, 206, (40, 40, 46)); d.line([(520, 198), (556, 198)], (40, 40, 46), 8)
    for x in (180, 270):
        d.ell(x, 222, 30, 30, (18, 18, 22)); d.ell(x, 222, 14, 14, (150, 154, 160))
    hull = spline([(40, 120), (500, 112), (530, 140), (470, 186), (90, 186), (30, 150)], 6)
    shade(d, hull, (250, 250, 250), (190, 196, 204), 110, 186)
    d.poly(hull, None, (40, 44, 60), 4)
    d.line([(46, 150), (500, 150)], (200, 40, 50), 8)
    d.poly([(150, 112), (200, 70), (320, 70), (330, 112)], (120, 170, 210, 220), (40, 44, 60), 3)
    d.rect(14, 110, 36, 186, (40, 40, 46), r=4)
    return img

# ================================================================ the one background oddity per episode (never mentioned)
def odd_cow(d, x, fy, t, s=1.0):
    """A dairy cow wearing a VR headset, calmly looking around in a virtual world."""
    sw = math.sin(t * 2.0)
    for i, lx in enumerate((-70, -40, 40, 70)):
        k = math.sin(t * 2 + i) * 2
        d.rect(x + lx * s - 9 * s, fy - 92 * s, x + lx * s + 9 * s, fy + k * s, (250, 250, 248), ol=(30, 30, 36), w=3)
        d.rect(x + lx * s - 10 * s, fy - 12 * s, x + lx * s + 10 * s, fy + 2 * s, (40, 34, 30))
    d.ell(x, fy - 140 * s, 108 * s, 62 * s, (250, 250, 248), (30, 30, 36), 4)
    for px, py, rx, ry in ((-40, -150, 34, 24), (30, -128, 26, 20), (70, -158, 20, 16)):
        d.ell(x + px * s, fy + py * s, rx * s, ry * s, (34, 30, 30))
    d.ell(x + 20 * s, fy - 88 * s, 22 * s, 12 * s, (246, 170, 180), (30, 30, 36), 2)           # udder
    tx = x + 104 * s                                                                              # swishing tail
    d.line([(tx, fy - 170 * s), (tx + 26 * s + sw * 14 * s, fy - 110 * s)], (30, 30, 36), max(2, 6 * s))
    d.ell(tx + 26 * s + sw * 14 * s, fy - 104 * s, 9 * s, 13 * s, (34, 30, 30))
    hx, hy = x - 120 * s, fy - 186 * s + math.sin(t * 1.3) * 6 * s                               # head, slow look-around
    look = math.sin(t * .9) * 10 * s
    d.ell(hx + 20 * s, hy + 30 * s, 26 * s, 34 * s, (250, 250, 248), (30, 30, 36), 3)
    d.ell(hx + look, hy, 44 * s, 48 * s, (250, 250, 248), (30, 30, 36), 4)
    for sd in (-1, 1):
        d.ell(hx + look + sd * 52 * s, hy - 20 * s, 18 * s, 9 * s, (250, 250, 248), (30, 30, 36), 3)   # ears
        d.poly([(hx + look + sd * 24 * s, hy - 40 * s), (hx + look + sd * 34 * s, hy - 66 * s), (hx + look + sd * 16 * s, hy - 46 * s)],
               (236, 226, 196), (30, 30, 36), 2)                                                 # horns
    d.ell(hx + look, hy + 34 * s, 34 * s, 22 * s, (246, 170, 180), (30, 30, 36), 3)              # muzzle
    for sd in (-1, 1): d.ell(hx + look + sd * 12 * s, hy + 34 * s, 4 * s, 5 * s, (120, 60, 70))
    d.rect(hx + look - 46 * s, hy - 24 * s, hx + look + 46 * s, hy + 6 * s, (22, 22, 26), r=10 * s)      # VR headset
    glow = 150 + int(80 * (0.5 + 0.5 * math.sin(t * 5)))
    d.rect(hx + look - 40 * s, hy - 18 * s, hx + look + 40 * s, hy, (60, glow, 255), r=6 * s)
    d.line([(hx + look - 46 * s, hy - 12 * s), (hx + look - 58 * s, hy - 14 * s)], (22, 22, 26), max(2, 6 * s))
    d.line([(hx + look + 46 * s, hy - 12 * s), (hx + look + 58 * s, hy - 14 * s)], (22, 22, 26), max(2, 6 * s))

def odd_knight(d, x, fy, t, s=1.0):
    """A knight in full plate armour sipping tea, pinky out."""
    M, M2, OLc = (196, 202, 212), (130, 138, 150), (30, 32, 40)
    for sd in (-1, 1):
        d.rect(x + sd * 22 * s - 14 * s, fy - 150 * s, x + sd * 22 * s + 14 * s, fy - 10 * s, M, ol=OLc, w=3)
        d.ell(x + sd * 22 * s, fy - 80 * s, 14 * s, 10 * s, M2, OLc, 2)
        d.ell(x + sd * 26 * s, fy - 8 * s, 22 * s, 10 * s, M2, OLc, 3)
    d.poly([(x - 56 * s, fy - 300 * s), (x + 56 * s, fy - 300 * s), (x + 46 * s, fy - 150 * s), (x - 46 * s, fy - 150 * s)], M, OLc, 4)
    d.line([(x, fy - 296 * s), (x, fy - 156 * s)], M2, max(2, 4 * s))
    d.poly([(x - 50 * s, fy - 170 * s), (x + 50 * s, fy - 170 * s), (x + 60 * s, fy - 130 * s), (x - 60 * s, fy - 130 * s)], (150, 30, 40), OLc, 3)
    bob = math.sin(t * 1.1) * 3 * s
    hy = fy - 350 * s + bob
    d.rect(x - 40 * s, hy - 50 * s, x + 40 * s, hy + 46 * s, M, r=18 * s, ol=OLc, w=4)          # great helm
    for i in range(3): d.line([(x - 28 * s, hy - 8 * s + i * 10 * s), (x + 28 * s, hy - 8 * s + i * 10 * s)], (24, 24, 30), max(2, 4 * s))
    d.poly([(x - 6 * s, hy - 50 * s), (x + 6 * s, hy - 50 * s), (x + 20 * s, hy - 96 * s), (x - 18 * s, hy - 86 * s)], (200, 40, 50))   # plume
    sip = 0.5 + 0.5 * math.sin(t * .8)                                                            # slow sip cycle
    cx_, cy_ = x + 46 * s, fy - 250 * s - sip * 70 * s
    d.line([(x + 52 * s, fy - 285 * s), (x + 70 * s, fy - 220 * s), (cx_, cy_ + 12 * s)], OLc, max(3, 24 * s))
    d.line([(x + 52 * s, fy - 285 * s), (x + 70 * s, fy - 220 * s), (cx_, cy_ + 12 * s)], M, max(2, 18 * s))
    d.rect(x + 30 * s, fy - 214 * s, x + 76 * s, fy - 206 * s, (250, 250, 252), r=4 * s)          # saucer
    d.rect(cx_ - 14 * s, cy_ - 4 * s, cx_ + 14 * s, cy_ + 20 * s, (250, 250, 252), r=4 * s, ol=OLc, w=2)
    d.arc(cx_ + 16 * s, cy_ + 8 * s, 7 * s, 7 * s, 270, 90, OLc, max(1, 3 * s))
    d.line([(cx_ + 12 * s, cy_ + 20 * s), (cx_ + 26 * s, cy_ + 14 * s)], M, max(2, 5 * s))         # pinky out
    for i in range(2):                                                                            # steam
        k = (t * .6 + i * .5) % 1
        d.ell(cx_ + math.sin(k * 6 + i) * 6 * s, cy_ - 14 * s - k * 40 * s, 5 * s, 7 * s, (255, 255, 255, int(160 * (1 - k))))

def odd_octopus(d, x, fy, t, s=1.0):
    """A purple octopus sitting on a traffic cone, juggling three oranges with four of its arms."""
    d.poly([(x - 50 * s, fy), (x + 50 * s, fy), (x + 12 * s, fy - 120 * s), (x - 12 * s, fy - 120 * s)], (246, 120, 30), (40, 20, 10), 3)
    d.rect(x - 60 * s, fy - 8 * s, x + 60 * s, fy, (246, 120, 30), ol=(40, 20, 10), w=3)
    d.poly([(x - 34 * s, fy - 50 * s), (x + 34 * s, fy - 50 * s), (x + 26 * s, fy - 76 * s), (x - 26 * s, fy - 76 * s)], (250, 250, 250))
    P_, P2 = (150, 70, 180), (110, 44, 140)
    by = fy - 190 * s
    for i in range(8):
        a = math.radians(200 + i * 20)
        ph = t * 3 + i
        if i in (2, 3, 4, 5):                                                                    # juggling arms swing up
            ex, ey = x + math.cos(a) * 90 * s, by - 20 * s - abs(math.sin(ph)) * 40 * s
        else:
            ex, ey = x + math.cos(a) * 110 * s, by + 90 * s + math.sin(ph) * 10 * s
        mx, my = (x + ex) / 2 + math.sin(ph) * 14 * s, (by + 30 * s + ey) / 2
        d.line(spline([(x, by + 30 * s), (mx, my), (ex, ey)], 6, closed=False), P2, max(3, 20 * s))
        d.line(spline([(x, by + 30 * s), (mx, my), (ex, ey)], 6, closed=False), P_, max(2, 14 * s))
    d.ell(x, by, 64 * s, 70 * s, P_, (40, 20, 50), 4)
    d.ell(x - 20 * s, by - 30 * s, 16 * s, 12 * s, (190, 120, 214))
    for sd in (-1, 1):
        d.ell(x + sd * 24 * s, by + 6 * s, 14 * s, 16 * s, (255, 255, 255), (40, 20, 50), 2)
        d.ell(x + sd * 24 * s + math.sin(t * 3) * 4 * s, by + 8 * s, 6 * s, 8 * s, (20, 16, 24))
    for i in range(3):                                                                            # the oranges
        ph = (t * 1.4 + i / 3) % 1
        ox = x + (-60 + 120 * ph if i % 2 else 60 - 120 * ph) * s
        oy = by - 70 * s - math.sin(ph * math.pi) * 110 * s
        d.ell(ox, oy, 15 * s, 15 * s, (250, 150, 20), (120, 60, 10), 2)
        d.ell(ox - 4 * s, oy - 5 * s, 4 * s, 3 * s, (255, 220, 140))

ODD = {'cow': odd_cow, 'knight': odd_knight, 'octopus': odd_octopus}

# ================================================================ backgrounds (static, cached) + per-scene life
HOR = 760
def _sky(c0, c1, h=HOR): return grad(h * K, W * K, c0, c1)
def _base(sky, ground, h=HOR):
    arr = np.concatenate([_sky(*sky, h=h), grad((H - h) * K, W * K, *ground)])
    return Image.fromarray(arr.astype(np.uint8))
def _glow(img, x, y, r, col, a=120):
    g = Image.new('L', img.size, 0)
    ImageDraw.Draw(g).ellipse([(x - r) * K, (y - r) * K, (x + r) * K, (y + r) * K], fill=a)
    g = g.filter(ImageFilter.GaussianBlur(r * K * .45))
    return Image.composite(Image.new('RGB', img.size, col), img, g)
def _hills(d, pts, col):
    d.poly(spline(pts, 8, closed=False) + [(W + 40, HOR + 4), (-40, HOR + 4)], col)

@lru_cache(None)
def logo(name, h):
    im = Image.open(os.path.join(ASSETS, name)).convert('RGBA')
    bb = im.getbbox(); im = im.crop(bb)
    return im.resize((max(1, int(im.width * h * K / im.height)), int(h * K)), Image.LANCZOS)
def put_logo(img, name, cx, cy, h, a=1.0):
    lg = logo(name, h)
    if a < 1: lg = lg.copy(); lg.putalpha(lg.getchannel('A').point(lambda v: int(v * a)))
    img.alpha_composite(lg, (int(cx * K - lg.width / 2), int(cy * K - lg.height / 2))) if img.mode == 'RGBA' else \
        img.paste(lg, (int(cx * K - lg.width / 2), int(cy * K - lg.height / 2)), lg)

@lru_cache(None)
def photo_tile(name, w, h):
    ph = Image.open(os.path.join(ASSETS, name)).convert('RGB')
    r = max(w * K / ph.width, h * K / ph.height)
    ph = ph.resize((int(ph.width * r) + 1, int(ph.height * r) + 1), Image.LANCZOS)
    x0, y0 = (ph.width - w * K) // 2, (ph.height - h * K) // 2
    return ph.crop((x0, y0, x0 + w * K, y0 + h * K))

SHOW = {   # wall, floor, panel, trim, ceiling, logo, name, night windows
    'tesla': dict(wall=((236, 238, 241), (250, 250, 251)), floor=((196, 198, 202), (232, 233, 235)), panel=(244, 245, 247),
                  trim=(200, 30, 40), ceil=(250, 250, 252), logo='logo_tesla.png', name='T E S L A', namecol=(30, 32, 38)),
    'tesla_night': dict(wall=((30, 34, 46), (52, 56, 70)), floor=((70, 72, 80), (120, 122, 130)), panel=(40, 44, 58),
                        trim=(220, 36, 46), ceil=(24, 26, 34), logo='logo_tesla.png', name='T E S L A', namecol=(240, 240, 244), night=True),
    'duo': dict(wall=((226, 230, 236), (244, 246, 248)), floor=((150, 154, 162), (204, 206, 212)), panel=(236, 238, 242),
                trim=(30, 60, 140), ceil=(240, 242, 246), logo=None, name='', namecol=(30, 32, 38)),
}
@lru_cache(None)
def bg_showroom(kind):
    B = SHOW[kind]
    arr = np.concatenate([grad(WALL_Y * K, W * K, *B['wall']), grad((H - WALL_Y) * K, W * K, *B['floor'])])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    d.rect(0, 0, W, 84, B['ceil']); d.rect(0, 78, W, 84, tuple(int(c * .8) for c in B['ceil']))
    for x in range(30, W, 210):                                                   # floor-to-ceiling glass bays
        if B.get('night'):
            shade(d, [(x, 120), (x + 190, 120), (x + 190, WALL_Y - 40), (x, WALL_Y - 40)], (14, 20, 44), (40, 40, 80), 120, WALL_Y - 40)
            rng = np.random.default_rng(x)
            for _ in range(14):                                                    # distant city lights
                px, py = x + rng.uniform(8, 182), rng.uniform(560, WALL_Y - 60)
                d.rect(px, py, px + 6, py + 9, (255, 214, 120, int(rng.uniform(120, 255))))
        else:
            shade(d, [(x, 120), (x + 190, 120), (x + 190, WALL_Y - 40), (x, WALL_Y - 40)], (214, 230, 246), (240, 246, 252), 120, WALL_Y - 40)
            d.poly([(x + 30, 120), (x + 80, 120), (x + 20, WALL_Y - 40), (x - 30 + 30, WALL_Y - 40)], (255, 255, 255, 70))
        d.rect(x - 4, 110, x + 4, WALL_Y - 30, B['panel'])
        d.rect(x + 186, 110, x + 194, WALL_Y - 30, B['panel'])
    for px in (230, 459, 690):                                                     # linear light strips
        d.rect(px - 90, 90, px + 90, 100, (255, 250, 236))
    d.rect(0, WALL_Y - 30, W, WALL_Y, B['panel']); d.rect(0, WALL_Y - 6, W, WALL_Y, B['trim'])
    for i, y in enumerate(range(WALL_Y + 70, H, 150)):
        d.line([(0, y + i * 14), (W, y + i * 14)], tuple(min(255, c + 14) for c in B['floor'][1]), 2)
    img = spot(img, CX, 120, 80, 480, 820, 70 if not B.get('night') else 90)
    d = D(img)
    d.rect(CX - 230, 150, CX + 230, 360, (250, 250, 252) if not B.get('night') else (16, 18, 26), r=18,
           ol=B['trim'] + (255,), w=4)                                             # brand plinth sign
    if B['logo']:
        put_logo(img, B['logo'], CX, 230, 110)
        d.text(CX, 322, B['name'], 34, B['namecol'], path=FONT_X)
    else:
        put_logo(img, 'logo_honda.png', CX - 110, 255, 120)
        put_logo(img, 'logo_vw.png', CX + 110, 255, 130)
        d.text(CX, 255, 'vs', 40, (40, 40, 48))
    if kind == 'duo':
        for cx in (230, 680):
            d.ell(cx, 905, 240, 36, (14, 16, 16)); d.ell(cx, 899, 234, 32, (46, 46, 50), (30, 60, 140), 4)
    else:
        d.ell(CX, 905, 400, 50, (14, 16, 16)); d.ell(CX, 897, 394, 44, (46, 46, 50), B['trim'], 5); d.ell(CX, 897, 340, 34, (60, 60, 64))
    return img

@lru_cache(None)
def bg_dragstrip():
    img = _base(((92, 150, 224), (200, 226, 246)), ((70, 72, 78), (120, 122, 128)))
    d = D(img)
    for i, (cx, cy, rx) in enumerate(((180, 300, 90), (760, 230, 120), (520, 380, 70))):       # clouds
        for dx in (-rx * .6, 0, rx * .6): d.ell(cx + dx, cy - (16 if dx == 0 else 0), rx * .7, rx * .45, (255, 255, 255, 220))
    d.poly([(0, 560), (W, 520), (W, HOR), (0, HOR)], (60, 66, 80))                                # grandstand
    rng = np.random.default_rng(4)
    for row in range(6):
        y = 570 + row * 30
        for x in range(0, W, 14):
            d.ell(x + rng.uniform(-3, 3), y - x * .04 + rng.uniform(-3, 3), 5, 6, tuple(int(c) for c in rng.choice(
                [(230, 60, 60), (240, 240, 240), (60, 120, 220), (250, 200, 40), (40, 40, 50)])))
    d.rect(0, HOR - 20, W, HOR, (220, 220, 220)); d.line([(0, HOR - 10), (W, HOR - 10)], (200, 30, 40), 5)   # wall
    for x in range(0, W, 60): d.text(x + 30, HOR - 10, 'DRAG', 12, (255, 255, 255))
    d.poly([(0, HOR), (W, HOR), (W, H), (0, H)], (66, 68, 74))
    for i in range(3):                                                                            # lane lines in perspective
        x0 = 160 + i * 380; d.poly([(x0 - 4, HOR), (x0 + 4, HOR), (x0 * 1.6 - 300 + 20, H), (x0 * 1.6 - 300 - 20, H)], (240, 240, 240))
    d.rect(0, 905, W, 925, (255, 255, 255, 230))                                                  # start line
    for x in range(0, W, 40): d.rect(x, 905, x + 20, 915, (20, 20, 20)); d.rect(x + 20, 915, x + 40, 925, (20, 20, 20))
    d.rect(842, 420, 856, 905, (50, 50, 56))                                                      # christmas tree pole
    d.rect(812, 420, 886, 720, (24, 24, 28), r=8)
    return img
def life_dragstrip(img, t, p):
    d = D(img)
    ta = A(p['go']) if 'go' in p else 1e9
    for i in range(4):                                                            # staging lights count down to the launch
        y = 450 + i * 64
        on = (t >= ta - .9 + i * .3) if i < 3 else (t >= ta)
        col = ((250, 190, 30) if i < 3 else (40, 230, 90)) if on else (60, 54, 40)
        for sd in (-1, 1): d.ell(849 + sd * 18, y, 14, 14, col)
        if on: img = _glow(img, 849, y, 46, col, 90); d = D(img)
    return img

@lru_cache(None)
def bg_desert():
    img = _base(((40, 30, 90), (250, 150, 80)), ((170, 110, 70), (214, 160, 108)))
    img = _glow(img, 700, HOR - 70, 220, (255, 220, 140), 200); d = D(img)
    d.ell(700, HOR - 70, 90, 90, (255, 214, 120))
    for y, a in ((HOR - 110, 70), (HOR - 80, 50)): d.rect(560, y, 840, y + 10, (250, 120, 90, a))
    _hills(d, [(-40, HOR - 40), (120, HOR - 60), (220, HOR - 150), (360, HOR - 150), (420, HOR - 60), (640, HOR - 50),
               (700, HOR - 210), (900, HOR - 210), (960, HOR - 60), (1120, HOR - 40)], (150, 70, 80))
    _hills(d, [(-40, HOR - 10), (260, HOR - 30), (520, HOR - 12), (820, HOR - 40), (1120, HOR - 10)], (110, 50, 70))
    d.poly([(CX - 14, HOR), (CX + 14, HOR), (CX + 900, H), (CX - 900, H)], (60, 58, 64))           # road to the horizon
    d.poly([(CX - 18, HOR), (CX - 12, HOR), (CX - 860, H), (CX - 900, H)], (230, 220, 200))
    d.poly([(CX + 12, HOR), (CX + 18, HOR), (CX + 900, H), (CX + 860, H)], (230, 220, 200))
    for cx, s in ((90, 1.0), (980, 1.3), (230, .6)):                                              # saguaro cacti
        b = HOR + 160 * s
        d.rect(cx - 16 * s, b - 200 * s, cx + 16 * s, b, (60, 110, 70), r=16 * s, ol=(30, 60, 40), w=3)
        for sd in (-1, 1):
            d.rect(cx + sd * 30 * s - 10 * s, b - 150 * s, cx + sd * 30 * s + 10 * s, b - 90 * s, (60, 110, 70), r=10 * s, ol=(30, 60, 40), w=3)
            d.rect(cx + sd * 10 * s, b - 100 * s, cx + sd * 34 * s, b - 82 * s, (60, 110, 70), r=8 * s)
    return img
def life_desert(img, t, p):
    d = D(img)
    for i in range(8):                                                            # centre dashes rushing at the camera
        k = ((t * .9 + i / 8) % 1) ** 2
        y = HOR + k * (H - HOR); w_ = 3 + k * 30; h_ = 6 + k * 120
        d.poly([(CX - w_, y), (CX + w_, y), (CX + w_ * 1.1, y + h_), (CX - w_ * 1.1, y + h_)], (250, 210, 60))
    return img

@lru_cache(None)
def bg_workshop(sign):
    arr = np.concatenate([grad(WALL_Y * K, W * K, (150, 158, 168), (186, 192, 200)), grad((H - WALL_Y) * K, W * K, (118, 120, 124), (160, 162, 166))])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    for x in range(0, W, 54): d.line([(x, 90), (x, 520)], (138, 146, 156), 3)                     # corrugated upper wall
    d.rect(0, 520, W, WALL_Y, (210, 214, 220)); d.rect(0, 520, W, 532, (240, 200, 40))
    for x in range(0, W, 60): d.poly([(x, 520), (x + 30, 520), (x + 18, 532), (x - 12, 532)], (30, 30, 34))   # hazard stripe
    d.rect(0, 0, W, 90, (60, 64, 72))
    for x in (160, 459, 760):                                                                     # fluorescent tubes
        d.rect(x - 120, 100, x + 120, 116, (255, 255, 250), r=6); d.rect(x - 124, 96, x + 124, 100, (90, 94, 100))
    d.rect(40, 150, 300, 420, (214, 190, 150), r=6, ol=(120, 100, 70), w=4)                       # pegboard + tools
    for i in range(5):
        for j in range(4): d.ell(70 + i * 50, 180 + j * 60, 3, 3, (120, 100, 70))
    for i, (x, h_, c) in enumerate(((80, 120, (200, 40, 40)), (130, 90, (60, 60, 70)), (180, 140, (40, 90, 200)), (230, 100, (60, 60, 70)), (270, 80, (240, 180, 30)))):
        d.rect(x - 6, 200, x + 6, 200 + h_, c, r=4); d.ell(x, 200, 14, 10, (150, 154, 160))
    d.rect(800, 300, 1000, 520, (200, 30, 36), r=10, ol=(90, 10, 14), w=4)                         # red tool chest
    for j in range(4): d.rect(814, 318 + j * 48, 986, 356 + j * 48, (220, 50, 56), r=4); d.rect(880, 332 + j * 48, 920, 338 + j * 48, (230, 230, 236))
    d.rect(440 - 200, 150, 440 + 200, 220, (24, 26, 32), r=10)
    d.text(440, 186, sign, 44, (255, 255, 255), path=FONT_X)
    for x, y in ((60, 760), (120, 760), (90, 690)):                                               # tyre stack
        d.ell(x + 900, y, 56, 34, (26, 26, 30), (60, 60, 66), 4); d.ell(x + 900, y, 24, 14, (60, 60, 66))
    d.rect(0, WALL_Y - 4, W, WALL_Y + 4, (90, 92, 96))
    for (x, y, rx) in ((200, 1300, 120), (800, 1500, 90), (520, 1700, 160)):                      # oil stains
        d.ell(x, y, rx, rx * .3, (90, 92, 96, 120))
    for sd in (-1, 1):                                                                            # two-post lift
        d.rect(CX + sd * 330 - 20, 380, CX + sd * 330 + 20, 930, (220, 180, 30), r=4, ol=(120, 90, 10), w=3)
    return img
def life_workshop(img, t, p):
    d = D(img)
    rng = np.random.default_rng(int(t * 15))                                       # welding sparks in the back corner
    if (t % 2.6) < 1.4:
        img = _glow(img, 120, 900, 60, (255, 230, 160), 120); d = D(img)
        for _ in range(10):
            a = rng.uniform(math.pi, 2 * math.pi); r = rng.uniform(10, 60)
            d.line([(120, 900), (120 + math.cos(a) * r, 900 + math.sin(a) * r)], (255, 220, 120), 3)
    return img

@lru_cache(None)
def bg_night_street():
    img = _base(((10, 12, 30), (40, 40, 80)), ((30, 32, 40), (60, 62, 74)))
    d = D(img)
    rng = np.random.default_rng(9)
    x = -20
    while x < W:                                                                                  # skyline with lit windows
        bw, bh = rng.uniform(110, 190), rng.uniform(260, 600)
        d.rect(x, HOR - bh, x + bw, HOR, (26, 28, 46) if rng.random() < .5 else (34, 34, 56))
        for wy in range(int(HOR - bh + 24), HOR - 30, 34):
            for wx in range(int(x + 14), int(x + bw - 20), 28):
                if rng.random() < .45: d.rect(wx, wy, wx + 14, wy + 18, (255, 210, 110, int(rng.uniform(120, 240))))
        x += bw + rng.uniform(4, 20)
    d.rect(300, 250, 560, 330, (20, 20, 30), r=12)                                                # neon sign
    d.text(430, 290, 'OPEN 24/7', 40, (255, 70, 160), stroke=2, sc=(255, 170, 220))
    img = _glow(img, 430, 290, 130, (255, 60, 160), 60); d = D(img)
    d.rect(0, HOR, W, HOR + 30, (80, 82, 92))                                                     # kerb
    for lx in (120, 820):                                                                         # street lamps
        d.rect(lx - 6, 330, lx + 6, HOR + 10, (50, 52, 60)); d.rect(lx - 40, 320, lx + 10, 336, (50, 52, 60), r=6)
        img = _glow(img, lx - 30, 340, 120, (255, 220, 150), 110); d = D(img)
        d.ell(lx - 30, 340, 18, 8, (255, 240, 200))
    for i in range(14):                                                                           # wet reflections
        y = HOR + 60 + i * 80; d.rect(rng.uniform(0, 900), y, rng.uniform(0, 900) + 160, y + 6, (255, 220, 150, 40))
    return img
def life_rain(img, t, p):
    d = D(img)
    rng = np.random.default_rng(1)
    xs, ys, sp = rng.uniform(-200, W, 120), rng.uniform(0, H, 120), rng.uniform(1600, 2400, 120)
    for x, y, v in zip(xs, ys, sp):
        yy = (y + t * v) % (H + 100) - 50; xx = x + (yy * .18)
        d.line([(xx, yy), (xx + 7, yy + 40)], (200, 210, 240, 110), 2)
    for i in range(6):                                                            # puddle ripples
        k = (t * .8 + i / 6) % 1
        cx_, cy_ = 120 + (i * 173) % 860, 1000 + (i * 97) % 180
        d.ell(cx_, cy_, 10 + k * 50, (10 + k * 50) * .25, None, (220, 230, 255, int(120 * (1 - k))), 2)
    if p.get('tow'):                                                              # tow truck beacon washing over the scene
        ph = (t * 2.2) % 1
        img = _glow(img, 1000, 600, 260, (255, 160, 20), int(110 * (0.5 + 0.5 * math.sin(ph * 2 * math.pi))))
        d = D(img)
        d.rect(930, 560, 1080, 760, (230, 180, 30), r=10, ol=(80, 60, 10), w=4)
        d.rect(950, 580, 1040, 650, (40, 60, 80), r=6)
        d.rect(960, 540, 1030, 560, (255, 140, 20) if ph < .5 else (120, 70, 20), r=4)
        d.ell(990, 760, 34, 34, (20, 20, 24))
    return img

@lru_cache(None)
def bg_lot(time):
    if time == 'day': sky, grd, sun = ((90, 160, 230), (210, 232, 248)), ((80, 82, 88), (128, 130, 136)), None
    else: sky, grd, sun = ((60, 50, 110), (250, 140, 90)), ((70, 62, 70), (120, 104, 104)), (180, HOR - 60)
    img = _base(sky, grd)
    if sun: img = _glow(img, *sun, 200, (255, 200, 120), 200)
    d = D(img)
    if sun: d.ell(*sun, 70, 70, (255, 220, 150))
    _hills(d, [(-40, HOR - 60), (200, HOR - 120), (430, HOR - 80), (700, HOR - 140), (1120, HOR - 70)],
           (110, 150, 110) if time == 'day' else (90, 70, 100))
    rng = np.random.default_rng(2)
    for x in range(-20, W, 70):                                                                   # tree line
        h_ = rng.uniform(70, 130); col = (60, 110, 70) if time == 'day' else (60, 50, 70)
        d.ell(x, HOR - h_ * .6, 46, h_ * .6, col)
    d.rect(0, HOR - 30, W, HOR, (210, 210, 214) if time == 'day' else (150, 130, 140))           # low fence
    for x in range(0, W, 40): d.rect(x, HOR - 44, x + 6, HOR, (160, 160, 166))
    for i in range(3):                                                                            # parked cars, back row
        x0 = 30 + i * 360
        c = road_car(((200, 40, 40), (240, 240, 240), (40, 60, 120))[i], 300)
        img.paste(c, (int((x0 - 30) * K), int((HOR + 40 - 300 * .6) * K)), c)
    d = D(img)
    for x in range(-200, W + 200, 230):                                                           # parking bays
        d.line([(x, HOR + 120), (x - 260, H)], (240, 240, 230, 160), 6)
    d.rect(900, 160, 916, HOR, (60, 60, 66))                                                      # USED CARS sign
    d.rect(760, 150, 1060, 300, (200, 30, 40), r=14, ol=(250, 210, 60), w=6)
    d.text(910, 200, 'USED', 52, (255, 255, 255)); d.text(910, 260, 'CARS', 52, (250, 210, 60))
    return img
def life_lot(img, t, p):
    d = D(img)
    cols = [(230, 40, 50), (250, 200, 40), (40, 120, 230), (60, 190, 100)]
    for row, (y0, y1) in enumerate(((120, 200), (180, 240))):                                      # bunting flapping in the wind
        for i in range(14):
            u = i / 13; x = -20 + u * 800
            y = y0 + (y1 - y0) * u + math.sin(u * math.pi) * 60 + row * 10
            fl = math.sin(t * 6 + i) * 6
            d.poly([(x - 18, y), (x + 18, y), (x + fl, y + 44)], cols[(i + row) % 4])
        d.line([(-20, y0 + row * 10), (380, y0 + (y1 - y0) * .5 + 60 + row * 10), (780, y1 + row * 10)], (40, 40, 46), 2)
    return img

@lru_cache(None)
def bg_country():
    img = _base(((110, 170, 236), (220, 236, 250)), ((80, 140, 70), (120, 170, 90)))
    d = D(img)
    for cx, cy, rx in ((200, 220, 110), (820, 300, 90)):
        for dx in (-rx * .6, 0, rx * .6): d.ell(cx + dx, cy - (18 if dx == 0 else 0), rx * .75, rx * .45, (255, 255, 255, 230))
    _hills(d, [(-40, HOR - 120), (240, HOR - 200), (560, HOR - 130), (860, HOR - 220), (1120, HOR - 140)], (130, 170, 120))
    _hills(d, [(-40, HOR - 40), (300, HOR - 100), (640, HOR - 50), (1120, HOR - 90)], (96, 150, 84))
    mx, my = 760, HOR - 150                                                                       # stately manor on the hill
    d.rect(mx - 130, my - 70, mx + 130, my, (226, 214, 190), ol=(120, 100, 80), w=3)
    d.poly([(mx - 140, my - 70), (mx, my - 130), (mx + 140, my - 70)], (120, 70, 60))
    for i in range(6):
        d.rect(mx - 110 + i * 40, my - 52, mx - 90 + i * 40, my - 20, (80, 100, 130))
    for sd in (-1, 1): d.rect(mx + sd * 100 - 8, my - 150, mx + sd * 100 + 8, my - 110, (150, 90, 70))
    for x in range(-20, W, 90): d.ell(x, HOR - 10, 60, 30, (60, 110, 60))                          # hedgerow
    d.rect(0, HOR + 40, W, HOR + 70, (150, 150, 140)); d.rect(0, HOR + 36, W, HOR + 44, (180, 180, 170))   # stone wall
    for x in range(0, W, 46): d.line([(x, HOR + 44), (x, HOR + 70)], (120, 120, 112), 2)
    d.poly([(0, HOR + 120), (W, HOR + 90), (W, 960), (0, 990)], (90, 92, 96))                      # country lane
    d.line([(0, 955), (W, 925)], (240, 240, 230), 4)
    for x, y, s in ((90, HOR + 40, 1.2), (1000, HOR + 30, 1.0)):                                  # oak trees
        d.rect(x - 14 * s, y - 160 * s, x + 14 * s, y, (100, 70, 50))
        for dx, dy, r_ in ((-50, -170, 70), (40, -190, 80), (0, -240, 70)): d.ell(x + dx * s, y + dy * s, r_ * s, r_ * .8 * s, (60, 120, 60))
    return img

@lru_cache(None)
def bg_office():
    arr = np.concatenate([grad(WALL_Y * K, W * K, (226, 218, 204), (240, 234, 224)), grad((H - WALL_Y) * K, W * K, (120, 96, 80), (150, 124, 104))])
    img = Image.fromarray(arr.astype(np.uint8)); d = D(img)
    shade(d, [(80, 150), (520, 150), (520, 620), (80, 620)], (130, 190, 240), (210, 232, 250), 150, 620)      # window + skyline
    rng = np.random.default_rng(5)
    for x in range(80, 520, 50):
        h_ = rng.uniform(100, 300); d.rect(x, 620 - h_, x + 44, 620, (150, 170, 196))
    for y in range(150, 620, 26): d.rect(80, y, 520, y + 10, (240, 240, 236, 120))                # blinds
    d.rect(70, 140, 530, 630, None, ol=(90, 70, 56), w=10)
    d.rect(600, 160, 960, 420, (24, 26, 32), r=10, ol=(60, 60, 66), w=6)                          # wall monitor
    d.rect(620, 180, 940, 400, (34, 60, 110), r=4)
    d.text(780, 290, 'FINANCE', 48, (255, 255, 255), path=FONT_X)
    for i, x in enumerate((620, 720, 820)):                                                       # framed awards
        d.rect(x, 470, x + 80, 570, (250, 246, 236), ol=(160, 120, 40), w=5); d.ell(x + 40, 520, 18, 18, (210, 170, 60))
    d.ell(990, 470, 60, 50, (60, 140, 70)); d.ell(960, 420, 40, 50, (70, 160, 80)); d.ell(1020, 420, 40, 50, (60, 140, 70))   # plant
    d.rect(960, 500, 1020, 600, (190, 110, 70), r=6)
    d.rect(0, WALL_Y - 26, W, WALL_Y, (110, 84, 64))
    d.ell(300, 760, 70, 70, (250, 250, 250), (60, 60, 66), 5)                                     # wall clock
    d.line([(300, 760), (300, 712)], (30, 30, 36), 5)
    return img
def life_office(img, t, p):
    d = D(img)
    a = t * 1.2
    d.line([(300, 760), (300 + 40 * math.cos(a), 760 + 40 * math.sin(a))], (200, 30, 40), 3)    # clock seconds hand racing
    return img

@lru_cache(None)
def bg_track():
    img = _base(((80, 150, 230), (200, 226, 248)), ((70, 150, 70), (90, 170, 80)))
    d = D(img)
    for cx, cy, rx in ((260, 260, 100), (800, 200, 120)):
        for dx in (-rx * .6, 0, rx * .6): d.ell(cx + dx, cy - (16 if dx == 0 else 0), rx * .7, rx * .45, (255, 255, 255, 230))
    d.rect(0, HOR - 170, W, HOR - 40, (230, 232, 236)); d.rect(0, HOR - 180, W, HOR - 170, (40, 44, 52))   # pit building
    for x in range(20, W, 120): d.rect(x, HOR - 150, x + 90, HOR - 60, (60, 70, 90))
    for x in range(0, W, 40): d.rect(x, HOR - 210, x + 30, HOR - 186, ((230, 40, 40), (250, 250, 250))[(x // 40) % 2])
    d.rect(0, HOR - 40, W, HOR, (210, 210, 214))
    for x in range(0, W, 70): d.text(x + 35, HOR - 20, 'SPEED', 14, (220, 30, 40))
    d.poly([(0, 800), (W, 780), (W, 1000), (0, 1030)], (70, 72, 78))                              # track
    for x in range(0, W + 60, 60):                                                                # kerbs
        d.poly([(x, 1030 - x * .028), (x + 60, 1030 - (x + 60) * .028), (x + 60, 1050 - (x + 60) * .028), (x, 1050 - x * .028)],
               ((220, 30, 40), (250, 250, 250))[(x // 60) % 2])
    for x in range(-40, W, 90): d.ell(x, 788, 40, 18, (40, 40, 44), (20, 20, 24), 3)               # tyre wall
    d.rect(960, 300, 970, HOR - 200, (60, 60, 66))                                                # checkered flag pole
    return img
def life_track(img, t, p):
    d = D(img)
    for i in range(4):
        for j in range(3):
            wv = math.sin(t * 6 + i * .8) * 8
            d.rect(970 + i * 24, 300 + j * 24 + wv, 994 + i * 24, 324 + j * 24 + wv, ((20, 20, 20), (250, 250, 250))[(i + j) % 2])
    return img

@lru_cache(None)
def bg_snow():
    img = _base(((150, 180, 220), (226, 236, 248)), ((236, 240, 248), (250, 252, 255)))
    d = D(img)
    for pts, col in (([(-40, HOR - 60), (160, HOR - 400), (330, HOR - 160), (520, HOR - 480), (760, HOR - 200), (900, HOR - 380), (1120, HOR - 80)], (110, 130, 170)),
                     ([(-40, HOR - 20), (240, HOR - 220), (480, HOR - 60), (760, HOR - 260), (1120, HOR - 30)], (150, 170, 200))):
        d.poly(pts + [(1120, HOR + 4), (-40, HOR + 4)], col)
    for x, y in ((160, HOR - 400), (520, HOR - 480), (900, HOR - 380)):                           # snow caps
        d.poly([(x - 70, y + 90), (x, y), (x + 70, y + 90), (x + 30, y + 74), (x, y + 96), (x - 34, y + 76)], (250, 252, 255))
    for x in range(-20, W, 64):                                                                   # pine line
        h_ = 120 + (x * 37 % 60)
        d.poly([(x - 34, HOR + 20), (x, HOR + 20 - h_), (x + 34, HOR + 20)], (40, 90, 80))
        d.poly([(x - 20, HOR - h_ * .45), (x, HOR + 20 - h_), (x + 20, HOR - h_ * .45)], (245, 248, 255))
    d.poly([(0, 820), (W, 800), (W, 1000), (0, 1030)], (150, 156, 170))                           # snowy road with tracks
    for y in (870, 940): d.line([(0, y + 20), (W, y)], (120, 126, 140), 10)
    return img
def life_snow(img, t, p):
    d = D(img)
    rng = np.random.default_rng(3)
    xs, ys, sp, sz = rng.uniform(0, W, 140), rng.uniform(0, H, 140), rng.uniform(80, 200, 140), rng.uniform(3, 9, 140)
    for x, y, v, s in zip(xs, ys, sp, sz):
        yy = (y + t * v) % H; xx = (x + math.sin(t * 1.5 + y) * 20) % W
        d.ell(xx, yy, s, s, (255, 255, 255, 220))
    return img

BG = {'showroom': (lambda p: bg_showroom(p['brand']), None), 'dragstrip': (lambda p: bg_dragstrip(), life_dragstrip),
      'desert': (lambda p: bg_desert(), life_desert), 'workshop': (lambda p: bg_workshop(p['sign']), life_workshop),
      'night': (lambda p: bg_night_street(), life_rain), 'lot': (lambda p: bg_lot(p['time']), life_lot),
      'country': (lambda p: bg_country(), None), 'office': (lambda p: bg_office(), life_office),
      'track': (lambda p: bg_track(), life_track), 'snow': (lambda p: bg_snow(), life_snow)}

# ================================================================ cast (same buyer every episode)
SALES_EP = dict(SALES); SALES_EP.update({k: (hexc(v) if isinstance(v, str) else v) for k, v in getattr(E, 'SALES', {}).items()})
if 'suit' in getattr(E, 'SALES', {}): SALES_EP['suit2'] = tuple(int(c * .72) for c in SALES_EP['suit'])
SALES_EP['badgecol'] = getattr(E, 'BADGE', (200, 40, 40))

def _sched(spec, rest, who):
    s = [(0.0,) + spec.get('open', rest)]
    for li in range(NL):
        if E.LINES[li][0] != who or li not in spec: continue
        lp, rp, ex = spec[li]
        s.append((LS[li] - .05, lp, rp, ex))
        if who == 'S': s.append((LE[li] + .2,) + rest)
    for k, v in spec.items():
        if isinstance(k, str) and k[0] in 'LE0123456789S' and k != 'open': s.append((A(k),) + v)
    return sorted(s, key=lambda e: e[0])
BS = _sched(E.BPOSE, ('rest', 'rest', dict(brows='flat')), 'B')
SS_ = _sched(E.SPOSE, ('clasp', 'clasp', {}), 'S')

MOUTH = None
def load_mouth(voice):
    global MOUTH
    raw = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', voice, '-ac', '1', '-ar', '48000', '-f', 'f32le', '-'],
                                       capture_output=True, check=True).stdout, np.float32)
    n = int(DUR * FPS) + 2; hop = 48000 // FPS
    rms = np.array([np.sqrt((np.mean(raw[i * hop:(i + 1) * hop] ** 2) if i * hop < len(raw) else 0) + 1e-9) for i in range(n)])
    lev = np.clip((20 * np.log10(rms) + 38) / 22, 0, 1)
    M = {'S': np.zeros(n), 'B': np.zeros(n)}
    for w in WORDS:
        a, b = int((w['s'] - .03) * FPS), int((w['e'] + .03) * FPS) + 1
        M[w['spk']][a:b] = lev[a:b]
    f = np.arange(n)
    for k_ in M: M[k_] = M[k_] * (0.75 + 0.25 * np.abs(np.sin(f * 1.9)))
    MOUTH = M
def talking(spk, t): return any(w['spk'] == spk and w['s'] - .05 <= t <= w['e'] + .05 for w in WORDS)
def pose_at(sched, t, tr=0.2):
    i = max(j for j, e in enumerate(sched) if e[0] <= t)
    cur, prev = sched[i], sched[max(0, i - 1)]
    k = io(prog(t, cur[0], tr))
    lp = [a + (b - a) * k for a, b in zip(POSES[prev[1]], POSES[cur[1]])]
    rp = [a + (b - a) * k for a, b in zip(POSES[prev[2]], POSES[cur[2]])]
    ex = dict(cur[3]) if k > 0.5 else dict(prev[3])
    src = cur if k > 0.5 else prev
    ex['out_lpose'], ex['out_rpose'] = src[1] in OUTBEND, src[2] in OUTBEND
    ex['prop'] = cur[3].get('prop', {}) if k > 0.6 else prev[3].get('prop', {})
    return lp, rp, ex

# ================================================================ world per scene
def car_state(c, t, t_in):
    """Animated car placement -> (x0, ground, rot, sag)."""
    x0, g, rot, sag = c['x0'], c['g'], 0.0, c.get('sag', 0.0)
    an = c.get('anim')
    if an == 'launch':                                    # rockets off left, comes back in from the right
        ta = A(c['at'])
        if ta <= t < ta + .8: x0 -= 1500 * prog(t, ta, .8) ** 2; rot = -1.5 * (1 - prog(t, ta, .3))
        elif ta + .8 <= t < ta + 1.4: x0 = 5000
        elif t >= ta + 1.4: x0 += 1300 * (1 - oc(prog(t, ta + 1.4, .9)))
    elif an == 'in_right':
        x0 += 1100 * (1 - oc(prog(t, t_in + .05, 1.1)))
    elif an == 'in_left':
        x0 -= 1100 * (1 - oc(prog(t, t_in + .05, 1.1)))
    elif an == 'lift':
        g -= 150 * oc(prog(t, t_in + .1, 1.6))
    elif an == 'bounce':
        g += math.sin(t * 9) * 2
    if 'sag_at' in c:                                      # air suspension gives up
        for at, amt in c['sag_at']:
            if t >= A(at): sag = max(sag, amt * ob(prog(t, A(at), .35)))
    if 'drop_at' in c and t >= A(c['drop_at']): g += 18 * ob(prog(t, A(c['drop_at']), .3))
    return x0, g, rot, sag

def world(t, sc=None):
    sc = scene_at(t) if sc is None else sc
    S = E.SCN[sc]; t_in = SCENES[sc]
    mk_bg, life = BG[S['bg']]
    img = mk_bg(S).copy()
    if life: img = life(img, t, S)
    if S['bg'] == 'workshop':                                                     # lift arms under the car
        g = car_state(S['cars'][0], t, t_in)[1] if S.get('cars') else 900
        d = D(img)
        for sd in (-1, 1): d.rect(CX + sd * 330 - 60, g + 4, CX + sd * 330 + 60, g + 18, (90, 90, 96), r=4)
    if S.get('trailer'):
        tx = S['trailer']; paste_rot(img, trailer_img(), tx[0], tx[1])
    for c in S.get('cars', []):
        x0, g, rot, sag = car_state(c, t, t_in)
        if x0 < 3000: paste_car(img, c['kind'], x0, g, c['L'], rot, sag)
        if c.get('trim_fall'):                                                    # the cant-rail trim lets go
            tf = A(c['trim_fall'])
            if t >= tf - .3:
                L = c['L']; Hh = L * .42
                k = prog(t, tf, .7)
                p0 = (x0 + .2 * L, g - .62 * Hh); p1 = (x0 + .45 * L, g - .80 * Hh)
                wob = math.sin(t * 40) * 3 if t < tf else 0
                dy = (k ** 2) * (.62 * Hh + 10); rr = k * 18
                cxp, cyp = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2 + dy + wob
                hl = math.hypot(p1[0] - p0[0], p1[1] - p0[1]) / 2; ang = math.atan2(p1[1] - p0[1], p1[0] - p0[0]) + math.radians(rr)
                D(img).line([(cxp - hl * math.cos(ang), cyp - hl * math.sin(ang)), (cxp + hl * math.cos(ang), cyp + hl * math.sin(ang))], (236, 238, 242), 9)
    if S.get('odd'):
        ox, oy, os_ = S['odd']
        ODD[E.ODD](D(img), ox, oy, t, os_)
    d = D(img)
    f = int(round(t * FPS))
    if sc == 0: walk_k, bx0, dur_w = prog(t, 0, 1.0), 170, 11                    # frame 1: already striding in, mid-sentence
    else: walk_k, bx0, dur_w = prog(t, t_in, .7), -60, 13
    bx = bx0 + (270 - bx0) * oc(walk_k)
    for who, x, sched, cfg, spk in (('S', 670, SS_, SALES_EP, 'S'), ('B', bx, BS, BUYER, 'B')):
        lp, rp, ex = pose_at(sched, t)
        st = dict(lpose=lp, rpose=rp, mouth=float(MOUTH[spk][min(f, len(MOUTH[spk]) - 1)]) if MOUTH else 0.0,
                  look=(-1 if who == 'S' else 1))
        st.update(ex)
        st['blink'] = ((t + (0.0 if who == 'S' else 1.3)) % 3.4) < 0.12
        st['dy'] = math.sin(t * 2.2 + (0 if who == 'S' else 1)) * 3 + (-4 if talking(spk, t) and (f // 4) % 2 else 0)
        if who == 'B' and walk_k < 1:
            st['walk'] = t * dur_w; st['dy'] -= abs(math.sin(t * dur_w)) * 10
        if st.get('sweat'): st['sweat'] = t
        person(d, x, FEET_Y, cfg, st)
    return img

PUNCH = [(A(a), amt) for a, amt in E.PUNCH]
def camera(t):
    sc = scene_at(t); t0 = SCENES[sc]
    sx = sy = 0.0
    if sc == 0:
        z = 1.10 - 0.06 * oc(prog(t, 0, 1.6)) + 0.01 * math.sin(t * .5)          # frame 1 already pulling out
        sx = 30 * (1 - oc(prog(t, 0, 1.6)))
    elif sc < len(SCENES) - 1:
        z = 1.05 + 0.02 * io(prog(t, t0, 6))
        sx = 46 * (1 - oc(prog(t, t0, 1.2))) - 26 * io(prog(t, t0 + 1.2, 5))
    else:
        z = 1.03 + 0.01 * math.sin((t - t0) * .6)
        pk = io(prog(t, T_FINAL - .05, .5)); z += 0.16 * pk; sx = 150 * pk        # push in on the salesman's question
    for tp, amt in PUNCH:
        if tp <= t < tp + .5: z += amt * (1 - oc(prog(t, tp, .5)))
    for tp in [A(x) for x in getattr(E, 'SHAKE', [])]:
        if tp - .05 <= t < tp + .6:
            k_ = 1 - prog(t, tp - .05, .65); sx += 14 * k_ * math.sin(t * 61); sy += 10 * k_ * math.sin(t * 47 + 1)
    return z, sx, sy

def shoot(t, sc=None):
    wimg = world(t, sc)
    z, sx, sy = camera(t if sc is None else max(t, SCENES[sc]))
    ax, ay = CX * K, 1150 * K
    cw, ch = W * K / z, H * K / z
    x0 = clamp(ax - ax / z + sx * K, 0, W * K - cw); y0 = clamp(ay - ay / z + sy * K, 0, H * K - ch)
    return wimg.resize((W, H), Image.LANCZOS, box=(x0, y0, x0 + cw, y0 + ch)).convert('RGBA')

# ================================================================ overlays
GREEN, TAG, RED = (70, 200, 120), (255, 214, 64), (226, 48, 58)
INK2, DRED = (24, 20, 16), (176, 20, 30)
COL = {'ink': INK2, 'red': DRED, 'green': (20, 120, 60), 'G': GREEN, 'R': RED, 'Y': TAG, 'W': (255, 255, 255), 'B': (40, 110, 220)}

@lru_cache(None)
def big_photo(name, label, logo_name, w=560, h=330, bar=(20, 22, 30)):
    card = Image.new('RGBA', ((w + 30) * K, (h + 96) * K), (0, 0, 0, 0)); cd = D(card)
    cd.rect(8, 10, w + 28, h + 94, (0, 0, 0, 100), r=14)
    cd.rect(0, 0, w + 20, h + 84, (250, 250, 248), r=14)
    card.paste(photo_tile(name, w, h), (10 * K, 10 * K))
    cd.rect(10, h + 18, w + 10, h + 74, bar, r=10)
    if logo_name:
        lg = logo(logo_name, 34)
        if lg.width / K > 90: lg = lg.resize((int(90 * K), int(lg.height * 90 * K / lg.width)), Image.LANCZOS)
        lw = lg.width / K
        cd.rect(22, h + 24, 38 + lw, h + 68, (250, 250, 248), r=8)
        card.paste(lg, (int(30 * K), int((h + 46) * K - lg.height / 2)), lg)
        x0 = 46 + lw
    else:
        x0 = 20
    size = 30
    while font(size).getlength(label) > (w + 6 - x0) and size > 16: size -= 1
    cd.text((x0 + w + 6) / 2, h + 46, label, size, (255, 255, 255))
    return card

def chip_rows(d, t, rows, y0, a):
    al = int(255 * a)
    for i, (lab, chip, col, tn) in enumerate(rows):
        t_lab = A(tn)
        if t < t_lab - .05: continue
        ra = min(a, prog(t, t_lab - .05, .2)); k_ = popin(t, t_lab - .05, .3)
        w_ = font(32 * K).getlength(chip) / K
        y = y0 + i * 130
        d.text(110, y, lab, 34, (220, 224, 234, int(255 * ra)), anchor='lm', path=FONT_X)
        d.rect(106, y + 30, 106 + (w_ + 36) * k_, y + 86, COL[col] + (al,), r=12)
        if k_ > .6: d.text(106 + (w_ + 36) / 2, y + 59, chip, 32, (255, 255, 255, al))

def _rows(rows): return tuple((tx, sz, COL[c]) for tx, sz, c in rows)

def overlays(t):
    img = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0))
    used = False
    for o in E.OVER:
        a0, a1 = A(o['a']), A(o['b'])
        a = window(t, a0, a1, .12, .25)
        if a <= 0: continue
        used = True
        s = popin(t, a0, .35)
        k = o['k']
        if k == 'photo':
            put(img, big_photo(o['img'], o['label'], o.get('logo'), o.get('w', 560), o.get('h', 330)), o.get('x', CX), o['y'], s * o.get('s', 1), a, o.get('rot', -2))
        elif k == 'vs':                                                                 # two photos side by side
            for j, (im, lab, lg) in enumerate(o['pair']):
                sj = popin(t, a0 + .12 * j, .35)
                put(img, big_photo(im, lab, lg, 360, 230), CX + (-195 if j == 0 else 195), o['y'] + (0 if j == 0 else 30), sj * .98, a, (-3, 3)[j])
            if t > a0 + .25:
                D(img).text(CX, o['y'] + 30, 'VS', 84 * popin(t, a0 + .25, .3), TAG + (int(255 * a),), stroke=7, sc=(10, 10, 16, int(255 * a)))
        elif k == 'card':
            sh = 1.0
            if o.get('jolt') and t >= A(o['jolt']):
                tp = A(o['jolt']); sh = 1 + .07 * math.sin((t - tp) * 14) * math.exp(-(t - tp) * 4)
            put(img, info_card(_rows(o['rows']), o.get('w', 700)), CX, o['y'], s * sh, a, o.get('rot', -1.5))
        elif k == 'tag':
            sw = math.sin((t - a0) * 6) * 4 * math.exp(-(t - a0) * 2)
            put(img, price_tag(o['txt'], o['sub'], COL[o.get('col', 'Y')], o.get('w', 560)), CX, o['y'], s * .9, a, sw + o.get('rot', -3))
        elif k == 'stamp':
            put(img, stamp_img(o['txt'], COL[o.get('col', 'R')], o.get('size', 96)), o.get('x', CX), o['y'], s, a, o.get('rot', 8))
        elif k == 'chips':
            d = D(img)
            d.rect(70, o['y'] - 50, 830, o['y'] - 50 + 130 * len(o['rows']) + 20, (14, 16, 22, int(236 * a)), r=30)
            chip_rows(d, t, o['rows'], o['y'], a)
        elif k == 'logo':
            put(img, logo(o['img'], o.get('h', 120)), o.get('x', CX), o['y'], s, a)
    if t >= T_CARD:                                                                     # final caption card
        used = True
        fa = prog(t, T_CARD, .25); d = D(img)
        F = E.FINAL; y0, dy = 410, 104
        d.rect(50, y0 - 90, 868, y0 + dy * (len(F) - 1) + 80, (12, 14, 20, int(225 * fa)), r=34)
        for i, (txt, size, col) in enumerate(F):
            k_ = popin(t, T_CARD + .08 * i, .3)
            if k_ > .05: d.text(CX, y0 + dy * i, txt, size * k_, COL[col] + (int(255 * fa),), stroke=4, sc=(10, 10, 16, int(255 * fa)))
    return img if used else None

def final_boxes():
    out = []
    for i, (txt, size, _) in enumerate(E.FINAL):
        f = font(size); bb = f.getbbox(txt, anchor='mm', stroke_width=4); y = 410 + 104 * i
        cap = f.getbbox('H')[3] - f.getbbox('H')[1]
        out.append(dict(text=txt, x0=CX + bb[0], x1=CX + bb[2], y0=y + bb[1], y1=y + bb[3], cap_height=cap))
    return out

# ================================================================ captions (tesla-locked system)
def ctext(w): return w['w'].lstrip('.').replace('...', '')
CAP_Y, CAP_SIZE = 1128, 78
def chunks():
    out = []
    for ln in sorted(LINES):
        cur = []
        for w in LINES[ln]:
            if cur and font(CAP_SIZE).getlength(' '.join(ctext(x) for x in cur + [w])) > 800:
                out.append(cur); cur = []
            cur.append(w)
            if w['w'][-1] in '.?!,' or len(cur) == 3:
                out.append(cur); cur = []
        if cur: out.append(cur)
    res = []
    for i, c in enumerate(out):
        nxt = out[i + 1][0]['s'] if i + 1 < len(out) else DUR
        end = nxt if nxt - c[-1]['e'] < 0.6 else c[-1]['e'] + 0.45
        res.append(dict(words=c, s=c[0]['s'], e=T_CARD if i == len(out) - 1 else min(end, T_CARD)))
    return res
CHUNKS = chunks()
def cap_size(ws):
    size = CAP_SIZE
    while font(size).getlength(' '.join(ws)) > 800 and size > 60: size -= 2
    return size
@lru_cache(None)
def caption_img(ci, active):
    ws = [ctext(w) for w in CHUNKS[ci]['words']]
    f = font(cap_size(ws)); total = f.getlength(' '.join(ws)); sp = f.getlength(' ')
    img = Image.new('RGBA', (W, 200), (0, 0, 0, 0)); d = ImageDraw.Draw(img)
    x = (W - total) / 2
    for i, w in enumerate(ws):
        d.text((x, 100), w, font=f, fill=(255, 214, 64) if i == active else (255, 255, 255), anchor='lm', stroke_width=9, stroke_fill=(16, 16, 28))
        x += f.getlength(w) + sp
    return img
def caption_boxes():
    res = []
    for ci, c in enumerate(CHUNKS):
        a = np.array(caption_img(ci, -1).getchannel('A')); ys, xs = np.nonzero(a > 8)
        ox, oy = CX - W // 2, CAP_Y - 100
        ws = [ctext(w) for w in c['words']]; size = cap_size(ws)
        res.append(dict(text=' '.join(ws), s=c['s'], e=c['e'], x0=int(xs.min() + ox), x1=int(xs.max() + ox), y0=int(ys.min() + oy),
                        y1=int(ys.max() + oy), cap_height=int(font(size).getbbox('H')[3] - font(size).getbbox('H')[1])))
    return res
def captions(img, t):
    if t >= T_CARD: return
    live = [ci for ci, c in enumerate(CHUNKS) if c['s'] - 0.02 <= t < c['e']]
    for ci in live[-1:]:
        c = CHUNKS[ci]; act = -1
        for i, w in enumerate(c['words']):
            if w['s'] - .02 <= t: act = i
        ci_img = caption_img(ci, act)
        s = 0.86 + 0.14 * ob(prog(t, c['s'], .12))
        if s != 1: ci_img = ci_img.resize((int(W * s), int(200 * s)), Image.LANCZOS)
        img.alpha_composite(ci_img, (int(CX - ci_img.width / 2), int(CAP_Y - ci_img.height / 2)))

# ================================================================ frame
TR = 0.4
FLASH = [A(x) for x in getattr(E, 'FLASH', [])]
def frame(n, caps=True, ovl=True):
    t = n / FPS
    tr = next((s for s in SCENES[1:] if s - TR / 2 <= t < s + TR / 2), None)
    if tr is None:
        img = shoot(t)
    else:                                                                       # whip pan with motion blur
        k = io(prog(t, tr - TR / 2, TR)); sc_new = SCENES.index(tr)
        a, b = shoot(min(t, tr - .001), sc_new - 1), shoot(max(t, tr), sc_new)
        img = Image.new('RGBA', (W, H), (0, 0, 0, 255)); off = int(W * k)
        img.alpha_composite(a, (-off, 0)); img.alpha_composite(b, (W - off, 0))
        bl = math.sin(math.pi * k)
        if bl > .05:
            smear = img.resize((W // 24, H), Image.BILINEAR).resize((W, H), Image.BILINEAR)
            img = Image.blend(img, smear, min(.85, bl))
    for tf in FLASH:
        if tf <= t < tf + .3: img = Image.blend(img, Image.new('RGBA', img.size, (255, 255, 255, 255)), 0.45 * (1 - prog(t, tf, .3)))
    ov = overlays(t) if t >= 3.0 and ovl else None                                      # nothing over the picture in the first 3 s
    if ov is not None:
        img.alpha_composite(ov.convert('RGBa').resize((W, H), Image.LANCZOS).convert('RGBA'))
    if BEAT[0] + .1 <= t < T_FINAL:
        img = Image.blend(img, Image.new('RGBA', img.size, (0, 0, 0, 255)), 0.22 * io(prog(t, BEAT[0] + .1, .5)))
    if T_FINAL <= t < T_FINAL + .5:
        img = Image.blend(img, Image.new('RGBA', img.size, (255, 255, 255, 255)), 0.25 * (1 - prog(t, T_FINAL, .5)))
    if t >= T_CARD:
        k_ = io(prog(t, T_CARD, 1.0)) * .45; v = vignette()
        img.alpha_composite(Image.merge('RGBA', (*v.split()[:3], v.getchannel('A').point(lambda p: int(p * k_)))))
    if caps: captions(img, t)
    return img.convert('RGB').tobytes()

@lru_cache(None)
def vignette():
    yy, xx = np.mgrid[0:H, 0:W]
    r = np.sqrt(((xx - CX) / (W * .62)) ** 2 + ((yy - 1100) / (H * .55)) ** 2)
    return Image.fromarray(np.dstack([np.zeros((H, W, 3)), np.clip((r - .55) * 1.6, 0, 1) * 255]).astype(np.uint8), 'RGBA')

# ================================================================ audio: voice + cues + the user's music bed (ducked)
def build_audio(voice, music, out_wav):
    SR = sfx.SR
    def load(p, ss=0.0):
        return np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(ss), '-i', p, '-ac', '1', '-ar', str(SR), '-f', 'f32le', '-'],
                                            capture_output=True, check=True).stdout, np.float32).astype(np.float64)
    n = int(DUR * SR)
    v = load(voice); v = np.pad(v, (0, max(0, n - len(v))))[:n]
    m = load(music, getattr(E, 'MUSIC_AT', 0.0)); m = np.pad(m, (0, max(0, n - len(m))))[:n]
    T_ = np.arange(n) / SR
    rng = np.random.default_rng(3)
    speech = np.zeros(n)
    for w in WORDS: speech[int((w['s'] - .08) * SR):int((w['e'] + .12) * SR)] = 1
    k = int(.08 * SR); duck = np.convolve(speech, np.ones(k) / k, mode='same')
    mgain = 10 ** ((-17 + 5 * (1 - duck)) / 20)                                  # music sits ~17 dB under, lifts 5 dB between lines
    mgain *= np.clip(T_ / .25, 0, 1) * np.clip((DUR - T_) / 1.2, 0, 1)
    m = m / (np.sqrt(np.mean(m[:SR * 20] ** 2)) + 1e-9) * 0.1 * mgain
    def tone(f, d, rate, amp=1.0):
        tt = np.arange(int(SR * d)) / SR; return np.sin(2 * np.pi * f * tt) * np.exp(-tt * rate) * amp
    def click(f1=2400, f2=3300, d=0.06):
        tt = np.arange(int(SR * d)) / SR
        return (tone(f1, d, 90) + tone(f2, d, 120) * .7 + rng.standard_normal(len(tt)) * np.exp(-tt * 200) * .6) * .5
    def step():
        a = tone(90, .12, 40, .6); a[:int(SR * .03)] += tone(1200, .03, 200, .15); return a
    def sting():
        d = 2.4; tt = np.arange(int(SR * d)) / SR; s = np.zeros_like(tt)
        for f in (73.4, 110.0, 146.8, 174.6, 220.0):
            for det in (-0.6, 0.6): s += ((tt * (f + det)) % 1 * 2 - 1)
        s = np.convolve(s, np.ones(6) / 6, 'same') * np.exp(-tt * 2.2) * np.minimum(1, tt * 200) * .09
        s += np.sin(2 * np.pi * 48 * tt) * np.exp(-tt * 5) * .9
        return s
    def clank():
        return (tone(523, .5, 7) + tone(1310, .5, 9) * .7 + tone(2210, .5, 12) * .5 + rng.standard_normal(int(SR * .5)) * np.exp(-np.arange(int(SR * .5)) / SR * 30) * .5) * .5
    def hiss():
        tt = np.arange(int(SR * .9)) / SR
        x = rng.standard_normal(len(tt)); x = x - np.convolve(x, np.ones(8) / 8, 'same')
        return x * np.exp(-tt * 3) * .6
    LIB = dict(pop=sfx.pop, whoosh=lambda: sfx.whoosh(.45, 18), thump=sfx.thump, stamp=sfx.stamp, ding=sfx.ding, buzzer=sfx.buzzer,
               cha=sfx.cha_ching, vroom=sfx.vroom, screech=sfx.screech, slide=sfx.slide_down, crash=sfx.crash, boom=sfx.boom,
               click=click, clank=clank, hiss=hiss, step=step, tick=lambda: click(4200, 5200, .03) * .5, sting=sting)
    cues = []
    def add(t0, s, vol): cues.append((int(max(0, t0) * SR), s * vol))
    for k_ in range(3): add(0.02 + k_ * 0.3, step(), .45)
    for s_ in SCENES[1:]:
        add(s_ - .22, sfx.whoosh(.45, 18), .5); add(s_ + .12, sfx.thump(), .32)
        for k_ in range(3): add(s_ + .08 + k_ * .25, step(), .3)
    for o in E.OVER:                                                              # every overlay lands with a pop (stamps thud)
        if A(o['a']) >= 3.0: add(A(o['a']), sfx.stamp() if o['k'] == 'stamp' else sfx.pop(), .3)
    for at, name, vol in E.CUES: add(A(at), LIB[name](), vol)
    for k_ in range(2): add(BEAT[0] + .2 + k_ * .4, LIB['tick'](), .6)
    add(T_FINAL - .02, sting(), .7); add(T_CARD, sfx.pop(), .35)
    fxa = np.zeros(n + SR * 4)
    for i, s in cues: fxa[i:i + len(s)] += s
    mixd = v * 1.0 + fxa[:n] * 0.5 + m
    mixd = np.clip(mixd / max(1.0, np.abs(mixd).max() / 0.95), -1, 1)
    tmp = out_wav + '.pre.wav'
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f64le', '-ar', str(SR), '-ac', '1', '-i', '-', tmp], input=mixd.tobytes(), check=True)
    r = subprocess.run(['ffmpeg', '-hide_banner', '-i', tmp, '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    mj = json.loads(r[r.rindex('{'):r.rindex('}') + 1])
    af = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={mj['input_i']}:measured_TP={mj['input_tp']}:measured_LRA={mj['input_lra']}"
          f":measured_thresh={mj['input_thresh']}:offset={mj['target_offset']}")
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp, '-af', af, '-ar', '48000', '-ac', '2', tmp + '2.wav'], check=True)
    # loudnorm can land short of target: trim the rest with a static gain, keeping >= 1.5 dB true-peak headroom
    r = subprocess.run(['ffmpeg', '-hide_banner', '-nostats', '-i', tmp + '2.wav', '-af', 'ebur128=peak=true', '-f', 'null', '-'],
                       capture_output=True, text=True).stderr
    I = float(r.split('I:')[-1].split('LUFS')[0]); tp = float(r.split('Peak:')[-1].split('dBFS')[0])
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', tmp + '2.wav', '-af', f'volume={min(-14.0 - I, -1.5 - tp):.2f}dB', out_wav], check=True)
    os.remove(tmp); os.remove(tmp + '2.wav')

def thumb(out, voice):
    """Thumbnail: the twist frame (no captions), darkened, with the car photo, brand logo and the hook in big type."""
    load_mouth(voice)
    T = E.THUMB
    img = Image.frombytes('RGB', (W, H), frame(int(A(T['t']) * FPS), caps=False, ovl=False)).convert('RGBA')
    img = Image.blend(img, Image.new('RGBA', img.size, (0, 0, 0, 255)), .25)
    big = Image.new('RGBA', (W * K, H * K), (0, 0, 0, 0)); d = D(big)
    for j, ph in enumerate(T['photos']):
        n_ = len(T['photos']); w_ = 760 if n_ == 1 else 470
        x = W / 2 if n_ == 1 else (W / 2 - 250 + 500 * j)
        put(big, big_photo(ph[0], ph[1], ph[2], w_, int(w_ * .6)), x, 560 + (0 if n_ == 1 else (-20, 40)[j]), 1, 1, (-3, 3)[j % 2])
    y = 1080
    for txt, size, col in T['text']:
        d.text(W / 2, y, txt, size, COL[col], stroke=10, sc=(10, 10, 16)); y += size * 1.12
    img.alpha_composite(big.convert('RGBa').resize((W, H), Image.LANCZOS).convert('RGBA'))
    img.convert('RGB').save(out)

def _init(voice): load_mouth(voice)

if __name__ == '__main__':
    mode = sys.argv[1]
    if mode == 'still':
        load_mouth(sys.argv[4]); Image.frombytes('RGB', (W, H), frame(int(float(sys.argv[2]) * FPS))).save(sys.argv[3])
    elif mode == 'sheet':                                                        # 12 stills across the cut -> one contact sheet
        load_mouth(sys.argv[2]); ts = list(np.linspace(0.05, DUR - .1, 12)) if len(sys.argv) < 5 else [float(x) for x in sys.argv[4].split(',')]
        with Pool(os.cpu_count(), initializer=_init, initargs=(sys.argv[2],)) as pool:
            fr = pool.map(frame, [int(x * FPS) for x in ts])
        cols = 6 if len(ts) > 6 else len(ts); rows = (len(ts) + cols - 1) // cols
        sh = Image.new('RGB', (cols * 270, rows * 480), 'white')
        for i, b in enumerate(fr):
            sh.paste(Image.frombytes('RGB', (W, H), b).resize((270, 480)), ((i % cols) * 270, (i // cols) * 480))
            ImageDraw.Draw(sh).text(((i % cols) * 270 + 6, (i // cols) * 480 + 4), f'{ts[i]:.1f}s', fill=(255, 0, 0))
        sh.save(sys.argv[3])
    elif mode == 'thumb':
        thumb(sys.argv[2], sys.argv[3])
    elif mode == 'meta':
        ons = [x for o in E.OVER for x in ([o.get('txt', ''), o.get('sub', ''), o.get('label', '')] + [r[0] for r in o.get('rows', [])]
                                         + [p_[1] for p_ in o.get('pair', [])])] + [f[0] for f in E.FINAL]
        json.dump(dict(captions=caption_boxes(), final=final_boxes(), onscreen=[x for x in ons if x], duration=DUR, size=[W, H], fps=FPS, scenes=SCENES),
                  open(sys.argv[2], 'w'), indent=1)
    elif mode == 'video':
        voice, music, out = sys.argv[2], sys.argv[3], sys.argv[4]
        t1 = float(sys.argv[5]) if len(sys.argv) > 5 else DUR
        os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
        wav = os.path.splitext(out)[0] + '_mix.wav'
        build_audio(voice, music, wav)
        nf = int(min(t1, DUR) * FPS)
        ff = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                               '-i', '-', '-i', wav, '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-maxrate', '13M',
                               '-bufsize', '26M', '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart',
                               '-shortest', out], stdin=subprocess.PIPE)
        with Pool(os.cpu_count(), initializer=_init, initargs=(voice,)) as pool:
            for i, buf in enumerate(pool.imap(frame, range(nf), chunksize=4)):
                ff.stdin.write(buf)
                if i % 300 == 0: print(f'frame {i}/{nf}', flush=True)
        ff.stdin.close(); ff.wait(); os.remove(wav)
        print('done', out)
