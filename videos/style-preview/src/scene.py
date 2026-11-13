"""Blender (Cycles CPU) scenes for the style preview.

blender -b -P scene.py -- STYLE OUTDIR [--draft] [--start S] [--end E] [--step K]
STYLE: 1 light tunnel, 2 tilt-shift, 4 cutaway, mesh (wireframe edges json), sprite (car PNG).
Writes OUTDIR/####.png (+ mask_####.png, depth_####.png) and OUTDIR/anchors.json.
The car is procedural (no model download, no logos)."""
import bpy, bmesh, sys, os, json, math, random
from mathutils import Vector, Matrix
from bpy_extras.object_utils import world_to_camera_view
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import beat

argv = sys.argv[sys.argv.index('--') + 1:]
STYLE, OUT = argv[0], argv[1]
DRAFT = '--draft' in argv
def opt(name, d):
    return int(argv[argv.index(name) + 1]) if name in argv else d
os.makedirs(OUT, exist_ok=True)

# ---------------------------------------------------------------- helpers
def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def mat(name, col, rough=0.4, metal=0.0, emit=None, estr=0.0, coat=0.0, alpha=1.0, trans=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1)
    b.inputs['Roughness'].default_value = rough
    b.inputs['Metallic'].default_value = metal
    b.inputs['Coat Weight'].default_value = coat
    b.inputs['Transmission Weight'].default_value = trans
    if emit:
        b.inputs['Emission Color'].default_value = (*emit, 1)
        b.inputs['Emission Strength'].default_value = estr
    return m

def link(ob):
    bpy.context.scene.collection.objects.link(ob); return ob

def prism(name, prof, y0, y1, m):
    """Extrude an (x,z) profile between y0 and y1 (closed solid)."""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    a = [bm.verts.new((x, y0, z)) for x, z in prof]
    b = [bm.verts.new((x, y1, z)) for x, z in prof]
    bm.faces.new(a[::-1]); bm.faces.new(b)
    n = len(prof)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new((a[i], a[j], b[j], b[i]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me); bm.free()
    ob = link(bpy.data.objects.new(name, me)); ob.data.materials.append(m)
    return ob

def box(name, c, s, m, parent=None):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0); bm.to_mesh(me); bm.free()
    ob = link(bpy.data.objects.new(name, me)); ob.location = c; ob.scale = s
    ob.data.materials.append(m); ob.parent = parent; return ob

def cyl(name, c, r, depth, m, axis='Y', seg=48, parent=None):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r, radius2=r, depth=depth)
    bm.to_mesh(me); bm.free()
    ob = link(bpy.data.objects.new(name, me)); ob.location = c
    if axis == 'Y': ob.rotation_euler = (math.pi / 2, 0, 0)
    if axis == 'X': ob.rotation_euler = (0, math.pi / 2, 0)
    for p in me.polygons: p.use_smooth = True
    ob.data.materials.append(m); ob.parent = parent; return ob

def smooth(ob, angle=40):
    for p in ob.data.polygons: p.use_smooth = True
    bpy.context.view_layer.objects.active = ob
    try:
        bpy.ops.object.shade_smooth_by_angle(angle=math.radians(angle))
    except Exception:
        pass

def bevel(ob, w, seg):
    md = ob.modifiers.new('bev', 'BEVEL'); md.width = w; md.segments = seg
    md.limit_method = 'ANGLE'; md.angle_limit = math.radians(25); md.harden_normals = False
    return md

# ---------------------------------------------------------------- the car
BODY = [(-2.30, 0.24), (-2.40, 0.40), (-2.36, 0.56), (-2.12, 0.66), (-1.40, 0.76),
        (-0.90, 0.84), (1.70, 0.88), (2.22, 0.84), (2.36, 0.70), (2.38, 0.44), (2.26, 0.24)]
CABIN = [(-1.05, 0.80), (-0.15, 1.30), (0.80, 1.31), (1.95, 0.86)]
WR, WX, WZ, WW = 0.36, 1.45, 0.36, 1.62     # wheel radius, axle x, axle z, track

def build_car(paint, glass, cut=None, interior=False, shell=False, lights=True):
    root = link(bpy.data.objects.new('car', None))
    body = prism('body', BODY, -0.93, 0.93, paint); body.parent = root
    bevel(body, 0.16, 6)
    cab = prism('cabin', CABIN, -0.74, 0.74, glass); cab.parent = root
    # taper the greenhouse: roof narrower than its base
    for v in cab.data.vertices:
        k = (v.co.z - 0.80) / 0.51
        v.co.y *= 1.0 - 0.18 * max(k, 0)
    bevel(cab, 0.12, 5)
    for ob in (body, cab):
        smooth(ob)
        if shell:
            sd = ob.modifiers.new('sh', 'SOLIDIFY'); sd.thickness = 0.05; sd.offset = -1
    for sx in (-WX, WX):        # wheel arches
        c = cyl('arch', (sx, 0, WZ), WR + 0.07, 2.4, paint, seg=40)
        c.hide_render = True; c.display_type = 'WIRE'
        md = body.modifiers.new('arch', 'BOOLEAN'); md.object = c; md.solver = 'EXACT'
    if cut:
        for ob in (body, cab):
            md = ob.modifiers.new('cut', 'BOOLEAN'); md.object = cut; md.solver = 'EXACT'
            md.material_mode = 'TRANSFER'
    tyre = mat('tyre', (0.025, 0.025, 0.028), rough=0.65)
    rim = mat('rim', (0.75, 0.76, 0.78), rough=0.25, metal=1.0)
    wheels = []
    for sx in (-WX, WX):
        for sy in (-WW / 2, WW / 2):
            hub = link(bpy.data.objects.new('wheel', None)); hub.parent = root
            hub.location = (sx, sy, WZ); wheels.append(hub)
            t = cyl('tyre', (0, 0, 0), WR, 0.26, tyre, parent=hub)
            md = t.modifiers.new('b', 'BEVEL'); md.width = 0.06; md.segments = 4
            side = -1 if sy < 0 else 1
            cyl('disc', (0, side * 0.11, 0), WR * 0.68, 0.06, rim, parent=hub)
            for k in range(5):      # spokes so the rotation reads
                a = k * 2 * math.pi / 5
                sp = box('spoke', (math.cos(a) * 0.14, side * 0.145, math.sin(a) * 0.14),
                         (0.26, 0.02, 0.05), rim, parent=hub)
                sp.rotation_euler = (0, -a, 0)
            cyl('cap', (0, side * 0.15, 0), 0.05, 0.02, rim, parent=hub)
    if lights:
        hl = mat('head', (1, 1, 1), emit=(0.85, 0.95, 1.0), estr=8)
        tl = mat('tail', (0.6, 0.02, 0.02), emit=(1.0, 0.05, 0.03), estr=6)
        box('headL', (-2.27, 0, 0.60), (0.12, 1.55, 0.035), hl, parent=root)
        box('tailL', (2.31, 0, 0.74), (0.10, 1.65, 0.04), tl, parent=root)
    if interior:
        cell = mat('cell', (0.05, 0.55, 0.6), rough=0.35)
        cell2 = mat('cell2', (0.02, 0.32, 0.36), rough=0.4)
        for i in range(8):
            for j in range(5):
                box('cell', (-1.12 + i * 0.32, -0.62 + j * 0.31, 0.29),
                    (0.29, 0.28, 0.12), cell if (i + j) % 2 == 0 else cell2, parent=root)
        box('tray', (0.0, 0, 0.215), (2.7, 1.62, 0.04), mat('tray', (0.15, 0.15, 0.17), 0.5, 0.6), parent=root)
        eng = mat('engine', (0.32, 0.33, 0.36), rough=0.35, metal=0.8)
        box('motor', (-1.75, 0, 0.47), (0.55, 0.62, 0.36), eng, parent=root)
        cyl('motor_drum', (-1.75, 0, 0.47), 0.2, 1.05, eng, parent=root)
        cyl('inverter', (-1.72, 0, 0.72), 0.15, 0.45, mat('inv', (0.9, 0.55, 0.05), 0.4), axis='X', parent=root)
        orange = mat('hv', (1.0, 0.38, 0.02), 0.45)
        cyl('cable', (-1.3, -0.25, 0.42), 0.035, 0.75, orange, axis='X', parent=root)
        cyl('cable2', (-1.3, 0.25, 0.42), 0.035, 0.75, orange, axis='X', parent=root)
        seat = mat('seat', (0.08, 0.08, 0.1), 0.7)
        for sx, sy in ((-0.35, -0.4), (-0.35, 0.4), (0.75, -0.4), (0.75, 0.4)):
            box('seat_b', (sx, sy, 0.48), (0.5, 0.48, 0.12), seat, parent=root)
            sb = box('seat_r', (sx + 0.25, sy, 0.8), (0.1, 0.46, 0.6), seat, parent=root)
            sb.rotation_euler = (0, -0.2, 0)
        sw = cyl('wheelS', (-0.75, -0.4, 0.85), 0.17, 0.04, seat, axis='X', parent=root)
        sw.rotation_euler = (0, math.pi / 2 - 0.5, 0)
    return root, wheels, body

# ---------------------------------------------------------------- scene setup
def setup_render(samples, w=1080, h=1920, blur=False, transparent=False, passes=True):
    s = bpy.context.scene
    s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'
    s.cycles.samples = samples; s.cycles.use_adaptive_sampling = True
    s.cycles.adaptive_threshold = 0.04; s.cycles.use_denoising = True
    s.cycles.denoiser = 'OPENIMAGEDENOISE'
    s.cycles.max_bounces = 4; s.cycles.diffuse_bounces = 2; s.cycles.glossy_bounces = 2
    s.cycles.transmission_bounces = 2; s.cycles.transparent_max_bounces = 4
    sc = 0.6667 if DRAFT else 1.0
    s.render.resolution_x, s.render.resolution_y = int(w * sc), int(h * sc)
    s.render.resolution_percentage = 100
    s.render.fps = beat.FPS
    s.render.use_motion_blur = blur; s.render.motion_blur_shutter = 0.5
    s.render.film_transparent = transparent
    s.render.image_settings.file_format = 'PNG'
    s.render.image_settings.color_mode = 'RGBA' if transparent else 'RGB'
    s.view_settings.view_transform = 'AgX'; s.view_settings.look = 'AgX - Medium High Contrast'
    if not passes:
        return
    vl = bpy.context.view_layer
    vl.use_pass_object_index = True; vl.use_pass_z = True
    s.use_nodes = True; nt = s.node_tree; nt.nodes.clear()
    rl = nt.nodes.new('CompositorNodeRLayers')
    comp = nt.nodes.new('CompositorNodeComposite')
    nt.links.new(rl.outputs['Image'], comp.inputs['Image'])
    idm = nt.nodes.new('CompositorNodeIDMask'); idm.index = 1; idm.use_antialiasing = True
    nt.links.new(rl.outputs['IndexOB'], idm.inputs['ID value'])
    mr = nt.nodes.new('CompositorNodeMapRange')
    mr.inputs['From Min'].default_value = 2.0; mr.inputs['From Max'].default_value = 40.0
    mr.inputs['To Min'].default_value = 0.0; mr.inputs['To Max'].default_value = 1.0
    mr.use_clamp = True
    nt.links.new(rl.outputs['Depth'], mr.inputs['Value'])
    fo = nt.nodes.new('CompositorNodeOutputFile'); fo.base_path = OUT
    fo.format.file_format = 'PNG'; fo.format.color_mode = 'BW'; fo.format.color_depth = '16'
    fo.file_slots.clear(); fo.file_slots.new('mask_'); fo.file_slots.new('depth_')
    nt.links.new(idm.outputs['Alpha'], fo.inputs['mask_'])
    nt.links.new(mr.outputs['Value'], fo.inputs['depth_'])
    s.view_settings.view_transform = 'AgX'

def tag_index(root):
    for ob in bpy.context.scene.objects:
        p = ob
        while p is not None and p is not root:
            p = p.parent
        if p is root:
            ob.pass_index = 1

def camera(loc, target, lens=40, shift_y=0.0):
    cd = bpy.data.cameras.new('cam'); cd.lens = lens; cd.shift_y = shift_y
    cd.sensor_fit = 'VERTICAL'; cd.sensor_height = 24
    cam = link(bpy.data.objects.new('cam', cd)); bpy.context.scene.camera = cam
    aim(cam, loc, target); return cam

def aim(cam, loc, target):
    cam.location = loc
    d = Vector(target) - Vector(loc)
    cam.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler()

def area(name, loc, target, size, energy, col=(1, 1, 1), sy=None):
    ld = bpy.data.lights.new(name, 'AREA'); ld.energy = energy; ld.color = col
    ld.shape = 'RECTANGLE'; ld.size = size; ld.size_y = sy or size
    ob = link(bpy.data.objects.new(name, ld)); aim(ob, loc, target); return ob

def world(col, strength=1.0):
    w = bpy.data.worlds.new('w'); w.use_nodes = True
    bg = w.node_tree.nodes['Background']
    bg.inputs['Color'].default_value = (*col, 1); bg.inputs['Strength'].default_value = strength
    bpy.context.scene.world = w

def anchors_for(cam, pts):
    s = bpy.context.scene
    W, H = s.render.resolution_x, s.render.resolution_y
    out = {}
    for k, ob_or_v in pts.items():
        v = ob_or_v.matrix_world.translation if hasattr(ob_or_v, 'matrix_world') else Vector(ob_or_v)
        c = world_to_camera_view(s, cam, v)
        out[k] = [c.x * 1080, (1 - c.y) * 1920]
    return out

# ---------------------------------------------------------------- styles
def style1():
    world((0, 0, 0))
    floor = mat('floor', (0.003, 0.003, 0.004), rough=0.32)
    floor.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value = 0.25
    fl = box('floor', (0, 0, -0.05), (200, 200, 0.1), floor)
    paint = mat('paint', (0.012, 0.013, 0.016), rough=0.22, metal=0.5, coat=1.0)
    glass = mat('glass', (0.0, 0.0, 0.0), rough=0.05, coat=1.0)
    root, wheels, body = build_car(paint, glass)
    tag_index(root)
    # strip softboxes above (long highlights) + rim lights behind
    area('top', (0.3, -0.6, 4.2), (0.3, 0, 0), 0.35, 900, (0.92, 0.97, 1.0), sy=6.0)
    area('rimB', (0.0, 5.0, 1.6), (0, 0, 0.7), 6.0, 2600, (0.75, 0.92, 1.0), sy=0.6)
    area('rimF', (-5.0, 1.5, 1.0), (0, 0, 0.6), 2.0, 900, (0.6, 0.9, 1.0))
    area('kick', (3.5, -3.0, 0.4), (0, 0, 0.5), 1.0, 160, (1, 1, 1))
    # light linking: the studio lights only touch the car, so the floor stays black (reflections only)
    col = bpy.data.collections.new('carcol')
    for ob in bpy.context.scene.objects:
        if ob.pass_index == 1:
            col.objects.link(ob)
    for ob in bpy.context.scene.objects:
        if ob.type == 'LIGHT':
            ob.light_linking.receiver_collection = col
    # car sits left of centre so the wake has room behind it
    cam = camera((-1.0, -19.0, 1.9), (0.9, 0, 0.75), lens=34, shift_y=0.16)
    return dict(root=root, wheels=wheels, cam=cam, blur=True, samples=20,
                move=lambda t: aim(cam, (-1.0 + 0.3 * t, -19.0 + 0.3 * t, 1.9 + 0.04 * t), (0.9, 0, 0.75)))

def style2():
    world((0.55, 0.72, 0.95), 0.9)
    wood = bpy.data.materials.new('wood'); wood.use_nodes = True
    nt = wood.node_tree; b = nt.nodes['Principled BSDF']
    wv = nt.nodes.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 1.2
    wv.inputs['Distortion'].default_value = 6; wv.inputs['Detail'].default_value = 4
    cr = nt.nodes.new('ShaderNodeValToRGB')
    cr.color_ramp.elements[0].color = (0.32, 0.16, 0.06, 1); cr.color_ramp.elements[1].color = (0.62, 0.36, 0.16, 1)
    nt.links.new(wv.outputs['Fac'], cr.inputs['Fac']); nt.links.new(cr.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.45
    box('table', (0, 0, -0.3), (80, 80, 0.4), wood)
    grass = mat('grass', (0.18, 0.62, 0.12), rough=0.85)
    road = mat('road', (0.16, 0.16, 0.19), rough=0.8)
    paintl = mat('lines', (1.0, 0.95, 0.85), rough=0.6)
    box('board', (0, 0, -0.06), (60, 12, 0.12), grass)
    box('road', (0, 0, 0.005), (60, 3.2, 0.02), road)
    for i in range(-30, 31):
        box('dash', (i * 2.0, 0, 0.02), (1.0, 0.12, 0.012), paintl)
    random.seed(3)
    leaf = [mat('l%d' % i, c, rough=0.6) for i, c in enumerate(
        [(0.05, 0.55, 0.12), (0.35, 0.75, 0.08), (0.02, 0.4, 0.2), (0.95, 0.55, 0.05)])]
    trunk = mat('trunk', (0.35, 0.18, 0.06), 0.7)
    roofs = [mat('r%d' % i, c, 0.5) for i, c in enumerate([(0.9, 0.12, 0.1), (0.1, 0.35, 0.9), (0.95, 0.75, 0.05)])]
    walls = mat('wall', (0.97, 0.94, 0.86), 0.6)
    for i in range(70):
        x = random.uniform(-28, 28); y = random.choice((-1, 1)) * random.uniform(2.6, 5.5)
        if random.random() < 0.8:
            h = random.uniform(0.9, 1.8)
            cyl('trunk', (x, y, h * 0.25), 0.08, h * 0.5, trunk, axis='Z', seg=8)
            me = bpy.data.meshes.new('cone'); bm = bmesh.new()
            bmesh.ops.create_cone(bm, cap_ends=True, segments=10, radius1=0.5 * h / 1.3, radius2=0.0, depth=h)
            bm.to_mesh(me); bm.free()
            o = link(bpy.data.objects.new('tree', me)); o.location = (x, y, h * 0.9)
            o.data.materials.append(random.choice(leaf))
        else:
            box('house', (x, y, 0.45), (1.2, 1.0, 0.9), walls)
            me = bpy.data.meshes.new('roof'); bm = bmesh.new()
            bmesh.ops.create_cone(bm, cap_ends=True, segments=4, radius1=0.95, radius2=0.0, depth=0.6)
            bm.to_mesh(me); bm.free()
            o = link(bpy.data.objects.new('roof', me)); o.location = (x, y, 1.2)
            o.rotation_euler = (0, 0, math.pi / 4); o.data.materials.append(random.choice(roofs))
    paint = mat('toy', (0.95, 0.12, 0.05), rough=0.28, coat=0.6)
    glass = mat('glass', (0.02, 0.05, 0.08), rough=0.08, coat=1.0)
    root, wheels, body = build_car(paint, glass)
    tag_index(root)
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 4.0; sun.angle = math.radians(6)
    sun.color = (1.0, 0.93, 0.8)
    so = link(bpy.data.objects.new('sun', sun)); so.rotation_euler = (math.radians(45), 0, math.radians(-35))
    cam = camera((0, -9, 9), (0, 0, 0.5), lens=40)
    def move(t):
        x = -6.0 + 2.2 * (t * 1.0 + 0.22 * t * t)   # car slowly accelerates along the road
        root.location = (x, -0.75, 0)
        aim(cam, (x - 9.0, -13.5, 13.5), (x + 0.6, -0.5, 0.4))
    return dict(root=root, wheels=wheels, cam=cam, blur=False, samples=24, move=move, rolling=True)

def style4():
    world((0.78, 0.8, 0.84), 0.55)
    floor = mat('floor', (0.8, 0.81, 0.84), rough=0.55)
    box('floor', (0, 0, -0.05), (200, 200, 0.1), floor)
    cutm = mat('cutface', (1.0, 0.32, 0.04), rough=0.5)
    cutter = box('cutter', (0, -1.25, 1.62), (6.0, 2.5, 2.7), cutm)   # removes the near half above the sills
    cutter.hide_render = True; cutter.display_type = 'WIRE'
    clay = mat('clay', (0.86, 0.87, 0.9), rough=0.45, coat=0.3)
    root, wheels, body = build_car(clay, clay, cut=cutter, interior=True, shell=True)
    cutter.parent = root
    tag_index(root)
    area('key', (-4, -6, 6), (0, 0, 0.6), 4.0, 1500, (1, 0.97, 0.92))
    area('fill', (6, -4, 3), (0, 0, 0.6), 4.0, 500, (0.85, 0.9, 1.0))
    area('top', (0, 0, 6), (0, 0, 0), 3.0, 600)
    area('rim', (1, 6, 3), (0, 0, 0.6), 4.0, 900)
    cam = camera((-5.0, -11.0, 3.4), (-0.15, 0, 0.55), lens=36, shift_y=0.1)
    def move(t):
        a = math.radians(-30 + 4.5 * t)
        r = 14.0 - 0.2 * t
        aim(cam, (r * math.sin(a), -r * math.cos(a), 3.6 - 0.1 * t), (-1.0, 0, 0.5))
    pts = {}
    return dict(root=root, wheels=wheels, cam=cam, blur=True, samples=20, move=move,
                extra={'battery': (0.0, -0.62, 0.35), 'motor': (-1.75, -0.3, 0.6),
                       'cut_top': (0.3, 0.0, 1.31)})

def export_mesh():
    paint = mat('p', (1, 1, 1)); root, wheels, body = build_car(paint, paint, lights=False)
    for ob in bpy.data.objects:
        for md in ob.modifiers:
            if md.type == 'BEVEL':
                md.segments = 2
    dg = bpy.context.evaluated_depsgraph_get()
    out = {'body': [], 'wheels': []}
    for ob in list(bpy.context.scene.objects):
        if ob.type != 'MESH' or ob.hide_render or ob.name.startswith('arch'):
            continue
        ev = ob.evaluated_get(dg); me = ev.to_mesh()
        mw = ob.matrix_world
        vs = [list(mw @ v.co) for v in me.vertices]
        es = [list(e.vertices) for e in me.edges]
        out['wheels' if ob.parent and ob.parent.name.startswith('wheel') else 'body'].append(
            {'name': ob.name, 'v': [[round(c, 4) for c in v] for v in vs], 'e': es,
             'hub': list(ob.parent.matrix_world.translation) if ob.parent else None})
        ev.to_mesh_clear()
    json.dump(out, open(os.path.join(OUT, 'car_mesh.json'), 'w'))
    print('MESH', sum(len(o['e']) for k in out for o in out[k]), 'edges')

def sprite():
    world((0.12, 0.13, 0.16), 1.0)
    paint = mat('paint', (0.9, 0.9, 0.92), rough=0.25, metal=0.3, coat=1.0)
    glass = mat('glass', (0.01, 0.01, 0.015), rough=0.05, coat=1.0)
    root, wheels, body = build_car(paint, glass)
    area('key', (-2, -6, 5), (0, 0, 0.6), 4, 900)
    area('rim', (0, 6, 2), (0, 0, 0.6), 6, 1500, (0.8, 0.9, 1))
    camera((0, -30, 1.0), (0, 0, 0.75), lens=100)
    setup_render(32, 1400, 500, transparent=True, passes=False)
    s = bpy.context.scene; s.render.resolution_x, s.render.resolution_y = 1400, 500
    s.render.filepath = os.path.join(OUT, 'car_sprite.png')
    bpy.ops.render.render(write_still=True)

# ---------------------------------------------------------------- main
reset()
if STYLE == 'mesh':
    export_mesh(); sys.exit(0)
if STYLE == 'sprite':
    sprite(); sys.exit(0)
cfg = {'1': style1, '2': style2, '4': style4}[STYLE]()
setup_render(opt('--samples', cfg['samples']), blur=cfg['blur'])
s = bpy.context.scene
start, end, step = opt('--start', 0), opt('--end', beat.N), opt('--step', 1)
fps = beat.FPS
anch_path = os.path.join(OUT, 'anchors.json')
anchors = json.load(open(anch_path)) if os.path.exists(anch_path) else {}
import time
frames = range(start, end, step)
if STYLE == '2':   # stop-motion: only the 12 fps frames are rendered, post holds them
    frames = [i for i in sorted({int(k * 2.5) for k in range(48)}) if start <= i < end]
for i in frames:
    t = i / fps
    s.frame_set(i + 1)
    cfg['move'](t)
    if cfg.get('rolling'):
        ang = (cfg['root'].location.x + 6.0) / WR
    else:
        ang = beat.wheel_angle(i)
    for w in cfg['wheels']:
        w.rotation_euler = (0, ang, 0)
        w.keyframe_insert('rotation_euler', frame=i + 1)
        # for motion blur: also key the next frame's angle
        nxt = beat.wheel_angle(i + 1) if not cfg.get('rolling') else ang
        w.rotation_euler = (0, nxt, 0); w.keyframe_insert('rotation_euler', frame=i + 2)
        w.rotation_euler = (0, ang, 0)
    cam = cfg['cam']
    cam.keyframe_insert('location', frame=i + 1); cam.keyframe_insert('rotation_euler', frame=i + 1)
    s.frame_set(i + 1)
    bpy.context.view_layer.update()
    pts = {'front': (-2.40, -0.93, 0.45), 'rear': (2.38, -0.93, 0.5), 'roof': (0.3, 0, 1.31),
           'center': (0, 0, 0.6), 'ground_front': (-2.3, -0.93, 0.0), 'ground_rear': (2.3, -0.93, 0.0)}
    pts.update(cfg.get('extra', {}))
    mw = cfg['root'].matrix_world
    pts = {k: mw @ Vector(v) for k, v in pts.items()}
    anchors[str(i)] = anchors_for(cam, pts)
    s.render.filepath = os.path.join(OUT, '%04d.png' % i)
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    print('FRAME', i, 'sec', round(time.time() - t0, 2), flush=True)
    json.dump(anchors, open(anch_path, 'w'))
