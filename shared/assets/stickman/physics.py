"""Seated crash-dummy ragdoll (pymunk) in the car's frame: a frontal-crash pulse is a forward pseudo-force, the shoulder
belt is a slide joint from the D-ring to the chest. With a pretensioner the belt is reeled in at the start of the pulse;
without one the belt has slack, so the torso and head travel further forward before the belt catches them.

    frames = crash(pretensioner=True)     # list (1 per ms of sim time) of joint dicts in car units (see car.SEAT_DUMMY)
    pose = sample(frames, t_sim)          # interpolated joints + 'chest' + 'slack' (0 = belt tight)
Deterministic: same input, same output; cached per process.
"""
import math
from functools import lru_cache
import pymunk
from . import car as C

G = 233.0                 # 1 g in car units (car length 100 units ~ 4.2 m)
PULSE_T0, PULSE_LEN, PULSE_G = 0.004, 0.11, 24.0
SIM_LEN = 0.42


def _pulse(t):
    if t < PULSE_T0 or t > PULSE_T0 + PULSE_LEN: return 0.0
    return PULSE_G * G * math.sin(math.pi * (t - PULSE_T0) / PULSE_LEN)


def _seg(space, a, b, m, r):
    cx, cy = (a[0] + b[0]) / 2, (a[1] + b[1]) / 2
    body = pymunk.Body(m, pymunk.moment_for_segment(m, (a[0] - cx, a[1] - cy), (b[0] - cx, b[1] - cy), r))
    body.position = (cx, cy)
    sh = pymunk.Segment(body, (a[0] - cx, a[1] - cy), (b[0] - cx, b[1] - cy), r)
    sh.filter = pymunk.ShapeFilter(group=1)
    space.add(body, sh)
    return body


@lru_cache(4)
def crash(pretensioner=True):
    J = C.SEAT_DUMMY
    sp = pymunk.Space(); sp.gravity = (0, G); sp.damping = 0.5
    st = sp.static_body
    torso = _seg(sp, J['hip'], J['neck'], 40.0, 1.7)
    head = _seg(sp, J['neck'], J['head'], 5.0, 1.0)
    uarm = _seg(sp, J['sh'], J['eF'], 2.5, 0.8)
    farm = _seg(sp, J['eF'], J['hF'], 2.0, 0.8)

    def piv(a, b, w):
        sp.add(pymunk.PivotJoint(a, b, w))

    lap_slack = 0.25 if pretensioner else 1.1
    hip_anchor = pymunk.SlideJoint(st, torso, J['hip'], torso.world_to_local(J['hip']), 0, lap_slack)
    sp.add(hip_anchor)
    back = (J['hip'][0] - 3, J['hip'][1])               # second lap-belt point: stops the pelvis spinning freely
    sp.add(pymunk.SlideJoint(st, torso, back, torso.world_to_local(back), 0, lap_slack + 0.6))
    piv(torso, head, J['neck']); piv(torso, uarm, J['sh']); piv(uarm, farm, J['eF'])
    # limits + muscle tone (rotary springs back to the seated posture)
    sp.add(pymunk.RotaryLimitJoint(st, torso, -0.12, 1.25))
    sp.add(pymunk.DampedRotarySpring(st, torso, 0, 9000.0, 1300.0))
    sp.add(pymunk.RotaryLimitJoint(torso, head, -0.55, 0.95))
    sp.add(pymunk.DampedRotarySpring(torso, head, 0, 500.0, 25.0))
    sp.add(pymunk.RotaryLimitJoint(uarm, farm, -2.2, 0.2))
    sp.add(pymunk.DampedRotarySpring(uarm, farm, 0, 60.0, 4.0))
    sp.add(pymunk.DampedSpring(farm, st, farm.world_to_local(J['hF']), J['hF'], 0, 900.0, 30.0))     # hands on the wheel
    sp.add(pymunk.DampedSpring(st, torso, (J['neck'][0] - 2.5, J['neck'][1]), torso.world_to_local(J['neck']), 2.5, 3000.0, 200.0))  # seatback
    chest_l = torso.world_to_local(_chest(J))
    rest = math.dist(C.D_RING, _chest(J))
    slack0 = 1.6
    belt = pymunk.SlideJoint(st, torso, C.D_RING, chest_l, 0, rest + slack0)
    sp.add(belt)

    out, dt, t = [], 1 / 4000, 0.0
    bodies = (torso, head, uarm, farm)
    for step in range(int(SIM_LEN * 4000) + 1):
        if pretensioner:      # reel in the slack (and a little more) in the first ~8 ms
            k = min(1.0, max(0.0, (t - 0.002) / 0.008))
            belt.max = rest + slack0 * (1 - k) - 0.12 * k
        else:                 # slack stays; the webbing spools out a little under load
            belt.max = rest + slack0 + 1.5 * min(1.0, max(0.0, (t - 0.02) / 0.06))
        a = _pulse(t)
        for b in bodies: b.apply_force_at_world_point((b.mass * a, 0), b.position)
        if step % 4 == 0:
            out.append(_joints(torso, head, uarm, farm, J, chest_l, belt, rest))
        sp.step(dt); t += dt
    return out


def _chest(J):
    return (J['neck'][0] * 0.62 + J['hip'][0] * 0.38 + 1.5, J['neck'][1] * 0.62 + J['hip'][1] * 0.38)


def _joints(torso, head, uarm, farm, J, chest_l, belt, rest):
    j = dict(J)
    tl = _local0
    j['hip'] = tuple(torso.local_to_world(tl['t_hip'])); j['neck'] = tuple(torso.local_to_world(tl['t_neck']))
    j['sh'] = tuple(torso.local_to_world(tl['t_sh']))
    j['head'] = tuple(head.local_to_world(tl['h_head']))
    j['eF'] = tuple(uarm.local_to_world(tl['u_e'])); j['hF'] = tuple(farm.local_to_world(tl['f_h']))
    j['eB'] = (j['eF'][0] + 0.6, j['eF'][1] - 0.8); j['hB'] = (j['hF'][0] + 0.8, j['hF'][1] - 0.8)
    ch = tuple(torso.local_to_world(chest_l))
    j['chest'] = ch
    j['slack'] = max(0.0, belt.max - math.dist(C.D_RING, ch))
    return j


def _locals():
    J = C.SEAT_DUMMY
    def mid(a, b): return ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2)
    m_t, m_h, m_u, m_f = mid(J['hip'], J['neck']), mid(J['neck'], J['head']), mid(J['sh'], J['eF']), mid(J['eF'], J['hF'])
    sub = lambda p, m: (p[0] - m[0], p[1] - m[1])
    return dict(t_hip=sub(J['hip'], m_t), t_neck=sub(J['neck'], m_t), t_sh=sub(J['sh'], m_t), h_head=sub(J['head'], m_h),
                u_e=sub(J['eF'], m_u), f_h=sub(J['hF'], m_f))


_local0 = _locals()


def sample(frames, ts):
    """Joints at sim time ts (s), linearly interpolated between the 1 ms samples."""
    x = max(0.0, min(ts * 1000, len(frames) - 1.001))
    i = int(x); k = x - i; a, b = frames[i], frames[i + 1]
    out = {}
    for key, v in a.items():
        if isinstance(v, tuple): out[key] = (v[0] + (b[key][0] - v[0]) * k, v[1] + (b[key][1] - v[1]) * k)
        else: out[key] = v + (b[key] - v) * k
    return out
