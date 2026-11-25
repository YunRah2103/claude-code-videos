"""2D face texture drawing (expressions) for Yub, drawn at 4x and downsampled to 256 px."""
from PIL import Image, ImageDraw
SKIN = (190, 128, 90); HAIR = (30, 24, 28)
N, SS = 256, 4
EX = (0.31, 0.69); EY = 0.47              # eye centres in face uv (also used to place the 3D glasses)
EXPR = {   # eyes, brows (left dy, right dy, inner tilt), mouth
    "smile": ("norm", (0, 0, 0), "smile"), "grin": ("closed", (-4, -4, 0), "grin"), "shock": ("wide", (-16, -16, 0), "o"),
    "panic": ("wide", (-14, -14, 8), "grit"), "sad": ("norm", (0, 0, -9), "frown"), "smug": ("half", (-12, 2, 0), "smirk"),
    "confused": ("norm", (-14, 4, 0), "squiggle"), "deadpan": ("half", (2, 2, 0), "flat"), "cringe": ("squeeze", (4, 4, 8), "grit"),
    "proud": ("closed", (-6, -6, 0), "smile"), "angry": ("norm", (4, 4, 12), "grit"),
}

def _face(expr="smile", look="c", sweat=False, blush=False):
    eyes, (bl, br, tilt), mouth = EXPR[expr]
    M = N * SS; s = M / 256
    im = Image.new("RGB", (M, M), SKIN); d = ImageDraw.Draw(im)
    def E(x0, y0, x1, y1, **kw): d.ellipse(tuple(v * s for v in (x0, y0, x1, y1)), **kw)
    def L(pts, w, col): d.line([(x * s, y * s) for x, y in pts], fill=col, width=int(w * s), joint="curve")
    def PG(pts, col): d.polygon([(x * s, y * s) for x, y in pts], fill=col)
    lx = {"l": -6, "r": 6, "c": 0, "u": 0}[look]; ly = -5 if look == "u" else 0
    ey = EY * 256
    for i, cx in enumerate((EX[0] * 256, EX[1] * 256)):
        if eyes == "closed":
            L([(cx - 18, ey + 4), (cx, ey - 10), (cx + 18, ey + 4)], 7, HAIR)
        elif eyes == "squeeze":
            sgn = 1 if i == 0 else -1
            L([(cx - 15 * sgn, ey - 12), (cx + 12 * sgn, ey), (cx - 15 * sgn, ey + 12)], 7, HAIR)
        else:
            rw, rh = (21, 24) if eyes == "wide" else (19, 19)
            E(cx - rw, ey - rh, cx + rw, ey + rh, fill=(252, 252, 250), outline=(70, 46, 40), width=int(3 * s))
            pr = 8 if eyes == "wide" else 12
            E(cx + lx - pr, ey + ly - pr, cx + lx + pr, ey + ly + pr, fill=(92, 58, 36))
            E(cx + lx - pr * 0.55, ey + ly - pr * 0.55, cx + lx + pr * 0.55, ey + ly + pr * 0.55, fill=(30, 20, 18))
            E(cx + lx + 2, ey + ly - pr + 2, cx + lx + 7, ey + ly - pr + 7, fill=(255, 255, 255))
            if eyes == "half":
                PG([(cx - rw - 2, ey - rh - 2), (cx + rw + 2, ey - rh - 2), (cx + rw + 2, ey - 1), (cx - rw - 2, ey - 1)], SKIN)
                L([(cx - rw, ey - 1), (cx + rw, ey - 1)], 4, (70, 46, 40))
        dy = bl if i == 0 else br; sg = 1 if i == 0 else -1
        y0 = ey - 36 + dy
        PG([(cx - 24, y0 + sg * tilt + 2), (cx + 24, y0 - sg * tilt - 2), (cx + 24, y0 - sg * tilt + 9), (cx - 24, y0 + sg * tilt + 11)], HAIR)
    if blush:
        for cx in (62, 194): E(cx - 18, 168, cx + 18, 182, fill=(214, 112, 104))
    my = 196; m = (120, 36, 42)
    if mouth == "smile":
        d.chord(tuple(v * s for v in (98, my - 20, 158, my + 22)), 0, 180, fill=m); PG([(104, my + 1), (152, my + 1), (150, my + 7), (106, my + 7)], (252, 252, 252))
    elif mouth == "grin":
        d.chord(tuple(v * s for v in (82, my - 26, 174, my + 30)), 0, 180, fill=m); PG([(88, my + 1), (168, my + 1), (166, my + 9), (90, my + 9)], (252, 252, 252))
        E(110, my + 12, 146, my + 28, fill=(222, 96, 104))
    elif mouth == "o":
        E(110, my - 16, 146, my + 30, fill=(96, 22, 30)); E(118, my + 10, 138, my + 26, fill=(206, 84, 96))
    elif mouth == "grit":
        d.rounded_rectangle(tuple(v * s for v in (86, my - 12, 170, my + 16)), int(8 * s), fill=(252, 252, 252), outline=m, width=int(4 * s))
        L([(88, my + 2), (168, my + 2)], 2, (170, 160, 160))
        for x in range(100, 170, 14): L([(x, my - 10), (x, my + 14)], 2, (180, 170, 170))
    elif mouth == "frown":
        d.arc(tuple(v * s for v in (100, my, 156, my + 34)), 200, 340, fill=m, width=int(6 * s))
    elif mouth == "smirk":
        L([(108, my + 6), (144, my + 6), (162, my - 8)], 6, m)
    elif mouth == "squiggle":
        L([(100, my + 4), (114, my - 4), (128, my + 4), (142, my - 4), (156, my + 4)], 6, m)
    else:
        L([(104, my + 2), (152, my + 2)], 6, m)
    if sweat:
        PG([(236, 40), (224, 76), (248, 76)], (110, 196, 255)); E(222, 64, 250, 92, fill=(110, 196, 255))
    return im.resize((N, N), Image.LANCZOS)

