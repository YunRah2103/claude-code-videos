# wheel.py - procedural BMW-style bronze multi-spoke alloy wheel (Blender 4.0)
# Fixed copy of the Qwen design: placeholders and invalid lines replaced.
# Run:  WHEEL_ONE=1 blender -b -P wheel.py      (one test frame)
#       blender -b -P wheel.py                  (full turntable frames)
import bpy, bmesh, math, os

OUT = os.environ.get("WHEEL_OUT", "/home/user/claude-code-videos/out/wheel")
FRAMES = int(os.environ.get("WHEEL_FRAMES", "60"))
RES = int(os.environ.get("WHEEL_RES", "480"))
SAMPLES = int(os.environ.get("WHEEL_SAMPLES", "32"))
ONE = os.environ.get("WHEEL_ONE", "") == "1"


# ---------- material helpers ----------
def set_input(node, names, value):
    if isinstance(names, str):
        names = [names]
    for n in names:
        if n in node.inputs:
            node.inputs[n].default_value = value
            return
    raise KeyError(f"{node.name}: none of {names} found")


def make_principled(name, color, metallic=0.0, roughness=0.5, coat=None, sheen=None):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links   # Blender 4.x: nodes live on node_tree
    nodes.clear()
    out = nodes.new("ShaderNodeOutputMaterial"); out.location = (400, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled"); bsdf.location = (100, 0)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    set_input(bsdf, "Base Color", color)
    set_input(bsdf, "Metallic", metallic)
    set_input(bsdf, "Roughness", roughness)
    if coat is not None:
        set_input(bsdf, "Coat Weight", coat)
    if sheen is not None:
        set_input(bsdf, "Sheen Weight", sheen)
    return mat, nodes, links, bsdf


def material_bronze():
    mat, nodes, links, bsdf = make_principled("Bronze_Alloy", (0.62, 0.38, 0.14, 1.0), metallic=1.0)
    tex = nodes.new("ShaderNodeTexNoise"); tex.location = (-350, -100)
    tex.inputs["Scale"].default_value = 90.0
    tex.inputs["Detail"].default_value = 3.0
    mr = nodes.new("ShaderNodeMapRange"); mr.location = (-120, -100)
    mr.inputs["From Min"].default_value = 0.35
    mr.inputs["From Max"].default_value = 0.65
    mr.inputs["To Min"].default_value = 0.18
    mr.inputs["To Max"].default_value = 0.42
    links.new(tex.outputs["Fac"], mr.inputs["Value"])
    links.new(mr.outputs["Result"], bsdf.inputs["Roughness"])
    return mat


def material_tire():
    mat, nodes, links, bsdf = make_principled("Tire_Rubber", (0.018, 0.018, 0.02, 1.0), roughness=0.6)
    set_input(bsdf, "Sheen Weight", 0.12)
    tc = nodes.new("ShaderNodeTexCoord"); tc.location = (-700, 0)
    mapping = nodes.new("ShaderNodeMapping"); mapping.location = (-520, -150)
    mapping.inputs["Rotation"].default_value = (math.pi / 2, 0, 0)
    wave = nodes.new("ShaderNodeTexWave"); wave.location = (-220, -150)
    wave.inputs["Scale"].default_value = 60.0
    wave.inputs["Distortion"].default_value = 0.0
    wave.wave_type = "BANDS"
    bump = nodes.new("ShaderNodeBump"); bump.location = (0, -200)
    bump.inputs["Strength"].default_value = 0.08
    links.new(tc.outputs["Object"], mapping.inputs["Vector"])
    links.new(mapping.outputs["Vector"], wave.inputs["Vector"])
    links.new(wave.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


def material_disc():
    mat, nodes, links, bsdf = make_principled("Brake_Disc", (0.27, 0.27, 0.29, 1.0), metallic=0.9, roughness=0.4)
    tc = nodes.new("ShaderNodeTexCoord"); tc.location = (-700, 0)
    sep = nodes.new("ShaderNodeSeparateXYZ"); sep.location = (-520, 0)
    atan = nodes.new("ShaderNodeMath"); atan.operation = "ARCTAN2"; atan.location = (-340, 0)
    mul = nodes.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.location = (-160, 0)
    mul.inputs[1].default_value = 900.0
    sin = nodes.new("ShaderNodeMath"); sin.operation = "SINE"; sin.location = (-20, 0)
    bump = nodes.new("ShaderNodeBump"); bump.location = (80, -150)
    bump.inputs["Strength"].default_value = 0.06
    links.new(tc.outputs["Object"], sep.inputs[0])
    links.new(sep.outputs["Y"], atan.inputs[0])      # atan2(y, x)
    links.new(sep.outputs["X"], atan.inputs[1])
    links.new(atan.outputs[0], mul.inputs[0])
    links.new(mul.outputs[0], sin.inputs[0])
    links.new(sin.outputs[0], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], bsdf.inputs["Normal"])
    return mat


# ---------- geometry helpers ----------
def obj_from_bmesh(name, bm, material=None):
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    mesh = bpy.data.meshes.new(name)
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    if material is not None:
        obj.data.materials.append(material)
    return obj


def revolve(bm, profile, segments=96, closed=False):
    """Revolve an (r, z) profile around the Z axis."""
    n = len(profile)
    rings = []
    for i in range(segments):
        a = 2 * math.pi * i / segments
        ca, sa = math.cos(a), math.sin(a)
        rings.append([bm.verts.new((r * ca, r * sa, z)) for r, z in profile])
    for i in range(segments):
        ra, rb = rings[i], rings[(i + 1) % segments]
        for j in range(n if closed else n - 1):
            k = (j + 1) % n
            bm.faces.new((ra[j], ra[k], rb[k], rb[j]))


def loft_spoke(bm, base_angle, twist0, twist1, bow, r0, r1, w0, w1, h0, h1, steps=26, sec=24):
    """Spoke from hub (r0) to rim (r1): superellipse (n=4) cross-section along a bent path."""
    rings = []
    for i in range(steps + 1):
        t = i / steps
        r = r0 + (r1 - r0) * t
        ang = base_angle + twist0 + (twist1 - twist0) * t + bow * math.sin(math.pi * t)
        ca, sa = math.cos(ang), math.sin(ang)
        cx, cy = r * ca, r * sa
        tx, ty = -sa, ca                       # tangent (across the spoke width)
        w = w0 + (w1 - w0) * t
        h = h0 + (h1 - h0) * t
        ring = []
        for j in range(sec):
            phi = 2 * math.pi * j / sec
            c, s = math.cos(phi), math.sin(phi)
            px = math.copysign(abs(c) ** 0.5, c)   # 2/n with n=4
            pz = math.copysign(abs(s) ** 0.5, s)
            ring.append(bm.verts.new((cx + tx * 0.5 * w * px, cy + ty * 0.5 * w * px, 0.5 * h * pz)))
        rings.append(ring)
    for i in range(steps):
        ra, rb = rings[i], rings[i + 1]
        for j in range(sec):
            k = (j + 1) % sec
            bm.faces.new((ra[j], ra[k], rb[k], rb[j]))
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])


def build_pie_prism(bm, radius, a0, a1, z, th, steps=16):
    c0 = bm.verts.new((0, 0, z))
    c1 = bm.verts.new((0, 0, z + th))
    r0, r1 = [], []
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * i / steps
        x, y = radius * math.cos(a), radius * math.sin(a)
        r0.append(bm.verts.new((x, y, z)))
        r1.append(bm.verts.new((x, y, z + th)))
    for i in range(steps):
        bm.faces.new((c0, r0[i + 1], r0[i]))                   # bottom fan
        bm.faces.new((c1, r1[i], r1[i + 1]))                   # top fan
        bm.faces.new((r0[i], r0[i + 1], r1[i + 1], r1[i]))     # arc side
    bm.faces.new((c0, r0[0], r1[0], c1))                       # flat radial side
    bm.faces.new((c0, c1, r1[-1], r0[-1]))                     # flat radial side


def add_cylinder(location, radius, depth, verts=6):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=radius, depth=depth, location=location)
    return bpy.context.active_object


def add_box(location, size, rot_z, material):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    ob = bpy.context.active_object
    ob.scale = size
    ob.rotation_euler.z = rot_z
    ob.data.materials.append(material)
    return ob


# ---------- scene ----------
def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def setup_scene():
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = SAMPLES
    scene.cycles.use_denoising = False
    scene.render.resolution_x = RES
    scene.render.resolution_y = RES
    scene.render.image_settings.file_format = "PNG"

    scene.world = bpy.data.worlds.new("World")
    scene.world.use_nodes = True
    bg = scene.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.08, 0.08, 0.09, 1.0)
    bg.inputs[1].default_value = 1.0

    cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
    scene.collection.objects.link(cam)
    cam.location = (0.0, -0.9, 1.6)
    direction = -cam.location
    cam.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam

    sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN"))
    sun.data.energy = 1.2
    sun.rotation_euler = (0.6, 0.2, 0.4)
    scene.collection.objects.link(sun)

    fill = bpy.data.objects.new("Fill", bpy.data.lights.new("Fill", "AREA"))
    fill.data.energy = 40.0
    fill.data.size = 1.5
    fill.location = (0.5, -0.5, 0.8)
    scene.collection.objects.link(fill)


def build_wheel():
    mats = {
        "bronze": material_bronze(),
        "dark": make_principled("Dark_Bronze", (0.30, 0.17, 0.07, 1.0), metallic=1.0, roughness=0.48)[0],
        "tire": material_tire(),
        "steel": make_principled("Steel_Lug", (0.42, 0.42, 0.45, 1.0), metallic=1.0, roughness=0.3)[0],
        "disc": material_disc(),
        "red": make_principled("Caliper_Red", (0.55, 0.02, 0.03, 1.0), roughness=0.16, coat=0.6)[0],
        "blue": make_principled("BMW_Blue", (0.02, 0.12, 0.6, 1.0), metallic=0.0, roughness=0.25)[0],
    }
    parts = []

    # rim barrel (open profile, lip at the top and bottom)
    bm = bmesh.new()
    revolve(bm, [(0.26, -0.04), (0.27, -0.03), (0.275, 0.0), (0.27, 0.03), (0.26, 0.04)], 96)
    parts.append(obj_from_bmesh("Rim", bm, mats["bronze"]))

    # hub (closed rectangle)
    bm = bmesh.new()
    revolve(bm, [(0.04, -0.05), (0.10, -0.05), (0.10, 0.05), (0.04, 0.05)], 64, closed=True)
    parts.append(obj_from_bmesh("Hub", bm, mats["bronze"]))

    # five bent spokes
    bm = bmesh.new()
    for k in range(5):
        loft_spoke(bm, base_angle=2 * math.pi * k / 5, twist0=0.0, twist1=0.35, bow=0.25,
                   r0=0.07, r1=0.265, w0=0.035, w1=0.05, h0=0.03, h1=0.045)
    parts.append(obj_from_bmesh("Spokes", bm, mats["dark"]))

    # tyre: closed circular profile revolved around the wheel axis
    bm = bmesh.new()
    prof = []
    for i in range(24):
        t = 2 * math.pi * i / 24
        prof.append((0.36 + 0.09 * math.cos(t), 0.07 * math.sin(t)))
    revolve(bm, prof, 128, closed=True)
    parts.append(obj_from_bmesh("Tire", bm, mats["tire"]))

    # blue quadrant pieces on the hub face
    bm = bmesh.new()
    for q in range(4):
        a0 = q * math.pi / 2 + 0.08
        build_pie_prism(bm, 0.095, a0, a0 + math.pi / 2 - 0.16, 0.05, 0.015)
    parts.append(obj_from_bmesh("BlueQuadrants", bm, mats["blue"]))

    # brake disc behind the wheel, with a red caliper on its edge
    bm = bmesh.new()
    revolve(bm, [(0.09, -0.012), (0.19, -0.012), (0.19, 0.012), (0.09, 0.012)], 96, closed=True)
    disc = obj_from_bmesh("BrakeDisc", bm, mats["disc"])
    disc.location.z = -0.12
    parts.append(disc)
    caliper = add_box((0.19 * math.cos(0.8), 0.19 * math.sin(0.8), -0.12),
                      (0.07, 0.035, 0.05), 0.8, mats["red"])
    parts.append(caliper)

    # five steel lug nuts
    for k in range(5):
        a = 2 * math.pi * k / 5 + math.pi / 5
        lug = add_cylinder((0.05 * math.cos(a), 0.05 * math.sin(a), 0.07), 0.012, 0.035)
        lug.data.materials.append(mats["steel"])
        parts.append(lug)

    root = bpy.data.objects.new("WheelRoot", None)
    bpy.context.scene.collection.objects.link(root)
    for p in parts:
        p.parent = root
    root.rotation_euler.x = 0.35   # slight tilt so the spin reads as a wheel, not a flat disc
    return root


def render_frames(root):
    scene = bpy.context.scene
    os.makedirs(OUT, exist_ok=True)
    frames = [0] if ONE else range(FRAMES)
    for f in frames:
        root.rotation_euler.z = 2 * math.pi * f / FRAMES
        scene.render.filepath = os.path.join(OUT, f"f{f:04d}.png")
        bpy.ops.render.render(write_still=True)
    print("DONE frames:", len(list(frames)), "->", OUT)


clear_scene()
setup_scene()
render_frames(build_wheel())
