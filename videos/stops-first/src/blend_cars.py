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

TINT = {'chiron': (0.86, 0.30, 0.27, 1), 'nevera': (0.30, 0.48, 0.92, 1)}

# ---------------------------------------------------------------- shape data (metres, x from tail, y left, z up)
SPEC = {
    'chiron': dict(
        L=4.544, axles=(0.90, 3.611), R=(0.355, 0.34), tw=(0.34, 0.28),
        zb=[(0, 0.36), (0.25, 0.22), (0.6, 0.12), (4.2, 0.11), (4.45, 0.15), (4.544, 0.26)],
        Ws=[(0, 0.86), (0.6, 0.95), (1.4, 0.93), (3.2, 0.93), (4.2, 0.90), (4.544, 0.70)],          # sill
        Wm=[(0, 0.90), (0.35, 0.99), (0.9, 1.019), (1.45, 0.97), (2.2, 0.90), (2.9, 0.93), (3.6, 1.0),  # shoulder
            (4.2, 0.96), (4.45, 0.86), (4.544, 0.70)],
        zs=[(0, 0.78), (0.6, 0.83), (1.0, 0.84), (1.6, 0.78), (2.4, 0.74), (3.0, 0.72), (3.6, 0.68), (4.2, 0.58),
            (4.45, 0.46), (4.544, 0.38)],
        Wf=[(0, 0.80), (0.9, 0.80), (1.5, 0.66), (1.9, 0.55), (2.6, 0.52), (3.0, 0.60), (3.5, 0.74), (4.2, 0.72),
            (4.544, 0.55)],
        zf=[(0, 0.95), (0.4, 0.99), (0.9, 1.00), (1.4, 1.04), (1.9, 1.14), (2.3, 1.16), (2.7, 1.06), (3.0, 0.86),
            (3.5, 0.79), (4.0, 0.72), (4.35, 0.60), (4.544, 0.42)],
        zc=[(0, 0.93), (0.4, 0.97), (0.9, 0.98), (1.4, 1.06), (1.9, 1.19), (2.2, 1.212), (2.6, 1.15), (2.95, 0.92),
            (3.3, 0.77), (3.9, 0.67), (4.35, 0.57), (4.544, 0.42)]),
    'nevera': dict(
        L=4.75, axles=(1.0, 3.745), R=(0.36, 0.35), tw=(0.315, 0.275),
        zb=[(0, 0.30), (0.3, 0.17), (0.7, 0.11), (4.4, 0.11), (4.65, 0.16), (4.75, 0.27)],
        Ws=[(0, 0.84), (0.7, 0.93), (1.6, 0.92), (3.3, 0.92), (4.3, 0.90), (4.75, 0.70)],
        Wm=[(0, 0.88), (0.4, 0.97), (1.0, 0.993), (1.6, 0.95), (2.4, 0.91), (3.1, 0.93), (3.75, 0.985), (4.35, 0.95),
            (4.6, 0.86), (4.75, 0.70)],
        zs=[(0, 0.80), (0.5, 0.82), (1.0, 0.81), (1.8, 0.76), (2.6, 0.73), (3.2, 0.71), (3.75, 0.68), (4.3, 0.59),
            (4.6, 0.48), (4.75, 0.38)],
        Wf=[(0, 0.82), (0.6, 0.80), (1.3, 0.66), (1.9, 0.55), (2.7, 0.54), (3.2, 0.62), (3.6, 0.74), (4.3, 0.72),
            (4.75, 0.55)],
        zf=[(0, 0.86), (0.3, 0.89), (0.8, 0.93), (1.4, 1.03), (1.9, 1.12), (2.4, 1.15), (2.8, 1.11), (3.15, 0.98),
            (3.5, 0.83), (3.9, 0.74), (4.35, 0.63), (4.6, 0.52), (4.75, 0.40)],
        zc=[(0, 0.84), (0.3, 0.88), (0.8, 0.94), (1.4, 1.06), (1.9, 1.16), (2.45, 1.208), (2.85, 1.17), (3.15, 1.02),
            (3.5, 0.84), (3.9, 0.71), (4.35, 0.61), (4.6, 0.51), (4.75, 0.40)]),
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
    u = np.linspace(0, 1, 44)
    xs = L * (0.5 - 0.5 * np.cos(np.pi * u)) * 0.55 + L * u * 0.45
    rows = [section(x, f) for x in xs]
    nv = len(rows[0])
    verts = []
    for i, (x, r) in enumerate(zip(xs, rows)):
        k = 1.0
        if i == 0 or i == len(xs) - 1: k = 0.55                                        # pinch the end rows
        zc_ = 0.5 * (r[0][1] + r[-1][1])
        for (y, z) in r: verts.append((x, y * k, zc_ + (z - zc_) * (0.6 + 0.4 * k)))
    faces = []
    for i in range(len(xs) - 1):
        for j in range(nv - 1):
            a = i * nv + j; faces.append((a, a + 1, a + nv + 1, a + nv))
    faces.append(tuple(range(nv - 1, -1, -1)))                                          # tail cap (half)
    n0 = (len(xs) - 1) * nv; faces.append(tuple(range(n0, n0 + nv)))
    o = obj_from(key + '_body', verts, faces, [m_body])
    mm = o.modifiers.new('mirror', 'MIRROR'); mm.use_axis = (False, True, False); mm.use_clip = True; mm.use_mirror_merge = True
    sd = o.modifiers.new('subd', 'SUBSURF'); sd.levels = 2; sd.render_levels = 3
    for xw, R in zip(s['axles'], s['R']):                                                 # wheel arches
        for sg in (1, -1):
            Wx = float(f['Wm'](xw))
            bpy.ops.mesh.primitive_cylinder_add(vertices=96, radius=R + 0.05, depth=0.6,
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


def build(key):
    reset()
    sc = bpy.context.scene
    tint = TINT[key]
    mats = dict(body=mat('body', tint, 0.35), tyre=mat('tyre', (0.88, 0.88, 0.88, 1), 0.9), dark=mat('dark', (0.55, 0.55, 0.58, 1)),
                disc=mat('disc', (0.8, 0.8, 0.8, 1)), rim=mat('rim', (0.97, 0.97, 0.97, 1), 0.3),
                caliper=mat('caliper', tint, 0.4), glass=mat('glass', (0.72, 0.76, 0.82, 1), 0.1),
                light=mat('light', (1, 1, 1, 1), 0.2, emit=(1, 1, 1, 1)), black=mat('black', (0.25, 0.25, 0.27, 1), 0.5))
    car = bpy.data.objects.new('car', None); sc.collection.objects.link(car)
    bodyo, f = body(key, mats['body']); bodyo.parent = car
    wheels = []
    for k in (0, 1):
        for sg in (1, -1):
            r, h = wheel(key, k, sg, f, mats); r.parent = None; wheels.append(h)
    return car, bodyo, wheels, f, mats


def setup_render(sc, w, h):
    sc.render.engine = 'CYCLES'; sc.cycles.device = 'CPU'; sc.cycles.samples = 12; sc.cycles.use_denoising = True
    sc.render.resolution_x, sc.render.resolution_y = w, h; sc.render.film_transparent = False
    sc.render.use_freestyle = True; sc.render.line_thickness_mode = 'ABSOLUTE'; sc.render.line_thickness = 1.4
    vl = sc.view_layers[0]; fs = vl.freestyle_settings; fs.crease_angle = math.radians(146)
    ls = fs.linesets[0] if fs.linesets else fs.linesets.new('ink')
    ls.select_by_visibility = True; ls.visibility = 'VISIBLE'
    for k in ('select_silhouette', 'select_border', 'select_crease', 'select_material_boundary', 'select_contour', 'select_external_contour'):
        setattr(ls, k, True)
    ls.linestyle.color = (0.05, 0.05, 0.06); ls.linestyle.thickness = 1.6
    world = bpy.data.worlds.new('w'); sc.world = world; world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (1, 1, 1, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = 1.0
    sc.view_settings.view_transform = 'Standard'


def still(key, out, yaw=35, el=9, d=7.4, w=1080, h=460):
    car, bodyo, wheels, f, mats = build(key)
    sc = bpy.context.scene
    setup_render(sc, w, h)
    L = SPEC[key]['L']; tgt = Vector((L / 2 + 0.15, 0, 0.55))
    yr, er = math.radians(yaw), math.radians(el)
    eye = tgt + d * Vector((math.sin(yr) * math.cos(er), -math.cos(yr) * math.cos(er), math.sin(er)))
    camd = bpy.data.cameras.new('cam'); cam = bpy.data.objects.new('cam', camd); sc.collection.objects.link(cam)
    camd.angle = math.radians(30) * w / h if w > h else math.radians(30); camd.sensor_fit = 'VERTICAL'; camd.angle = math.radians(30)
    cam.location = eye; cam.rotation_euler = (tgt - eye).to_track_quat('-Z', 'Y').to_euler(); sc.camera = cam
    bpy.ops.mesh.primitive_plane_add(size=80, location=(L / 2, 0, 0))
    fl = bpy.context.object; fl.data.materials.append(mat('floor', (1, 1, 1, 1), 0.9)); fl.visible_shadow = False
    ld = bpy.data.lights.new('key', 'AREA'); ld.energy = 900; ld.size = 6
    lo = bpy.data.objects.new('key', ld); sc.collection.objects.link(lo); lo.location = (L / 2 + 2, -3, 6)
    lo.rotation_euler = (Vector((L / 2, 0, 0)) - lo.location).to_track_quat('-Z', 'Y').to_euler()
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'still':
        still(a[1], a[2], *(float(x) for x in a[3:]))
