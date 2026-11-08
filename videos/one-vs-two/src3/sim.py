"""Active-ragdoll fight simulation (pymunk). All motion is generated here: physics + joint motors
driving toward hand-designed poses, procedural footwork, physical hits and knockdowns."""
import math, random, sys, os
import numpy as np
import pymunk

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src'))
from engine import POSES, BASE

G = 1500.0
DT = 1/480
REC = 1/240
LEN = dict(torso=50, neck=9, head=14, ua=28, fa=27, th=40, sn=40)
MASS = dict(torso=12, head=3, ua=1.8, fa=1.4, th=4.0, sn=2.8)
RAD = dict(torso=8, head=14, ua=5, fa=5, th=6, sn=6)
JOINTS = ['hip', 'neck', 'head', 'rel', 'rhand', 'fel', 'fhand', 'rkn', 'rft', 'fkn', 'fft']
JI = {n: i for i, n in enumerate(JOINTS)}

def P(name, **kw):
    d = dict(BASE); d.update(POSES[name]); d.update(kw); return d

POSES.update({
    'hook':    dict(t=26, h=-6, fa1=78, fa2=150, ra1=30, ra2=150, rl1=-34, rl2=-46, fl1=46, fl2=12),
    'upper':   dict(t=8, h=-14, ra1=40, ra2=175, fa1=55, fa2=145, rl1=-26, rl2=-40, fl1=38, fl2=6),
    'chamber2':dict(t=-12, ra1=40, ra2=150, fa1=50, fa2=140, rl1=100, rl2=10, fl1=-4, fl2=-8),
    'highkick':dict(t=-38, h=14, fa1=-40, fa2=10, ra1=70, ra2=130, rl1=150, rl2=152, fl1=-6, fl2=-10),
    'sidekick':dict(t=-34, h=10, fa1=-30, fa2=20, ra1=60, ra2=120, rl1=100, rl2=100, fl1=-8, fl2=-12),
    'duck':    dict(t=52, h=-24, ra1=40, ra2=150, fa1=55, fa2=145, fl1=92, fl2=-8, rl1=30, rl2=-84),
    'backstep':dict(t=-6, h=-6, ra1=35, ra2=150, fa1=55, fa2=140, rl1=-30, rl2=-44, fl1=20, fl2=0),
    'flinch':  dict(t=-24, h=-30, fa1=45, fa2=80, ra1=25, ra2=90, fl1=24, fl2=8, rl1=-24, rl2=-34),
    'slash1':  dict(t=-4, h=-6, fa1=160, fa2=175, ra1=150, ra2=170, fl1=34, fl2=6, rl1=-24, rl2=-36),
    'slash2':  dict(t=36, h=-10, fa1=70, fa2=60, ra1=60, ra2=55, fl1=60, fl2=12, rl1=-44, rl2=-58),
    'slashb':  dict(t=8, h=-6, fa1=-70, fa2=-95, ra1=-40, ra2=-20, fl1=40, fl2=8, rl1=-30, rl2=-44),
    'slashf':  dict(t=30, h=-8, fa1=95, fa2=98, ra1=-40, ra2=-20, fl1=58, fl2=10, rl1=-46, rl2=-58),
    'getup1':  dict(t=40, h=10, fa1=40, fa2=0, ra1=-10, ra2=-20, fl1=95, fl2=-5, rl1=10, rl2=-95),
})

# action = list of phases (duration, pose, active_limb or None, power)
ACTIONS = {
    'jab':     [(0.07, 'guard2', None, 0), (0.10, 'jab', 'fhand', 1.0), (0.16, 'guard', None, 0)],
    'cross':   [(0.09, 'guard2', None, 0), (0.11, 'cross', 'rhand', 1.4), (0.18, 'guard', None, 0)],
    'hook':    [(0.10, 'guard2', None, 0), (0.12, 'hook', 'fhand', 1.5), (0.18, 'guard', None, 0)],
    'upper':   [(0.10, 'crouch', None, 0), (0.12, 'upper', 'rhand', 2.0), (0.2, 'guard', None, 0)],
    'kick':    [(0.12, 'chamber', None, 0), (0.12, 'kick', 'fft', 2.2), (0.22, 'guard', None, 0)],
    'highkick':[(0.13, 'chamber2', None, 0), (0.14, 'highkick', 'rft', 2.8), (0.25, 'guard', None, 0)],
    'sidekick':[(0.13, 'chamber2', None, 0), (0.13, 'sidekick', 'rft', 3.2), (0.25, 'guard', None, 0)],
    'duck':    [(0.10, 'duck', None, 0), (0.18, 'duck', None, 0), (0.12, 'guard', None, 0)],
    'block':   [(0.06, 'block', None, 0), (0.22, 'block', None, 0), (0.10, 'guard', None, 0)],
    'slip':    [(0.08, 'backstep', None, 0), (0.14, 'backstep', None, 0), (0.10, 'guard', None, 0)],
    'slash':   [(0.12, 'slash1', None, 0), (0.12, 'slash2', 'blade', 3.0), (0.22, 'swguard', None, 0)],
    'cut':     [(0.10, 'slashb', None, 0), (0.12, 'slashf', 'blade', 3.4), (0.25, 'swguard', None, 0)],
}

GAIN = {'torso': (50000, 18, 0.9), 'head': (600, 20, 0.9), 'ua': (1600, 28, 0.85), 'fa': (360, 30, 0.8),
        'th': (6600, 22, 0.9), 'sn': (1500, 26, 0.85)}
PARENT = {'head': 'torso', 'rua': 'torso', 'fua': 'torso', 'rfa': 'rua', 'ffa': 'fua',
          'rth': 'torso', 'fth': 'torso', 'rsn': 'rth', 'fsn': 'fth'}

def wrap(a): return (a + math.pi) % (2*math.pi) - math.pi

class Fighter:
    def __init__(s, space, name, x, face, group):
        s.name, s.face, s.space = name, face, space
        s.filter = pymunk.ShapeFilter(group=group, categories=0b10, mask=0b01)
        s.parts = {}
        y_hip = LEN['th'] + LEN['sn'] + 4
        def part(key, kind, a, b):
            L = LEN[kind]; m = MASS[kind]
            body = pymunk.Body(m, pymunk.moment_for_segment(m, (0, 0), (0, -L), RAD[kind]))
            body.position = a if a is not None else (x, 100)
            sh = pymunk.Segment(body, (0, 0), (0, -L), RAD[kind]); sh.friction = 0.9; sh.filter = s.filter; sh.elasticity = 0.05
            space.add(body, sh); s.parts[key] = (body, kind, L)
            return body
        hip = (x, y_hip)
        tor = pymunk.Body(MASS['torso'], pymunk.moment_for_segment(MASS['torso'], (0, 0), (0, LEN['torso']), RAD['torso']))
        tor.position = hip; sh = pymunk.Segment(tor, (0, 0), (0, LEN['torso']), RAD['torso']); sh.friction = 0.6; sh.filter = s.filter
        space.add(tor, sh); s.parts['torso'] = (tor, 'torso', LEN['torso'])
        hd = pymunk.Body(MASS['head'], pymunk.moment_for_circle(MASS['head'], 0, RAD['head']))
        hd.position = (x, y_hip + LEN['torso'] + LEN['neck'] + RAD['head']); c = pymunk.Circle(hd, RAD['head']); c.filter = s.filter; c.friction = 0.6
        space.add(hd, c); s.parts['head'] = (hd, 'head', 0)
        nk = (x, y_hip + LEN['torso']); sh_pt = (x, y_hip + LEN['torso'] - 4)
        for side in 'rf':
            ua = part(side + 'ua', 'ua', sh_pt, None); ua.position = sh_pt
            fa = part(side + 'fa', 'fa', None, None); fa.position = (x, sh_pt[1] - LEN['ua'])
            th = part(side + 'th', 'th', None, None); th.position = hip
            sn = part(side + 'sn', 'sn', None, None); sn.position = (x, y_hip - LEN['th'])
        J = []
        def pivot(a, b, wp):
            j = pymunk.PivotJoint(a, b, wp); j.collide_bodies = False; J.append(j)
        pivot(tor, hd, (x, nk[1] + LEN['neck']))
        s.limits = {}
        for side in 'rf':
            ua, fa, th, sn = (s.parts[side + k][0] for k in ('ua', 'fa', 'th', 'sn'))
            pivot(tor, ua, sh_pt); pivot(ua, fa, (x, sh_pt[1] - LEN['ua']))
            pivot(tor, th, hip); pivot(th, sn, (x, y_hip - LEN['th']))
            el = pymunk.RotaryLimitJoint(ua, fa, 0, 0); kn = pymunk.RotaryLimitJoint(th, sn, 0, 0)
            J += [el, kn]; s.limits[side] = (el, kn)
        nl = pymunk.RotaryLimitJoint(tor, hd, -0.9, 0.9); J.append(nl)
        space.add(*J)
        s.set_face(face)
        # controller state
        s.mode = 'stand'; s.support = 1.0; s.tone = 1.0
        s.x_target = x; s.pose = P('guard'); s.pose_prev = dict(s.pose); s.pose_t = 0.0; s.pose_blend = 0.06
        s.action = None; s.act_t = 0.0; s.act_hit = False; s.phase = 0.0
        s.force_ko = False; s.down_until = 0; s.stun = 0.0; s.flinch = 0.0; s.lean_extra = 0.0
        s.sword = False; s.flip = None; s.air_pose = None
        s.queue = []

    def set_face(s, face):
        s.face = face
        for side in 'rf':
            el, kn = s.limits[side]
            if face > 0: el.min, el.max = 0.0, math.radians(165); kn.min, kn.max = -math.radians(155), 0.0
            else: el.min, el.max = -math.radians(165), 0.0; kn.min, kn.max = 0.0, math.radians(155)

    # ---- geometry
    def joint(s, key):
        b, kind, L = s.parts[key]
        if kind == 'torso': return b.local_to_world((0, LEN['torso']))
        return b.local_to_world((0, -L))
    def hip(s): return s.parts['torso'][0].position
    def snapshot(s):
        tor = s.parts['torso'][0]
        out = [tor.position, tor.local_to_world((0, LEN['torso'])), s.parts['head'][0].position]
        for side in 'rf':
            out += [s.joint(side + 'ua'), s.joint(side + 'fa')]
        for side in 'rf':
            out += [s.joint(side + 'th'), s.joint(side + 'sn')]
        return [(p[0], -p[1]) for p in out]   # renderer: y down, ground 0
    def segments(s):
        segs = []
        for key, (b, kind, L) in s.parts.items():
            if kind == 'head': segs.append((b.position, b.position, RAD['head']))
            elif kind == 'torso': segs.append((b.position, b.local_to_world((0, LEN['torso'])), RAD['torso']))
            else: segs.append((b.local_to_world((0, 0)), b.local_to_world((0, -L)), RAD[kind]))
        return segs
    def strike_point(s, limb):
        if limb == 'blade':
            fa = s.parts['rfa'][0]; h = fa.local_to_world((0, -LEN['fa'])); d = fa.rotation_vector.rotated(math.pi*0.5 if False else 0)
            e = fa.local_to_world((0, -LEN['fa'] - 1)); v = (e - h).normalized()
            return h, h + v.rotated(-0.35*s.face)*88
        key = {'fhand': 'ffa', 'rhand': 'rfa', 'fft': 'fsn', 'rft': 'rsn'}[limb]
        p = s.joint(key); return p, p
    def grounded(s):
        return min(s.joint('rsn')[1], s.joint('fsn')[1]) < 8 + RAD['sn']

    # ---- control
    def set_pose(s, pose, t, blend=0.06):
        s.pose_prev = s.cur_pose(t); s.pose = pose; s.pose_t = t; s.pose_blend = blend
    def cur_pose(s, t):
        u = min(1.0, (t - s.pose_t)/max(1e-4, s.pose_blend)); u = u*u*(3 - 2*u)
        out = {}
        for k, v in s.pose.items():
            a = s.pose_prev.get(k, v)
            out[k] = v if (v is None or a is None) else a + (v - a)*u
        return out
    def start_action(s, name, t):
        if isinstance(name, (list, tuple)):
            s.combo = list(name[1:]); name = name[0]
        else:
            s.combo = []
        s.action = name; s.act_t = t; s.act_hit = False; s.act_phase = -1
    def update_action(s, t):
        if s.action is None: return None
        ph = ACTIONS[s.action]; tt = t - s.act_t; acc = 0.0
        last = len(ph) - 1
        for i, (d, pose, limb, power) in enumerate(ph):
            if i == last and getattr(s, 'combo', None) and pose in ('guard', 'swguard') and tt >= acc + d*0.15:
                nxt = s.combo.pop(0); s.action = nxt; s.act_t = t; s.act_hit = False; s.act_phase = -1
                return s.update_action(t)
            if tt < acc + d:
                if i != s.act_phase:
                    s.act_phase = i; kw = {'sw': 160} if s.sword else {}
                    p = P(pose, **kw)
                    if s.sword and pose in ('guard', 'guard2', 'crouch', 'chamber', 'chamber2'): p['fa1'], p['fa2'] = 40, 118
                    s.set_pose(p, t, blend=min(0.07, d*0.6))
                return (limb, power) if limb else None
            acc += d
        s.action = None; return None

    def target_angles(s, t, vx):
        p = s.cur_pose(t); f = s.face
        sd = (sum(map(ord, s.name)) % 13)*0.7
        lean = p['t'] + s.lean_extra + (5*math.sin(t*2.6 + sd) + 3*math.sin(t*4.1 + 2*sd) if s.mode == 'stand' else 0)
        ang = {'torso': -math.radians(lean)*f, 'head': -math.radians(lean + p['h'])*f}
        for side in 'rf':
            ang[side + 'ua'] = math.radians(p[side + 'a1'])*f; ang[side + 'fa'] = math.radians(p[side + 'a2'])*f
            ang[side + 'th'] = math.radians(p[side + 'l1'])*f; ang[side + 'sn'] = math.radians(p[side + 'l2'])*f
        if s.mode == 'stand' and s.action is None:
            A = min(1.0, abs(vx)/180)
            if A > 0.03:
                q = s.phase; sn, cs = math.sin(q), math.cos(q)
                for side, sg in (('f', 1), ('r', -1)):
                    ang[side + 'th'] += math.radians(24*A*sn*sg)*f
                    ang[side + 'sn'] += math.radians(24*A*sn*sg - 34*A*max(0, cs*sg))*f
            ang['fua'] += 0.10*math.sin(t*3.3 + sd)*f; ang['ffa'] += 0.14*math.sin(t*3.3 + sd + 0.6)*f
            ang['rua'] += 0.08*math.sin(t*2.9 + sd + 1.3)*f; ang['rfa'] += 0.12*math.sin(t*2.9 + sd + 1.9)*f
            bob = math.sin(t*7.5 + sd)*0.07
            ang['fth'] += bob*f; ang['fsn'] -= bob*0.8*f; ang['rth'] += bob*0.6*f; ang['rsn'] -= bob*f
        return ang

    def control(s, t, opp):
        tor = s.parts['torso'][0]
        vx = tor.velocity[0]
        s.phase += abs(vx)*DT/36.0
        ang = s.target_angles(t, vx)
        k = 1.0 if s.mode in ('stand', 'air') else (0.15 if s.mode == 'down' else s.support)
        rot = 0.0
        if s.flip is not None:
            t0, dur, dirn = s.flip; u = min(1, (t - t0)/dur); rot = -dirn*s.face*2*math.pi*(u*u*(3 - 2*u))
        for key, (b, kind, L) in s.parts.items():
            if key == 'torso' and s.mode == 'down': continue
            I, w, z = GAIN[kind]
            kk = k if key != 'torso' else (k if s.mode != 'getup' else max(0.25, s.support))
            kp = I*w*w*kk; kd = 2*z*I*w*max(0.35, kk)
            err = wrap(ang[key] + rot - b.angle)
            tau = kp*err - kd*b.angular_velocity
            b.torque += tau
            if key in PARENT: s.parts[PARENT[key]][0].torque -= tau
        # balance / footwork (the 'muscles' of the legs, as in game ragdolls)
        if s.mode == 'stand' or (s.mode == 'getup'):
            sup = 1.0 if s.mode == 'stand' else s.support
            sup *= (1 - 0.55*min(1, s.stun))
            hip_h = tor.position[1]
            pose = s.cur_pose(t)
            crouch = 0.0
            if pose['fl1'] > 70 or pose['rl1'] > 70 or pose['t'] > 40: crouch = 26
            target_h = LEN['th'] + LEN['sn'] - 6 - crouch - 4*math.sin(t*7.5)
            if s.grounded() or s.mode == 'getup':
                mt = sum(MASS[v[1]] for v in s.parts.values())
                fy = mt*G*sup + 9000*(target_h - hip_h)*sup - 260*tor.velocity[1]*sup
                tor.force += (0, fy)
                fx = (2400*(s.x_target - tor.position[0]) - 170*vx)*sup
                fx = max(-130000, min(130000, fx))
                tor.force += (fx, 0)
                for key in ('rsn', 'fsn'):
                    b = s.parts[key][0]; b.force += (-b.velocity[0]*6*sup, 0)
        s.stun = max(0.0, s.stun - DT*2.5)
        s.lean_extra *= (1 - DT*6)

    def jump(s, t, vx, vy, flip=None, pose='tuck'):
        s.mode = 'air'; s.action = None; s.impulse_all((vx, vy)); s.set_pose(P(pose), t, 0.08)
        if flip: s.flip = (t, flip[0], flip[1])
    def impulse_all(s, v):
        for b, kind, L in s.parts.values(): b.velocity = (b.velocity[0] + v[0], b.velocity[1] + v[1])

class Fight:
    def __init__(s):
        s.space = pymunk.Space(); s.space.gravity = (0, -G); s.space.iterations = 25
        g = pymunk.Segment(s.space.static_body, (-6000, 0), (6000, 0), 2); g.friction = 1.0
        g.filter = pymunk.ShapeFilter(categories=0b01, mask=0b10); s.space.add(g)
        s.f = {}
        s.events = []        # (t, kind, data)
        s.cmds = []          # (t, fighter, fn)
        s.rng = random.Random(7); s._pending = []
        s.spar = []          # (t0, t1, attacker, defender, rate)
        s.rec = {}
    def add(s, name, x, face):
        s.f[name] = Fighter(s.space, name, x, face, len(s.f) + 1); return s.f[name]
    def at(s, t, name, fn): s.cmds.append((t, name, fn))
    def nearest(s, me):
        others = [o for o in s.f.values() if o is not me]
        return min(others, key=lambda o: abs(o.hip()[0] - me.hip()[0]))

    def hit_check(s, t, F):
        res = F.update_action(t)
        if res is None or F.act_hit: return
        limb, power = res
        a, b = F.strike_point(limb)
        for V in s.f.values():
            if V is F or V.mode == 'down' or getattr(V, 'team', 0) == getattr(F, 'team', -1): continue
            for p, q, r in V.segments():
                d = seg_dist(a, b, p, q) if limb == 'blade' else point_seg(a, p, q)
                if d < r + (4 if limb == 'blade' else 7) + (getattr(F, 'assist', 0) if F.force_ko or getattr(F, 'scripted', False) else 0):
                    F.act_hit = True
                    s.on_hit(t, F, V, limb, power, (a if limb != 'blade' else closest_on(a, b, p, q)))
                    return
    def on_hit(s, t, F, V, limb, power, pt):
        heavy = power >= getattr(V, 'ko_threshold', 2.6) or getattr(F, 'force_ko', False)
        dirn = 1 if V.hip()[0] > F.hip()[0] else -1
        if V.action == 'block' and not heavy:
            s.events.append((t, 'block', dict(x=pt[0], y=-pt[1], power=power, attacker=F.name, victim=V.name)))
            V.impulse_all((dirn*(40 + 25*power), 0)); V.x_target += dirn*(8 + 6*power); V.lean_extra = 8*power
            return
        s.events.append((t, 'hit', dict(x=pt[0], y=-pt[1], power=power, attacker=F.name, victim=V.name, heavy=heavy, blade=limb == 'blade')))
        if heavy:
            V.mode = 'down'; V.down_until = t + getattr(V, 'down_time', 1.4); V.action = None
            V.impulse_all((dirn*(260 + 90*power), 300 + 60*power))
            V.parts['torso'][0].angular_velocity += -dirn*7
            s.events.append((t, 'ko', dict(victim=V.name)))
        else:
            V.stun = min(1.2, V.stun + 0.5*power); V.lean_extra = 26*power
            V.impulse_all((dirn*(70 + 40*power), 0)); V.x_target += dirn*(16 + 14*power)
            V.action = None; V.set_pose(P('flinch'), t, 0.05)
            s.later(t + 0.18, V.name, lambda F_, tt: F_.set_pose(P('guard' if not F_.sword else 'swguard'), tt, 0.15))

    COMBOS = [['jab', 'cross'], ['jab', 'jab', 'cross'], ['jab', 'cross', 'hook'], ['cross', 'hook', 'kick'],
              ['jab', 'kick'], ['hook', 'upper'], ['jab', 'cross', 'highkick'], ['kick', 'cross']]
    SWORD_COMBOS = [['slash', 'cut'], ['cut', 'slash'], ['slash'], ['cut']]
    def step_ai(s, t):
        for t0, t1, an, dn, rate in s.spar:
            if not (t0 <= t < t1): continue
            A, D = s.f[an], s.f[dn]
            if A.mode != 'stand' or A.action is not None or getattr(A, 'scripted', False): continue
            if t < getattr(A, 'cool', 0): continue
            dist = abs(D.hip()[0] - A.hip()[0])
            if dist < 125 and s.rng.random() < rate*DT*3:
                combo = s.rng.choice(s.SWORD_COMBOS if A.sword else s.COMBOS)
                A.start_action(combo, t); A.cool = t + 0.25
                d = 1 if D.hip()[0] > A.hip()[0] else -1
                A.x_target = D.hip()[0] - d*70
                if D.mode == 'stand' and D.action is None and not getattr(D, 'scripted', False):
                    r = s.rng.random()
                    react = 'block' if r < 0.45 else ('duck' if r < 0.62 else ('slip' if r < 0.78 else None))
                    if react:
                        s.later(t + 0.05, dn, lambda F_, tt, react=react: F_.start_action(react, tt))
                    # counter attack right after
                    cc = s.rng.choice(s.SWORD_COMBOS if D.sword else s.COMBOS)
                    s.later(t + 0.45 + 0.1*len(combo), dn,
                            lambda F_, tt, cc=cc: F_.start_action(cc, tt) if F_.mode == 'stand' and F_.action is None and not getattr(F_, 'scripted', False) else None)
    def footwork(s, t):
        """Continuous circling / pressure: idle fighters never stand still."""
        for F in s.f.values():
            ch = getattr(F, 'chase', None)
            if ch and F.mode == 'stand':
                V = s.f[ch[0]]; d = 1 if V.hip()[0] > F.hip()[0] else -1
                if F.action is None: F.set_face(d)
                F.x_target = V.hip()[0] - d*ch[1]; continue
            if F.mode != 'stand' or F.action is not None or getattr(F, 'scripted', False) or getattr(F, 'free', False): continue
            tgt = getattr(F, 'track', None)
            if not tgt: continue
            name, dist, amp = tgt; V = s.f[name]; d = 1 if V.hip()[0] > F.hip()[0] else -1
            sd = (sum(map(ord, F.name)) % 13)*0.9
            F.x_target = V.hip()[0] - d*(dist + amp*math.sin(t*1.9 + sd) + 0.5*amp*math.sin(t*3.7 + 2*sd))

    def run(s, T):
        cmds = sorted(s.cmds, key=lambda c: c[0]); ci = 0
        n = int(T/DT); rec_every = int(REC/DT)
        frames = {k: [] for k in s.f}
        for i in range(n):
            t = i*DT
            while ci < len(cmds) and cmds[ci][0] <= t:
                _, name, fn = cmds[ci]; fn(s.f[name], t); ci += 1
                cmds = cmds  # list already sorted; late inserts handled below
            if s._pending:
                cmds += s._pending; s._pending = []; cmds[ci:] = sorted(cmds[ci:], key=lambda c: c[0])
            s.step_ai(t); s.footwork(t)
            for F in s.f.values():
                if F.mode == 'stand' and F.action is None and not getattr(F, 'lock_face', False):
                    o = s.nearest(F); nf = 1 if o.hip()[0] > F.hip()[0] else -1
                    if nf != F.face: F.set_face(nf)
                if F.mode == 'down' and t >= F.down_until:
                    F.mode = 'getup'; F.support = 0.0; F.set_pose(P('getup1'), t, 0.2)
                    s.events.append((t, 'getup', dict(victim=F.name)))
                if F.mode == 'getup':
                    F.support = min(1.0, F.support + DT/0.9)
                    if F.support >= 1.0:
                        F.mode = 'stand'; F.x_target = F.hip()[0]; F.set_pose(P('guard' if not F.sword else 'swguard'), t, 0.25)
                if F.mode == 'air' and F.grounded() and F.parts['torso'][0].velocity[1] < 0 and (F.flip is None or t > F.flip[0] + F.flip[1]*0.8):
                    F.mode = 'stand'; F.flip = None; F.x_target = F.hip()[0]
                    F.set_pose(P('land'), t, 0.05); s.later(t + 0.22, F.name, lambda F_, tt: F_.set_pose(P('guard' if not F_.sword else 'swguard'), tt, 0.2))
                    s.events.append((t, 'land', dict(victim=F.name)))
                s.hit_check(t, F)
                F.control(t, None)
            # knockdown landings for dust
            for F in s.f.values():
                if F.mode == 'down':
                    tor = F.parts['torso'][0]
                    if tor.position[1] < 22 and tor.velocity[1] < -250 and not getattr(F, '_landed', False):
                        F._landed = True; s.events.append((t, 'slam', dict(x=tor.position[0], victim=F.name)))
                else: F._landed = False
            s.space.step(DT)
            if i % rec_every == 0:
                for k, F in s.f.items():
                    frames[k].append((F.snapshot(), F.face, F.sword))
        s.rec = frames
        return frames
    _pending = []
    def later(s, t, name, fn): s._pending.append((t, name, fn))

def point_seg(p, a, b):
    ax, ay = a; bx, by = b; px, py = p
    dx, dy = bx - ax, by - ay; L = dx*dx + dy*dy
    u = 0 if L < 1e-9 else max(0, min(1, ((px - ax)*dx + (py - ay)*dy)/L))
    return math.hypot(px - ax - u*dx, py - ay - u*dy)
def seg_dist(a, b, p, q):
    return min(point_seg(a, p, q), point_seg(b, p, q), point_seg(p, a, b), point_seg(q, a, b))
def closest_on(a, b, p, q):
    best = None
    for i in range(9):
        u = i/8; x = (a[0] + (b[0] - a[0])*u, a[1] + (b[1] - a[1])*u); d = point_seg(x, p, q)
        if best is None or d < best[0]: best = (d, x)
    return best[1]
