"""v3 3D race: both v1 cars (with the v3 front opening + side line) on one minimal track, low chase camera.

Reuses blend_cars.py (body loft, wheels, decals, materials, Freestyle ink setup). The ground is one static plane
whose shader scrolls each lane by its own car's distance (Values 'sr' / 'sb'), so a stopped car's lane stops while
the other keeps moving. Track: pale ground, fine grid, thin lane lines, red/blue kerbs, a hatched brake zone
(Value 'bz'), fading to white towards the horizon.
usage: out/bpyenv/bin/python blend_race.py STATES.json OUTDIR [i0 i1] | still STATES.json OUTDIR i [i ...]
"""
import json, math, sys
from pathlib import Path
import bpy
from mathutils import Vector, Matrix

sys.path.insert(0, str(Path(__file__).resolve().parent))
import blend_cars as B  # noqa: E402

B.V3 = True
LANE_Y = {'chiron': 1.16, 'nevera': -1.16}                   # red left, blue right (camera looks along +x)
KEY = {'red': 'chiron', 'blue': 'nevera'}


def build_scene(w=1080, h=1920):
    B.reset(); real_reset = B.reset; B.reset = lambda: None
    cars = {}
    for key in ('chiron', 'nevera'):
        car, bodyo, wheels, f, mats = B.build(key)
        for hub in wheels: hub.parent.parent = car                # wheel roots ride with the car
        brakes = [B.brake_material(mats['dark']), B.brake_material(mats['caliper'])]
        for name, col, em in (('tail', (0.75, 0.03, 0.02, 1), 2.5), ('mesh', (0.05, 0.05, 0.055, 1), 0.0)):
            b = mats[name].node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = col
            b.inputs['Emission Color'].default_value = col; b.inputs['Emission Strength'].default_value = em
        cars[key] = dict(car=car, wheels=wheels, brakes=brakes, L=B.SPEC[key]['L'], axles=B.SPEC[key]['axles'],
                         R=B.SPEC[key]['R'][0])
    B.reset = real_reset
    sc = bpy.context.scene; B.setup_render(sc, w, h); B.white_world(sc)
    sc.world.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.45
    sc.render.line_thickness = 1.6
    fm, vals = track_material()
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0, 0, 0)); fl = bpy.context.object
    fl.scale = (3000, 400, 1); bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    fl.location = (1200, 0, 0); bpy.ops.object.transform_apply(location=True, rotation=False, scale=False)
    fl.data.materials.append(fm); fl.visible_shadow = False
    col = bpy.data.collections.new('nolines'); sc.collection.children.link(col)
    for c in fl.users_collection: c.objects.unlink(fl)
    col.objects.link(fl)
    ls = sc.view_layers[0].freestyle_settings.linesets[0]
    ls.select_by_collection = True; ls.collection = col; ls.collection_negation = 'EXCLUSIVE'
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 1.5; sun.angle = math.radians(8)
    so = bpy.data.objects.new('sun', sun); sc.collection.objects.link(so)
    so.rotation_euler = Vector((-0.45, 0.25, -1)).to_track_quat('-Z', 'Y').to_euler()
    camd = bpy.data.cameras.new('cam'); camd.sensor_fit = 'HORIZONTAL'; camd.angle = math.radians(33)
    cam = bpy.data.objects.new('cam', camd); sc.collection.objects.link(cam); sc.camera = cam
    camd.clip_end = 2500; camd.shift_y = 0.16                       # cars sit low, clear of the text band
    return dict(sc=sc, cars=cars, cam=cam, vals=vals)


def track_material():
    m = bpy.data.materials.new('track'); m.use_nodes = True; nt = m.node_tree; N = nt.nodes
    bsdf = N['Principled BSDF']; bsdf.inputs['Roughness'].default_value = 0.9; bsdf.inputs['Emission Strength'].default_value = 0.10
    tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Object'], sep.inputs[0])
    V = {}
    for k in ('sr', 'sb', 'bz', 'u0r', 'u0b'):
        n = N.new('ShaderNodeValue'); n.name = k; V[k] = n

    def M(op, a, b=None, c=None):
        n = N.new('ShaderNodeMath'); n.operation = op
        for i, v in enumerate((a, b, c)):
            if v is None: continue
            if isinstance(v, (int, float)): n.inputs[i].default_value = v
            else: nt.links.new(v, n.inputs[i])
        return n.outputs[0]

    def mix(f, a, b, col=None):
        n = N.new('ShaderNodeMix'); n.data_type = 'RGBA'; nt.links.new(f, n.inputs[0])
        for i, v in ((6, a), (7, b)):
            if isinstance(v, tuple): n.inputs[i].default_value = v
            else: nt.links.new(v, n.inputs[i])
        return n.outputs[2]

    def SS(v, e0, e1):
        mr = N.new('ShaderNodeMapRange'); mr.interpolation_type = 'SMOOTHSTEP'; nt.links.new(v, mr.inputs['Value'])
        mr.inputs['From Min'].default_value = e0; mr.inputs['From Max'].default_value = e1
        return mr.outputs['Result']

    X, Y = sep.outputs['X'], sep.outputs['Y']; aY = M('ABSOLUTE', Y)
    left = M('GREATER_THAN', Y, 0.0)
    pick = lambda a, b: M('ADD', b, M('MULTIPLY', left, M('SUBTRACT', a, b)))   # left lane (red) -> a
    u = M('ADD', X, pick(V['sr'].outputs[0], V['sb'].outputs[0]))

    def ln(q, period, w):
        d = M('MULTIPLY', M('ABSOLUTE', M('SUBTRACT', M('FRACT', M('ADD', M('DIVIDE', q, period), 0.5)), 0.5)), period)
        return M('LESS_THAN', d, w)
    grid = M('MAXIMUM', M('MULTIPLY', M('MAXIMUM', ln(u, 1.0, 0.012), ln(Y, 1.0, 0.012)), 0.35),
             M('MULTIPLY', M('MAXIMUM', ln(u, 5.0, 0.022), ln(Y, 5.0, 0.022)), 0.7))
    edge = M('LESS_THAN', M('ABSOLUTE', M('SUBTRACT', aY, 2.62)), 0.035)
    centre = M('MULTIPLY', M('LESS_THAN', aY, 0.07), M('LESS_THAN', M('FRACT', M('DIVIDE', u, 6.0)), 0.5))
    kerb = M('MULTIPLY', M('GREATER_THAN', aY, 2.66), M('LESS_THAN', aY, 3.05))
    kstripe = M('MULTIPLY', kerb, M('LESS_THAN', M('FRACT', M('DIVIDE', u, 2.4)), 0.5))
    u0 = pick(V['u0r'].outputs[0], V['u0b'].outputs[0]); du = M('SUBTRACT', u, u0)
    zone = M('MULTIPLY', M('MULTIPLY', M('GREATER_THAN', du, 0.0), M('LESS_THAN', du, 22.0)), M('LESS_THAN', aY, 2.4))
    hatch = M('MULTIPLY', zone, M('LESS_THAN', M('FRACT', M('DIVIDE', M('ADD', du, M('MULTIPLY', aY, 0.9)), 1.6)), 0.42))
    zband = M('MULTIPLY', zone, M('MAXIMUM', M('LESS_THAN', du, 0.25), M('GREATER_THAN', du, 21.75)))
    zmark = M('MULTIPLY', M('MAXIMUM', M('MULTIPLY', hatch, 0.55), zband), V['bz'].outputs[0])
    c = mix(grid, (0.80, 0.82, 0.85, 1), (0.40, 0.50, 0.70, 1))
    kcol = mix(left, (0.12, 0.30, 0.86, 1), (0.85, 0.12, 0.08, 1))
    c = mix(kerb, c, (1, 1, 1, 1)); c = mix(kstripe, c, kcol)
    c = mix(M('MAXIMUM', edge, centre), c, (0.08, 0.08, 0.09, 1))
    c = mix(zmark, c, (0.95, 0.42, 0.06, 1))
    du0 = M('SUBTRACT', u, -1.0)                                                 # chequered start line just behind the cars
    sl = M('MULTIPLY', M('MULTIPLY', M('GREATER_THAN', du0, 0.0), M('LESS_THAN', du0, 0.6)), M('LESS_THAN', aY, 2.6))
    chk = M('MODULO', M('ADD', M('FLOOR', M('DIVIDE', du0, 0.3)), M('FLOOR', M('DIVIDE', M('ADD', Y, 3.0), 0.3))), 2.0)
    c = mix(M('MULTIPLY', sl, chk), mix(sl, c, (1, 1, 1, 1)), (0.06, 0.06, 0.07, 1))
    cd = N.new('ShaderNodeCameraData'); far = SS(cd.outputs['View Distance'], 35.0, 260.0)
    c = mix(far, c, (1, 1, 1, 1))
    nt.links.new(c, bsdf.inputs['Base Color']); nt.links.new(c, bsdf.inputs['Emission Color'])
    return m, V


def key_frame(S, st, fr):
    for tag, key in KEY.items():
        C = S['cars'][key]; car = C['car']; L = C['L']; xm = 0.5 * sum(C['axles'])
        a = math.radians(st['p' + tag[0]]); piv = Vector((xm, 0, 0.35)); R = Matrix.Rotation(a, 4, 'Y')
        car.rotation_euler = (0, a, 0)
        car.location = piv - (R @ piv) + Vector((st['x' + tag[0]], LANE_Y[key], 0))
        car.keyframe_insert('location', frame=fr); car.keyframe_insert('rotation_euler', frame=fr)
        for h in C['wheels']:
            h.rotation_euler = (0, st['s' + tag[0]] / C['R'], 0); h.keyframe_insert('rotation_euler', frame=fr)
        for v in C['brakes']:
            v.outputs[0].default_value = st['h' + tag[0]]; v.outputs[0].keyframe_insert('default_value', frame=fr)
    for k in ('sr', 'sb', 'bz', 'u0r', 'u0b'):
        n = S['vals'][k]; n.outputs[0].default_value = st[k]; n.outputs[0].keyframe_insert('default_value', frame=fr)
    xc = 0.5 * (st['xr'] + st['xb']) + 2.35                          # orbit around the pair of cars
    yr, er, d = math.radians(st['yaw']), math.radians(st['el']), st['cd']
    tgt = Vector((xc, 0, 0.55))
    eye = tgt + d * Vector((-math.cos(yr) * math.cos(er), math.sin(yr) * math.cos(er), math.sin(er)))
    cam = S['cam']
    cam.location = eye; cam.rotation_euler = (tgt - eye).to_track_quat('-Z', 'Y').to_euler()
    cam.keyframe_insert('location', frame=fr); cam.keyframe_insert('rotation_euler', frame=fr)


def run(states, outdir, frames):
    st = json.load(open(states)); S = build_scene(); sc = S['sc']
    for i, x in enumerate(st): key_frame(S, x, i + 1)
    for ob in list(bpy.data.objects) + list(bpy.data.materials):
        ad = getattr(ob, 'animation_data', None) or (ob.node_tree.animation_data if getattr(ob, 'node_tree', None) else None)
        if ad and ad.action:
            for fc in ad.action.fcurves:
                for kp in fc.keyframe_points: kp.interpolation = 'LINEAR'
    sc.render.threads_mode = 'AUTO'
    out = Path(outdir); out.mkdir(parents=True, exist_ok=True)
    for i in frames:
        p = out / f'f_{i:04d}.png'
        if p.exists(): continue
        sc.frame_set(i + 1); sc.render.filepath = str(p)
        bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'still':
        run(a[1], a[2], [int(x) for x in a[3:]])
    else:
        n = len(json.load(open(a[0])))
        run(a[0], a[1], range(int(a[2]) if len(a) > 2 else 0, int(a[3]) if len(a) > 3 else n))
