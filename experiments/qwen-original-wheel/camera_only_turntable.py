"""Camera-only orbit render of the UNMODIFIED Qwen .blend output.
This helper does not create, edit or replace any wheel mesh/material.
"""
import bpy, math, os
from mathutils import Vector

home = os.path.expanduser("~")
blend = os.path.join(home, "wheel_test.blend")
bpy.ops.wm.open_mainfile(filepath=blend)
scene = bpy.context.scene
scene.render.engine = "BLENDER_EEVEE" if bpy.app.version < (4, 2, 0) else "BLENDER_EEVEE_NEXT"
scene.render.resolution_x = 800
scene.render.resolution_y = 450
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = False
scene.camera.data.lens = 56
target = Vector((0, 0, 0.4))
out = os.environ.get("WHEEL_FRAMES", "/tmp/qwen-frames")
os.makedirs(out, exist_ok=True)
N = 48
for i in range(N):
    a = 2 * math.pi * i / N
    # Camera movement only; all Qwen-authored meshes and lights untouched.
    scene.camera.location = (1.17*math.sin(a), 1.5*math.cos(a), 0.57 + 0.08*math.sin(2*a))
    direction = target - scene.camera.location
    scene.camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.render.filepath = os.path.join(out, f"frame_{i:03d}.png")
    bpy.ops.render.render(write_still=True)
print("DONE orbit, Qwen geometry untouched")
