"""Brake explainer: the stick duel moves onto a road, a car brakes hard, then the stickmen explain disc brakes.

1280x720 @30fps. Reuses the stick-duel fighters/FX and the new-car-trap pixel car, font and sound effects.
usage: python render.py still OUTDIR t1 t2 ...   |   python render.py video OUT.mp4 [END]
"""
import importlib.util, json, math, subprocess, sys, wave
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
_spec = importlib.util.spec_from_file_location('duel', ROOT / 'videos/stick-duel/src/render.py')
duel = importlib.util.module_from_spec(_spec); _spec.loader.exec_module(duel)
sys.path.insert(0, str(ROOT / 'videos/new-car-trap/src'))
import pix, sfx  # noqa: E402

DUR = 61.0
W, H, FPS, SR = 1280, 720, 30, sfx.SR
VO = ROOT / 'out/brake/vo'
LINES = json.load(open(HERE / 'script.json'))
WORDS = json.load(open(HERE / 'words.json'))
pix.FONT.update({'Q': ["01110", "10001", "10001", "10001", "10101", "10010", "01101"],
                 'Z': ["11111", "00001", "00010", "00100", "01000", "10000", "11111"],
                 'J': ["00111", "00010", "00010", "00010", "00010", "10010", "01100"],
                 "'": ["1", "1", "0", "0", "0", "0", "0"], ':': ["0", "1", "0", "0", "0", "1", "0"]})


def wav_len(i):
    with wave.open(str(VO / f'line_{i:02d}.wav')) as w: return w.getnframes() / w.getframerate()


DURS = [wav_len(i) for i in range(len(LINES))]
GAP = {1: 1.3, 7: 1.2}                       # room for the zoom transitions into / out of the diagram
START, _t = [], 3.5
for _i, _d in enumerate(DURS):
    START.append(_t); _t += _d + GAP.get(_i, 0.3)
END_VO = START[-1] + DURS[-1]
assert END_VO + 1.5 <= DUR, END_VO
TR1 = (START[2] - 1.5, START[2] - 0.1)      # road -> diagram
TR2 = (START[8] - 1.4, START[8] - 0.1)      # diagram -> road
CLASH = END_VO + 0.45                        # fighters resume: final clash
FIGHT_END = 2.32                             # duel footage (duel time 5.1 -> 7.42)


def ss(x):
    x = min(1.0, max(0.0, x)); return x * x * (3 - 2 * x)


def lerp(a, b, k): return a + (b - a) * k


def wt(i, prefix, nth=0):
    """Absolute time a word starts in line i (prefix match, case-insensitive)."""
    hits = [w for w in WORDS[i] if ''.join(c for c in w['w'].lower() if c.isalpha()).startswith(prefix)]
    return START[i] + hits[nth]['s']


def pop(t, t0, d=0.25):
    """0 before t0, springy 0->1 scale after."""
    u = (t - t0) / d
    if u <= 0: return 0.0
    if u >= 1: return 1.0
    return 1 + 0.25 * math.sin(u * math.pi) * (1 - u) - (1 - u) ** 3


# ---------------------------------------------------------------- road scene
def build_road():
    big, _ = duel.build_bg()
    small = big[(np.arange(68) * H / 68 + H / 136).astype(int)][:, (np.arange(120) * W / 120 + W / 240).astype(int)]
    img = Image.fromarray(small.astype(np.uint8)); px = img.load()
    rnd = np.random.default_rng(8)
    for y in range(53, 65):
        for x in range(120):
            c = (74, 76, 86) if rnd.random() > .12 else (66, 68, 78)
            if y in (53, 64): c = (190, 188, 176)                    # curbs
            if y == 59 and (x // 4) % 2 == 0: c = (240, 200, 70)      # dashed centre line
            px[x, y] = c
    for x in range(120): px[x, 52] = (60, 130, 60); px[x, 65] = (60, 130, 60)
    road = np.asarray(img.resize((W, H), Image.Resampling.NEAREST)).astype(np.float32)
    dark = road * 0.15 * np.array([0.9, 1.0, 1.15], np.float32) + np.array([8, 10, 16], np.float32)
    return road, dark


GY = 622                                     # feet line (duel camera at z=1 clamps cy to 360 -> gy 622)
CAR_S = 6
CAR_IMG = pix.up(pix.car('blue', 0), CAR_S), pix.up(pix.car('blue', 1), CAR_S)
CAR_Y = GY + 8 - 22 * CAR_S                  # wheel bottoms (grid y 22) sit on the road


def car_front(t):
    if t < 2.4: return 250 - 900 * (2.4 - t)
    s = min(1.0, t - 2.4)
    return 250 + 900 * s - 450 * s * s       # constant deceleration: stops 700 px from the left at 3.4 s


def car_draw(img, t, fx):
    f = car_front(t)
    if f < -40: return
    ox = f - 50 * CAR_S
    braking = 2.4 <= t < 3.4
    spr = CAR_IMG[int(f / 22) % 2] if t < 3.4 else CAR_IMG[0]
    dip = (-2.2 if braking else 0) + (1.4 * math.sin((t - 3.4) * 18) * math.exp(-(t - 3.4) * 5) if t >= 3.4 else 0)
    if dip: spr = spr.rotate(dip, resample=Image.Resampling.NEAREST, center=(spr.width * .8, spr.height))
    img.alpha_composite(spr, (int(ox), int(CAR_Y + (6 if braking else 0) * min(1, (t - 2.4) * 6))))
    if braking or 3.4 <= t < 4.0:            # brake lights flare red
        fx.rectangle([ox + 2 * CAR_S, CAR_Y + 12 * CAR_S, ox + 4 * CAR_S, CAR_Y + 14 * CAR_S], fill=(255, 40, 40, 255))
    return ox


def skid_and_smoke(base, fxd, t):
    if t < 2.5: return
    d = ImageDraw.Draw(base)
    for wx in (13, 40):                      # skid marks from both wheels
        x0 = car_front(2.5) - 50 * CAR_S + wx * CAR_S
        x1 = car_front(min(t, 3.4)) - 50 * CAR_S + wx * CAR_S
        d.rectangle([x0, GY + 2, x1, GY + 10], fill=(40, 40, 46, 255))
    rr = np.random.default_rng(3)
    for k in range(int((min(t, 3.35) - 2.45) / 0.04)):   # tyre smoke puffs, each drifting back and fading
        ts = 2.45 + k * 0.04; age = t - ts
        if age > 0.9: continue
        for wx in (13, 40):
            x = car_front(ts) - 50 * CAR_S + wx * CAR_S - 40 * age + rr.uniform(-10, 10)
            y = GY - 10 - 70 * age + rr.uniform(-8, 8)
            r = 14 + 34 * age
            duel.puff(fxd, x, y, r, (226, 228, 232), 150 * (1 - age / 0.9) ** 1.5)


G2 = [(2.32, 950, 0, 'land', -1, -720), (2.6, 950, 0, 'stand', -1, -720), (3.35, 960, 0, 'guardup', -1, -720),
      (4.0, 960, 0, 'stand', -1, -720)]
R2 = [(2.32, 775, 0, 'crouch', 1, -360), (2.55, 775, 0, 'stand', -1, -360), (3.3, 790, 0, 'guardup', -1, -360),
      (3.45, 840, -70, 'knock', -1, -360), (3.65, 860, 0, 'crouch', -1, -360), (4.2, 860, 0, 'stand', -1, -360)]


def outro_keys():
    c = CLASH
    g = G2 + [(START[8], 960, 0, 'stand', -1, -720), (c - 0.5, 960, 0, 'stand', -1, -720), (c - 0.25, 980, 0, 'windup', -1, -720),
              (c, 905, -120, 'slash', -1, -720), (DUR, 905, -120, 'slash', -1, -720)]
    r = R2 + [(START[8], 860, 0, 'stand', -1, -360), (c - 0.6, 860, 0, 'stand', -1, -360), (c - 0.45, 850, 0, 'crouch', 1, -360),
              (c - 0.25, 830, 0, 'windup', 1, -360), (c, 880, -120, 'slash', 1, -360), (DUR, 880, -120, 'slash', 1, -360)]
    return g, r


G2, R2 = outro_keys()
OUTRO_WORDS = [('PEDAL', 'pedal'), ('FLUID', 'fluid'), ('CLAMP', 'clamp'), ('HEAT', 'heat')]


def road_frame(t, road, dark, tail):
    if t < FIGHT_END:                        # the duel itself, now fought on the road
        img = Image.fromarray(duel.frame(5.1 + t, road, dark, tail)).convert('RGBA')
        fx = Image.new('RGBA', (W, H), (0, 0, 0, 0))
        car_draw(img, t, ImageDraw.Draw(fx))
        return Image.alpha_composite(img, duel.pixel_fx(fx, duel.FPX)).convert('RGB')
    img = Image.fromarray(road.astype(np.uint8)).convert('RGBA')
    fx = Image.new('RGBA', (W, H), (0, 0, 0, 0)); fxd = ImageDraw.Draw(fx)
    gl = Image.new('RGB', (W, H)); gld = ImageDraw.Draw(gl)
    skid_and_smoke(img, fxd, t)
    ox = car_draw(img, t, fxd)
    if ox is not None and 2.4 <= t < 4.0:
        gld.ellipse([ox, CAR_Y + 8 * CAR_S, ox + 8 * CAR_S, CAR_Y + 18 * CAR_S], fill=(255, 40, 40))
    chars = Image.new('RGBA', (W, H), (0, 0, 0, 0)); cd = ImageDraw.Draw(chars)
    duel.draw_fighter(cd, G2, t, 'green', 1.0, GY)
    duel.draw_fighter(cd, R2, t, 'red', 1.0, GY)
    img = Image.alpha_composite(img, duel.pixelate(chars, duel.CPX))
    duel.ambient(fxd, 5.1 + t)
    if 3.38 < t < 3.75:                      # the car's stop: a little shock ring
        duel.shock(fxd, gld, car_front(3.4) - 10, GY - 20, (t - 3.38) / 0.37, (255, 255, 255), 160)
    cards = []
    if t > START[8]:                         # outro word cards
        for k, (txt, w) in enumerate(OUTRO_WORDS):
            s = pop(t, wt(8, w)) * (1 - pop(t, CLASH - 0.6, 0.3))
            if s <= 0: continue
            lab = pix.up(pix.label(txt, '#ffd23f'), 6)
            lab = lab.resize((max(1, int(lab.width * s)), max(1, int(lab.height * s))), Image.Resampling.NEAREST)
            cx = 250 + k * 260
            cards.append((outline(lab, 6), (int(cx - lab.width / 2), int(140 - lab.height / 2))))
    if CLASH <= t < CLASH + 0.6:             # they go right back to fighting
        u = (t - CLASH) / 0.6
        duel.shock(fxd, gld, 895, GY - 150, u, (255, 230, 150), 420)
        duel.particles(fxd, gld, 895, GY - 150, 300, u, 24, 77, col=(255, 230, 120))
        duel.streak(fxd, gld, 500, 1290, GY - 150, 40 * (1 - u), (255, 255, 255))
    img = Image.alpha_composite(img, duel.pixel_fx(fx, duel.FPX))
    for c, pos in cards: img.alpha_composite(c, pos)
    out = np.asarray(img.convert('RGB')).astype(np.float32) + np.asarray(duel.pixel_glow(gl, duel.FPX)).astype(np.float32) * 0.75
    if CLASH <= t < CLASH + 0.1: out = out * 0.25 + 255 * 0.75
    return Image.fromarray(out.clip(0, 255).astype(np.uint8))


def outline(img, k):
    """Dark 1-pixel (k px) outline around an RGBA sprite."""
    a = np.asarray(img)[..., 3] > 0
    pad = np.pad(a, k)
    ring = np.zeros_like(pad)
    for dy in (-k, 0, k):
        for dx in (-k, 0, k): ring |= np.roll(np.roll(pad, dy, 0), dx, 1)
    out = Image.new('RGBA', (img.width + 2 * k, img.height + 2 * k), (0, 0, 0, 0))
    o = np.zeros((*ring.shape, 4), np.uint8); o[ring] = (16, 16, 28, 255)
    out = Image.fromarray(o); out.alpha_composite(img, (k, k))
    return out


# ---------------------------------------------------------------- diagram (low-res 640x180 canvas, x4 = 2560x720)
LW, LH, S4 = 640, 180, 4
NAVY, GRID_C, FLOOR = (18, 24, 40), (26, 34, 56), (44, 52, 78)
STEEL, STEEL_D, PIPE, FLUID, FLUID_HI = (150, 156, 168), (96, 102, 116), (90, 96, 110), (200, 150, 40), (255, 236, 120)
P_PIV = (62, 54)
ROTOR = (250, 100); R_ROT = 38
PIPE_PTS = [(150, 89), (208, 89), (208, 60), (236, 60)]


def press(t):
    """Brake pedal travel 0..1."""
    on = wt(2, 'press') + 0.15
    return ss((t - on) / 0.25) * (1 - ss((t - (START[7] + 0.2)) / 0.4))


def clamp_amt(t): return ss((t - wt(5, 'clamp')) / 0.35) * (1 - ss((t - (START[7] + 0.2)) / 0.4))


def heat(t): return ss((t - wt(6, 'friction')) / 2.2) * (1 - ss((t - (START[7] + 0.4)) / 0.8))


def rotor_angle(t):
    """Fast spin that bleeds off once the pads clamp (integrated speed)."""
    t0 = wt(5, 'clamp')
    if t < t0: return t * 9
    dt = t - t0
    return t0 * 9 + 9 * (1 - math.exp(-dt * 0.9)) / 0.9


def path_point(pts, s):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]):
        L = math.hypot(x1 - x0, y1 - y0)
        if s <= L: return x0 + (x1 - x0) * s / L, y0 + (y1 - y0) * s / L
        s -= L
    return pts[-1]


PIPE_LEN = sum(math.hypot(b[0] - a[0], b[1] - a[1]) for a, b in zip(PIPE_PTS, PIPE_PTS[1:]))


def label_at(img, txt, x, y, s, col='#ffffff'):
    if s <= 0: return
    lab = outline(pix.label(txt, col), 1)
    if s != 1: lab = lab.resize((max(1, round(lab.width * s)), max(1, round(lab.height * s))), Image.Resampling.NEAREST)
    img.alpha_composite(lab, (int(x - lab.width / 2), int(y - lab.height / 2)))


def arrow(d, x0, y, x1, col, w=3):
    if x1 - x0 < 6: return
    d.rectangle([x0, y - w // 2, x1 - 4, y + w // 2], fill=col)
    d.polygon([(x1, y), (x1 - 6, y - 5), (x1 - 6, y + 5)], fill=col)


def diagram_lowres(t):
    img = Image.new('RGBA', (LW, LH), NAVY + (255,)); d = ImageDraw.Draw(img)
    for x in range(0, LW, 16): d.line([(x, 0), (x, 158)], fill=GRID_C)
    for y in range(0, 158, 16): d.line([(0, y), (LW, y)], fill=GRID_C)
    d.rectangle([0, 160, LW, LH], fill=FLOOR); d.line([(0, 160), (LW, 160)], fill=(70, 80, 110))
    p, cl, h = press(t), clamp_amt(t), heat(t)
    # --- pedal + push rod + master cylinder
    a = lerp(-0.18, 0.32, p)
    pad = (P_PIV[0] + 66 * math.sin(a), P_PIV[1] + 66 * math.cos(a))
    att = (P_PIV[0] + 34 * math.sin(a), P_PIV[1] + 34 * math.cos(a))
    xp = 104 + 16 * p
    d.line([att, (xp, 89)], fill=STEEL, width=3)
    d.line([P_PIV, pad], fill=(60, 64, 76), width=5)
    d.rectangle([pad[0] - 9, pad[1] - 3, pad[0] + 9, pad[1] + 3], fill=(40, 42, 50)); d.line([(pad[0] - 8, pad[1] - 2), (pad[0] + 8, pad[1] - 2)], fill=(90, 94, 104))
    d.ellipse([P_PIV[0] - 4, P_PIV[1] - 4, P_PIV[0] + 4, P_PIV[1] + 4], fill=STEEL)
    d.rectangle([112, 70, 136, 81], fill=(60, 66, 80)); d.rectangle([114, 74, 134, 80], fill=FLUID)   # reservoir
    d.rectangle([100, 82, 150, 96], fill=(70, 76, 92)); d.rectangle([102, 84, 148, 94], fill=(36, 40, 52))
    d.rectangle([xp + 3, 84, 148, 94], fill=FLUID if p < .5 else FLUID_HI)
    d.rectangle([xp - 2, 83, xp + 2, 95], fill=STEEL)                                                     # piston
    # --- brake line with pressure pulses
    d.line(PIPE_PTS, fill=PIPE, width=6); d.line(PIPE_PTS, fill=FLUID, width=2)
    t_go = wt(3, 'races') - 0.6
    if t >= t_go and p > 0.3:
        for k in range(12):
            s = ((t - t_go) * 110 - k * 26) % (PIPE_LEN + 60) - 20
            if 0 <= s <= PIPE_LEN:
                x, y = path_point(PIPE_PTS, s); d.rectangle([x - 2, y - 2, x + 2, y + 2], fill=FLUID_HI)
    # --- rotor (heats up) + hub + caliper
    rot_col = tuple(int(c) for c in (np.array(STEEL) * (1 - h) + np.array([255, 110, 40]) * h))
    d.ellipse([ROTOR[0] - R_ROT, ROTOR[1] - R_ROT, ROTOR[0] + R_ROT, ROTOR[1] + R_ROT], fill=STEEL_D)
    d.ellipse([ROTOR[0] - R_ROT + 3, ROTOR[1] - R_ROT + 3, ROTOR[0] + R_ROT - 3, ROTOR[1] + R_ROT - 3], fill=rot_col)
    ang = rotor_angle(t)
    for k in range(10):
        q = ang + k * math.tau / 10; x = ROTOR[0] + 27 * math.cos(q); y = ROTOR[1] + 27 * math.sin(q)
        d.rectangle([x - 1.5, y - 1.5, x + 1.5, y + 1.5], fill=STEEL_D)
    d.ellipse([ROTOR[0] - 13, ROTOR[1] - 13, ROTOR[0] + 13, ROTOR[1] + 13], fill=(54, 58, 70))
    for k in range(5):
        q = ang + k * math.tau / 5; x = ROTOR[0] + 7 * math.cos(q); y = ROTOR[1] + 7 * math.sin(q)
        d.rectangle([x - 1, y - 1, x + 1, y + 1], fill=(200, 204, 214))
    d.rectangle([234, 52, 268, 70], fill=(170, 34, 44)); d.rectangle([234, 52, 268, 54], fill=(220, 70, 70))
    # --- callout: top-down view of the clamp (pads squeeze the rotor)
    cs = pop(t, wt(5, 'pistons') - 0.1)
    if cs > 0:
        box = Image.new('RGBA', (66, 50), (12, 16, 30, 255)); bd = ImageDraw.Draw(box)
        bd.rectangle([0, 0, 65, 49], outline=(120, 140, 200)); bd.rectangle([31, 4, 35, 45], fill=rot_col)   # rotor edge-on
        gap = lerp(9, 1, cl)
        for sgn in (-1, 1):
            px0 = 33 + sgn * (2 + gap)
            bd.rectangle([min(px0, px0 + sgn * 5), 14, max(px0, px0 + sgn * 5), 35], fill=(200, 180, 130))   # pad
            bd.rectangle([min(px0 + sgn * 5, px0 + sgn * 13), 16, max(px0 + sgn * 5, px0 + sgn * 13), 33], fill=(170, 34, 44))  # piston
        if cl > .6:
            for k in range(4): bd.point((33 + (k % 2) * 2 - 1, 8 + k * 9), fill=(255, 200, 80))
        box = box.resize((max(1, int(66 * cs)), max(1, int(50 * cs))), Image.Resampling.NEAREST)
        img.alpha_composite(box, (int(286 - box.width / 2), int(34 - box.height / 2)))
        d.line([(268, 58), (286 - 33 * cs, 40)], fill=(120, 140, 200))
    # --- force multiplier panel
    ms = pop(t, wt(4, 'bigger') - 0.1)
    if ms > 0 and t < START[5] - 0.1:
        mp = Image.new('RGBA', (110, 44), (0, 0, 0, 0)); md = ImageDraw.Draw(mp)
        md.rectangle([4, 14, 12, 30], fill=STEEL); md.rectangle([60, 6, 82, 38], fill=(170, 34, 44))
        g1 = pop(t, wt(4, 'pushes') - .1, .4); g2 = pop(t, wt(4, 'multiplies') - .1, .5)
        arrow(md, 14, 22, 14 + 18 * g1, (255, 236, 120), 3); arrow(md, 84, 22, 84 + 24 * g2, (255, 236, 120), 7)
        md.line([(12, 22), (60, 22)], fill=FLUID, width=2)
        mp = mp.resize((max(1, int(110 * ms)), max(1, int(44 * ms))), Image.Resampling.NEAREST)
        img.alpha_composite(mp, (int(150 - mp.width / 2), int(132 - mp.height / 2)))
        label_at(img, 'SMALL', 103, 116, pop(t, wt(4, 'pushes')))
        label_at(img, 'BIG FORCE', 178, 110, pop(t, wt(4, 'multiplies')), '#ffd23f')
    # --- labels as the narrator names each part
    label_at(img, 'PEDAL', 104, 128, pop(t, wt(2, 'pedal')) * (t < START[4]))
    label_at(img, 'MASTER CYLINDER', 125, 62, pop(t, wt(2, 'master')) * (t < START[4]))
    label_at(img, 'BRAKE FLUID', 180, 98, pop(t, wt(3, 'fluid', 0)) * (t < START[4]))
    label_at(img, 'ROTOR', 312, 110, pop(t, wt(5, 'rotor')))
    label_at(img, 'PADS', 286, 66, pop(t, wt(5, 'pads')))
    if t > wt(6, 'motion') - .1:                        # MOTION -> HEAT
        s = pop(t, wt(6, 'motion') - .1)
        label_at(img, 'MOTION', 150, 40, s); arrow(d, 172, 40, 172 + 20 * pop(t, wt(6, 'heat') - .1), (255, 140, 40), 3)
        label_at(img, 'HEAT', 212, 40, pop(t, wt(6, 'heat')), '#ff8c32')
    if t > START[7] - 0.6: abs_panel(img, d, t)      # only once the camera heads there
    return img


def abs_panel(img, d, t):
    """Right half of the canvas: locked wheel vs ABS wheel."""
    on = pop(t, wt(7, 'abs'))
    d.rectangle([330, 126, 630, 150], fill=(70, 72, 82)); d.line([(330, 126), (630, 126)], fill=(190, 188, 176))
    for x in range(334, 630, 16): d.rectangle([x, 137, x + 7, 138], fill=(240, 200, 70))
    loop = (t - START[7]) % 3.0
    for k, (cx, locked) in enumerate(((405, True), (555, False))):
        slide = cx - 30 + 40 * ss(loop / 2.4)
        if locked:                                     # skid mark + smoke, wheel frozen
            d.rectangle([cx - 30, 124, slide, 126], fill=(30, 30, 34))
            for j in range(4):
                a = ((loop * 3 + j * .3) % 1)
                r = 3 + 7 * a; x = slide - 18 - 18 * a; y = 118 - 10 * a
                d.ellipse([x - r, y - r, x + r, y + r], fill=(200, 202, 208))
            ang = 0.4
        else:
            ang = -(slide / 18)
        d.ellipse([slide - 18, 88, slide + 18, 124], fill=(30, 30, 36))
        d.ellipse([slide - 10, 96, slide + 10, 116], fill=(150, 156, 168))
        for j in range(5):
            q = ang + j * math.tau / 5
            d.rectangle([slide + 6 * math.cos(q) - 1, 106 + 6 * math.sin(q) - 1, slide + 6 * math.cos(q) + 1, 106 + 6 * math.sin(q) + 1], fill=(60, 64, 76))
        if not locked:                                 # pressure pulsing many times a second
            for j in range(6):
                hgt = 4 + 10 * (int((t * 14 + j * 0.5)) % 2)
                d.rectangle([cx - 24 + j * 9, 70 - hgt, cx - 18 + j * 9, 70], fill=(255, 236, 120))
    label_at(img, 'NO ABS', 405, 40, on, '#ff7a80'); label_at(img, 'ABS', 555, 40, on, '#7ab0f0')
    g = pop(t, wt(7, 'gripping'))
    if g > 0:
        for icon, x in ((pix.xmark(), 405), (pix.check(), 555)):
            ic = icon.resize((max(1, int(icon.width * g)), max(1, int(icon.height * g))), Image.Resampling.NEAREST)
            img.alpha_composite(ic, (int(x + 40 - ic.width / 2), int(104 - ic.height / 2)))


# narrator (green stickman) in full-res canvas coords
def narrator_keys():
    k = [(0, 160, 0, 'stand', 1)]
    tp = wt(2, 'press')
    k += [(tp - 0.5, 175, 0, 'stand', 1), (tp - 0.25, 200, 0, 'windup', 1), (tp, 250, -50, 'flykick', 1),
          (tp + 0.25, 215, 0, 'land', 1), (tp + 0.6, 190, 0, 'stand', 1)]
    for i, word in ((3, 'fluid'), (4, 'wheel'), (5, 'pistons'), (6, 'friction')):
        w0 = wt(i, word)
        k += [(w0 - 0.2, 190, 0, 'stand', 1), (w0, 200, 0, 'punch', 1), (w0 + 1.4, 200, 0, 'punch', 1), (w0 + 1.7, 190, 0, 'stand', 1)]
    s7 = START[7]                                      # backflip across to the ABS panel as the camera pans
    k += [(s7 - 0.1, 190, 0, 'crouch', 1), (s7 + 0.3, 700, -260, 'tuck', 1, -180), (s7 + 0.7, 1300, -200, 'tuck', 1, -360),
          (s7 + 1.0, 1400, 0, 'land', 1, -360), (s7 + 1.3, 1400, 0, 'stand', 1, -360),
          (wt(7, 'steer') - .2, 1400, 0, 'stand', 1, -360), (wt(7, 'steer'), 1410, 0, 'punch', 1, -360), (TR2[1], 1410, 0, 'punch', 1, -360)]
    k.sort(key=lambda e: e[0])
    return k


NK = None
CAM_D = None


def diagram_cam():
    s = START
    return [(TR1[0], 1.0, 1000, 400), (TR1[1] - 0.1, 1.0, 1000, 400), (s[2] + 0.5, 1.0, 640, 360), (wt(2, 'press') - .4, 1.25, 470, 410),
            (s[3] - 0.2, 1.25, 470, 410), (s[3] + 0.4, 1.0, 640, 360), (s[4] - 0.2, 1.0, 640, 360),
            (s[4] + 0.4, 1.15, 640, 450), (s[5] - 0.2, 1.15, 640, 450), (s[5] + 0.4, 1.6, 990, 300),
            (s[6] - 0.2, 1.6, 990, 300), (s[6] + 0.4, 1.3, 900, 380), (s[7] - 0.1, 1.3, 900, 380),
            (s[7] + 0.9, 1.0, 1920, 360), (TR2[0], 1.0, 1920, 360), (TR2[0] + 0.6, 1.0, 1000, 400), (TR2[1], 1.0, 1000, 400)]


def cam_at(keys, t):
    if t <= keys[0][0]: return keys[0][1:]
    for a, b in zip(keys, keys[1:]):
        if t <= b[0]:
            u = ss((t - a[0]) / max(1e-6, b[0] - a[0]))
            return tuple(lerp(p, q, u) for p, q in zip(a[1:], b[1:]))
    return keys[-1][1:]


def zoom(img, z, cx, cy, cw=W, ch=H):
    cx = min(max(cx, 640 / z), cw - 640 / z); cy = min(max(cy, 360 / z), ch - 360 / z)
    return img.transform((W, H), Image.Transform.AFFINE, (1 / z, 0, cx - 640 / z, 0, 1 / z, cy - 360 / z), Image.Resampling.NEAREST)


def diagram_frame(t, z=None, cx=None, cy=None):
    global NK, CAM_D
    if NK is None: NK, CAM_D = narrator_keys(), diagram_cam()
    low = diagram_lowres(t)
    big = low.resize((LW * S4, LH * S4), Image.Resampling.NEAREST)
    gl = Image.new('RGB', (LW * S4, LH * S4)); gld = ImageDraw.Draw(gl)
    h = heat(t)
    if h > 0.05:
        r = R_ROT * S4; c = (ROTOR[0] * S4, ROTOR[1] * S4)
        gld.ellipse([c[0] - r, c[1] - r, c[0] + r, c[1] + r], fill=tuple(int(v * h) for v in (255, 90, 30)))
    chars = Image.new('RGBA', big.size, (0, 0, 0, 0))
    duel.draw_fighter(ImageDraw.Draw(chars), NK, t, 'green', 1.0, 640)
    cw = big.size[0]
    small = chars.resize((round(cw / duel.CPX), round(H / duel.CPX)), Image.Resampling.BOX)
    a = np.asarray(small).copy(); on = a[..., 3] > 90; a[..., 3] = np.where(on, 255, 0)
    ring = np.zeros_like(on)
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)): ring |= np.roll(np.roll(on, dy, 0), dx, 1)
    ring &= ~on; a[ring] = (200, 214, 245, 255)                    # light rim so the dark stickman reads on navy
    big = Image.alpha_composite(big, Image.fromarray(a).resize(big.size, Image.Resampling.NEAREST))
    glow = gl.resize((cw // 8, H // 8)).resize(big.size, Image.Resampling.NEAREST)
    out = Image.fromarray((np.asarray(big.convert('RGB')).astype(np.float32) + np.asarray(glow).astype(np.float32) * .5).clip(0, 255).astype(np.uint8))
    if z is None: z, cx, cy = cam_at(CAM_D, t)
    return zoom(out, z, cx, cy, cw, H)


# ---------------------------------------------------------------- composition
WHEEL = (car_front(3.4) - 50 * CAR_S + 40 * CAR_S, CAR_Y + 18 * CAR_S)   # front wheel centre once stopped


def road_cam(t):
    """Gentle push-in on the wheel while the question is asked, then zoom right into it."""
    if t < START[1]: return 1.0, 640, 360
    if t < TR1[0]:
        u = ss((t - START[1]) / (TR1[0] - START[1])); return lerp(1, 1.3, u), lerp(640, WHEEL[0], u), lerp(360, WHEEL[1], u)
    if t < TR1[1]:
        u = ss((t - TR1[0]) / (TR1[1] - TR1[0])); return 1.3 * (10 / 1.3) ** u, WHEEL[0], WHEEL[1] - 40 / (1.3 * (10 / 1.3) ** u)
    if t < TR2[0]: return 10.0, WHEEL[0], WHEEL[1] - 4
    if t < TR2[1] + 0.9:
        u = ss((t - (TR2[0] + 0.5)) / (TR2[1] + 0.4 - TR2[0])); return 10 * (1 / 10) ** u, lerp(WHEEL[0], 640, u), lerp(WHEEL[1] - 4, 360, u)
    return 1.0, 640, 360


def caption(t):
    for i, words in enumerate(WORDS):
        if not (START[i] - 0.05 <= t <= START[i] + words[-1]['e'] + 0.25): continue
        chunks, cur = [], []
        for w in words:
            cur.append(w)
            if len(cur) == 3 or w['w'][-1] in '.,!?:': chunks.append(cur); cur = []
        if cur: chunks.append(cur)
        for j, c in enumerate(chunks):
            t0 = START[i] + c[0]['s']
            t1 = START[i] + (chunks[j + 1][0]['s'] if j + 1 < len(chunks) else c[-1]['e'] + 0.25)
            if t0 - 0.05 <= t < t1:
                txt = ' '.join(''.join(ch for ch in w['w'].upper() if ch in pix.FONT) for w in c)
                return txt, pop(t, t0 - 0.05, 0.15)
    return None, 0


def draw_caption(img, t):
    txt, s = caption(t)
    if not txt: return img
    lab = outline(pix.up(pix.label(txt), 6), 6)
    if s != 1: lab = lab.resize((max(1, int(lab.width * s)), max(1, int(lab.height * s))), Image.Resampling.NEAREST)
    img = img.convert('RGBA'); img.alpha_composite(lab, (int(W / 2 - lab.width / 2), int(650 - lab.height / 2)))
    return img.convert('RGB')


def frame(t, road, dark, tail):
    mid1, mid2 = (TR1[0] + TR1[1]) / 2 + 0.25, (TR2[0] + TR2[1]) / 2 + 0.2
    if t < mid1 - 0.2 or t > mid2 + 0.2:
        img = zoom(road_frame(t, road, dark, tail), *road_cam(t))
    elif mid1 + 0.2 <= t <= mid2 - 0.2:
        img = diagram_frame(t)
    else:                                            # match cut: wheel <-> rotor cross-dissolve while both are zoomed
        a = zoom(road_frame(t, road, dark, tail), *road_cam(t))
        b = diagram_frame(t)
        k = ss((t - (mid1 - 0.2)) / 0.4) if t < (mid1 + mid2) / 2 else 1 - ss((t - (mid2 - 0.2)) / 0.4)
        img = Image.blend(a, b, k)
    img = draw_caption(img, t)
    if t > DUR - 0.5:
        img = Image.fromarray((np.asarray(img).astype(np.float32) * (DUR - t) / 0.5).astype(np.uint8))
    return np.asarray(img)


# ---------------------------------------------------------------- audio
def add(buf, i, s):
    i = max(0, i); j = min(len(buf), i + len(s))
    if i < len(buf): buf[i:j] += s[:j - i]


def read_vo(i):
    with wave.open(str(VO / f'line_{i:02d}.wav')) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), np.int16).astype(np.float32) / 32768
        sr = w.getframerate()
    return np.interp(np.arange(int(len(x) * SR / sr)) * sr / SR, np.arange(len(x)), x)


def audio(path):
    n = int(DUR * SR)
    tmp = path.with_name('duel_tmp.wav'); duel.audio(tmp)                   # the duel's own soundtrack for the fight
    with wave.open(str(tmp)) as w:
        da = np.frombuffer(w.readframes(w.getnframes()), np.int16).reshape(-1, 2)[:, 0].astype(np.float32) / 32768
    tmp.unlink()
    seg = da[int(5.1 * SR):int((5.1 + FIGHT_END + 0.3) * SR)].copy()
    seg[-int(0.3 * SR):] *= np.linspace(1, 0, int(0.3 * SR))
    mix = np.zeros(n); add(mix, 0, seg * 0.9)
    mus = duel.music(n + int(5.1 * SR))[int(5.1 * SR):]
    env = np.full(n, 0.16)
    a0, a1 = int(FIGHT_END * SR), int(3.6 * SR)
    env[:a0] = 0; env[a0:a1] = np.linspace(0.0, 0.16, a1 - a0) ** 0.5 * 2.2
    vo = np.zeros(n)
    for i in range(len(LINES)): add(vo, int(START[i] * SR), read_vo(i))
    speak = np.convolve(np.abs(vo) > 0.02, np.ones(int(0.25 * SR)) / int(0.25 * SR), 'same')
    env *= 1 - 0.45 * np.clip(speak * 3, 0, 1)                             # duck music under the voice
    env[int((DUR - 0.6) * SR):] *= np.linspace(1, 0, n - int((DUR - 0.6) * SR))
    mix += mus * env + vo * 1.15
    ev = [(1.8, sfx.vroom(1.3) * .8), (2.4, sfx.screech(1.0) * .9), (3.4, sfx.thump(0.3)), (3.42, duel.clang(0.4) * .3),
          (TR1[0], sfx.whoosh(1.0, 20) * .8), (TR2[0] + 0.4, sfx.whoosh(1.0, 20) * .8),
          (wt(2, 'press') - .02, sfx.thump(0.25)), (wt(5, 'clamp'), duel.clang(0.4) * .5), (wt(7, 'abs'), sfx.pop()),
          (CLASH, sfx.boom(1.0)), (CLASH, duel.clang(0.8)), (CLASH - 0.25, sfx.whoosh(0.25, 6))]
    for i, word in ((2, 'pedal'), (2, 'master'), (3, 'fluid'), (4, 'bigger'), (4, 'multiplies'), (5, 'pads'), (5, 'rotor'),
                    (6, 'motion'), (6, 'heat'), (7, 'gripping')):
        ev.append((wt(i, word), sfx.pop() * .5))
    for _, w in OUTRO_WORDS: ev.append((wt(8, w), sfx.ding(1568, 0.4) * .35))
    hiss = sfx.lp(np.random.default_rng(4).standard_normal(int(SR * 2.0)), 6) * np.sin(np.linspace(0, np.pi, int(SR * 2.0))) * .25
    ev.append((wt(3, 'races') - .4, hiss))
    ev.append((wt(6, 'friction'), duel.crackle(2.0) * .5))
    t_abs = wt(7, 'abs')
    for k in range(int(3.0 * 14)):                                        # ABS chatter
        click = np.random.default_rng(k).standard_normal(int(SR * .012)) * np.exp(-sfx.T(.012) * 300) * .35
        ev.append((t_abs + k / 14, click))
    for t0, s in ev: add(mix, int(t0 * SR), s)
    mix = np.tanh(mix * 1.1) * 0.85
    pcm = (np.stack([mix, mix], 1) * 32767).astype(np.int16)
    with wave.open(str(path), 'wb') as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())


def setup():
    duel.CZ, duel.CX, duel.CY = [(0, 1.0), (99, 1.0)], [(0, 640), (99, 640)], [(0, 360), (99, 360)]   # steady camera
    road, dark = build_road()
    return road, dark, duel.make_tail()


def main():
    mode = sys.argv[1]
    road, dark, tail = setup()
    if mode == 'still':
        out = Path(sys.argv[2]); out.mkdir(parents=True, exist_ok=True)
        for s in sys.argv[3:]: Image.fromarray(frame(float(s), road, dark, tail)).save(out / f'f_{s}.png')
        return
    dst = Path(sys.argv[2]); dst.parent.mkdir(parents=True, exist_ok=True)
    t_end = float(sys.argv[3]) if len(sys.argv) > 3 else DUR
    t_start = float(sys.argv[4]) if len(sys.argv) > 4 else 0.0
    wav = dst.with_suffix('.wav'); audio(wav)
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS),
                          '-i', '-', '-ss', str(t_start), '-i', str(wav), '-t', str(t_end - t_start), '-c:v', 'libx264', '-crf', '18',
                          '-pix_fmt', 'yuv420p', '-c:a', 'aac', '-b:a', '192k', '-shortest', str(dst)], stdin=subprocess.PIPE)
    for i in range(int(round(t_start * FPS)), int(round(t_end * FPS))):
        p.stdin.write(frame(i / FPS, road, dark, tail).tobytes())
    p.stdin.close(); sys.exit(p.wait())


if __name__ == '__main__':
    main()
