"""Cozy top-down room kit (oblique view, 270x480 native, 4x nearest).

48-colour master palette `PAL` (one char per colour) and hand-authored pixel maps for a lived-in room:
cat (breathing, tail flick), mug, console shelf, monitor frame, gaming chair, plush creature, car posters,
and small floor props. All sprites return float RGBA arrays for `ambient.paste`.
First used by videos/cozy-sim-room.
"""
import os, sys
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ambient import _sprite  # noqa: E402

HEX = {
    '0': '0a1016', '1': '121b24', '2': '1a2732', '3': '233544', '4': '2f4656', '5': '3e5a68', '6': '4e6e78', '7': '6a8a90',
    'a': '2a1c3e', 'b': '40285e', 'c': '5c3a8a', 'd': '7d52c0', 'e': 'a777f0', 'f': 'd2b0ff',
    'g': '1c2f63', 'h': '2850a8', 'i': '3d7ee0', 'j': '66b4ff', 'k': 'b4e4ff',
    'l': '3a2422', 'm': '5e3a2c', 'n': '8a5634', 'o': 'c07a3c', 'p': 'e8a850', 'q': 'ffd88a', 'r': 'fff2c8',
    's': '4a1420', 't': '7a1e2a', 'u': 'b02c34', 'v': 'e0484a', 'w': 'ff8a7a', 'x': '8a5a40', 'y': 'c08862',
    'z': '1e3a2a', 'A': '2e6a3a', 'B': '4fa04a', 'C': '9ad86a',
    'D': '4a4a58', 'E': '6e6e80', 'F': '9a9aae', 'G': 'c8c8d8', 'H': 'f0f0f8',
    'I': '1f6a78', 'J': '3ec8c8', 'K': 'a0fff0', 'L': '8a2a6a', 'M': 'e050a8', 'N': 'ff9ad0',
}
PAL = {k: tuple(int(v[i:i + 2], 16) for i in (0, 2, 4)) for k, v in HEX.items()}
PAL_ARR = np.array(list(PAL.values()), np.float32)          # 48 x 3, for palette quantisation


def S(rows, outline='1', sub=None):
    """Pixel map -> float RGBA. `sub` remaps chars (recolour); `outline` adds a 1px dark edge (None = off)."""
    if sub: rows = [''.join(sub.get(c, c) for c in r) for r in rows]
    if outline:
        h, w = len(rows), max(len(r) for r in rows)
        g = [['.'] * (w + 2) for _ in range(h + 2)]
        for y, r in enumerate(rows):
            for x, c in enumerate(r): g[y + 1][x + 1] = c
        for y in range(h + 2):
            for x in range(w + 2):
                if g[y][x] == '.' and any(0 <= y + dy < h + 2 and 0 <= x + dx < w + 2 and g[y + dy][x + dx] not in '.#'
                                          for dy, dx in ((0, 1), (0, -1), (1, 0), (-1, 0))):
                    g[y][x] = '#'
        rows = [''.join(outline if c == '#' else c for c in r) for r in g]
    return _sprite(rows, PAL)


# ------------------------------------------------------------------ cat (top view, curled, orange tabby)
_CAT = [
    "..m.m...............",
    ".mwmwm....mmmmmm....",
    ".mooom..mmopppppmm..",
    "moppppm.mopnppnpppm.",
    "moqpqpomopnppnppnppm",
    "molpolpmopnppnppnppm",
    "moppppppppnppnppnpom",
    ".mrrrppppppppppppnom",
    "..mrrmoppnppnppnpom.",
    "...mm.moppnppnpppom.",
    ".....mnooppppppoonm.",
    "....mnnoooooooonnm..",
    "...mnnmmmmmmmmmmm...",
    "..mnnm..............",
    "..mnm...............",
]


def cat(breath=0.0, flick=0):
    """breath 0..1 swells the body 1px; flick -1/0/1 bends the tail tip."""
    rows = [list(r) for r in _CAT]
    if breath > .5:                                   # inhale: back rises 1px (extra row of fur on top)
        for x in range(10, 16): rows[0][x] = 'm'
        for x in range(10, 16): rows[1][x] = 'o'
        rows[1][9] = 'm'; rows[1][16] = 'm'
    if flick:
        rows[13][2:6] = list('....'); rows[14][2:5] = list('...')
        if flick > 0: rows[12][0:3] = list('mnn'); rows[11][0:2] = list('mn')
        else: rows[13][3:6] = list('mnm'); rows[14][4:7] = list('mnm')
    return S([''.join(r) for r in rows], outline='0')


# ------------------------------------------------------------------ desk things
MUG = [
    ".GGGGGG...",
    "GlmmmmlG..",
    "GHmmmmHGGG",
    "GHHHHHHG.G",
    "GHHMMHHG.G",
    "GHMHHMHGGG",
    "GHHHHHHG..",
    ".FGGGGF...",
]


def mug(): return S(MUG)


def monitor(w, h):
    """Bezel + stand for a w x h screen; the screen area is [2:2+h, 2:2+w] (draw content there)."""
    rows = ['1' * (w + 4)] + ['10' + '.' * w + '01' for _ in range(h)] + ['1' * (w + 4)]
    rows[0] = '1' + '2' * (w + 2) + '1'
    cx = (w + 4) // 2
    rows += [' ' * (cx - 2) + '2332' + ' ' * (w + 4 - cx - 2), ' ' * (cx - 5) + '22333322' + ' ' * (w + 4 - cx - 3)]
    rows = [r.replace(' ', '.') for r in rows]
    return S(rows, outline='0')


_CONSOLES = {
    'boxy': ["GGGGGGGGGGGGGGGGGGGGGGGG", "GHHHHHHHHHHHHHHHHHHHHHHG", "GGDDDDDDDDDGGGGGGGGGGGGG", "GGGGGGGGGGGGGGGGGGGGGGGG",
             "EEEEEEEEEEEEEEEEEEEEEEEE", "EvEEDDEEDDEEEEEEEEEEEEEE", "EEEEEEEEEEEEEEEEEEEEEEEE", "DDDDDDDDDDDDDDDDDDDDDDDD"],
    'slim': ["2222222222222222222222", "3333333333333333333333", "2222222222222222222222", "2jjj22222222222222D2D2", "1111111111111111111111"],
    'cube': ["..cccccccccccc", ".deeeeeeeeeeec", "deeeeeeeeeeedc", "dccccccccccccc", "dcc1111cccccbc",
             "dcccccccccMcbc", "dcccccccccccbc", "bbbbbbbbbbbbbb"],
    'tower': ["1111111111", "1222222221", "1233333321", "123JJ33321", "1233333321", "1233333321", "1233333321",
              "1222222221", "1222D22221", "1111111111"],
    'handheld': ["GGGGGGGG", "G000000G", "G0IJJI0G", "G0IJJI0G", "G000000G", "GGGGGGGG", "GDGGGvGG", "DDDGGGvG",
                 "GDGGGGGG", "GGGEEGGG", "GGGGGGGG"],
    'pad': [".EEE....EEE.", "EEDEEEEEEvEE", "EDDDEEEEhEuE", "EEDEEDDEEiEE", ".EEEE..EEEE.", "..EE....EE.."],
}


def console(kind): return S(_CONSOLES[kind])


def console_shelf(w=190):
    """Wall shelf (front edge) with five generic consoles standing on it; returns (sprite, led_y)."""
    items = [('boxy', 4), ('cube', 34), ('slim', 54), ('tower', 82), ('handheld', 98), ('pad', 112), ('boxy', 132), ('cube', 162)]
    hgt = 16
    a = np.zeros((hgt + 5, w, 4), np.float32)
    for k, x in items:
        s = console(k); y = hgt - s.shape[0] + 1
        if x + s.shape[1] <= w:
            m = s[..., 3:4] > 0
            a[y:y + s.shape[0], x:x + s.shape[1]] = np.where(m, s, a[y:y + s.shape[0], x:x + s.shape[1]])
    a[hgt:hgt + 1, :] = (*PAL['n'], 255); a[hgt + 1:hgt + 3, :] = (*PAL['m'], 255); a[hgt + 3, :] = (*PAL['l'], 255)
    a[hgt, :, :3] = PAL['o']
    return a, hgt + 4


# ------------------------------------------------------------------ chair (seen from above / behind)
CHAIR = [
    "....bbbbbbbbbbbb....",
    "...bcdcccccccdccb...",
    "..bcdccccccccccdcb..",
    "..bcd1111111111dcb..",
    ".bvcd1aaaaaaaa1dcvb.",
    ".bvcd1aaaaaaaa1dcvb.",
    ".bvcd1aaaaaaaa1dcvb.",
    ".bvcd1aaaaaaaa1dcvb.",
    ".bvcd1abbbbbba1dcvb.",
    ".bvcd1aaaaaaaa1dcvb.",
    ".bucd1aaaaaaaa1dcub.",
    ".bucd1aaaaaaaa1dcub.",
    "..bcd1111111111dcb..",
    "..bbcccccccccccccb..",
    "...bbbbbbbbbbbbbb...",
    ".......b2222b.......",
    "........2332........",
    "..D.....2332.....D..",
    "..DD222223322222DD..",
    "....2222233222222...",
    "......22.33.22......",
    ".....D2..33..2D.....",
    ".........DD.........",
]


def chair(): return S(CHAIR, outline='0')


# ------------------------------------------------------------------ plush creature (original: round mint dumpling with a sprout)
PLUSH = [
    "......AB.......",
    "......CBA......",
    ".......B.......",
    "....KKKKKKK....",
    "..KKKKKKKKKKK..",
    ".KKHHKKKKKKKKJ.",
    ".KHHKKKKKKKKKJ.",
    "KKKK0KKKKK0KKJJ",
    "KKKN0KKKKK0NKJJ",
    "KKKKKKK0KKKKKJJ",
    ".KKKKKKKKKKKJJ.",
    ".JKKKKKKKKKJJI.",
    "..JJJKKKKJJJI..",
    "..KK.JJJJJ.KK..",
]


def plush(): return S(PLUSH, outline='I')


# ------------------------------------------------------------------ car posters (no text, no logos)
def poster(kind, w=14, h=30):
    a = np.zeros((h, w, 4), np.float32)
    if kind == 'sunset':          # sunset bands, sun, road, car from behind
        bands = ['p', 'o', 'v', 'M', 'L', 'c', 'b']
        for y in range(h): a[y, :] = (*PAL[bands[min(len(bands) - 1, y * len(bands) // 18)]], 255)
        for y in range(7, 14):
            for x in range(w):
                if (x - w / 2 + .5) ** 2 + (y - 13) ** 2 < 22 and y % 2: a[y, x, :3] = PAL['q']
        a[18:, :, :3] = PAL['a']
        for y in range(18, h):
            half = 1 + (y - 18) // 2
            a[y, w // 2 - half:w // 2 + half, :3] = PAL['2']
            if y % 3 == 0: a[y, w // 2, :3] = PAL['q']
        car = S(["..uuuuuu..", ".uvvvvvvu.", "uukkkkkkuu", "uuuuuuuuuu", "wuu0000uuw", "11......11"], outline=None)
        _blit(a, car, 2, 21)
    elif kind == 'track':         # top-down race car on a track with kerbs
        a[:, :] = (*PAL['A'], 255); a[:, 3:11, :3] = PAL['D']
        for y in range(0, h, 2): a[y, 2, :3] = PAL['v' if y % 4 else 'H']; a[y, 11, :3] = PAL['v' if y % 4 else 'H']
        for y in range(h): a[y, 7, :3] = PAL['F'] if (y // 3) % 2 else PAL['D']
        car = S(["..u..", ".uvu.", "1uvu1", "1uku1", ".uvu.", ".uuu.", "1uvu1", "1uuu1", ".v.v."], outline=None)
        _blit(a, car, 5, 11)
        a[1:4, 4:10, :3] = PAL['H']; a[2, 5:10:2, :3] = PAL['0']; a[1, 4:10:2, :3] = PAL['0']; a[3, 4:10:2, :3] = PAL['0']
    else:                         # blueprint: car side outline, rotated to fit the tall frame
        a[:, :] = (*PAL['g'], 255)
        for y in range(0, h, 4): a[y, :, :3] = PAL['h']
        for x in range(0, w, 4): a[:, x, :3] = PAL['h']
        side = ["..kkkkk...", ".k....kk..", "k.......kk", "k........k", "kk.kk..kkk", "..k..k.k..", "...kk...kk"]
        rot = [''.join(side[len(side) - 1 - i][j] for i in range(len(side))) for j in range(len(side[0]))]
        _blit(a, S(rot, outline=None), 3, 9)
    a[0, :, :3] = a[-1, :, :3] = PAL['G']; a[:, 0, :3] = a[:, -1, :3] = PAL['G']
    return a


def _blit(a, s, x, y):
    h, w = s.shape[:2]; m = s[..., 3:4] > 0
    a[y:y + h, x:x + w, :3] = np.where(m, s[..., :3], a[y:y + h, x:x + w, :3])


# ------------------------------------------------------------------ small floor / desk props
PROPS = {
    'car_red': ["..vvv..", ".vkkkv.", "1vvvvv1", "1vuuuv1", ".vvvvv.", "1vkkkv1", "1vvvvv1", ".w...w."],
    'car_blue': ["..jjj..", ".jkkkj.", "1jiiij1", "1jhhhj1", ".jiiij.", "1jkkkj1", "1jiiij1", ".q...q."],
    'car_yel': ["..qqq..", ".qkkkq.", "1qpppq1", "1qooop1", ".qpppq.", "1qkkkq1", "1qpppq1", ".r...r."],
    'controller': [".DDD...DDD.", "DEEEDDDEEED", "DEdEEEEEjED", "DdddEEEMEvD", "DEdEDEDEuED", "DEEED.DEEED", ".DDD...DDD."],
    'snack': ["..vvvvvvv..", ".vwwwwwwwv.", "vvqqqqqqqvv", "vvqpppppqvv", "vvqqqqqqqvv", "vvvvqqvvvvv", ".vvvvvvvvv.", "..vvvvvvv.."],
    'chips': ["p.q", ".qp", "qp."],
    'trainer': ["..GGGG.", ".GHHHHG", "GHHjHHG", "GHjHjHG", "GHHjHHG", "GHHHHHG", "GHHHHHG", ".GGjGG.", ".FFFFF."],
    'hoodie': ["....tt.tt....", "..tuutttuut..", ".tuuuuuuuuut.", "tuuuvuuuvuuut", "tuuuuuuuuuuut", ".tuuuuuuuuut.",
               "..tuuuuuuut..", "...ttuuutt...", "tt.tuuuuut.tt", "ut..ttttt..tu"],
    'tee': ["..GG..GG..", ".GHHGGHHG.", "GHHHHHHHHG", "GGHHiiHHGG", "..GHHHHG..", "..GHHHHG..", "...GGGG..."],
    'jeans': ["hhhhhhhh", "hiiiiiih", "hiiihiih", "hiih.hih", "hii...ih", ".hh...hh", "..h....h"],
    'sock': ["GG..", "GHG.", ".GHG", ".GHGG", "..GHG", "..GGG"],
    'can': [".FF.", "GJJG", "GKJG", "GJJG", "GJKG", ".FF."],
    'bottle': [".G.", "GkG", "jkj", "jkj", "jij", "jij", ".j."],
    'helmet': ["..vvvvv..", ".vvwwvvv.", "vvwvvvvvv", "vv11111vv", "vv1kkk1vv", "vvv111vvv", ".vvvvvvv.", "..uuuuu.."],
    'cone': ["...w...", "...p...", "..vHv..", "..vvv..", ".vHHHv.", ".vvvvv.", "uuuuuuu"],
    'tyre': [".22222.", "2333332", "23DDD32", "23D2D32", "23DDD32", "2333332", ".22222."],
    'toolbox': ["..DDDD...", ".D....D..", "uuuuuuuuu", "uvvvvvvvu", "uuuuDuuuu", "uvvvvvvvu", "sssssssss"],
    'books': ["iiiiiiii", "jjjjjjjh", "vvvvvvvv", "wwwwwwwu", "qqqqqqqp", "AAAAAAAz"],
    'cases': ["DDDDDD", "EEhEEE", "DDDDDD", "EEvEEE", "DDDDDD", "EEAEEE"],
    'headphones': [".DDDDD.", "D.....D", "D.....D", "E.....E", "ED...DE", "EE...EE"],
    'phone': ["11111", "1ghg1", "1hih1", "1ghg1", "1ggg1", "11111"],
    'keyboard': ["2222222222222222222", "2DEDEDEDEDEDEDEDED2", "2EDEDEDEDEDEDEDEDE2", "2DEEEEEEEEEEEEEEED2", "2222222222222222222"],
    'mouse': [".D.", "DED", "DED", ".D."],
    'lamp': ["..ppp..", ".pqqqp.", "pqrrrqp", ".pqqqp.", "..222..", "...2...", "..222.."],
    'plant': ["..A.B..", ".BABAB.", "ABCBABA", ".BABAB.", "..BAB..", ".nooon.", ".noppn.", "..nnn.."],
    'basket': [".GFGFGFG.", "GFHGHGHFG", "FHuHGHjHF", "GFGFGFGFG", "FGFGFGFGF", ".FGFGFGF."],
    'backpack': [".iii.", "ihhhi", "hiiih", "hhkhh", "hiiih", "hhhhh", ".h.h."],
    'beanbag': ["...ddddd...", ".ddeeeeedd.", "ddeeeffeeed", "deeeeeeeedd", "ddeeeeeeddc", ".cddddddcc.", "..ccccccc.."],
    'skate': [".222.", "2E2E2", "2vvv2", "2vwv2", "2vvv2", "2vwv2", "2vvv2", "2E2E2", ".222."],
    'bin': [".DDDD.", "DEEEED", "DGHGED", "DEGHED", "DEEEED", ".DDDD."],
    'paper': [".G.", "GHG", ".G."],
    'bowl': [".EEE.", "EpopE", ".EEE."],
    'bowl2': [".EEE.", "EjkjE", ".EEE."],
    'yarn': [".MN.", "MNMN", "NMNM", ".NM."],
    'cable': ["DD.....", "..D....", "..D.DDD", "...D..D", "....DD."],
    'slipper': [".ccc.", "cdddc", "cfffc", "cdddc", "cdddc", ".ccc."],
    'pizza': ["oooooooo", "oppppppo", "opvpppvo", "oppvpppo", "oooooooo"],
    'box': ["nnnnnnnnnnnnnn", "noooooppoooooon", "noooooppoooooon", "nnnnnnnnnnnnnnn", "noooooooooooooon",
            "noooooooooooooon", "noooooooooooooon", "nmmmmmmmmmmmmmmn"],
    'figure': [".v.", "vwv", ".u.", "u.u"],
    'notes': ["qqqNNN", "qpqNMN", "qqqNNN"],
    'flag': ["H0H0H0", "0H0H0H", "H0H0H0", "0H0H0H"],
    'umbrella': [".t.", "tut", "uvu", ".2.", ".2.", ".2.", "22."],
    'speaker': ["1111", "1D21", "1222", "1D21", "1111"],
    'drink': [".M.", "NMN", "MNM", "NMN", ".M."],
    'remote': ["DDDD", "DvED", "DEED", "DjjD", "DDDD"],
    'cap': [".vvv.", "vvwvv", "vvvvv", "uuuuu", ".ttt."],
}


def prop(name, outline='1'): return S(PROPS[name], outline=outline)
