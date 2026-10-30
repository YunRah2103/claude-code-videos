import bpy, bmesh, math, os
from mathutils import Vector

# =====================================================================
#  QWEN 27B — PREMIUM 20" PERFORMANCE ALLOY WHEEL  (Blender 5.2)
#  Z = vertical, Y = axle, X = horizontal.  Front faces +Y.  Floor z=0.
# =====================================================================

# ---------- reset ----------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.lights,
             bpy.data.cameras, bpy.data.worlds):
    for d in list(coll):
        if d.users == 0:
            coll.remove(d)

# ---------- dimensions ----------
CY        = 0.38      # wheel centre height (tyre outer radius)
R_TYRE    = 0.38
R_RIM     = 0.25
TYRE_W    = 0.22
N_SPOKE   = 10
N_LUG     = 5
N_HOLE    = 24

# ---------- helpers ----------
def link(o):
    bpy.context.collection.objects.link(o)
    return o

def new_obj(name, mesh):
    return link(bpy.data.objects.new(name, mesh))

def smooth(o, auto=True):
    for p in o.data.polygons:
        p.use_smooth = auto
    if auto:
        try:
            o.data.use_auto_smooth = True
            o.data.auto_smooth_angle = math.radians(35)
        except Exception:
            pass

def mat(name, base, metallic=0.0, rough=0.5, coat=0.0, cr=0.03, spec=0.5):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*base, 1)
    b.inputs['Metallic'].default_value = metallic
    b.inputs['Roughness'].default_value = rough
    if 'Specular IOR Level' in b.inputs:
        b.inputs['Specular IOR Level'].default_value = spec
    if coat:
        b.inputs['Coat Weight'].default_value = coat
        b.inputs['Coat Roughness'].default_value = cr
    return m

mat_tyre   = mat('Tyre',   (0.030,0.030,0.032), 0.0, 0.88)
mat_rim    = mat('Rim',    (0.22,0.23,0.25), 1.0, 0.34)
mat_mach   = mat('Machined',(0.62,0.63,0.66), 1.0, 0.18)
mat_dark   = mat('Dark',   (0.045,0.045,0.05), 0.6, 0.45)
mat_disc   = mat('Disc',   (0.52,0.53,0.55), 1.0, 0.30)
mat_cal    = mat('Caliper',(0.55,0.03,0.03), 0.0, 0.32, 1.0)

# ---------- revolved tyre (custom profile, axis -> Y) ----------
def build_tyre():
    # (radius, circumferential position) profile in the XZ plane
    prof = [
        (0.115, 0.000), (0.140, 0.010), (0.165, 0.025), (0.185, 0.045),
        (0.205, 0.070), (0.225, 0.100), (0.245, 0.140), (0.262, 0.185),
        (0.278, 0.230), (0.288, 0.270), (0.293, 0.305), (0.291, 0.335),
        (0.282, 0.360), (0.266, 0.375), (0.245, 0.380), (0.220, 0.380),
        (0.195, 0.380), (0.170, 0.380), (0.148, 0.380), (0.130, 0.380),
        (0.115, 0.378), (0.100, 0.370), (0.090, 0.355), (0.082, 0.335),
        (0.076, 0.310), (0.072, 0.280), (0.070, 0.250), (0.068, 0.220),
        (0.066, 0.190), (0.065, 0.160), (0.064, 0.130), (0.063, 0.100),
        (0.062, 0.070), (0.062, 0.040), (0.062, 0.020), (0.062, 0.000),
    ]
    nseg = 128
    bm = bmesh.new()
    rings = []
    for r, c in prof:
        ring = []
        for i in range(nseg):
            a = i * 2*math.pi/nseg
            ring.append(bm.verts.new((r*math.cos(a), c, r*math.sin(a))))
        rings.append(ring)
    for j in range(len(prof)-1):
        for i in range(nseg):
            i2 = (i+1) % nseg
            bm.faces.new((rings[j][i], rings[j][i2], rings[j+1][i2], rings[j+1][i]))
    # small circumferential tread grooves: thin dark rings on the tread
    for g in (0.30, 0.345):
        for i in range(nseg):
            a  = i*2*math.pi/nseg
            a2 = (i+1)*2*math.pi/nseg
            r1, r2 = 0.378, 0.381
            v1 = bm.verts.new((r1*math.cos(a),  g,      r1*math.sin(a)))
            v2 = bm.verts.new((r1*math.cos(a2), g,      r1*math.sin(a2)))
            v3 = bm.verts.new((r2*math.cos(a2), g+0.012, r2*math.sin(a2)))
            v4 = bm.verts.new((r2*math.cos(a),  g+0.012, r2*math.sin(a)))
            bm.faces.new((v1, v2, v3, v4))
    m = bpy.data.meshes.new('Tyre')
    bm.to_mesh(m); bm.free()
    o = new_obj('Tyre', m)
    o.location = (0, 0, CY)
    o.data.materials.append(mat_tyre)
    smooth(o)
    return o

# ---------- revolved rim barrel (open centre, axis -> Y) ----------
def build_barrel():
    # outer wall -> lip -> inner wall (front to back), in XZ plane
    prof = [
        (0.250, 0.075), (0.250, 0.020), (0.248, -0.030),
        (0.240, -0.075), (0.228, -0.100), (0.210, -0.110),
        (0.190, -0.105), (0.175, -0.090), (0.165, -0.060),
        (0.160, -0.020), (0.160, 0.020),
    ]
    nseg = 96
    bm = bmesh.new()
    rings = []
    for r, c in prof:
        ring = [bm.verts.new((r*math.cos(i*2*math.pi/nseg), c,
                              r*math.sin(i*2*math.pi/nseg))) for i in range(nseg)]
        rings.append(ring)
    for j in range(len(prof)-1):
        for i in range(nseg):
            i2 = (i+1) % nseg
            bm.faces.new((rings[j][i], rings[j][i2], rings[j+1][i2], rings[j+1][i]))
    m = bpy.data.meshes.new('Barrel')
    bm.to_mesh(m); bm.free()
    o = new_obj('Barrel', m)
    o.location = (0, 0, CY)
    o.data.materials.append(mat_rim)
    smooth(o)
    return o

# ---------- sculpted double-spoke (custom mesh, axis -> Y) ----------
def build_spoke():
    """One V double-spoke assembly (two arms) in the XZ plane, extruded along Y.
       Arms run from the hub (r~0.07) out to the rim (r~0.25)."""
    arm = [   # (radius, angle offset from radial axis)
        (0.070, 0.000), (0.100, 0.010), (0.135, 0.020), (0.170, 0.028),
        (0.200, 0.030), (0.225, 0.028), (0.245, 0.020), (0.250, 0.005),
        (0.250, -0.005), (0.245, -0.020), (0.225, -0.028), (0.200, -0.030),
        (0.170, -0.028), (0.135, -0.020), (0.100, -0.010), (0.070, 0.000),
    ]
    def arm_pts(sign):
        pts = []
        for r, off in arm:
            a = sign*off
            pts.append((r*math.cos(a), r*math.sin(a)))
        return pts
    a1 = arm_pts(+1)
    a2 = arm_pts(-1)
    # merge the shared hub ends into one continuous profile
    prof = a1[:-1] + a2[1:]
    y0, y1 = 0.030, -0.055          # front face to back (concave sweep)
    ymid   = -0.010
    bm = bmesh.new()
    # build three cross-sections (front, mid, back) for a sculpted profile
    def section(y, scale, lift):
        vs = []
        for x, z in prof:
            r = math.hypot(x, z)
            if r < 1e-6:
                vs.append(bm.verts.new((0, y, 0)))
                continue
            a = math.atan2(z, x)
            nr = r*scale
            nz = lift
            vs.append(bm.verts.new((nr*math.cos(a), y, nr*math.sin(a)+nz)))
        return vs
    s_f = section(y0,   1.00,  0.000)
    s_m = section(ymid, 0.90,  0.010)
    s_b = section(y1,   0.78,  0.022)
    n = len(prof)
    for i in range(n):
        i2 = (i+1) % n
        bm.faces.new((s_f[i], s_f[i2], s_m[i2], s_m[i]))
        bm.faces.new((s_m[i], s_m[i2], s_b[i2], s_b[i]))
    # cap front and back
    bm.faces.new(s_f)
    bm.faces.new(list(reversed(s_b)))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    m = bpy.data.meshes.new('Spoke')
    bm.to_mesh(m); bm.free()
    return m

def place_spokes(spoke_mesh):
    for i in range(N_SPOKE):
        a = i * 2*math.pi/N_SPOKE
        o = new_obj(f'Spoke{i}', spoke_mesh.copy())
        o.location = (0, 0, CY)
        o.rotation_euler = (0, 0, a)      # rotate about Y (axle)
        o.data.materials.append(mat_rim)
        # machined silver accent strip on the front face of each arm
        smooth(o)

# ---------- hub, lugs, centre cap ----------
def build_hub():
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=False, segments=48,
                           radius1=0.085, radius2=0.085, depth=0.10)
    m = bpy.data.meshes.new('Hub'); bm.to_mesh(m); bm.free()
    o = new_obj('Hub', m)
    o.location = (0, 0.01, CY)
    o.rotation_euler = (0, math.radians(90), 0)   # axis -> Y
    o.data.materials.append(mat_rim)
    smooth(o)
    # centre cap (front, +Y)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=48,
                           radius1=0.055, radius2=0.050, depth=0.025)
    m = bpy.data.meshes.new('Cap'); bm.to_mesh(m); bm.free()
    c = new_obj('CentreCap', m)
    c.location = (0, 0.09, CY)
    c.rotation_euler = (0, math.radians(90), 0)
    c.data.materials.append(mat_mach)
    smooth(c)
    # five lug bolts
    for i in range(N_LUG):
        a = i*2*math.pi/N_LUG + 2*math.pi/N_LUG/2
        bm = bmesh.new()
        bmesh.ops.create_cone(bm, cap_ends=True, segments=6,
                               radius1=0.014, radius2=0.014, depth=0.04)
        m = bpy.data.meshes.new(f'Lug{i}'); bm.to_mesh(m); bm.free()
        n = new_obj(f'Lug{i}', m)
        n.location = (0.062*math.cos(a), 0.10, CY + 0.062*math.sin(a))
        n.rotation_euler = (0, math.radians(90), 0)
        n.data.materials.append(mat_dark)

# ---------- brake rotor with real drilled holes ----------
def build_rotor():
    nseg = 96
    r0, r1 = 0.075, 0.190
    y0, y1 = -0.115, -0.100
    bm = bmesh.new()
    front, back = [], []
    for i in range(nseg):
        a = i*2*math.pi/nseg
        front.append(bm.verts.new((r1*math.cos(a), y0, r1*math.sin(a))))
        back.append(bm.verts.new((r0*math.cos(a), y1, r0*math.sin(a))))
    # annulus faces (front ring to back ring)
    for i in range(nseg):
        i2 = (i+1) % nseg
        bm.faces.new((front[i], front[i2], back[i2], back[i]))
    # outer rim strip
    for i in range(nseg):
        i2 = (i+1) % nseg
        v1 = bm.verts.new((r1*math.cos(i*2*math.pi/nseg), y1, r1*math.sin(i*2*math.pi/nseg)))
        v2 = bm.verts.new((r1*math.cos(i2*2*math.pi/nseg), y1, r1*math.sin(i2*2*math.pi/nseg)))
        bm.faces.new((front[i], front[i2], v2, v1))
    # drilled holes: boolean-free — punch by deleting front faces near hole centres
    hole_r = 0.135
    holes = []
    for i in range(N_HOLE):
        a = i*2*math.pi/N_HOLE
        holes.append((hole_r*math.cos(a), hole_r*math.sin(a)))
    for f in list(bm.faces):
        c = f.calc_center_median()
        for hx, hz in holes:
            if math.hypot(c.x-hx, c.z-hz) < 0.012 and abs(c.y - y0) < 1e-4:
                bm.faces.remove(f)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    m = bpy.data.meshes.new('Rotor'); bm.to_mesh(m); bm.free()
    o = new_obj('Rotor', m)
    o.location = (0, 0, CY)
    o.data.materials.append(mat_disc)
    smooth(o)
    # hat (dome behind hub)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=48,
                           radius1=0.080, radius2=0.060, depth=0.035)
    m = bpy.data.meshes.new('Hat'); bm.to_mesh(m); bm.free()
    h = new_obj('Hat', m)
    h.location = (0, -0.085, CY)
    h.rotation_euler = (0, math.radians(90), 0)
    h.data.materials.append(mat_dark)
    smooth(h)

# ---------- red caliper (curved housing) ----------
def build_caliper():
    nseg = 24
    rr = 0.205
    y0, y1 = -0.075, -0.125
    z0, z1 = 0.10, 0.24
    bm = bmesh.new()
    rows = []
    for y in (y0, y1):
        row = []
        for i in range(nseg):
            a = (i/(nseg-1)) * math.radians(60) - math.radians(30)
            row.append(bm.verts.new((rr*math.sin(a), y, rr*math.cos(a))))
        rows.append(row)
    for i in range(nseg - 1):
        bm.faces.new((rows[0][i], rows[0][i+1], rows[1][i+1], rows[1][i]))
    m = bpy.data.meshes.new("Caliper")
    bm.to_mesh(m); bm.free()
    c = new_obj("Caliper", m)
    c.location = (0, 0, CY)
    c.data.materials.append(mat_cal)
    return c

# ======================================================================
# EXECUTION COMPLETION BY GPT-6: The Qwen source ended mid-expression.
# This tail solely calls Qwen's geometry builders and sets presentation.
# No Qwen mesh profile or geometry algorithms are redesigned.
# ======================================================================
build_tyre()
build_barrel()
place_spokes(build_spoke())
build_hub()
build_rotor()
build_caliper()

# A simple studio, required because source cuts off before creating any.
bpy.ops.mesh.primitive_plane_add(size=4, location=(0, 0, -0.005))
floor = bpy.context.active_object
floor.name = "RenderFloor (completion)"
floor.data.materials.append(mat("RenderFloor", (0.025, 0.028, 0.034), 0, 0.72))
world = bpy.data.worlds.new("StudioWorld (completion)")
bpy.context.scene.world = world
world.use_nodes = True
world.node_tree.nodes["Background"].inputs[0].default_value = (0.04,0.045,0.055,1)
world.node_tree.nodes["Background"].inputs[1].default_value = 0.4

def add_area(name, position, power, size):
    bpy.ops.object.light_add(type="AREA", location=position)
    lamp = bpy.context.active_object
    lamp.name = name
    lamp.data.energy = power
    lamp.data.shape = "DISK"
    lamp.data.size = size
    direction = Vector((0, 0, CY)) - lamp.location
    lamp.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()

add_area("Studio key (completion)", (1.5, 1.8, 2.2), 520, 2.5)
add_area("Studio fill (completion)", (-1.5, 1.6, 0.95), 330, 2.5)
add_area("Studio backlight (completion)", (0.4, -1.5, 1.6), 400, 1.6)

camdata=bpy.data.cameras.new("Wheel camera")
cam=bpy.data.objects.new("Wheel camera",camdata)
bpy.context.collection.objects.link(cam)
bpy.context.scene.camera=cam
camdata.type="ORTHO"
camdata.ortho_scale=1.28
target=Vector((0,0,CY))
cam.location=Vector((0.54, 1.5, 0.68))
cam.rotation_euler=(target-cam.location).to_track_quat("-Z","Y").to_euler()

scene=bpy.context.scene
scene.render.engine="BLENDER_EEVEE"
scene.render.resolution_x=1280
scene.render.resolution_y=720
scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"
scene.render.film_transparent=False
scene.render.filepath="/tmp/qwen_detailed_original.png"
scene.view_settings.view_transform="Standard"
scene.view_settings.look="Medium High Contrast"
scene.camera.data.lens=45

out=os.environ.get("OUTPUT_DIR", "/tmp/qwen-result")
os.makedirs(out,exist_ok=True)
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out,"qwen_detailed_wheel.blend"))
scene.render.filepath=os.path.join(out,"qwen_detailed_preview.png")
bpy.ops.render.render(write_still=True)

# Camera-only sequence: frame motion, not geometry or materials changes.
scene.render.resolution_x=640
scene.render.resolution_y=360
scene.render.resolution_percentage=100
# Keep turntable angle small so geometry remains visible as designed.
N=16
for i in range(N):
    a=2*math.pi*i/N
    cam.location=Vector((0.68*math.sin(a), 1.65, CY+0.25+0.05*math.cos(a)))
    cam.rotation_euler=(target-cam.location).to_track_quat("-Z","Y").to_euler()
    scene.render.filepath=os.path.join(out,"frames",f"frame_{i:03d}.png")
    os.makedirs(os.path.dirname(scene.render.filepath),exist_ok=True)
    bpy.ops.render.render(write_still=True)
print("DONE QWEN DETAILED ORIGINAL, ONLY TAIL COMPLETION AND CAMERA")
