"""Build the two original hypercars in Blender (bpy) and render one lane frame-sequence each in hollow line-art style.

Body: a low-poly cage lofted from profile curves (Subdivision Surface level 3, mirrored), wheel arches cut with
booleans; real wheels (tyre, 10-spoke / 5 twin-spoke rims, disc, caliper), wing, splitter, diffuser blades, mirrors,
C-line tube (red car), light bar (blue car). Rendered with Cycles + Freestyle (black ink on white, tinted body).
usage: out/bpyenv/bin/python blend_cars.py still KEY T OUT.png | seq KEY OUTDIR [START END]
"""
import math, sys, json
from pathlib import Path
import numpy as np
import bpy, bmesh
from mathutils import Vector, Matrix

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from r3d import smooth_curve  # noqa: E402

MBLUR = False
TINT = {'chiron': (0.86, 0.30, 0.27, 1), 'nevera': (0.30, 0.48, 0.92, 1)}

# ---------------------------------------------------------------- shape data (metres, x from tail, y left, z up)
SPEC = {
    'chiron': dict(                                   # traced from the getoutlines.com Chiron blueprint (CC BY 4.0)
        L=4.544, axles=(0.93, 3.62), R=(0.358, 0.345), tw=(0.355, 0.285), arch=0.085,
        cabin=(1.6, 3.3), mirror=(3.12, 0, 0),
        zb=[(0, 0.30), (0.2, 0.20), (0.5, 0.13), (1.3, 0.11), (3.9, 0.11), (4.3, 0.15), (4.544, 0.20)],
        Ws=[(0, 0.20), (0.2, 0.70), (0.35, 0.90), (0.6, 0.97), (1.2, 0.96), (1.6, 0.93), (3.0, 0.95), (3.6, 0.97),
            (4.0, 0.95), (4.25, 0.79), (4.4, 0.59), (4.5, 0.38), (4.544, 0.18)],
        Wm=[(0, 0.22), (0.2, 0.76), (0.35, 0.95), (0.5, 0.99), (0.7, 1.025), (1.1, 1.025), (1.4, 0.995), (1.6, 0.98),
            (2.2, 1.0), (2.75, 0.995), (3.3, 1.02), (3.6, 1.028), (3.9, 1.02), (4.1, 0.97), (4.25, 0.83), (4.4, 0.63),
            (4.5, 0.42), (4.544, 0.20)],
        zs=[(0, 0.66), (0.3, 0.76), (0.6, 0.80), (0.9, 0.82), (1.5, 0.83), (2.5, 0.83), (3.2, 0.81), (3.6, 0.77),
            (4.0, 0.72), (4.3, 0.64), (4.45, 0.56), (4.544, 0.42)],
        Wf=[(0, 0.18), (0.25, 0.46), (0.6, 0.50), (1.3, 0.55), (1.9, 0.60), (2.7, 0.62), (3.05, 0.68), (3.35, 0.80),
            (3.6, 0.88), (4.0, 0.86), (4.25, 0.72), (4.4, 0.52), (4.544, 0.18)],
        zf=[(0, 0.76), (0.15, 0.81), (0.35, 0.86), (0.55, 0.91), (0.75, 0.97), (0.95, 1.02), (1.15, 1.06), (1.35, 1.095),
            (1.55, 1.125), (1.75, 1.145), (1.95, 1.16), (2.15, 1.165), (2.35, 1.15), (2.55, 1.13), (2.75, 1.09),
            (2.95, 1.03), (3.15, 0.96), (3.35, 0.88), (3.6, 0.86), (3.85, 0.83), (4.05, 0.79), (4.25, 0.75),
            (4.44, 0.66), (4.544, 0.44)],
        zc=[(0, 0.78), (0.15, 0.83), (0.35, 0.88), (0.55, 0.93), (0.75, 0.99), (0.95, 1.04), (1.15, 1.08), (1.35, 1.115),
            (1.55, 1.148), (1.75, 1.173), (1.95, 1.19), (2.15, 1.198), (2.35, 1.182), (2.55, 1.157), (2.75, 1.115),
            (2.95, 1.05), (3.15, 0.98), (3.35, 0.89), (3.6, 0.83), (3.85, 0.80), (4.05, 0.76), (4.25, 0.71),
            (4.44, 0.62), (4.544, 0.42)]),
    'nevera': dict(                                   # from published dimensions and CC photos (Wikimedia Commons)
        L=4.75, axles=(1.0, 3.745), R=(0.36, 0.35), tw=(0.335, 0.285), arch=0.08, cabin=(1.4, 3.45), mirror=(3.42, 0, 0),
        zb=[(0, 0.28), (0.3, 0.15), (0.7, 0.11), (4.3, 0.11), (4.6, 0.14), (4.75, 0.20)],
        Ws=[(0, 0.25), (0.15, 0.74), (0.4, 0.90), (1.0, 0.945), (3.75, 0.94), (4.2, 0.90), (4.45, 0.77), (4.62, 0.57), (4.75, 0.26)],
        Wm=[(0, 0.30), (0.15, 0.80), (0.4, 0.96), (1.0, 0.993), (1.5, 0.97), (2.4, 0.95), (3.2, 0.97), (3.75, 0.985),
            (4.2, 0.95), (4.45, 0.82), (4.62, 0.62), (4.75, 0.30)],
        zs=[(0, 0.78), (0.5, 0.84), (1.0, 0.85), (1.6, 0.80), (2.5, 0.78), (3.3, 0.76), (3.75, 0.74), (4.2, 0.66),
            (4.5, 0.56), (4.75, 0.42)],
        Wf=[(0, 0.70), (0.5, 0.68), (1.2, 0.62), (1.8, 0.58), (2.6, 0.58), (3.2, 0.64), (3.5, 0.78), (3.8, 0.86),
            (4.2, 0.80), (4.5, 0.60), (4.75, 0.25)],
        zf=[(0, 0.88), (0.4, 0.92), (0.8, 0.97), (1.2, 1.04), (1.6, 1.11), (2.0, 1.16), (2.4, 1.178), (2.8, 1.15),
            (3.1, 1.07), (3.35, 0.95), (3.6, 0.88), (3.8, 0.86), (4.1, 0.80), (4.4, 0.70), (4.6, 0.62), (4.75, 0.48)],
        zc=[(0, 0.90), (0.15, 0.93), (0.4, 0.95), (0.8, 1.00), (1.2, 1.07), (1.6, 1.14), (2.0, 1.19), (2.4, 1.208),
            (2.8, 1.18), (3.1, 1.10), (3.35, 0.97), (3.55, 0.85), (3.8, 0.77), (4.1, 0.71), (4.4, 0.64), (4.6, 0.57),
            (4.75, 0.46)]),
}


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def mat(name, col, rough=0.6, emit=None):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = col; b.inputs['Roughness'].default_value = rough
    if emit:
        b.inputs['Emission Color'].default_value = emit; b.inputs['Emission Strength'].default_value = 1.0
    return m


def obj_from(name, verts, faces, mats=None, smooth=True):
    me = bpy.data.meshes.new(name); me.from_pydata(verts, [], faces); me.update()
    o = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(o)
    if smooth:
        for p in me.polygons: p.use_smooth = True
    for m in mats or []: me.materials.append(m)
    return o


def section(x, f):
    zb, Ws, Wm, zs, Wf, zf, zc = (float(f[k](x)) for k in ('zb', 'Ws', 'Wm', 'zs', 'Wf', 'zf', 'zc'))
    Wf = min(Wf, Wm - 0.05); zs = min(zs, zf - 0.05)
    lerp = lambda a, b, k: a + (b - a) * k
    return [(0, zb), (0.5 * Ws, zb), (0.88 * Ws, zb + 0.004), (Ws, zb + 0.05), (lerp(Ws, Wm, 0.75), lerp(zb, zs, 0.38)),
            (Wm, zs - 0.07), (Wm - 0.012, zs), (lerp(Wm, Wf, 0.55) + 0.01, lerp(zs, zf, 0.62)), (Wf, zf),
            (0.66 * Wf, lerp(zf, zc, 0.62)), (0.33 * Wf, lerp(zf, zc, 0.93)), (0, zc)]


def body(key, m_body):
    s = SPEC[key]; L = s['L']
    f = {k: smooth_curve(s[k]) for k in ('zb', 'Ws', 'Wm', 'zs', 'Wf', 'zf', 'zc')}
    u = np.linspace(0, 1, 64)
    xs = L * (0.5 - 0.5 * np.cos(np.pi * u)) * 0.55 + L * u * 0.45
    rows = [section(x, f) for x in xs]
    nv = len(rows[0])
    verts = []
    for i, (x, r) in enumerate(zip(xs, rows)):
        k = 1.0
        if i == 0 or i == len(xs) - 1: k = 0.8                                        # pinch the end rows
        zc_ = 0.5 * (r[0][1] + r[-1][1])
        for (y, z) in r: verts.append((x, y * k, zc_ + (z - zc_) * (0.6 + 0.4 * k)))
    faces = []
    for i in range(len(xs) - 1):
        for j in range(nv - 1):
            a = i * nv + j; faces.append((a, a + 1, a + nv + 1, a + nv))
    faces.append(tuple(range(nv - 1, -1, -1)))                                          # tail cap (half)
    n0 = (len(xs) - 1) * nv; faces.append(tuple(range(n0, n0 + nv)))
    o = obj_from(key + '_body', verts, faces, [m_body])
    bm = bmesh.new(); bm.from_mesh(o.data)
    cl = bm.edges.layers.float.get('crease_edge') or bm.edges.layers.float.new('crease_edge')
    bm.verts.ensure_lookup_table()
    cab = s.get('cabin', (1.5, 3.0))
    for e in bm.edges:
        a, b = sorted(v.index for v in e.verts)
        if b - a != nv: continue                                   # only longitudinal edges
        j = a % nv; x = 0.5 * (e.verts[0].co.x + e.verts[1].co.x)
        if j == 6: e[cl] = 0.75
        elif j == 3: e[cl] = 0.55
        elif j == 8 and not (cab[0] < x < cab[1]): e[cl] = 0.45
    bm.to_mesh(o.data); bm.free()
    mm = o.modifiers.new('mirror', 'MIRROR'); mm.use_axis = (False, True, False); mm.use_clip = True; mm.use_mirror_merge = True
    sd = o.modifiers.new('subd', 'SUBSURF'); sd.levels = 2; sd.render_levels = 3
    for xw, R in zip(s['axles'], s['R']):                                                 # wheel arches
        for sg in (1, -1):
            Wx = float(f['Wm'](xw))
            bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=R + s.get('arch', 0.05), depth=0.6,
                                                location=(xw, sg * (Wx + 0.2 - 0.02), R), rotation=(math.pi / 2, 0, 0))
            c = bpy.context.object; c.hide_render = True; c.display_type = 'WIRE'
            b = o.modifiers.new('arch', 'BOOLEAN'); b.object = c; b.operation = 'DIFFERENCE'; b.solver = 'EXACT'
    o['f'] = 0
    return o, f


def wheel(key, k, sg, f, mats):
    s = SPEC[key]; xw, R, tw = s['axles'][k], s['R'][k], s['tw'][k]
    Wx = float(f['Wm'](xw)); yw = sg * (Wx - tw / 2 - 0.01)
    root = bpy.data.objects.new(f'{key}_wheel{k}{sg}', None); bpy.context.collection.objects.link(root)
    root.location = (xw, yw, R)
    hub = bpy.data.objects.new(f'{key}_hub{k}{sg}', None); bpy.context.collection.objects.link(hub); hub.parent = root
    parts = []
    bpy.ops.mesh.primitive_torus_add(major_radius=R - 0.07, minor_radius=0.07, major_segments=96, minor_segments=24)
    t = bpy.context.object; t.scale = (1, 1, 1); t.rotation_euler = (math.pi / 2, 0, 0)
    t.scale = (1, 1, tw / 0.14 * 0.95); t.data.materials.append(mats['tyre']); parts.append(t)
    Rr = R * 0.72
    bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=Rr, depth=tw * 0.85, rotation=(math.pi / 2, 0, 0))
    barrel = bpy.context.object; barrel.data.materials.append(mats['dark']); parts.append(barrel)
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=Rr * 0.82, depth=0.03, location=(0, -sg * 0.02 * 0 + sg * (tw * 0.1), 0),
                                        rotation=(math.pi / 2, 0, 0))
    disc = bpy.context.object; disc.data.materials.append(mats['disc']); parts.append(disc)
    n = 10 if key == 'chiron' else 5
    for i in range(n):
        for off in ((0,) if n == 10 else (-0.09, 0.09)):
            a = 2 * math.pi * i / n + off
            bpy.ops.mesh.primitive_cube_add(size=1)
            sp = bpy.context.object
            sp.scale = (Rr * 0.86 / 2, 0.025, 0.022 if n == 10 else 0.03)
            sp.location = (math.cos(a) * Rr * 0.45, sg * (tw * 0.40), math.sin(a) * Rr * 0.45)
            sp.rotation_euler = (0, -a, 0)
            bv = sp.modifiers.new('bv', 'BEVEL'); bv.width = 0.006; bv.segments = 2
            sp.data.materials.append(mats['rim']); parts.append(sp)
    bpy.ops.mesh.primitive_cylinder_add(vertices=64, radius=Rr, depth=0.03, location=(0, sg * tw * 0.42, 0), rotation=(math.pi / 2, 0, 0))
    lip = bpy.context.object
    so = lip.modifiers.new('sol', 'SOLIDIFY'); lip.data.materials.append(mats['rim'])
    bm = bmesh.new(); bm.from_mesh(lip.data)
    bmesh.ops.inset_region(bm, faces=[fc for fc in bm.faces if len(fc.verts) > 4], thickness=Rr * 0.08, depth=0)
    for fc in [fc for fc in bm.faces if len(fc.verts) > 4]: bm.faces.remove(fc)
    bm.to_mesh(lip.data); bm.free(); parts.append(lip)
    bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=Rr * 0.17, depth=0.06, location=(0, sg * tw * 0.42, 0), rotation=(math.pi / 2, 0, 0))
    cap = bpy.context.object; cap.data.materials.append(mats['rim']); parts.append(cap)
    for p in parts: p.parent = hub
    for p in parts:
        for poly in p.data.polygons: poly.use_smooth = True
    bpy.ops.mesh.primitive_cube_add(size=1, location=(xw + Rr * 0.45, yw + sg * (tw * 0.18 - tw / 2 + 0.12), R + Rr * 0.42))
    cal = bpy.context.object; cal.scale = (0.16, 0.05, 0.09); cal.rotation_euler = (0, math.radians(-40), 0)
    bv = cal.modifiers.new('bv', 'BEVEL'); bv.width = 0.02; bv.segments = 3
    cal.data.materials.append(mats['caliper'])
    return root, hub


# ---------------------------------------------------------------- surface-conforming detail ("decals" with real edges)
from mathutils.bvhtree import BVHTree  # noqa: E402


def body_bvh(o):
    dg = bpy.context.evaluated_depsgraph_get()
    return BVHTree.FromObject(o.evaluated_get(dg), dg)


def resample(poly, step):
    P = np.asarray(poly, float); P = np.vstack([P, P[:1]])
    seg = np.linalg.norm(np.diff(P, axis=0), axis=1); d = np.concatenate([[0], np.cumsum(seg)])
    n = max(8, int(d[-1] / step)); t = np.linspace(0, d[-1], n, endpoint=False)
    return np.stack([np.interp(t, d, P[:, 0]), np.interp(t, d, P[:, 1])], 1)


def ray_for(plane, u, v, L, sign=1):
    if plane == 'side': return Vector((u, sign * 3.0, v)), Vector((0, -sign, 0))
    if plane == 'top': return Vector((u, v, 3.0)), Vector((0, 0, -1))
    if plane == 'front': return Vector((L + 1.0, u, v)), Vector((-1, 0, 0))
    return Vector((-1.0, u, v)), Vector((1, 0, 0))                     # rear


def decal(name, poly, plane, bvh, m, L, off=0.004, step=0.02, sign=1, parent=None):
    pts = resample(poly, step * 0.5)
    bm = bmesh.new()
    vs = [bm.verts.new((u, v, 0)) for u, v in pts]
    es = [bm.edges.new((vs[i], vs[(i + 1) % len(vs)])) for i in range(len(vs))]
    bmesh.ops.triangle_fill(bm, use_beauty=True, use_dissolve=False, edges=es)
    for _ in range(8):
        long = [e for e in bm.edges if e.calc_length() > step]
        if not long: break
        bmesh.ops.subdivide_edges(bm, edges=long, cuts=1, use_grid_fill=False)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bmesh.ops.beautify_fill(bm, faces=bm.faces[:], edges=bm.edges[:])
    miss = []
    for v in bm.verts:
        o_, d_ = ray_for(plane, v.co.x, v.co.y, L, sign)
        hit, nrm, _, _ = bvh.ray_cast(o_, d_)
        if hit is None: miss.append(v); continue
        v.co = hit + nrm * off
    bmesh.ops.delete(bm, geom=miss, context='VERTS')
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(ob)
    for pl in me.polygons: pl.use_smooth = True
    me.materials.append(m)
    if parent: ob.parent = parent
    return ob


def tube(name, pts3, r, m, parent=None):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 4
    sp = cu.splines.new('POLY'); sp.points.add(len(pts3) - 1)
    for p_, c in zip(sp.points, pts3): p_.co = (c[0], c[1], c[2], 1)
    ob = bpy.data.objects.new(name, cu); bpy.context.collection.objects.link(ob); cu.materials.append(m)
    if parent: ob.parent = parent
    return ob


def project_side(bvh, pts2, sign, off):
    out = []
    for u, v in pts2:
        hit, nrm, _, _ = bvh.ray_cast(Vector((u, sign * 3.0, v)), Vector((0, -sign, 0)))
        if hit is not None: out.append(hit + nrm * off)
    return out


def superellipse(cy, cz, ry, rz, p=2.4, n=64):
    a = np.linspace(0, 2 * np.pi, n, endpoint=False)
    c, s_ = np.cos(a), np.sin(a)
    return np.stack([cy + ry * np.sign(c) * np.abs(c) ** (2 / p), cz + rz * np.sign(s_) * np.abs(s_) ** (2 / p)], 1)


def plate(name, poly_xy, z0, z1, m, parent=None):
    """Thin flat part (splitter, wing) extruded from a top-view outline."""
    pts = resample(poly_xy, 0.03)
    bm = bmesh.new(); vs = [bm.verts.new((u, v, z0)) for u, v in pts]
    f = bm.faces.new(vs)
    r = bmesh.ops.extrude_face_region(bm, geom=[f])
    for v in [g for g in r['geom'] if isinstance(g, bmesh.types.BMVert)]: v.co.z = z1
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); bpy.context.collection.objects.link(ob); me.materials.append(m)
    bv = ob.modifiers.new('bv', 'BEVEL'); bv.width = 0.004; bv.segments = 2
    if parent: ob.parent = parent
    return ob


def fin(name, x0, x1, y, z0, z1, m, parent=None):
    bpy.ops.mesh.primitive_cube_add(size=1, location=((x0 + x1) / 2, y, (z0 + z1) / 2))
    ob = bpy.context.object; ob.scale = (x1 - x0, 0.012, z1 - z0); ob.data.materials.append(m)
    if parent: ob.parent = parent
    return ob


def features(key, bodyo, f, M, car):
    s = SPEC[key]; L = s['L']; bvh = body_bvh(bodyo)
    D = lambda *a, **k: decal(*a, bvh=bvh, L=L, parent=car, **k)
    if key == 'chiron':
        side_win = [(2.93, 1.075), (2.6, 1.10), (2.2, 1.10), (2.01, 1.09), (2.04, 0.845), (2.6, 0.84), (3.28, 0.86),
                    (3.15, 0.95)]
        C = path_pts([(2.96, 1.09), (2.6, 1.12), (2.0, 1.12), (1.74, 1.07), (1.50, 0.98), (1.46, 0.70), (1.62, 0.50),
                      (1.80, 0.34), (2.5, 0.29), (3.38, 0.31)])
        for sg in (1, -1):
            D(f'win{sg}', side_win, 'side', m=M['glass'], sign=sg)
            D(f'qwin{sg}', superellipse(1.76, 0.975, 0.075, 0.062, 2, 40), 'side', m=M['glass'], sign=sg, step=0.01)
            tube(f'cline{sg}', project_side(bvh, C, sg, 0.008), 0.018, M['chrome'], car)
            D(f'bpil{sg}', [(1.99, 1.09), (2.02, 1.09), (2.06, 0.845), (2.03, 0.845)], 'side', m=M['black'], sign=sg, off=0.005, step=0.008)
            D(f'door{sg}', [(2.03, 0.84), (2.05, 0.84), (2.37, 0.33), (2.35, 0.33)], 'side', m=M['black'], sign=sg, off=0.003, step=0.008)
            D(f'doorf{sg}', [(3.30, 0.84), (3.32, 0.84), (3.40, 0.32), (3.38, 0.32)], 'side', m=M['black'], sign=sg, off=0.003, step=0.008)
            D(f'handle{sg}', superellipse(2.27, 0.67, 0.08, 0.022, 2, 32), 'side', m=M['black'], sign=sg, off=0.006, step=0.008)
            D(f'sill{sg}', [(1.30, 0.12), (3.25, 0.12), (3.25, 0.20), (1.30, 0.20)], 'side', m=M['black'], sign=sg)
            D(f'rlight{sg}', [(0.0, 0.69), (0.13, 0.70), (0.13, 0.715), (0.0, 0.71)], 'side', m=M['tail'], sign=sg, off=0.006, step=0.008)
        D('screen', [(3.38, -0.78), (3.38, 0.78), (2.90, 0.64), (2.90, -0.64)], 'top', m=M['glass'], off=0.006)
        D('hs_ring', superellipse(0, 0.41, 0.215, 0.235, 2.3), 'front', m=M['chrome'], off=0.004)
        D('hs', superellipse(0, 0.41, 0.185, 0.205, 2.3), 'front', m=M['mesh'], off=0.008)
        for sg in (1, -1):
            D(f'hlh{sg}', [(sg * 0.33, 0.60), (sg * 0.95, 0.585), (sg * 0.97, 0.66), (sg * 0.55, 0.685), (sg * 0.33, 0.625)],
              'front', m=M['black'], off=0.004)
            for k_, cy in enumerate((0.88, 0.79, 0.69, 0.60)):
                D(f'led{sg}{k_}', superellipse(sg * cy, 0.635, 0.032, 0.026, 4, 32), 'front', m=M['light'], off=0.008, step=0.008)
            D(f'ci{sg}', [(sg * 0.33, 0.22), (sg * 0.94, 0.22), (sg * 0.95, 0.40), (sg * 0.33, 0.40)], 'front', m=M['mesh'], off=0.004)
            D(f'cib{sg}', [(sg * 0.33, 0.30), (sg * 0.95, 0.30), (sg * 0.95, 0.315), (sg * 0.33, 0.315)], 'front', m=M['body2'], off=0.007, step=0.01)
        D('splitbar', [(-0.95, 0.165), (0.95, 0.165), (0.95, 0.19), (-0.95, 0.19)], 'front', m=M['black'], off=0.004, step=0.01)
        for sg in (1, -1):
            D(f'rearmesh{sg}', [(sg * 0.36, 0.40), (sg * 0.86, 0.40), (sg * 0.86, 0.64), (sg * 0.36, 0.64)], 'rear', m=M['mesh'])
        D('tail', [(-0.92, 0.685), (0.92, 0.685), (0.92, 0.705), (-0.92, 0.705)], 'rear', m=M['tail'], off=0.006, step=0.01)
        D('exh', [(-0.28, 0.24), (0.28, 0.24), (0.22, 0.37), (-0.22, 0.37)], 'rear', m=M['black'], off=0.006)
        for k_, yy in enumerate((-0.17, -0.06, 0.06, 0.17)):
            D(f'pipe{k_}', superellipse(yy, 0.30, 0.045, 0.04, 2, 32), 'rear', m=M['chrome'], off=0.012, step=0.01)
        for yy in np.arange(-0.70, 0.71, 0.14): fin(f'fin{yy:.2f}', -0.05, 0.55, yy, 0.10, 0.28, M['black'], car)
        plate('splitter', [(4.20, -0.90), (4.40, -0.78), (4.50, -0.45), (4.52, 0.0), (4.50, 0.45), (4.40, 0.78), (4.20, 0.90)], 0.11, 0.13, M['black'], car)
    else:
        for sg in (1, -1):
            D(f'win{sg}', [(1.55, 0.92), (2.0, 1.10), (2.5, 1.165), (3.0, 1.12), (3.40, 0.95), (3.52, 0.87), (3.0, 0.84),
                           (2.3, 0.83), (1.8, 0.86)], 'side', m=M['glass'], sign=sg)
            D(f'carbon{sg}', [(1.30, 0.12), (3.40, 0.12), (3.40, 0.36), (2.6, 0.40), (1.95, 0.42), (1.30, 0.36)], 'side', m=M['black'], sign=sg)
            D(f'intake{sg}', [(1.40, 0.40), (1.78, 0.42), (2.02, 0.60), (1.92, 0.76), (1.55, 0.73), (1.40, 0.60)], 'side', m=M['mesh'], sign=sg, off=0.006)
            D(f'door{sg}', [(3.40, 0.84), (3.43, 0.84), (3.43, 0.36), (3.40, 0.36)], 'side', m=M['black'], sign=sg, off=0.003, step=0.008)
            D(f'blade{sg}', [(2.02, 0.60), (3.30, 0.66), (3.30, 0.675), (2.00, 0.615)], 'side', m=M['black'], sign=sg, off=0.004, step=0.008)
            D(f'hl{sg}', [(sg * 0.40, 0.57), (sg * 0.86, 0.63), (sg * 0.90, 0.67), (sg * 0.82, 0.675), (sg * 0.40, 0.605)],
              'front', m=M['light'], off=0.006, step=0.008)
            D(f'ci{sg}', [(sg * 0.40, 0.21), (sg * 0.88, 0.21), (sg * 0.93, 0.50), (sg * 0.74, 0.53), (sg * 0.40, 0.40)], 'front', m=M['mesh'], off=0.004)
        D('roof', [(1.60, -0.46), (3.00, -0.50), (3.00, 0.50), (1.60, 0.46)], 'top', m=M['black'], off=0.004)
        D('screen', [(3.00, -0.62), (3.00, 0.62), (3.58, 0.80), (3.58, -0.80)], 'top', m=M['glass'], off=0.006)
        D('hoodvent', [(3.85, -0.30), (4.22, -0.33), (4.22, 0.33), (3.85, 0.30)], 'top', m=M['black'], off=0.004)
        D('fintake', [(-0.38, 0.19), (0.38, 0.19), (0.36, 0.35), (-0.36, 0.35)], 'front', m=M['mesh'])
        D('rearpanel', [(-0.90, 0.40), (0.90, 0.40), (0.90, 0.78), (-0.90, 0.78)], 'rear', m=M['black'])
        D('lightbar', [(-0.94, 0.795), (0.94, 0.795), (0.94, 0.825), (-0.94, 0.825)], 'rear', m=M['tail'], off=0.008, step=0.01)
        for yy in np.arange(-0.64, 0.65, 0.16): fin(f'fin{yy:.2f}', -0.05, 0.62, yy, 0.10, 0.30, M['black'], car)
        plate('splitter', [(4.40, -0.86), (4.60, -0.74), (4.70, -0.45), (4.73, 0.0), (4.70, 0.45), (4.60, 0.74), (4.40, 0.86)], 0.10, 0.122, M['black'], car)
        plate('ducktail', [(-0.01, -0.70), (0.22, -0.70), (0.22, 0.70), (-0.01, 0.70)], 0.90, 0.92, M['body2'], car)

def path_pts(cp, n=80):
    """Cubic Bezier chain: start + groups of (c1, c2, end)."""
    pts = [np.array(cp[0], float)]
    for i in range(1, len(cp), 3):
        p0, p1, p2, p3 = map(np.array, (pts[-1], cp[i], cp[i + 1], cp[i + 2]))
        t = np.linspace(0, 1, n // 2)[1:, None]
        pts += list((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t ** 2 * p2 + t ** 3 * p3)
    return [tuple(p) for p in pts]


def bake(o):
    """Apply mirror/subsurf/booleans once so animation frames don't re-evaluate them."""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(o.evaluated_get(dg))
    o.modifiers.clear(); old = o.data; o.data = me; bpy.data.meshes.remove(old)
    for ob in [x for x in bpy.data.objects if x.type == 'MESH' and x.hide_render and x.display_type == 'WIRE']:
        bpy.data.objects.remove(ob)


def build(key):
    reset()
    sc = bpy.context.scene
    tint = TINT[key]
    mats = dict(body=mat('body', tint, 0.35), tyre=mat('tyre', (0.45, 0.45, 0.47, 1), 0.9), dark=mat('dark', (0.55, 0.55, 0.58, 1)),
                disc=mat('disc', (0.8, 0.8, 0.8, 1)), rim=mat('rim', (0.97, 0.97, 0.97, 1), 0.3),
                caliper=mat('caliper', tint, 0.4), glass=mat('glass', (0.42, 0.46, 0.52, 1), 0.1),
                light=mat('light', (1, 1, 1, 1), 0.2, emit=(1, 1, 1, 1)), black=mat('black', (0.25, 0.25, 0.27, 1), 0.5))
    mats.update(chrome=mat('chrome', (0.97, 0.97, 0.98, 1), 0.15), mesh=mat('mesh', (0.42, 0.42, 0.45, 1), 0.7),
                tail=mat('tail', (1, 0.55, 0.5, 1), 0.3, emit=(1, 0.3, 0.25, 1)),
                body2=mat('body2', tuple(c * 0.8 for c in tint[:3]) + (1,), 0.35))
    car = bpy.data.objects.new('car', None); sc.collection.objects.link(car)
    bodyo, f = body(key, mats['body']); bodyo.parent = car
    features(key, bodyo, f, mats, car)
    mx = SPEC[key]['mirror'][0]; Wm = float(f['Wm'](mx)); zm = float(f['zs'](mx))
    for sg in (1, -1):                                                    # door mirrors on stalks
        bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=16, radius=1, location=(mx, sg * (Wm + 0.05), zm + 0.08))
        h = bpy.context.object; h.scale = (0.11, 0.05, 0.05); h.data.materials.append(mats['body']); h.parent = car
        for pl in h.data.polygons: pl.use_smooth = True
        bpy.ops.mesh.primitive_cube_add(size=1, location=(mx + 0.03, sg * (Wm - 0.0), zm + 0.045))
        st = bpy.context.object; st.scale = (0.05, 0.11, 0.018); st.data.materials.append(mats['black']); st.parent = car
        bv = st.modifiers.new('bv', 'BEVEL'); bv.width = 0.006; bv.segments = 2
    bake(bodyo)
    wheels = []
    for k in (0, 1):
        for sg in (1, -1):
            r, h = wheel(key, k, sg, f, mats); r.parent = None; wheels.append(h)
    return car, bodyo, wheels, f, mats


def setup_render(sc, w, h):
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 4; sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 3; sc.cycles.diffuse_bounces = 1; sc.cycles.glossy_bounces = 1; sc.cycles.transmission_bounces = 0
    sc.cycles.transparent_max_bounces = 2; sc.cycles.caustics_reflective = False; sc.cycles.caustics_refractive = False
    sc.cycles.use_adaptive_sampling = True; sc.cycles.denoiser = 'OPENIMAGEDENOISE'
    sc.render.resolution_x, sc.render.resolution_y = int(w), int(h); sc.render.film_transparent = False
    sc.render.use_freestyle = True; sc.render.line_thickness_mode = 'ABSOLUTE'; sc.render.line_thickness = 1.4
    vl = sc.view_layers[0]; fs = vl.freestyle_settings; fs.crease_angle = math.radians(146)
    ls = fs.linesets[0] if fs.linesets else fs.linesets.new('ink')
    ls.select_by_visibility = True; ls.visibility = 'VISIBLE'
    ls.select_border = False
    for k in ('select_silhouette', 'select_crease', 'select_material_boundary', 'select_contour', 'select_external_contour'):
        setattr(ls, k, True)
    if ls.linestyle is None: ls.linestyle = bpy.data.linestyles.new('ink')
    ls.linestyle.color = (0.05, 0.05, 0.06); ls.linestyle.thickness = 1.6
    world = bpy.data.worlds.new('w'); sc.world = world; world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (1, 1, 1, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.55
    sc.view_settings.view_transform = 'Standard'


def still(key, out, yaw=35, el=9, d=7.4, w=1080, h=460):
    car, bodyo, wheels, f, mats = build(key)
    sc = bpy.context.scene
    setup_render(sc, w, h); white_world(sc)
    L = SPEC[key]['L']; tgt = Vector((L / 2 + 0.15, 0, 0.55))
    yr, er = math.radians(yaw), math.radians(el)
    eye = tgt + d * Vector((math.sin(yr) * math.cos(er), -math.cos(yr) * math.cos(er), math.sin(er)))
    camd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', camd); sc.collection.objects.link(cam)
    camd.angle = math.radians(30) * w / h if w > h else math.radians(30); camd.sensor_fit = 'VERTICAL'; camd.angle = math.radians(30)
    cam.location = eye; cam.rotation_euler = (tgt - eye).to_track_quat('-Z', 'Y').to_euler(); sc.camera = cam
    bpy.ops.mesh.primitive_plane_add(size=80, location=(L / 2, 0, 0))
    fl = bpy.context.object; fl.data.materials.append(mat('floor', (1, 1, 1, 1), 0.9)); fl.visible_shadow = False
    ld = bpy.data.lights.new('key', 'AREA'); ld.energy = 520; ld.size = 6
    lo = bpy.data.objects.new('key', ld); sc.collection.objects.link(lo); lo.location = (L / 2 + 2, -3, 6)
    lo.rotation_euler = (Vector((L / 2, 0, 0)) - lo.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)


def white_world(sc):
    nt = sc.world.node_tree; N = nt.nodes
    lp = N.new('ShaderNodeLightPath'); wb = N.new('ShaderNodeBackground'); mx = N.new('ShaderNodeMixShader')
    wb.inputs['Color'].default_value = (1, 1, 1, 1); wb.inputs['Strength'].default_value = 1.0
    out = N['World Output']; bg = N['Background']
    nt.links.new(bg.outputs[0], mx.inputs[1]); nt.links.new(wb.outputs[0], mx.inputs[2])
    nt.links.new(lp.outputs['Is Camera Ray'], mx.inputs[0]); nt.links.new(mx.outputs[0], out.inputs[0])


def heat_material(m, L):
    """Body paint mixed with a speed-heat (pressure-map style) colour ramp; Value node 'heat' sets the mix."""
    nt = m.node_tree; N = nt.nodes; out = N['Material Output']; base = N['Principled BSDF']
    hb = N.new('ShaderNodeBsdfPrincipled'); hb.inputs['Roughness'].default_value = 0.4
    tc = N.new('ShaderNodeTexCoord'); sx = N.new('ShaderNodeSeparateXYZ'); geo = N.new('ShaderNodeNewGeometry')
    sn = N.new('ShaderNodeSeparateXYZ')
    a = N.new('ShaderNodeMath'); a.operation = 'MULTIPLY'; a.inputs[1].default_value = 0.45 / L
    b = N.new('ShaderNodeMath'); b.operation = 'MULTIPLY_ADD'; b.inputs[1].default_value = 0.30; b.inputs[2].default_value = 0.30
    c = N.new('ShaderNodeMath'); c.operation = 'ADD'
    ramp = N.new('ShaderNodeValToRGB'); el = ramp.color_ramp.elements
    cols = [(0.03, 0.05, 0.75), (0.0, 0.55, 0.85), (0.05, 0.65, 0.12), (0.95, 0.85, 0.05), (0.95, 0.35, 0.02), (0.85, 0.02, 0.02)]
    el[0].color = cols[0] + (1,); el[1].position = 1.0; el[1].color = cols[-1] + (1,)
    for i, cc in enumerate(cols[1:-1], 1):
        e = el.new(i / 5); e.color = cc + (1,)
    nt.links.new(tc.outputs['Object'], sx.inputs[0]); nt.links.new(sx.outputs['X'], a.inputs[0])
    nt.links.new(geo.outputs['Normal'], sn.inputs[0]); nt.links.new(sn.outputs['X'], b.inputs[0])
    nt.links.new(a.outputs[0], c.inputs[0]); nt.links.new(b.outputs[0], c.inputs[1]); nt.links.new(c.outputs[0], ramp.inputs[0])
    nt.links.new(ramp.outputs[0], hb.inputs['Base Color'])
    mx = N.new('ShaderNodeMixShader'); v = N.new('ShaderNodeValue'); v.name = 'heat'; v.outputs[0].default_value = 0
    nt.links.new(v.outputs[0], mx.inputs[0]); nt.links.new(base.outputs[0], mx.inputs[1]); nt.links.new(hb.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs['Surface'])
    return v


def floor_material(L):
    """White blueprint floor: 1 m / 5 m grid, dashed lane edges, a start line. 'smear' widens lines across travel."""
    m = bpy.data.materials.new('floor'); m.use_nodes = True; nt = m.node_tree; N = nt.nodes
    bsdf = N['Principled BSDF']; bsdf.inputs['Roughness'].default_value = 0.9
    bsdf.inputs['Emission Strength'].default_value = 0.45
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Object'], sep.inputs[0])
    sm = N.new('ShaderNodeValue'); sm.name = 'smear'; sm.outputs[0].default_value = 0

    def M(op, a, b=None, c=None):
        n = N.new('ShaderNodeMath'); n.operation = op
        for i, v in enumerate((a, b, c)):
            if v is None: continue
            if isinstance(v, (int, float)): n.inputs[i].default_value = v
            else: nt.links.new(v, n.inputs[i])
        return n.outputs[0]

    def line(u, period, w, smear=None):
        d = M('ABSOLUTE', M('SUBTRACT', M('FRACT', M('ADD', M('DIVIDE', u, period), 0.5)), 0.5))
        d = M('MULTIPLY', d, period)
        ww = M('ADD', w, smear) if smear is not None else w
        return M('SUBTRACT', 1.0, M('SMOOTHSTEP', d, M('MULTIPLY', ww, 0.6) if smear is not None else w * 0.6,
                                    M('MULTIPLY', ww, 1.4) if smear is not None else w * 1.4)) if False else \
            M('LESS_THAN', d, ww)

    X, Y = sep.outputs['X'], sep.outputs['Y']
    g1 = M('MAXIMUM', line(X, 1.0, 0.012, sm.outputs[0]), line(Y, 1.0, 0.012))
    g5 = M('MAXIMUM', line(X, 5.0, 0.025, sm.outputs[0]), line(Y, 5.0, 0.025))
    grid = M('MAXIMUM', M('MULTIPLY', g1, 0.35), M('MULTIPLY', g5, 0.7))
    dash = M('LESS_THAN', M('FRACT', M('DIVIDE', X, 6.0)), 0.5)
    lane = M('MULTIPLY', M('LESS_THAN', M('ABSOLUTE', M('SUBTRACT', M('ABSOLUTE', Y), 2.1)), 0.05), M('MAXIMUM', dash, M('MINIMUM', sm.outputs[0], 1.0)))
    start = M('MULTIPLY', M('LESS_THAN', M('ABSOLUTE', M('SUBTRACT', X, L + 0.6)), 0.10), M('LESS_THAN', M('ABSOLUTE', Y), 2.1))
    ink = M('MAXIMUM', lane, start)
    c1 = N.new('ShaderNodeMix'); c1.data_type = 'RGBA'; c1.inputs[6].default_value = (1, 1, 1, 1); c1.inputs[7].default_value = (0.45, 0.58, 0.80, 1)
    nt.links.new(grid, c1.inputs[0])
    c2 = N.new('ShaderNodeMix'); c2.data_type = 'RGBA'; c2.inputs[7].default_value = (0.04, 0.04, 0.05, 1)
    nt.links.new(c1.outputs[2], c2.inputs[6]); nt.links.new(ink, c2.inputs[0])
    nt.links.new(c2.outputs[2], bsdf.inputs['Base Color']); nt.links.new(c2.outputs[2], bsdf.inputs['Emission Color'])
    return m, sm


def scene_for(key, w, h):
    car, bodyo, wheels, f, mats = build(key)
    sc = bpy.context.scene; setup_render(sc, w, h); white_world(sc)
    L = SPEC[key]['L']
    heat = heat_material(mats['body'], L)
    camd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', camd); sc.collection.objects.link(cam)
    camd.sensor_fit = 'VERTICAL'; camd.angle = math.radians(30); sc.camera = cam
    fm, smear = floor_material(L)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0))
    fl = bpy.context.object; fl.scale = (900, 400, 1)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True); fl.location = (300, 0, 0)
    fl.data.materials.append(fm); fl.visible_shadow = False
    ld = bpy.data.lights.new('key', 'AREA'); ld.energy = 520; ld.size = 6
    lo = bpy.data.objects.new('key', ld); sc.collection.objects.link(lo); lo.location = (L / 2 + 2, -3, 6)
    lo.rotation_euler = (Vector((L / 2, 0, 0)) - lo.location).to_track_quat('-Z', 'Y').to_euler()
    return dict(car=car, wheels=wheels, cam=cam, floor=fl, heat=heat, smear=smear, L=L, sc=sc)


def key_frame(S, key, st, fr):
    s = SPEC[key]; L = S['L']; xm = 0.5 * sum(s['axles'])
    a = math.radians(st['pitch']); piv = Vector((xm, 0, 0.35))
    R = Matrix.Rotation(a, 4, 'Y')
    car = S['car']; car.rotation_euler = (0, a, 0)
    car.location = piv - (R @ piv) + Vector((0, 0, st['heave']))
    car.keyframe_insert('location', frame=fr); car.keyframe_insert('rotation_euler', frame=fr)
    for h in S['wheels']:
        h.rotation_euler = (0, st['spin'], 0); h.keyframe_insert('rotation_euler', frame=fr)
    fl = S['floor']; fl.location = (300 - st['dist'], 0, 0); fl.keyframe_insert('location', frame=fr)
    fl.location.x = 300 - st['dist']
    tgt = Vector((L / 2 + st['tx'], 0, 0.55))
    yr, er, d = math.radians(st['yaw']), math.radians(st['elev']), st['cam_d']
    cam = S['cam']; cam.location = tgt + d * Vector((math.sin(yr) * math.cos(er), -math.cos(yr) * math.cos(er), math.sin(er)))
    cam.rotation_euler = (tgt - cam.location).to_track_quat('-Z', 'Y').to_euler()
    cam.keyframe_insert('location', frame=fr); cam.keyframe_insert('rotation_euler', frame=fr)
    S['heat'].outputs[0].default_value = st['heat']; S['heat'].outputs[0].keyframe_insert('default_value', frame=fr)
    S['smear'].outputs[0].default_value = min(1.2, st['mps'] / 30 * 0.6); S['smear'].outputs[0].keyframe_insert('default_value', frame=fr)


def seq(key, states, outdir, i0=0, i1=None, lines_off=False):
    st = json.load(open(states))[{'chiron': 'red', 'nevera': 'blue'}[key]]
    S = scene_for(key, 1080, 460); sc = S['sc']
    for i, x in enumerate(st): key_frame(S, key, x, i + 1)
    for ob in bpy.data.objects:                                          # linear interpolation, no easing
        if ob.animation_data and ob.animation_data.action:
            for fc in ob.animation_data.action.fcurves:
                for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    sc.render.use_motion_blur = MBLUR; sc.render.motion_blur_shutter = 0.5; sc.cycles.motion_blur_position = 'CENTER'
    sc.render.threads_mode = 'AUTO'
    if lines_off: sc.render.use_freestyle = False
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    i1 = len(st) if i1 is None else min(i1, len(st))
    for i in range(i0, i1):
        p = out / (('n_' if lines_off else 'f_') + f'{i:04d}.png')
        if p.exists(): continue
        sc.frame_set(i + 1); sc.render.filepath = str(p)
        bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'still':
        still(a[1], a[2], *(float(x) for x in a[3:]))
    elif a[0] == 'seq':
        seq(a[1], a[2], a[3], int(a[4]) if len(a) > 4 else 0, int(a[5]) if len(a) > 5 else None, len(a) > 6 and a[6] == 'nolines')
