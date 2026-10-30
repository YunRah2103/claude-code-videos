import bpy, math, bmesh, os
from mathutils import Vector

# ---------- scene reset ----------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights, bpy.data.cameras):
    for d in coll:
        if d.users == 0:
            coll.remove(d)

# ---------- helpers ----------
def new_obj(name, mesh):
    o = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(o)
    return o

def mat(name, base, metallic=0.0, rough=0.5, coat=0.0, clearcoat_rough=0.03):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*base, 1)
    b.inputs['Metallic'].default_value = metallic
    b.inputs['Roughness'].default_value = rough
    b.inputs['Coat Weight'].default_value = coat
    if coat:
        b.inputs['Coat Roughness'].default_value = clearcoat_rough
    return m

mat_tyre   = mat('Tyre',   (0.028,0.028,0.03), 0, 0.92)
mat_rim    = mat('Rim',    (0.28,0.29,0.31), 1.0, 0.28)
mat_dark   = mat('Dark',   (0.05,0.05,0.055), 0.4, 0.5)
mat_disc   = mat('Disc',   (0.55,0.56,0.58), 1.0, 0.35)
mat_cal    = mat('Caliper',(0.55,0.03,0.03), 0.0, 0.35, 1.0)

# wheel axle = Y axis; wheel centre height so the tyre touches the floor at z=0
CY = 0.40   # outer tyre radius (major 0.30 + minor 0.10)

# ---------- tyre (torus, axis -> Y) ----------
bpy.ops.mesh.primitive_torus_add(major_radius=0.30, minor_radius=0.10,
                                  major_segments=96, minor_segments=24,
                                  location=(0, 0, CY))
tyre = bpy.context.active_object
tyre.name = 'Tyre'
tyre.rotation_euler = (math.radians(90), 0, 0)
tyre.data.materials.append(mat_tyre)

# ---------- rim barrel (open-ended, no caps) ----------
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=False, segments=96,
                       radius1=0.215, radius2=0.215, depth=0.16)
m = bpy.data.meshes.new('Barrel'); bm.to_mesh(m); bm.free()
barrel = new_obj('Barrel', m)
barrel.location = (0, 0, CY)
barrel.rotation_euler = (0, math.radians(90), 0)
barrel.data.materials.append(mat_rim)

# ---------- spokes: radial geometry from hub to rim ----------
spoke_mesh = bpy.data.meshes.new('Spoke')
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=16,
                       radius1=0.045, radius2=0.022, depth=0.145)
bm.to_mesh(spoke_mesh); bm.free()
for i in range(10):
    a = i * (2*math.pi/10)
    s = new_obj(f'Spoke{i}', spoke_mesh.copy())
    s.location = (0.135*math.cos(a), 0, CY + 0.135*math.sin(a))
    s.rotation_euler = (0, math.radians(90), a)   # length radial, axis -> Y
    s.data.materials.append(mat_rim)

# ---------- hub (open-ended) ----------
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=False, segments=48,
                       radius1=0.075, radius2=0.075, depth=0.10)
m = bpy.data.meshes.new('Hub'); bm.to_mesh(m); bm.free()
hub = new_obj('Hub', m)
hub.location = (0, 0.02, CY)
hub.rotation_euler = (0, math.radians(90), 0)
hub.data.materials.append(mat_rim)

# hub cap (front face, +Y)
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=48,
                       radius1=0.055, radius2=0.055, depth=0.02)
m = bpy.data.meshes.new('HubCap'); bm.to_mesh(m); bm.free()
cap = new_obj('HubCap', m)
cap.location = (0, 0.09, CY)
cap.rotation_euler = (0, math.radians(90), 0)
cap.data.materials.append(mat_dark)

# five lug nuts
for i in range(5):
    a = i * (2*math.pi/5)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=6,
                           radius1=0.016, radius2=0.016, depth=0.035)
    m = bpy.data.meshes.new(f'Lug{i}'); bm.to_mesh(m); bm.free()
    n = new_obj(f'Lug{i}', m)
    n.location = (0.055*math.cos(a), 0.095, CY + 0.055*math.sin(a))
    n.rotation_euler = (0, math.radians(90), 0)
    n.data.materials.append(mat_dark)

# ---------- brake disc ----------
bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=96,
                       radius1=0.155, radius2=0.155, depth=0.018)
m = bpy.data.meshes.new('Disc'); bm.to_mesh(m); bm.free()
disc = new_obj('Disc', m)
disc.location = (0, -0.10, CY)
disc.rotation_euler = (0, math.radians(90), 0)
disc.data.materials.append(mat_disc)

bm = bmesh.new()
bmesh.ops.create_cone(bm, cap_ends=True, segments=48,
                       radius1=0.075, radius2=0.075, depth=0.03)
m = bpy.data.meshes.new('Hat'); bm.to_mesh(m); bm.free()
hat = new_obj('Hat', m)
hat.location = (0, -0.09, CY)
hat.rotation_euler = (0, math.radians(90), 0)
hat.data.materials.append(mat_dark)

# drilled holes
for i in range(24):
    a = i * (2*math.pi/24)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=6,
                           radius1=0.006, radius2=0.006, depth=0.03)
    m = bpy.data.meshes.new(f'Hole{i}'); bm.to_mesh(m); bm.free()
    h = new_obj(f'Hole{i}', m)
    h.location = (0.115*math.cos(a), -0.10, CY + 0.115*math.sin(a))
    h.rotation_euler = (0, math.radians(90), 0)
    h.data.materials.append(mat_dark)

# ---------- caliper ----------
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0)
for v in bm.verts:
    v.co.x *= 0.14; v.co.y *= 0.05; v.co.z *= 0.16
m = bpy.data.meshes.new('Caliper'); bm.to_mesh(m); bm.free()
cal = new_obj('Caliper', m)
cal.location = (0, -0.10, CY + 0.16)
cal.rotation_euler = (0, math.radians(90), math.radians(35))
cal.data.materials.append(mat_cal)

# ---------- studio: floor + backdrop ----------
bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=4)
m = bpy.data.meshes.new('Floor'); bm.to_mesh(m); bm.free()
fl = new_obj('Floor', m)
fl.data.materials.append(mat('Floor', (0.02,0.02,0.022), 0, 0.6))

bm = bmesh.new()
bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=4)
m = bpy.data.meshes.new('Backdrop'); bm.to_mesh(m); bm.free()
bd = new_obj('Backdrop', m)
bd.rotation_euler = (math.radians(90), 0, 0)
bd.location = (0, -3.5, CY)
bd.data.materials.append(mat('Backdrop', (0.015,0.015,0.018), 0, 0.8))

# ---------- lights ----------
def area(name, loc, rot, size, power):
    d = bpy.data.lights.new(name, 'AREA')
    d.size = size; d.energy = power
    o = bpy.data.objects.new(name, d)
    bpy.context.collection.objects.link(o)
    o.location = loc; o.rotation_euler = rot
    return o
area('Key',  (2.0, 2.2, CY + 1.8), (math.radians(50), 0, math.radians(135)), 2.5, 420)
area('Fill', (-2.4, 2.0, CY + 1.2), (math.radians(55), 0, math.radians(-140)), 3.0, 180)
area('Rim',  (0.2, -2.6, CY + 1.4), (math.radians(60), 0, math.radians(175)), 2.0, 120)

# ---------- camera: three-quarter view, aimed at wheel centre ----------
cam = bpy.data.cameras.new('Camera')
cam.lens = 50
camo = bpy.data.objects.new('Camera', cam)
bpy.context.collection.objects.link(camo)
camo.location = (1.55, 1.85, CY + 0.22)
target = Vector((0, 0, CY))
camo.rotation_euler = (target - camo.location).to_track_quat('-Z', 'Y').to_euler()

# ---------- world ----------
w = bpy.data.worlds.new('Studio'); bpy.context.scene.world = w
w.use_nodes = True
w.node_tree.nodes['Background'].inputs[0].default_value = (0.012,0.012,0.015,1)
w.node_tree.nodes['Background'].inputs[1].default_value = 1.0

# ---------- render settings ----------
sc = bpy.context.scene
try:
    sc.render.engine = 'BLENDER_EEVEE_NEXT'
except Exception:
    sc.render.engine = 'BLENDER_EEVEE'
try:
    sc.eevee.taa_render_samples = 64
    sc.eevee.use_gtao = True
except Exception:
    pass
sc.render.resolution_x = 1280
sc.render.resolution_y = 720
sc.render.resolution_percentage = 100
sc.render.image_settings.file_format = 'PNG'
sc.camera = camo

# ---------- save + render (Windows user folder) ----------
home = os.path.expanduser("~")
blend_path = os.path.join(home, "wheel_test.blend")
png_path   = os.path.join(home, "wheel_preview.png")
bpy.ops.wm.save_as_mainfile(filepath=blend_path)
sc.render.filepath = png_path
bpy.ops.render.render(write_still=True)
print('DONE')
