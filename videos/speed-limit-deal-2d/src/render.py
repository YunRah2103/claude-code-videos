"""Renders 'speed-limit-deal' (2D version): same script, voiceover, word timings, beats, text, gauge, poll and photo as
the 3D version (videos/speed-limit-deal-3d/src/beats.py), drawn with the 2D engine (shared/pixanim + garage backdrop).

World: garage set, three side-view cars (red / blue / silver, no badges) in three rows launching at a glowing force wall,
the shared pixel gauge (shared/assets/pix2d.py) hanging upper-middle. Camera: push-in + shake in code (crop/scale NEAREST).
    python render.py still <dir> t... | safecheck | safestill <dir> t... | video <vo.wav> <out.mp4> [t0 t1]
"""
import math, os, sys
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'videos', 'speed-limit-deal-3d', 'src'))     # shared beats for both versions
import beats as B
from beats import SLAM, BUMP, T2, STAMP, T3, FILL0, FILL1, T4, ZIP, T5, TURN, OPEN, T6, END_T, DUR, FPS
import episode as kit
from episode import W, H
from pixanim.motion import prog, lerp, io, oc, ob
from pixanim.grid import up
from pixanim.car import car, wheel_deg
from pixanim.autos import supercar
from pixanim import fx, transitions as T
from backdrops.garage import Garage
from assets import overlays as ov, pix2d

PRE = -0.4                                     # cars already rolling before frame 0 (the loop pre-roll)
G = Garage(W, H, 1440, 9)
WALL_X = 870                                   # force wall (x centre), spans the three rows
ROWS = [('silver', 1490, 5, 60), ('blue', 1660, 6, -10), ('red', 1850, 7, -80)]   # colour, ground y, pixel, x at PRE
GAUGE = (560, 760)                             # gauge centre (upper-middle, ~30 % of the width)


def car_x(i, t):
    col, gy, s, x0 = ROWS[i]
    xs = WALL_X - 90 * s / 2 - 22
    if t < SLAM: return x0 + (xs - x0) * prog(t, PRE, SLAM - PRE) ** 2
    hit = t - SLAM; x = xs - 40 * math.exp(-hit * 6) * abs(math.sin(hit * 14))
    if BUMP - 0.4 < t < BUMP + 1:
        b = t - BUMP; x = xs - (14 * prog(t, BUMP - 0.4, 0.4) if t < BUMP else 20 * math.exp(-b * 7) * abs(math.sin(b * 16)))
    if i == 1 and OPEN + 0.25 <= t < END_T: x = xs + 900 * io(prog(t, OPEN + 0.25, 0.9))
    return x


def gauge_state(t):
    if t < T3:
        run = prog(t, PRE, SLAM - PRE)
        v = 155 * run ** 1.4 if t < SLAM else 155 + math.sin(t * 50) * 1.2 * math.exp(-(t - SLAM) * 1.5)
        return v, v, (math.exp(-(t - SLAM) * 2) * 0.8 + 0.2 if t >= SLAM else 0), t >= SLAM - 0.05
    u = io(prog(t, FILL0, FILL1 - FILL0)); v = 155 * u + (math.sin(t * 40) * 0.8 if u >= 1 else 0)
    return v, v, 1.0 if t >= FILL1 else 0.2, True


def cam(t):
    """(zoom, centre x, centre y, shake px): fast push-in to the slam, punch on the stamp, held otherwise."""
    z = lerp(1.0, 1.16, oc(prog(t, PRE, 1.4 - PRE))) if t < T2 else 1.16
    if T2 <= t: z = lerp(1.16, 1.06, io(prog(t, T2, 0.35)))
    if t >= STAMP and t < T3: z += 0.08 * math.exp(-(t - STAMP) * 5)
    if t >= T6: z = lerp(1.06, 1.0, io(prog(t, T6, 0.5)))
    sh = (6 if t < SLAM else 0) + (40 * math.exp(-(t - SLAM) * 4.5) if t >= SLAM else 0) + (18 * math.exp(-(t - BUMP) * 6) if t >= BUMP else 0) \
        + (26 * math.exp(-(t - STAMP) * 7) if t >= STAMP else 0) + (18 * math.exp(-(t - OPEN) * 6) if t >= OPEN else 0)
    return z, 600, 1250, sh


def world(t):
    img = G.frame(t).convert('RGBA'); fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    fx.rays(fg, t + 20, 0, 540, -40, (255, 210, 63, 34), hold=True, r=1500, n=9)          # yellow light rays from the top
    img.alpha_composite(fg); fg = Image.new('RGBA', (W, H), (0, 0, 0, 0))
    # gauge on two chains from the ceiling
    v, fill, glow, lim = gauge_state(t)
    gimg = up(pix2d.gauge(v, fill, glow, lim), 4); gx, gy = GAUGE
    for dx in (-90, 90): fx.blit(fg, Image.new('RGBA', (8, gy - gimg.height // 2), (60, 63, 71, 255)), gx + dx, gy - gimg.height // 2)
    fx.blit(fg, gimg, gx, gy, anchor='center')
    # the three cars (back to front) with the wall drawn between them and the camera

    for i, (col, gy_, s, x0) in enumerate(ROWS):
        x = car_x(i, t); dist = x - x0
        fx.contact_shadow(fg, x, gy_, 90 * s * 0.9, s=s)
        pitch = -3 * math.exp(-(t - SLAM) * 7) * math.cos((t - SLAM) * 18) if t >= SLAM else 2 * prog(t, PRE, 0.5)
        fx.blit(fg, up(car(col, wheel_deg(dist, s), lights=True, brake=t >= SLAM), s), x + (2 * math.sin(t * 60 + i) if t < SLAM else 0), gy_, rot=pitch)
    # Porsche-like orange sports car zips past along the front
    if ZIP - 0.05 <= t < T5:
        u = prog(t, ZIP, 1.0); x = lerp(-500, 1700, u ** 1.1)
        fx.blit(fg, up(supercar('orange', spin=int(u * 40)), 6), x, 1915)
    # force wall: glows, flashes on hits, shatters on the unlock
    hits = [h for h in (SLAM, BUMP) if t >= h]
    k = math.exp(-(t - hits[-1]) * 4) if hits else 0
    if not (OPEN <= t < END_T):
        fx.blit(fg, up(pix2d.force_wall(14, 74, k, t, 0.85 if t < T2 else 0.6), 9), WALL_X, 1870)
    else:
        fx.burst(fg, t, OPEN, WALL_X, 1500, n=14); fx.flakes(fg, t, OPEN, WALL_X, 1500, n=14, seed=4, spread=300, life=1.2, rise=-300, s=9, t1=END_T)
    if t >= SLAM and t < SLAM + 0.5: fx.ring(fg, t, SLAM, WALL_X - 20, 1600, (255, 210, 63), life=0.4)
    # handshake (the deal), padlock + key (unlock)
    hk = (ob(prog(t, T2 + 0.1, 0.3)) * (1 - prog(t, T3 - 0.1, 0.2))) if T2 + 0.1 <= t < T3 + 0.1 else 0
    if hk > 0.01:
        rot = 6 * math.sin(t * 2.2) + (10 * math.exp(-(t - STAMP) * 6) * math.sin((t - STAMP) * 40) if t >= STAMP else 0)
        fx.blit(fg, up(pix2d.handshake(), 9), 470, 1200 + 10 * math.sin(t * 4), hk, hk, rot, anchor='center')
    if T5 - 0.05 <= t < OPEN + 0.9:
        lk = ob(prog(t, T5 - 0.05, 0.25)); fall = 2000 * max(0, t - OPEN - 0.15) ** 2
        fx.blit(fg, up(pix2d.padlock(oc(prog(t, OPEN, 0.12))), 10), WALL_X, 1450 + fall, lk, lk, -150 * max(0, t - OPEN - 0.15), anchor='center')
    if T5 <= t < OPEN + 0.4:
        u = io(prog(t, T5 + 0.05, TURN - T5 - 0.05))
        kimg = up(pix2d.key(), 8).transpose(Image.FLIP_LEFT_RIGHT)
        fx.blit(fg, kimg, lerp(1150, WALL_X + 110, u), lerp(1200, 1460, u), 1, 1 if t < TURN else max(0.15, 1 - io(prog(t, TURN, 0.15))), 20 * (1 - u), anchor='center')
    if t < SLAM + 0.05:
        fx.speed_lines(fg, 0.55 + 0.3 * math.sin(t * 9), int(t * 20) % 7, horizontal=True)
    fg = G.rim(fg); img.alpha_composite(fg)
    if P.get('visible', t, True): P.draw(img, t)
    return img.convert('RGB')


def frame_cam(img, t):
    z, cx, cy, sh = cam(t)
    w, h = W / z, H / z
    ox = sh * math.sin(t * 61) ; oy = sh * math.cos(t * 47)
    x0 = min(max(cx - w * (cx / W) + ox, 0), W - w); y0 = min(max(cy - h * (cy / H) + oy, 0), H - h)
    return img.crop((round(x0), round(y0), round(x0 + w), round(y0 + h))).resize((W, H), Image.NEAREST)


def scene(t): return frame_cam(world(t), t)


def anchor(name, t):
    """Screen positions after the camera, for the presenter, chips and pointing."""
    z, cx, cy, _ = cam(t)
    pts = {'carL': (car_x(0, t), ROWS[0][1] - 100), 'carM': (car_x(1, t), ROWS[1][1] - 120), 'carR': (car_x(2, t), ROWS[2][1] - 140),
           'hand': (470, 1200), 'dial': GAUGE, 'host': (985, 1440)}
    x, y = pts[name]
    if name == 'host': return x, y                      # the presenter is drawn in the world layer
    w, h = W / z, H / z; x0 = cx - w * (cx / W); y0 = cy - h * (cy / H)
    return (x - x0) * z, (y - y0) * z


def _world_anchor(name, t):
    return {'host': (985, 1440), 'carM': (car_x(1, t), ROWS[1][1] - 120), 'hand': (470, 1200)}.get(name, (540, 960))


P = B.presenter(_world_anchor)


def shot(t):
    ov.reset()
    if t >= END_T:                                      # loop: whip from the poll framing back to the cold-open pre-roll
        e = io(prog(t, END_T, 0.26))
        return scene(t - DUR) if e >= 1 else T.whip(scene(END_T - 0.01), scene(t - DUR), e, dx=-1)
    return scene(t)


B.setup(HERE, shot, anchor, 'red')

if __name__ == '__main__':
    if sys.argv[1] == 'safecheck':
        raise SystemExit(0 if B.safecheck() else 1)
    elif sys.argv[1] == 'safestill':
        os.makedirs(sys.argv[2], exist_ok=True)
        for ts in sys.argv[3:]:
            im = Image.frombytes('RGB', (W, H), kit.frame(round(float(ts) * FPS))).convert('RGBA'); ov.draw_safe(im)
            im.convert('RGB').save(f'{sys.argv[2]}/safe_{ts}.png')
    else:
        kit.main()
