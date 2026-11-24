"""veyron_tires: PS1 low-poly narrated short.
Oddity (never mentioned): a flamingo standing on one leg on top of a tyre stack at the back of the shop."""
import math, sys
from lowpoly import cat, box, cbox, cyl, sphere, tiles, wall, Cam, sky
import models as M
import fmodels as F
import ymodels as Y
import engine as E
from engine import ease, lerp, shake

NAME = "veyron"
V = E.Video(sys.modules[__name__]); ws = V.ws; DUR = V.dur
HOT = {"bugatti", "veyron", "$42,000.", "bespoke", "michelin", "run-flat,", "glued", "$100,000.", "$100,000", "larger", "$3,600",
       "catch:", "pay", "cheaper", "cheap", "fix.", "yes", "no"}
ONSCREEN = ["BUGATTI", "EB", "MICHELIN", "PAX", "$42,000", "$100,000", "$3,600", "INVOICE", "NEW WHEELS", "YES", "NO"]
ODDITY = "a pink flamingo standing on one leg on top of a tyre stack at the back of the tyre shop"

T_42 = Y.tag("$42,000", 128, 64)
T_100 = Y.tag("$100,000", 144, 64)
T_36 = Y.tag("$3,600", 128, 64, (140, 230, 140))
T_INV = Y.word("INVOICE\n\nNEW WHEELS\n$ $ $ $ $", 128, 176, (20, 20, 20), (250, 250, 246), 15)
T_RECEIPT = Y.word("TOTAL\n$ $ $\n$ $ $\n$ $ $\n$ $ $", 64, 256, (20, 20, 20), (250, 250, 246), 14)
T_GLUE = Y.word("GLUE", 64, 24, (255, 255, 255), (200, 40, 30), 14)
SHOP_POINTS = [((x, 4.2, z), (240, 246, 255), 9.0) for x in (-3.5, 3.5) for z in (-2.5, 2.0)] + [((0, 3.0, 3.5), (255, 220, 180), 6.0)]
SHOP_FOG = (12, 30, (24, 22, 24))

# ---------------------------------------------------------------- set
def standing_tire(side, r=0.37, w=0.3, rim_tex=None, spin=0.0):
    """Tyre standing on its tread, axis along z; side texture faces +z."""
    t = cyl(r, r, w, 14, (20, 20, 22), captex=side)
    if rim_tex is not None: t = cat([t, cyl(r * 0.62, r * 0.62, w + 0.01, 12, (200, 200, 206), captex=rim_tex).mv(0, -0.005, 0)])
    return t.mv(0, -w / 2, 0).rot("x", -90).rot("z", spin).mv(0, r, 0)

def shop(t, odd=True, sign=True):
    s = [tiles(-12, -7, 12, 8, 0, 2.0, M.T_TILE), wall(-12, 0, 12, 6, -6.0, 2.0, M.T_BRICK),
         wall(-7, 0, 8, 6, -9.0, 2.0, M.T_BRICK, axis="x"), wall(-7, 0, 8, 6, 9.0, 2.0, M.T_BRICK, axis="x")]
    if sign: s.append(box(-2.2, 3.6, -5.98, 2.2, 5.2, -5.9, (255, 255, 255), texs={"f": Y.T_BUG_SIGN}, e=0.9))
    s += [cbox(x, 5.6, z, 2.0, 0.08, 0.2, (240, 250, 255), e=1.0) for x in (-3.5, 3.5) for z in (-2.5, 2.0)]
    for i, x in enumerate((-7.5, -6.6, 5.6, 6.5, 7.4)):         # tyre stacks along the back wall
        s.append(Y.tire_stack(4 + i % 3, Y.T_SIDE_PAX if i % 2 else Y.T_SIDE_NEW).mv(x, 0, -5.2))
    s.append(box(-8.4, 0, -5.9, -5.8, 2.6, -5.85, (60, 60, 66)))
    if odd:
        s.append(Y.flamingo(t).rot("y", 30 + 20 * math.sin(t * 0.7)).mv(-6.6, 1.4, -5.2))
    return s

# ---------------------------------------------------------------- shots
def sh_hero(u, t, dt):
    """Low dolly across the Veyron's horseshoe grille in the tyre shop; flamingo on the back tyre stack."""
    e = ease(u)
    car = Y.veyron().rot("y", -30).mv(0.5, 0, -0.5)
    return dict(scene=shop(t) + [car], cam=Cam(lerp((5.6, 0.6, 5.0), (4.5, 0.65, 4.0), e), (0.9, 0.55, -0.3), 50, roll=-5 + 4 * e),
                bg=Y.SHOP_BG, fog=SHOP_FOG, points=SHOP_POINTS + [((3.0, 0.8, 2.0), (255, 90, 80), 4.0)], amb=0.3)

def sh_tyre(u, t, dt):
    """Close on the front wheel: the MICHELIN PAX sidewall and the red EB centre cap."""
    car = Y.veyron().rot("y", -70).mv(0.6, 0, -2.6)
    tyre = standing_tire(Y.T_SIDE_PAX, 0.42, 0.32, Y.T_HUB_BUG, spin=-t * 40).rot("y", -12).mv(0, 0, 0.4)
    return dict(scene=shop(t) + [car, tyre], cam=Cam((0.15, 0.7, 1.9 - 0.25 * u), (0, 0.5, 0.0), 46), bg=Y.SHOP_BG, fog=SHOP_FOG,
                points=SHOP_POINTS + [((1.6, 1.0, 2.0), (255, 240, 220), 3.0)], amb=0.35)

def sh_42(u, t, dt):
    """A stack of four Veyron tyres; a $42,000 tag slams onto it."""
    k = ease(min(1, u * 2.4))
    stack = Y.tire_stack(4, Y.T_SIDE_PAX, 0.37, 0.3)
    tg = box(-0.45, -0.22, -0.01, 0.45, 0.22, 0.01, (255, 255, 255), texs={"f": T_42, "b": T_42}).rot("x", -10).mv(0, 1.55 + 1.2 * (1 - k), 0.25)
    sx, sy, _ = shake(t, 0.03 if 0.4 < u < 0.52 else 0, 12)
    return dict(scene=shop(t) + [stack, tg], cam=Cam((0.4 + sx, 1.6 + sy, 2.6 - 0.3 * u), (0, 1.0, 0), 50), bg=Y.SHOP_BG, fog=SHOP_FOG,
                points=SHOP_POINTS + [((0.5, 2.5, 1.5), (255, 240, 200), 4.0)], amb=0.38)

def sh_bespoke(u, t, dt):
    """One tyre on a velvet plinth under spotlights, turning: MICHELIN PAX."""
    plinth = cat([cyl(0.5, 0.5, 0.8, 12, (40, 40, 44)), cyl(0.52, 0.52, 0.06, 12, (150, 20, 40)).mv(0, 0.8, 0)])
    tyre = standing_tire(Y.T_SIDE_PAX, 0.42, 0.32, Y.T_HUB_BUG).rot("y", -30 + 60 * ease(u)).mv(0, 0.86, 0)
    return dict(scene=shop(t) + [plinth, tyre], cam=Cam((0.0, 1.45, 2.0 - 0.3 * u), (0, 1.2, 0), 48), bg=Y.SHOP_BG, fog=(4, 14, (14, 12, 16)),
                points=[((0.8, 2.6, 1.2), (255, 236, 200), 4.0), ((-0.8, 2.6, 1.0), (200, 220, 255), 3.5)], amb=0.25)

def sh_runflat(u, t, dt):
    """Run-flat: cut-away tyre; it goes flat, the inner support ring takes the weight and the wheel keeps rolling."""
    sq = ease(min(1, u * 2.0))
    tyre = cyl(0.45, 0.45, 0.3, 16, (22, 22, 24), captex=Y.T_SIDE_PAX).mv(0, -0.15, 0).rot("x", -90).sc(1 + 0.08 * sq, 1 - 0.3 * sq, 1).mv(0, -0.135 * sq, 0)
    ring = cyl(0.31, 0.31, 0.24, 14, (250, 200, 40), capcol=(250, 200, 40)).mv(0, -0.12, 0).rot("x", -90).mv(0, 0, 0.05)
    rim = cyl(0.25, 0.25, 0.32, 12, (200, 200, 206), captex=Y.T_HUB_BUG).mv(0, -0.16, 0).rot("x", -90).mv(0, 0, 0.04)
    w = cat([tyre, cat([ring, rim]).rot("z", -t * 120)]).mv(0, 0.45, 0)
    nail = box(-0.01, 0, -0.01, 0.01, 0.12, 0.01, (200, 200, 200)).rot("z", 20).mv(0.2, 0.0, 0.1)
    return dict(scene=[tiles(-4, -4, 4, 4, 0, 1.0, M.T_TILE), wall(-4, 0, 4, 3, -1.5, 1.0, M.T_BRICK), w, nail],
                cam=Cam((0.3, 0.6, 2.3), (0, 0.42, 0), 44), bg=Y.SHOP_BG, fog=None, points=[((0.4, 1.4, 1.2), (255, 240, 220), 3.0)], amb=0.45)

def sh_glue(u, t, dt):
    """Glued to the wheel: a glue gun lays a bead round the rim, the tyre presses on."""
    rim = cyl(0.37, 0.37, 0.3, 14, (200, 200, 206), captex=Y.T_HUB_BUG).mv(0, 0, 0)
    n = int(min(1, u * 1.6) * 16)
    bead = [cbox(0.38 * math.cos(2 * math.pi * k / 16), 0.31, 0.38 * math.sin(2 * math.pi * k / 16), 0.07, 0.03, 0.07, (240, 230, 160)) for k in range(n)]
    a = 2 * math.pi * min(1, u * 1.6)
    gun = cat([cbox(0, 0.18, 0, 0.1, 0.35, 0.1, (200, 40, 30)), box(-0.02, 0, -0.02, 0.02, 0.05, 0.02, (60, 60, 60)),
               box(-0.051, 0.15, -0.06, -0.05, 0.25, 0.06, (255, 255, 255), texs={"l": T_GLUE})]).mv(0.38 * math.cos(a), 0.35, 0.38 * math.sin(a))
    k = max(0, (u - 0.65) / 0.35)
    tyre = Y.tire(Y.T_SIDE_PAX, 0.5, 0.3).mv(0, 0.9 - 0.9 * ease(k), 0) if k > 0 else None
    bench = box(-1.0, -0.05, -0.8, 1.0, 0.0, 0.8, (90, 70, 50))
    return dict(scene=[tiles(-4, -4, 4, 4, -0.9, 1.0, M.T_TILE), wall(-4, -0.9, 4, 3, -1.5, 1.0, M.T_BRICK), bench, rim, *bead, gun, tyre],
                cam=Cam((0.0, 1.35, 1.2), (0, 0.2, 0), 48), bg=Y.SHOP_BG, fog=None, points=[((0.4, 1.4, 1.0), (255, 240, 220), 3.0)], amb=0.45)

def sh_four(u, t, dt):
    """With the wheels: four complete Veyron wheels roll out across the shop floor towards the camera."""
    s = shop(t)
    for i in range(4):
        z = -2.0 + 3.0 * ease(min(1, max(0, u * 1.4 - i * 0.12)))
        s.append(standing_tire(Y.T_SIDE_PAX, 0.37, 0.3, Y.T_HUB_BUG, spin=-z * 150).rot("y", 90).mv(-1.5 + i, 0, z))
    return dict(scene=s, cam=Cam((0.0, 0.8, 2.9), (0, 0.4, 0), 52), bg=Y.SHOP_BG, fog=SHOP_FOG, points=SHOP_POINTS, amb=0.36)

def sh_100(u, t, dt):
    """Stacks of cash pile up beside the four wheels; a $100,000 tag lands on top."""
    s = shop(t)
    for i in range(4): s.append(standing_tire(Y.T_SIDE_PAX, 0.37, 0.3, Y.T_HUB_BUG).rot("y", 90).mv(-1.5 + i, 0, 1.0))
    n = int(1 + u * 9)
    for i in range(n): s.append(Y.cash_stack(5).mv(-1.2 + 0.45 * (i % 6), 0.33 * (i // 6), 1.9))
    k = ease(max(0, (u - 0.35) / 0.3))
    s.append(box(-0.5, -0.22, -0.01, 0.5, 0.22, 0.01, (255, 255, 255), texs={"f": T_100, "b": T_100}).mv(0.0, 1.35 + 1.0 * (1 - k), 2.0))
    return dict(scene=s, cam=Cam((0.4, 1.4, 4.4 - 0.3 * u), (0, 0.7, 1.3), 50), bg=Y.SHOP_BG, fog=SHOP_FOG, points=SHOP_POINTS, amb=0.38)

def sh_new(u, t, dt):
    """Now: the Bugatti sign; a technician pulls a cover off a new, larger wheel on a stand."""
    lift = ease(min(1, u * 1.6))
    stand = box(-0.15, 0, -0.15, 0.15, 0.6, 0.15, (60, 60, 66))
    wh = standing_tire(Y.T_SIDE_NEW, 0.45, 0.34, Y.T_HUB_BUG_NEW).rot("y", 10).mv(0, 0.6, 0)
    cover = cbox(0, 1.06, 0, 1.0, 0.95, 0.5, (214, 210, 200)).rot("z", -30 * lift, (-0.5, 0.6, 0)).mv(-1.6 * lift, 0.6 * lift, 0)
    tech = Y.guy(top=(30, 40, 90), ra=(90, 20, 20), la=(60, 10, 20)).rot("y", 60).mv(-1.0 - 0.4 * lift, 0, 0.3)
    return dict(scene=shop(t) + [stand, wh, cover, tech], cam=Cam((0.6, 1.6, 4.2 - 0.6 * u), (0, 1.5, -2.0), 50), bg=Y.SHOP_BG, fog=SHOP_FOG,
                points=SHOP_POINTS + [((0, 2.5, 1.5), (255, 240, 220), 3.5)], amb=0.36)

def sh_larger(u, t, dt):
    """Old wheel beside the new one: the new one is bigger (20 inch front, 21 inch rear)."""
    g = 1.0 + 0.14 * ease(min(1, u * 1.5))
    old = standing_tire(Y.T_SIDE_PAX, 0.37, 0.3, Y.T_HUB_BUG).mv(-0.5, 0, 0)
    new = standing_tire(Y.T_SIDE_NEW, 0.37 * g, 0.3, Y.T_HUB_BUG_NEW).mv(0.5, 0, 0)
    return dict(scene=shop(t) + [old, new], cam=Cam((0.0, 0.75, 2.9), (0, 0.45, 0), 46), bg=Y.SHOP_BG, fog=SHOP_FOG,
                points=SHOP_POINTS + [((0, 1.5, 1.5), (255, 240, 220), 3.0)], amb=0.4)

def sh_fit(u, t, dt):
    """A modern tyre slides onto the new wheel."""
    k = ease(min(1, u * 1.5))
    rim = cyl(0.3, 0.3, 0.32, 14, (206, 208, 214), captex=Y.T_HUB_BUG_NEW).mv(0, 0, 0)
    tyre = Y.tire(Y.T_SIDE_NEW, 0.45, 0.3).mv(0, 0.02 + 0.8 * (1 - k), 0)
    bench = box(-1.0, -0.05, -0.8, 1.0, 0.0, 0.8, (90, 70, 50))
    return dict(scene=[tiles(-4, -4, 4, 4, -0.9, 1.0, M.T_TILE), wall(-4, -0.9, 4, 3, -1.5, 1.0, M.T_BRICK), bench, rim, tyre],
                cam=Cam((0.0, 1.3, 1.4), (0, 0.25, 0), 46), bg=Y.SHOP_BG, fog=None, points=[((0.4, 1.4, 1.0), (255, 240, 220), 3.0)], amb=0.45)

def sh_36(u, t, dt):
    """A stack of four modern tyres; a green $3,600 tag swings onto it."""
    stack = Y.tire_stack(4, Y.T_SIDE_NEW, 0.4, 0.3)
    sw = 20 * math.sin(t * 5) * (1 - u)
    tg = cat([box(-0.004, 0, -0.004, 0.004, 0.3, 0.004, (230, 230, 230)),
              box(-0.45, -0.44, -0.01, 0.45, 0.0, 0.01, (255, 255, 255), texs={"f": T_36, "b": T_36})]).rot("z", sw).mv(0, 1.25, 0.42)
    return dict(scene=shop(t) + [stack, tg], cam=Cam((-0.4, 1.4, 2.6 - 0.3 * u), (0, 0.95, 0), 50), bg=Y.SHOP_BG, fog=SHOP_FOG,
                points=SHOP_POINTS + [((0.5, 2.5, 1.5), (200, 255, 200), 4.0)], amb=0.38)

def sh_catch(u, t, dt):
    """The catch: the Veyron up on the lift with its wheels off; an invoice for NEW WHEELS rises into view."""
    car = Y.veyron(lift=1.2, wheels_on=False).rot("y", -20)
    posts = [Y.lift_post(2.4).mv(x, 0, z) for x in (-1.6, 1.6) for z in (-1.3, 1.3)]
    k = ease(max(0, (u - 0.25) / 0.4))
    inv = box(-0.3, -0.42, -0.005, 0.3, 0.42, 0.005, (255, 255, 255), texs={"f": T_INV}).rot("x", -10).mv(0.2, 0.6 + 0.9 * k, 2.4)
    return dict(scene=shop(t) + [car, *posts, inv], cam=Cam((0.8, 1.6, 4.6 - 0.6 * u), (0.0, 1.4, 0), 50), bg=Y.SHOP_BG, fog=SHOP_FOG,
                points=SHOP_POINTS + [((0.3, 2.2, 3.2), (255, 240, 220), 3.0)], amb=0.36)

def sh_cheaper(u, t, dt):
    """Cheaper tyres: the small green $3,600 tag floats down onto a single new tyre."""
    tyre = standing_tire(Y.T_SIDE_NEW, 0.45, 0.32, Y.T_HUB_BUG_NEW)
    k = ease(min(1, u * 1.4))
    tg = box(-0.3, -0.15, -0.01, 0.3, 0.15, 0.01, (255, 255, 255), texs={"f": T_36}).rot("z", 15 * math.sin(t * 4) * (1 - k)).mv(0.0, 1.15 + 0.8 * (1 - k), 0.2)
    return dict(scene=shop(t) + [tyre, tg], cam=Cam((0.0, 0.9, 2.1), (0, 0.75, 0), 46), bg=Y.SHOP_BG, fog=SHOP_FOG,
                points=SHOP_POINTS + [((0, 2.0, 1.5), (200, 255, 200), 3.0)], amb=0.4)

def sh_fix(u, t, dt):
    """Just not a cheap fix: a till spits out a receipt that keeps on coming and coils on the floor."""
    till = cat([cbox(0, 0.95, 0, 0.5, 0.3, 0.4, (40, 40, 44)), box(-0.18, 1.1, 0.08, 0.18, 1.2, 0.2, (20, 20, 20)), box(-0.6, 0, -0.5, 0.6, 0.8, 0.5, (90, 70, 50))])
    L = 0.3 + 2.2 * ease(u)
    hang = min(L, 1.1); rest = L - hang
    rec = [box(-0.14, -hang, -0.005, 0.14, 0, 0.005, (255, 255, 255), texs={"f": T_RECEIPT}).rot("x", -8).mv(0, 1.12, 0.56)]
    if rest > 0: rec.append(box(-0.14, 0.004, 0, 0.14, 0.01, rest, (255, 255, 255), texs={"t": T_RECEIPT}).mv(0, 0, 0.62))
    return dict(scene=shop(t) + [till, *rec], cam=Cam((0.9, 1.5, 3.0), (0, 0.7, 0.7), 50), bg=Y.SHOP_BG, fog=SHOP_FOG,
                points=SHOP_POINTS + [((0.5, 2.0, 1.5), (255, 240, 220), 3.0)], amb=0.4)

def sh_question(u, t, dt):
    """Slow orbit of the Veyron on the shop floor with a fresh stack of tyres; flamingo behind."""
    car = Y.veyron().rot("y", -30).mv(0.3, 0, -0.3)
    a = math.radians(65 - 30 * ease(u))
    eye = (6.0 * math.cos(a), 1.5, 6.0 * math.sin(a))
    return dict(scene=shop(t) + [car], cam=Cam(eye, (-0.6, 0.7, -1.0), 50), bg=Y.SHOP_BG, fog=SHOP_FOG, points=SHOP_POINTS, amb=0.34)

def sh_yesno(u, t, dt):
    yes = F.button(F.T_YES_BTN, press=max(0, math.sin(t * 6))).rot("y", 180).mv(-0.7, 0, 2.6)
    no = F.button(F.T_NO_BTN, press=max(0, math.sin(t * 6 + 3))).rot("y", 180).mv(0.7, 0, 2.6)
    car = Y.veyron().rot("y", -30).mv(0.3, 0, -0.5)
    e = ease(u)
    return dict(scene=shop(t) + [car, yes, no], cam=Cam(lerp((0.0, 2.6, 6.0), (0.6, 1.5, 5.4), e), (0, 0.6, 1.4), 50), bg=Y.SHOP_BG, fog=SHOP_FOG,
                points=SHOP_POINTS + [((0, 1.5, 3.4), (255, 255, 255), 3.0)], amb=0.36)

SHOTS = [
    (0.0, sh_hero, "Veyron in a tyre shop, low dolly on the horseshoe grille (flamingo on a tyre stack behind)"),
    (ws(0, 5), sh_tyre, "close on the MICHELIN PAX sidewall and EB centre cap"),
    (ws(0, 8), sh_42, "$42,000 tag slams onto a stack of four tyres"),
    (ws(1, 0), sh_bespoke, "one tyre on a velvet plinth under spotlights"),
    (ws(1, 6), sh_runflat, "run-flat: tyre deflates, yellow inner support ring carries the wheel"),
    (ws(1, 7), sh_glue, "glue bead laid round the rim, tyre pressed on"),
    (ws(2, 0), sh_four, "four complete wheels roll out"),
    (ws(2, 7), sh_100, "cash piles up beside the wheels, $100,000 tag"),
    (ws(3, 0), sh_new, "Bugatti sign; cover pulled off a new, larger wheel"),
    (ws(3, 4), sh_larger, "old wheel beside the bigger new wheel"),
    (ws(3, 7), sh_fit, "modern tyre slides onto the new wheel"),
    (ws(3, 10), sh_36, "$3,600 tag swings onto four modern tyres"),
    (ws(4, 0), sh_catch, "Veyron on the lift, wheels off; INVOICE: NEW WHEELS"),
    (ws(5, 0), sh_cheaper, "small $3,600 tag floats onto one tyre"),
    (ws(5, 2), sh_fix, "endless receipt from the till"),
    (ws(6, 0), sh_question, "Veyron orbit in the shop"),
    (ws(6, 8), sh_yesno, "YES / NO buttons"),
]
SFX = [(0.5, "vroom", 0.5), (ws(0, 8) + 0.4, "thump", 0.9), (ws(1, 0), "sparkle", 0.4), (ws(1, 6), "poof", 0.5), (ws(1, 7), "slide_down", 0.3),
       (ws(2, 0), "whoosh", 0.4), (ws(2, 7) + 0.6, "cha_ching", 0.6), (ws(3, 0) + 0.3, "whoosh", 0.5), (ws(3, 4), "pop", 0.5),
       (ws(3, 10), "ding", 0.5), (ws(4, 0) + 0.5, "stamp", 0.7), (ws(5, 0), "sparkle", 0.3), (ws(5, 2), "cha_ching", 0.5), (ws(6, 8), "pop", 0.6)]

if __name__ == "__main__": E.main(V)
