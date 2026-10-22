"""Inspecciona el GLB de origen y vuelca un informe JSON.

Uso:
    blender -b -P blender/inspect.py
"""
import bpy
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GLB = os.path.join(ROOT, "models", "_src", "MRI_v1.glb")
OUT = os.path.join(ROOT, "blender", "out")


def vec(v):
    return [round(float(x), 5) for x in v]


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=GLB)

    meshes = [o for o in bpy.data.objects if o.type == "MESH"]
    empties = [o for o in bpy.data.objects if o.type == "EMPTY"]

    report = {
        "blender": bpy.app.version_string,
        "objects": [],
        "empties": [o.name for o in empties],
        "materials": [],
        "images": [],
        "totals": {},
    }

    tot_tris = 0
    tot_verts = 0
    for o in sorted(meshes, key=lambda x: x.name):
        o.data.calc_loop_triangles()
        tris = len(o.data.loop_triangles)
        verts = len(o.data.vertices)
        tot_tris += tris
        tot_verts += verts
        bb = [o.matrix_world @ __import__("mathutils").Vector(c) for c in o.bound_box]
        xs = [p.x for p in bb]
        ys = [p.y for p in bb]
        zs = [p.z for p in bb]
        report["objects"].append({
            "name": o.name,
            "data": o.data.name,
            "parent": o.parent.name if o.parent else None,
            "tris": tris,
            "verts": verts,
            "loc": vec(o.location),
            "rot_deg": [round(float(a) * 57.29578, 2) for a in o.rotation_euler],
            "scale": vec(o.scale),
            "dims": vec(o.dimensions),
            "world_min": vec((min(xs), min(ys), min(zs))),
            "world_max": vec((max(xs), max(ys), max(zs))),
            "uv": [u.name for u in o.data.uv_layers],
            "mats": [m.name if m else None for m in o.data.materials],
            "mods": [m.type for m in o.modifiers],
            "quads": sum(1 for p in o.data.polygons if p.loop_total == 4),
            "ngons": sum(1 for p in o.data.polygons if p.loop_total > 4),
        })

    report["totals"] = {"meshes": len(meshes), "tris": tot_tris, "verts": tot_verts}

    wanted = ["Base Color", "Metallic", "Roughness", "IOR", "Alpha", "Coat Weight",
              "Coat Roughness", "Sheen Weight", "Sheen Roughness", "Emission Color",
              "Emission Strength", "Transmission Weight", "Anisotropic"]
    for m in bpy.data.materials:
        if not m.use_nodes:
            continue
        bsdf = next((n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        info = {"name": m.name, "users": m.users, "bsdf": bsdf is not None, "inputs": {},
                "tex": [], "blend": getattr(m, "blend_method", None)}
        if bsdf:
            for key in wanted:
                if key in bsdf.inputs:
                    sock = bsdf.inputs[key]
                    val = sock.default_value
                    try:
                        val = vec(val)
                    except TypeError:
                        val = round(float(val), 4)
                    linked = sock.is_linked
                    if linked:
                        src = sock.links[0].from_node
                        val = f"<{src.type}:{src.name}>"
                    info["inputs"][key] = val
            for n in m.node_tree.nodes:
                if n.type == "TEX_IMAGE" and n.image:
                    info["tex"].append({
                        "node": n.name,
                        "image": n.image.name,
                        "size": list(n.image.size),
                        "to": [l.to_socket.name for l in n.outputs[0].links],
                    })
        report["materials"].append(info)

    for img in bpy.data.images:
        if img.type != "IMAGE":
            continue
        report["images"].append({
            "name": img.name,
            "size": list(img.size),
            "packed": img.packed_file is not None,
            "colorspace": img.colorspace_settings.name,
            "channels": img.channels,
        })

    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "inspect.json")
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=1, ensure_ascii=False)

    print("INSPECT_OK", path)
    print("MESHES", len(meshes), "TRIS", tot_tris, "VERTS", tot_verts)
    print("MATERIALS", len(report["materials"]), "IMAGES", len(report["images"]))
    names = [o["name"] for o in report["objects"]]
    print("MRI_NAMES", len([n for n in names if n.startswith("MRI_")]))
    for o in report["objects"]:
        print("OBJ", o["name"], o["tris"], o["dims"], "scale", o["scale"], "mats", o["mats"])


main()
sys.exit(0)
