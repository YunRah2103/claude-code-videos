"""Export Yub as a Wavefront OBJ (+ MTL + PNG textures) for Blender or any 3D tool.
python characters/yub-3d/export_obj.py [expr] [outdir]     default: smile -> characters/yub-3d/export/
The mesh is in metres, Y up, facing +Z, feet at y=0. One material per colour; the face and the LTN cap logo are textured."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE); sys.path.insert(1, os.path.join(HERE, "..", "..", "lib", "cine3d"))
import numpy as np
from PIL import Image
from geo import TEX, WHITE
from yub import yub

def export(p, out, name="yub"):
    os.makedirs(out, exist_ok=True)
    mats = {}; lines = [f"mtllib {name}.mtl", f"o {name}"]; vi = 1; vt = 1
    groups = {}
    for i in range(len(p.t)):
        key = (int(p.k[i]), tuple(np.round(p.c[i], 3)) if p.k[i] == WHITE else None)
        groups.setdefault(key, []).append(i)
    mtl = []
    for gi, (key, idx) in enumerate(groups.items()):
        k, col = key; mname = f"m{gi}"
        mtl.append(f"newmtl {mname}")
        if k == WHITE:
            srgb = np.clip(np.float32(col) ** (1 / 2.2), 0, 1); mtl.append("Kd %.4f %.4f %.4f" % tuple(srgb))
        else:
            png = f"{name}_tex{k}.png"
            Image.fromarray((np.clip(TEX[k], 0, 1) ** (1 / 2.2) * 255).astype(np.uint8)).save(os.path.join(out, png))
            mtl += ["Kd 1 1 1", f"map_Kd {png}"]
        lines.append(f"usemtl {mname}")
        for i in idx:
            for j in range(3): lines.append("v %.5f %.5f %.5f" % tuple(p.t[i, j]))
            for j in range(3): lines.append("vn %.5f %.5f %.5f" % tuple(p.nv[i, j]))
            for j in range(3): lines.append("vt %.5f %.5f" % (p.uv[i, j, 0], 1 - p.uv[i, j, 1]))
            lines.append(f"f {vi}/{vt}/{vi} {vi + 1}/{vt + 1}/{vi + 1} {vi + 2}/{vt + 2}/{vi + 2}"); vi += 3; vt += 3
    open(os.path.join(out, f"{name}.obj"), "w").write("\n".join(lines) + "\n")
    open(os.path.join(out, f"{name}.mtl"), "w").write("\n".join(mtl) + "\n")
    print("wrote", os.path.join(out, f"{name}.obj"), len(p.t), "triangles,", len(groups), "materials")

if __name__ == "__main__":
    expr = sys.argv[1] if len(sys.argv) > 1 else "smile"
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "export")
    export(yub(expr), out)
