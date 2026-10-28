"""Presenter: a living, mobile host driven by a timeline of beats.

    P = Presenter([
        (0.0, dict(path=Track([...], smooth=True), size=6, legs='fly', look=lambda t: (390, 820))),
        (0.57, dict(arms=('aim', 40), expr='grin')),
        (1.88, dict(expr='shock', arms='shock', squash=True)),
    ], words=WORDS)
    P.draw(layer, t, 'front')          # inside a scene, between background and foreground props
    P.draw(screen, t, 'front', cam=CAM) # as a screen-space overlay during a transition

Each beat overrides only the fields it names; the rest carry forward. Fields:
  path   object with .at(t) -> (x, y) feet position (Track, Orbit, Seq, lambda wrapped by Fn)
  size   pixel size (int or Track); always rendered at an integer scale, so pixels stay crisp
  arms   preset name, ('aim', deg), or 'point' to aim at `point`; anim presets cycle: 'wave', 'cheer', 'flail', 'talk'
  point  (x, y) or fn(t): the right arm aims at it (and the body faces it)
  look   (x, y) or fn(t): eyes and facing track it
  legs   pose, or 'auto' (fly when airborne, run when moving on the ground, stand when still)
  expr   expression; 'smile' talks automatically while the voiceover is speaking and blinks
  face   1 / -1 to force facing; None = automatic
  ground y of the floor under him (contact shadow + landing), or None while flying freely
  z      'front' / 'back', or fn(t) -> 'front'/'back' for orbits that pass behind objects
  hover  bob amplitude in px while airborne; tilt: lean into motion (deg per 1000 px/s)
  visible False hides him (let the mechanism take centre stage)
  trail  motion ghosts + speed lines when fast
  squash one-shot jelly wobble starting at this beat (landings, impacts)
"""
import math
from PIL import Image, ImageDraw
from .guy import guy, hand_offset, SHOULDER_R, FEET, W as GW, H as GH
from .grid import up
from .motion import clamp, jelly
from .fx import contact_shadow

ANIM = {'wave': ('wave1', 'wave2', 6), 'cheer': ('cheer1', 'cheer2', 7), 'flail': ('flail1', 'flail2', 10),
        'talk': ('talkR', 'talkB', 4), 'run': ('run1', 'run2', 9)}


class Fn:
    def __init__(self, f): self.f = f
    def at(self, t): return self.f(t)


def _val(v, t):
    if v is None: return None
    if callable(v): return v(t)
    if hasattr(v, 'at'): return v.at(t)
    return v


class Presenter:
    def __init__(self, beats, words=None, base_size=9):
        self.beats = sorted(beats, key=lambda b: b[0])
        self.words = words or []
        self.base_size = base_size
        self._squash = [t0 for t0, b in self.beats if b.get('squash')]

    # ------------------------------------------------------------ state
    def get(self, key, t, default=None):
        v = self.beats[0][1].get(key, default)     # before the first beat, hold its state
        for t0, b in self.beats:
            if t0 > t: break
            if key in b: v = b[key]
        return v

    def pos(self, t):
        return _val(self.get('path', t), t)

    def vel(self, t, dt=1 / 120):
        a, b = self.pos(t - dt), self.pos(t + dt)
        return (b[0] - a[0]) / (2 * dt), (b[1] - a[1]) / (2 * dt)

    def size(self, t):
        return max(2, int(round(_val(self.get('size', t, self.base_size), t))))

    def speaking(self, t):
        for w in self.words:
            if w['s'] <= t < w['e'] - 0.03: return True
        return False

    def facing(self, t):
        f = self.get('face', t)
        if f in (1, -1): return f
        x, y = self.pos(t)
        tgt = _val(self.get('point', t), t) or _val(self.get('look', t), t)
        if tgt is not None and abs(tgt[0] - x) > 20: return 1 if tgt[0] > x else -1
        vx, _ = self.vel(t)
        if abs(vx) > 250: return 1 if vx > 0 else -1
        return self.get('face_rest', t, 1)

    def airborne(self, t):
        g = self.get('ground', t)
        return g is None or self.pos(t)[1] < g - 6

    def hand(self, t, angle=None):
        """World position of the right hand (for interactions: pressing, holding, pushing)."""
        x, y = self.pos(t); s = self.size(t); f = self.facing(t)
        a = self._arm_angle(t) if angle is None else angle
        dx, dy = hand_offset(a if a is not None else 0, s, f)
        return x + dx, y + dy

    def _arm_angle(self, t):
        arms = self.get('arms', t, 'down')
        if isinstance(arms, tuple): return arms[1]
        if arms == 'point':
            tgt = _val(self.get('point', t), t)
            if tgt is None: return 0
            x, y = self.pos(t); s = self.size(t); f = self.facing(t)
            sx = x + (SHOULDER_R[0] - FEET[0]) * s * f; sy = y + (SHOULDER_R[1] - FEET[1]) * s
            a = math.degrees(math.atan2(tgt[1] - sy, (tgt[0] - sx) * f))
            return round(clamp(a, -115, 95) / 10) * 10
        return None

    def _pose(self, t):
        arms = self.get('arms', t, 'down')
        if arms == 'point': arms = ('aim', self._arm_angle(t))
        elif arms in ANIM:
            a, b, hz = ANIM[arms]; arms = a if int(t * hz) % 2 else b
        legs = self.get('legs', t, 'auto')
        if legs == 'auto':
            vx, vy = self.vel(t)
            if self.airborne(t): legs = 'tuck' if abs(vy) > 900 else 'fly'
            elif abs(vx) > 160: legs = 'run1' if int(t * 9) % 2 else 'run2'
            else: legs = 'stand'
        elif legs == 'run':
            legs = 'run1' if int(t * 9) % 2 else 'run2'
        expr = self.get('expr', t, 'smile')
        if expr in ('smile', 'smirk', 'think') and self.speaking(t) and int(t * 11) % 2 == 0: expr = 'talk'
        elif expr in ('smile', 'smirk', 'think', 'grin') and (t % 3.3) < 0.1: expr = 'blink'
        # gaze toward the look/point target, in sprite space
        x, y = self.pos(t); s = self.size(t); f = self.facing(t)
        tgt = _val(self.get('look', t), t) or _val(self.get('point', t), t)
        gx, gy = 1, 0
        if tgt is not None:
            hx, hy = x, y - 45 * s
            dx, dy = (tgt[0] - hx) * f, tgt[1] - hy
            gx = 1 if dx > 30 else (-1 if dx < -30 else 0)
            gy = -1 if dy < -1.2 * abs(dx) - 40 else (1 if dy > 1.2 * abs(dx) + 40 else 0)
        elif self.get('look_camera', t):
            gx = 0
        return expr, arms, legs, (gx, gy)

    # ------------------------------------------------------------ drawing
    def sprite(self, t, s=None):
        expr, arms, legs, gaze = self._pose(t)
        return _scaled(expr, arms, legs, gaze, s or self.size(t))

    def draw(self, cv, t, layer='front', cam=None, alpha=255):
        if not self.get('visible', t, True): return
        z = _val(self.get('z', t, 'front'), t)
        if layer is not None and z != layer: return
        x, y = self.pos(t); s = self.size(t); f = self.facing(t)
        vx, vy = self.vel(t)
        air = self.airborne(t)
        bob = self.get('hover', t, 10) * math.sin(t * 5.2) if air else 0
        tilt = 0.0
        if air:
            tilt = clamp(-vx * f * self.get('tilt', t, 9) / 1000, -16, 16) * f
            tilt = round(tilt / 2) * 2
        k = sum(jelly(t, a) for a in self._squash) * 0.12
        sxk, syk = 1 + k, 1 - k
        if air and abs(vy) > 300:        # stretch along fast vertical motion
            st = clamp(abs(vy) / 9000, 0, 0.12); sxk *= 1 - st; syk *= 1 + st
        if cam is not None:              # screen-space overlay: map through the camera
            (x, y), zc = cam.to_screen(t, x, y), cam.at(t)[2]
            s = max(2, int(round(s * zc)))
        g = self.get('ground', t)
        if g is not None and cam is None and layer != 'back_only':
            h = max(0.0, g - y)
            contact_shadow(cv, x, g, 230 * s / 9 * (1 - min(1, h / 500)), 1, s=max(3, s), alpha=int(120 * (1 - min(1, h / 500))))
        img = self.sprite(t, s)
        if f < 0: img = img.transpose(Image.FLIP_LEFT_RIGHT)
        speed = math.hypot(vx, vy)
        if self.get('trail', t, True) and speed > 1300 and cam is None:
            self._trail(cv, t, img, s, speed, vx, vy)
        if sxk != 1 or syk != 1:
            img = img.resize((max(1, int(img.width * sxk)), max(1, int(img.height * syk))), Image.NEAREST)
        h0 = img.height                  # rotate about the body centre, keeping the feet anchored before tilt
        if tilt:
            img = img.rotate(tilt, resample=Image.NEAREST, expand=True)
        if alpha < 255:
            img = img.copy(); a = img.split()[3].point(lambda v: v * alpha // 255); img.putalpha(a)
        cv.paste(img, (int(round(x - img.width / 2)), int(round(y + bob - h0 / 2 - img.height / 2))), img)

    def _trail(self, cv, t, img, s, speed, vx, vy):
        for i, a in ((3, 50), (2, 80), (1, 115)):
            x, y = self.pos(t - i * 0.022)
            ghost = img.copy(); ghost.putalpha(ghost.split()[3].point(lambda v, a=a: v * a // 255))
            cv.paste(ghost, (int(x - ghost.width / 2), int(y - ghost.height)), ghost)
        d = ImageDraw.Draw(cv); x, y = self.pos(t)
        ux, uy = -vx / speed, -vy / speed
        for j, off in enumerate((-18, -6, 6, 18)):
            cx, cy = x + -uy * off * s / 3, y - 30 * s + ux * off * s / 3
            L = (150 + 40 * j) * min(1.0, speed / 3000)
            d.line((cx + ux * 30 * s / 9, cy + uy * 30 * s / 9, cx + ux * (30 * s / 9 + L), cy + uy * (30 * s / 9 + L)),
                   fill=(235, 238, 246, 150), width=max(3, s // 2))


_CACHE = {}
def _scaled(expr, arms, legs, gaze, s):
    key = (expr, arms, legs, gaze, s)
    img = _CACHE.get(key)
    if img is None:
        if len(_CACHE) > 600: _CACHE.clear()
        img = _CACHE[key] = up(guy(expr, arms, legs, gaze), s)
    return img


def reach(target, angle, s, facing=1):
    """Path fn placing the presenter so his right hand (aimed at `angle`) lands on target (x, y) or fn(t)."""
    dx, dy = hand_offset(angle, s, facing)
    def f(t):
        tx, ty = target(t) if callable(target) else target
        return tx - dx, ty - dy
    return Fn(f)
