"""Top-view car sprites for stops-first v2: Blender (Cycles + Freestyle) render of two original 3D cars from above.

White clay body with ink outlines, tinted glass, real tyres/rims, one accent colour per car, soft contact shadow,
transparent background. Reuses the body loft, wheels, decals and render setup of blend_cars.py, but swaps in
original details: red = wide and low with a sabre-shaped shoulder crease (no horseshoe, no C-line);
blue = smooth cab-forward teardrop canopy, long sloping tail, full-width light bar. One still per car.
usage: out/bpyenv/bin/python blend_top.py KEY OUT.png [PX_PER_SPRITE_LENGTH]
"""
import math, sys, copy
from pathlib import Path
import numpy as np
import bpy
from mathutils import Vector

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blend_cars as B  # noqa: E402

CAR_W, CAR_L, PAD = 380, 820, 60                                # must match render_v2.py
ACCENT = {'chiron': (0.80, 0.08, 0.06, 1), 'nevera': (0.05, 0.26, 0.85, 1)}


def originalise():
    """Make the plan shapes our own: deeper waist + bigger haunches on red, rounder shoulders on blue."""
    s = B.SPEC['chiron']
    s['Wm'] = [(x, w * (0.93 if 1.5 < x < 2.9 else 1.0) * (1.02 if 0.4 < x < 1.2 else 1.0)) for x, w in s['Wm']]
    s['Ws'] = [(x, w * (0.93 if 1.5 < x < 2.9 else 1.0)) for x, w in s['Ws']]
    s['zc'] = [(x, z * 0.97) for x, z in s['zc']]; s['zf'] = [(x, z * 0.97) for x, z in s['zf']]
    n = B.SPEC['nevera']
    n['Wf'] = [(x, w * 1.06 if 3.2 < x < 4.3 else w) for x, w in n['Wf']]


def top_pts(bvh, pts, off=0.01):
    out = []
    for x, y in pts:
        hit, nrm, _, _ = bvh.ray_cast(Vector((x, y, 3.0)), Vector((0, 0, -1)))
        if hit is not None: out.append(hit + nrm * off)
    return out


def features(key, bodyo, f, M, car):
    s = B.SPEC[key]; L = s['L']; bvh = B.body_bvh(bodyo)
    D = lambda *a, **k: B.decal(*a, bvh=bvh, L=L, parent=car, **k)
    acc = M.setdefault('accent', B.mat('accent', ACCENT[key], 0.35, emit=ACCENT[key]))
    if key == 'chiron':
        D('screen', [(3.40, -0.74), (3.40, 0.74), (2.92, 0.62), (2.92, -0.62)], 'top', m=M['glass'], off=0.006)
        D('roof', [(2.92, -0.60), (2.92, 0.60), (2.05, 0.56), (2.05, -0.56)], 'top', m=M['body'], off=0.004)
        D('rglass', [(2.05, -0.52), (2.05, 0.52), (1.40, 0.40), (1.40, -0.40)], 'top', m=M['glass'], off=0.006)
        for k in range(7):                                                       # engine-cover louvres
            x = 1.48 + 0.08 * k
            D(f'lv{k}', [(x, -0.36 - 0.02 * k), (x, 0.36 + 0.02 * k), (x + 0.025, 0.36 + 0.02 * k), (x + 0.025, -0.36 - 0.02 * k)],
              'top', m=M['black'], off=0.009, step=0.01)
        for sg in (1, -1):
            cr = B.path_pts([(4.05, sg * 0.80), (3.55, sg * 0.76), (3.0, sg * 0.66), (2.45, sg * 0.62), (1.9, sg * 0.68),
                             (1.35, sg * 0.84), (0.95, sg * 0.90)], 90)
            B.tube(f'crease{sg}', top_pts(bvh, cr, 0.012), 0.016, acc, car)      # sabre crease (own design)
            for k in range(2):                                                   # bonnet vents
                y0 = 0.12 + 0.17 * k
                D(f'vent{sg}{k}', [(3.72, sg * y0), (4.06, sg * y0), (4.04, sg * (y0 + 0.12)), (3.74, sg * (y0 + 0.12))],
                  'top', m=M['black'], off=0.006)
            D(f'lamp{sg}', [(4.30, sg * 0.42), (4.40, sg * 0.40), (4.32, sg * 0.80), (4.22, sg * 0.82)], 'top', m=M['black'], off=0.006, step=0.01)
            D(f'drl{sg}', [(4.33, sg * 0.46), (4.37, sg * 0.45), (4.30, sg * 0.74), (4.26, sg * 0.75)], 'top', m=M['light'], off=0.009, step=0.008)
            D(f'tail{sg}', [(0.04, sg * 0.28), (0.12, sg * 0.28), (0.10, sg * 0.72), (0.03, sg * 0.70)], 'top', m=acc, off=0.008, step=0.01)
            B.plate(f'endplate{sg}', [(0.16, sg * 0.84), (0.44, sg * 0.84), (0.44, sg * 0.86), (0.16, sg * 0.86)], 0.80, 1.00, M['black'], car)
        B.plate('wing', [(0.18, -0.86), (0.42, -0.86), (0.42, 0.86), (0.18, 0.86)], 0.97, 0.99, M['body'], car)
        B.plate('splitter', [(4.30, -0.92), (4.50, -0.78), (4.58, -0.40), (4.60, 0.0), (4.58, 0.40), (4.50, 0.78), (4.30, 0.92)], 0.10, 0.12, M['black'], car)
    else:
        can = [(3.62, 0.0)] + [(3.62 - 2.3 * u, 0.70 * math.sin(math.pi * (0.5 * u + 0.5) ** 0.9) * (1 - u) ** 0.6) for u in np.linspace(0.02, 1, 30)]
        canopy = can + [(x, -y) for x, y in reversed(can[1:])]                    # cab-forward teardrop, long tapering tail
        D('canopy', canopy, 'top', m=M['glass'], off=0.006, step=0.015)
        for sg in (1, -1):
            D(f'blade{sg}', [(4.52, sg * 0.36), (4.60, sg * 0.36), (4.42, sg * 0.86), (4.34, sg * 0.84)], 'top', m=M['black'], off=0.006, step=0.01)
            D(f'drl{sg}', [(4.55, sg * 0.40), (4.58, sg * 0.40), (4.42, sg * 0.80), (4.39, sg * 0.79)], 'top', m=M['light'], off=0.009, step=0.008)
            but = B.path_pts([(1.40, sg * 0.30), (0.90, sg * 0.50), (0.40, sg * 0.70), (0.12, sg * 0.80)], 60)
            B.tube(f'buttress{sg}', top_pts(bvh, but, 0.006), 0.010, M['black'], car)
            D(f'scoop{sg}', [(2.05, sg * 0.80), (2.55, sg * 0.86), (2.50, sg * 0.90), (2.0, sg * 0.86)], 'top', m=M['black'], off=0.006, step=0.01)
        D('duct', [(3.95, -0.22), (4.30, -0.16), (4.30, 0.16), (3.95, 0.22)], 'top', m=M['black'], off=0.006)
        D('lightbar', [(0.02, -0.90), (0.09, -0.92), (0.09, 0.92), (0.02, 0.90)], 'top', m=acc, off=0.009, step=0.01)
        B.plate('splitter', [(4.50, -0.88), (4.68, -0.72), (4.78, -0.40), (4.80, 0.0), (4.78, 0.40), (4.68, 0.72), (4.50, 0.88)], 0.10, 0.12, M['black'], car)


def main():
    key, out = sys.argv[1], sys.argv[2]
    originalise()
    B.features = features
    car, bodyo, wheels, f, mats = B.build(key)
    # clay look: white body, light glass, accent only on its own parts
    for name, col, rough in (('body', (0.93, 0.93, 0.92, 1), 0.42), ('body2', (0.85, 0.85, 0.84, 1), 0.45),
                             ('glass', (0.30, 0.34, 0.40, 1), 0.05), ('black', (0.16, 0.16, 0.17, 1), 0.5),
                             ('tyre', (0.20, 0.20, 0.21, 1), 0.8)):
        b = bpy.data.materials[name].node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = col; b.inputs['Roughness'].default_value = rough
    sc = bpy.context.scene; L = B.SPEC[key]['L']
    w, h = (CAR_W + 2 * PAD) * 2, (CAR_L + 2 * PAD) * 2
    B.setup_render(sc, w, h)
    sc.render.film_transparent = True; sc.cycles.samples = 48; sc.render.line_thickness = 2.2
    sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.9
    camd = bpy.data.cameras.new('cam'); camd.type = 'ORTHO'; camd.sensor_fit = 'VERTICAL'
    camd.ortho_scale = L * (CAR_L + 2 * PAD) / CAR_L
    cam = bpy.data.objects.new('cam', camd); sc.collection.objects.link(cam); sc.camera = cam
    cam.location = (L / 2, 0, 12); cam.rotation_euler = (0, 0, -math.pi / 2)    # nose up the frame
    bpy.ops.mesh.primitive_plane_add(size=30, location=(L / 2, 0, 0)); fl = bpy.context.object; fl.is_shadow_catcher = True
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 3.0; sun.angle = math.radians(14)
    so = bpy.data.objects.new('sun', sun); sc.collection.objects.link(so); so.rotation_euler = (math.radians(14), math.radians(-10), 0)
    fill = bpy.data.lights.new('fill', 'AREA'); fill.energy = 400; fill.size = 8
    fo = bpy.data.objects.new('fill', fill); sc.collection.objects.link(fo); fo.location = (L / 2 + 2, 2.5, 6)
    fo.rotation_euler = (Vector((L / 2, 0, 0)) - fo.location).to_track_quat('-Z', 'Y').to_euler()
    ls = sc.view_layers[0].freestyle_settings.linesets[0]                       # no ink on the shadow catcher
    col = bpy.data.collections.new('nolines'); sc.collection.children.link(col)
    for c in fl.users_collection: c.objects.unlink(fl)
    col.objects.link(fl)
    ls.select_by_collection = True; ls.collection = col; ls.collection_negation = 'EXCLUSIVE'
    sc.render.filepath = out
    bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    main()
