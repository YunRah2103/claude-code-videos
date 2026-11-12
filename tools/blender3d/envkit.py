"""envkit: reusable low-poly 3D environment props for Blender (bpy) race / road scenes.

Everything is procedural (no downloaded assets, no logos, no text): trees, people (standing, seated crowd, wavers),
simple parked cars, grandstands with crowds, tyre walls, catch fences with plain banners, a start gantry,
marshal posts, light towers and cones. Style: flat muted colours, works with Cycles + Freestyle ink lines.

The scenery is built as two roadside strips (left = +y, right = -y) that repeat every `period` metres, so a strip
can scroll forever with `animate()` (location = -(distance mod period)) without a visible jump. Scroll each side by
the distance of the car next to it and the scenery stops when that car stops.

Quick use (inside a bpy script):
    import sys; sys.path.insert(0, 'tools/blender3d'); import envkit as E
    env = E.build_track_env(edge=3.05, seed=3, lines=ink_collection, nolines=plain_collection)
    E.animate(env, left_distance_m, right_distance_m, frame)    # once per keyframe
See docs/BLENDER_3D_KIT.md.
"""
import math, random
import bpy, bmesh
from mathutils import Vector, Matrix

PALETTE = dict(
    grass=(0.55, 0.68, 0.45), leaf=[(0.30, 0.52, 0.30), (0.38, 0.60, 0.32), (0.26, 0.45, 0.30), (0.45, 0.62, 0.36)],
    bark=(0.42, 0.32, 0.24), skin=[(0.93, 0.78, 0.66), (0.80, 0.60, 0.46), (0.55, 0.38, 0.27), (0.98, 0.86, 0.74)],
    shirt=[(0.85, 0.20, 0.18), (0.20, 0.40, 0.85), (0.95, 0.80, 0.25), (0.95, 0.95, 0.95), (0.25, 0.25, 0.28),
           (0.30, 0.65, 0.45), (0.95, 0.55, 0.20), (0.60, 0.35, 0.75)],
    car=[(0.95, 0.95, 0.93), (0.85, 0.25, 0.20), (0.20, 0.45, 0.85), (0.98, 0.78, 0.20), (0.30, 0.65, 0.45),
         (0.95, 0.55, 0.20), (0.60, 0.40, 0.80), (0.75, 0.78, 0.82)],
    concrete=(0.80, 0.80, 0.78), steel=(0.55, 0.57, 0.60), dark=(0.12, 0.12, 0.13), white=(0.95, 0.95, 0.94),
    banner=[(0.85, 0.15, 0.12), (0.15, 0.35, 0.85), (0.95, 0.95, 0.94)], cone=(0.98, 0.45, 0.10))
_MATS = {}


def mat(col, rough=0.75, emit=0.0):
    key = (tuple(round(c, 3) for c in col), rough, emit)
    if key not in _MATS:
        m = bpy.data.materials.new('env'); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = tuple(col) + (1,); b.inputs['Roughness'].default_value = rough
        if emit: b.inputs['Emission Color'].default_value = tuple(col) + (1,); b.inputs['Emission Strength'].default_value = emit
        _MATS[key] = m
    return _MATS[key]


def see_through(col, alpha):
    m = mat(col, 0.6); m = m.copy(); m.node_tree.nodes['Principled BSDF'].inputs['Alpha'].default_value = alpha
    m.blend_method = 'BLEND'; return m


# ---------------------------------------------------------------- primitive helpers (each returns a new object)
def _obj(op, m, **kw):
    op(**kw); o = bpy.context.object; o.data.materials.append(m)
    for p in o.data.polygons: p.use_smooth = False
    return o


def box(size, loc, m, bevel=0.0, rot=(0, 0, 0)):
    o = _obj(bpy.ops.mesh.primitive_cube_add, m, size=1, location=loc, rotation=rot); o.scale = size
    if bevel:
        b = o.modifiers.new('bv', 'BEVEL'); b.width = bevel; b.segments = 2
    return o


def cyl(r, depth, loc, m, verts=12, rot=(0, 0, 0)):
    return _obj(bpy.ops.mesh.primitive_cylinder_add, m, vertices=verts, radius=r, depth=depth, location=loc, rotation=rot)


def ball(r, loc, m, sub=1, scale=(1, 1, 1)):
    o = _obj(bpy.ops.mesh.primitive_ico_sphere_add, m, subdivisions=sub, radius=r, location=loc); o.scale = scale
    return o


def cone(r, depth, loc, m, verts=10):
    return _obj(bpy.ops.mesh.primitive_cone_add, m, vertices=verts, radius1=r, radius2=0, depth=depth, location=loc)


def join(objs, name):
    """Apply modifiers/scales and join into one mesh object (fewer objects = faster scenes)."""
    for o in objs:
        bpy.context.view_layer.objects.active = o
        for md in list(o.modifiers): bpy.ops.object.modifier_apply(modifier=md.name)
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active = objs[0]
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    bpy.ops.object.join(); o = bpy.context.object; o.name = name
    return o


# ---------------------------------------------------------------- props (built at the origin, facing +x)
def tree(rng, kind=None):
    kind = kind or rng.choice(['round', 'round', 'pine'])
    h = rng.uniform(4.5, 8.0); leaf = mat(rng.choice(PALETTE['leaf']))
    parts = [cyl(0.16, h * 0.45, (0, 0, h * 0.225), mat(PALETTE['bark']), 8)]
    if kind == 'pine':
        for k in range(3):
            parts.append(cone(h * (0.28 - 0.06 * k), h * 0.35, (0, 0, h * (0.42 + 0.17 * k)), leaf, 9))
    else:
        for k in range(3):
            a = rng.uniform(0, 6.28); r = h * rng.uniform(0.18, 0.26)
            parts.append(ball(r, (0.5 * math.cos(a) * (k > 0), 0.5 * math.sin(a) * (k > 0), h * (0.62 + 0.1 * k)), leaf, 1))
    return join(parts, 'tree')


def person(rng, seated=False, wave=False):
    """~1.75 m low-poly person facing -y (towards the track when placed on the left strip). Returns (obj, arm|None)."""
    skin = mat(rng.choice(PALETTE['skin'])); shirt = mat(rng.choice(PALETTE['shirt'])); legs = mat(rng.choice([PALETTE['dark'], (0.25, 0.30, 0.45), (0.55, 0.50, 0.42)]))
    z0 = 0.45 if seated else 0.0
    parts = [box((0.36, 0.22, 0.62), (0, 0, z0 + 1.12), shirt, 0.05), ball(0.13, (0, 0, z0 + 1.58), skin, 2)]
    if seated: parts.append(box((0.34, 0.45, 0.18), (0, -0.16, z0 + 0.78), legs, 0.04))
    else: parts += [box((0.13, 0.15, 0.82), (sx, 0, 0.41), legs, 0.03) for sx in (-0.09, 0.09)]
    parts.append(box((0.10, 0.10, 0.58), (-0.24, 0, z0 + 1.12), shirt, 0.03))
    arm = None
    if wave:                                                            # separate arm, pivot at the shoulder
        arm = join([box((0.10, 0.10, 0.58), (0, 0, 0.0), shirt, 0.03)], 'arm')
        arm.data.transform(Matrix.Translation((0, 0, 0.27)))           # mesh hangs from the origin = shoulder
    else:
        parts.append(box((0.10, 0.10, 0.58), (0.24, 0, z0 + 1.12), shirt, 0.03))
    body = join(parts, 'person')
    if arm: arm.parent = body; arm.location = (0.24, 0, z0 + 1.38)
    return body, arm


def wave_driver(arm, phase):
    """Arm swings with the frame number (simple driver expression, no Python auto-exec needed)."""
    fc = arm.driver_add('rotation_euler', 1); fc.driver.type = 'SCRIPTED'
    fc.driver.expression = f'2.6 + 0.45 * sin(frame * 0.45 + {phase:.2f})'


def simple_car(rng, col=None):
    """Plain hatchback/saloon, ~4.2 m, facing +x."""
    paint = mat(col or rng.choice(PALETTE['car']), 0.4); glass = mat((0.18, 0.22, 0.28), 0.1); tyre = mat(PALETTE['dark'], 0.9)
    L, Wd = rng.uniform(3.9, 4.5), 1.75
    parts = [box((L, Wd, 0.62), (0, 0, 0.55), paint, 0.12),
             box((L * 0.52, Wd * 0.86, 0.50), (-L * 0.06, 0, 1.08), glass, 0.10)]
    for sx in (-L * 0.32, L * 0.32):
        for sy in (-Wd / 2 + 0.05, Wd / 2 - 0.05):
            parts.append(cyl(0.32, 0.22, (sx, sy, 0.32), tyre, 14, rot=(math.pi / 2, 0, 0)))
    parts += [box((0.06, 0.32, 0.10), (L / 2, sy, 0.68), mat((1, 0.95, 0.8), 0.3), 0) for sy in (-0.55, 0.55)]
    return join(parts, 'car')


def grandstand(length, rows, rng, crowd=True):
    """Stepped concrete stand facing -y with roof and a seated crowd; returns (structure, crowd|None)."""
    conc = mat(PALETTE['concrete']); steel = mat(PALETTE['steel']); roofm = mat(PALETTE['white'], 0.5)
    parts = []
    for r in range(rows):
        parts.append(box((length, 0.9, 0.45 * (r + 1)), (0, 0.9 * r, 0.225 * (r + 1)), conc))
    d = 0.9 * rows
    for x in range(int(-length / 2), int(length / 2) + 1, 6):
        parts.append(cyl(0.12, 0.45 * rows + 3.2, (x, d - 0.2, (0.45 * rows + 3.2) / 2), steel, 8))
    parts.append(box((length + 1, d + 1.6, 0.18), (0, d / 2 - 0.4, 0.45 * rows + 3.2), roofm))
    st = join(parts, 'grandstand')
    people = None
    if crowd:
        seats = []
        for r in range(rows):
            for k in range(int(length / 0.75)):
                if rng.random() < 0.18: continue
                seats.append(Matrix.Translation((-length / 2 + 0.4 + k * 0.75 + rng.uniform(-0.1, 0.1), 0.9 * r + 0.1,
                                                 0.45 * (r + 1) - 0.45)) @ Matrix.Rotation(rng.uniform(-0.2, 0.2), 4, 'Z'))
        people = merge_instances('crowd', _variants(rng, seated=True), seats, rng)
    return st, people


_VARIANTS = {}


def _variants(rng, seated, n=12):
    """A few person meshes reused for whole crowds (built once, hidden)."""
    if seated not in _VARIANTS:
        vs = []
        for _ in range(n):
            b, _a = person(rng, seated=seated); b.hide_render = True; b.hide_viewport = True; vs.append(b)
        _VARIANTS[seated] = vs
    return _VARIANTS[seated]


def merge_instances(name, variants, mats4, rng):
    """Fast: merge transformed copies of variant meshes into one mesh with bmesh (no operators per instance)."""
    me = bpy.data.meshes.new(name); slots = {}
    bm = bmesh.new()
    for M4 in mats4:
        v = rng.choice(variants); tmp = v.data.copy(); tmp.transform(M4)
        n0 = len(bm.faces); bm.from_mesh(tmp); bm.faces.ensure_lookup_table()
        remap = []
        for m in v.data.materials:
            if m.name not in slots: slots[m.name] = len(slots); me.materials.append(m)
            remap.append(slots[m.name])
        for f in bm.faces[n0:]: f.material_index = remap[f.material_index] if f.material_index < len(remap) else 0
        bpy.data.meshes.remove(tmp)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    return ob


def tyre_wall(length):
    tyre = mat(PALETTE['dark'], 0.9); band = mat(PALETTE['white'], 0.6)
    parts = []
    for k in range(int(length / 0.62)):
        for z in range(3):
            parts.append(cyl(0.31, 0.22, (-length / 2 + k * 0.62, 0, 0.11 + 0.22 * z), tyre if z != 1 else band, 10))
    return join(parts, 'tyrewall')


def fence(length, rng, banners=True):
    steel = mat(PALETTE['steel']); mesh = see_through((0.70, 0.74, 0.80), 0.18)
    parts = [box((length, 0.03, 2.6), (0, 0, 1.6), mesh)]
    for x in range(int(-length / 2), int(length / 2) + 1, 4): parts.append(cyl(0.05, 3.0, (x, 0, 1.5), steel, 6))
    if banners:
        for k, x in enumerate(range(int(-length / 2) + 2, int(length / 2) - 2, 8)):
            parts.append(box((6.0, 0.04, 0.9), (x + 1, -0.05, 0.75), mat(PALETTE['banner'][k % 3], 0.5)))
    return join(parts, 'fence')


def gantry(width, height=5.6):
    """Start/finish gantry spanning the track (centred on y=0) with five plain light pods."""
    steel = mat(PALETTE['steel']); dark = mat(PALETTE['dark'])
    parts = [box((0.5, 0.5, height), (0, s * width / 2, height / 2), steel) for s in (-1, 1)]
    parts.append(box((0.8, width + 0.5, 0.9), (0, 0, height), steel))
    for k in range(5): parts.append(box((0.3, 0.55, 0.5), (-0.4, -1.2 + 0.6 * k, height - 0.2), dark))
    return join(parts, 'gantry')


def light_tower(h=14):
    steel = mat(PALETTE['steel']); lamp = mat((1, 0.97, 0.88), 0.3, 1.5)
    return join([cyl(0.18, h, (0, 0, h / 2), steel, 8), box((1.6, 0.4, 0.9), (0, 0, h), steel), box((1.4, 0.05, 0.7), (0, -0.22, h), lamp)], 'tower')


def marshal_post():
    return join([box((2.0, 1.6, 2.2), (0, 0, 1.1), mat(PALETTE['white'], 0.6), 0.04),
                 box((2.3, 1.9, 0.12), (0, 0, 2.3), mat(PALETTE['cone'], 0.5))], 'marshal')


def traffic_cone():
    return join([cone(0.18, 0.55, (0, 0, 0.3), mat(PALETTE['cone'], 0.5), 10), box((0.4, 0.4, 0.04), (0, 0, 0.02), mat(PALETTE['dark']))], 'cone')


# ---------------------------------------------------------------- scenery strips
def _place(o, x, y, z=0.0, rz=0.0, s=1.0, root=None, col=None):
    o.location = (x, y, z); o.rotation_euler = (0, 0, rz); o.scale = (s, s, s)
    if root: o.parent = root
    if col:
        for c in o.users_collection: c.objects.unlink(o)
        col.objects.link(o)
    return o


def build_side(side, rng, period, edge, lines, nolines, copies=(-1, 0, 1, 2)):
    """One roadside strip (side=+1 left / -1 right). Contents repeat every `period` m. Returns (root, wavers)."""
    root = bpy.data.objects.new(f'strip{side:+d}', None); bpy.context.scene.collection.objects.link(root)
    sg = side; rz = 0.0 if side > 0 else math.pi                         # props face the track
    tile = []                                                            # (obj, x, y, z, rz, scale, ink?)
    tile.append((tyre_wall(period), period / 2, sg * (edge + 5.6), 0, 0, 1, True))
    tile.append((fence(period, rng), period / 2, sg * (edge + 6.6), 0, rz, 1, False))
    for k in range(2):                                                   # two grandstands per tile
        st, crowd = grandstand(26, 6, rng)
        x = period * (0.22 + 0.5 * k)
        tile.append((st, x, sg * (edge + 12.0), 0, rz, 1, True))
        if crowd: tile.append((crowd, x, sg * (edge + 12.0), 0, rz, 1, False))
    for k in range(10):                                                  # standing spectators along the fence (some wave)
        b, arm = person(rng, wave=rng.random() < 0.45)
        tile.append((b, rng.uniform(0, period), sg * (edge + 7.4 + rng.uniform(0, 1.5)), 0, rz + rng.uniform(-0.4, 0.4), 1, False))
    for k in range(7):                                                   # paddock: simple parked cars
        c = simple_car(rng); x = period * (0.45 + 0.02 * k)
        tile.append((c, x, sg * (edge + 13.0 + 2.6 * (k % 2)), 0, math.pi / 2 + rng.uniform(-0.1, 0.1), 1, True))
    tile.append((light_tower(), period * 0.45, sg * (edge + 10.0), 0, rz, 1, True))
    tile.append((light_tower(), period * 0.95, sg * (edge + 10.0), 0, rz, 1, True))
    tile.append((marshal_post(), period * 0.08, sg * (edge + 4.0), 0, 0, 1, True))
    for k in range(4): tile.append((traffic_cone(), period * (0.06 + 0.01 * k), sg * (edge + 1.6), 0, 0, 1, False))
    for k in range(22):                                                  # tree line behind everything
        tile.append((tree(rng), rng.uniform(0, period), sg * (edge + rng.uniform(22, 40)), 0, rng.uniform(0, 6.28), rng.uniform(0.8, 1.3), False))
    wavers = []
    for c in copies:                                                     # periodic copies share mesh data
        for o, x, y, z, r, s, ink in tile:
            oo = o if c == copies[0] else o.copy()
            if oo is not o: bpy.context.scene.collection.objects.link(oo)
            _place(oo, x + c * period, y, z, r, s, root, lines if ink else nolines)
            for ch in o.children:                                       # waving arm
                a = ch if oo is o else ch.copy()
                if a is not ch: bpy.context.scene.collection.objects.link(a); a.parent = oo
                if nolines:
                    for cc in a.users_collection: cc.objects.unlink(a)
                    nolines.objects.link(a)
                wave_driver(a, rng.uniform(0, 6.28)); wavers.append(a)
    return root, wavers


def build_track_env(edge=3.05, period=150.0, seed=3, lines=None, nolines=None, gantry_width=None):
    """Both roadside strips + a start gantry every period over the track. Returns dict for animate()."""
    rng = random.Random(seed)
    left, wl = build_side(+1, rng, period, edge, lines, nolines)
    right, wr = build_side(-1, rng, period, edge, lines, nolines)
    g = gantry(gantry_width or 2 * edge + 1.0)                          # rides with the left strip
    _place(g, period * 0.3, 0, 0, 0, 1, left, lines)
    for c in (-1, 1, 2):
        gg = g.copy(); bpy.context.scene.collection.objects.link(gg); _place(gg, period * 0.3 + c * period, 0, 0, 0, 1, left, lines)
    return dict(left=left, right=right, period=period, wavers=wl + wr)


def animate(env, d_left, d_right, frame):
    """Scroll each strip by the distance travelled on its side (metres); seamless thanks to the periodic tile."""
    P = env['period']
    for root, d in ((env['left'], d_left), (env['right'], d_right)):
        root.location.x = -(d % P); root.keyframe_insert('location', index=0, frame=frame)
