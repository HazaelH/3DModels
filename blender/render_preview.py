"""Render de comprobacion con Cycles CPU (headless).

Uso:
    blender -b -P blender/render_preview.py -- --glb models/MRI_Realista_Modular.glb \
        --out shots/f1_hero.png --view hero --samples 48
"""
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
import m3t_lib as L  # noqa: E402

VIEWS = {
    # nombre: (posicion camara, objetivo, focal mm)  -- coords Blender
    # La camara debe quedar DENTRO de la sala (10x10): el visor orbita a ~5 m.
    "hero":  ((3.55, -4.55, 2.35), (0.05, -0.15, 1.02), 30),
    "front": ((0.00, -4.40, 1.75), (0.00, -0.10, 1.05), 32),
    "bore":  ((1.05, -2.35, 1.35), (-0.05, 0.10, 1.05), 45),
    "table": ((2.60, -3.60, 1.15), (-0.10, -1.90, 0.85), 38),
    "back":  ((-4.30, 4.10, 2.60), (0.10, 0.10, 1.00), 30),
}


def arg(name, default=None):
    if name in sys.argv:
        return sys.argv[sys.argv.index(name) + 1]
    return default


def setup_world():
    w = bpy.data.worlds.new("W")
    bpy.context.scene.world = w
    w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
    bg.inputs[0].default_value = (0.46, 0.51, 0.58, 1.0)
    bg.inputs[1].default_value = 0.55


def add_area(name, loc, target, power, size, color=(1, 1, 1)):
    d = bpy.data.lights.new(name, "AREA")
    d.energy = power
    d.shape = "RECTANGLE"
    d.size = size
    d.size_y = size * 0.7
    d.color = color
    o = bpy.data.objects.new(name, d)
    bpy.context.collection.objects.link(o)
    o.location = loc
    direction = Vector(target) - Vector(loc)
    o.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    return o


def setup_lights():
    add_area("key", (3.2, -4.6, 3.6), (0, 0, 1.1), 620, 3.2, (1.0, 0.98, 0.95))
    add_area("fill", (-4.2, -3.0, 2.4), (0, 0, 1.0), 200, 4.0, (0.88, 0.93, 1.0))
    add_area("rim", (-0.5, 3.6, 3.2), (0, 0, 1.2), 420, 2.6, (0.92, 0.96, 1.0))
    add_area("top", (0.0, -0.6, 4.2), (0, 0, 1.2), 110, 3.0)


def add_floor():
    bpy.ops.mesh.primitive_plane_add(size=26, location=(0, 0, -0.001))
    f = bpy.context.object
    f.name = "PREVIEW_FLOOR"
    m = L.new_material("PREVIEW_FLOOR_MAT", (0.26, 0.28, 0.31), metallic=0.0, roughness=0.34)
    f.data.materials.append(m)


def setup_camera(view):
    loc, target, lens = VIEWS[view]
    cam = bpy.data.cameras.new("cam")
    cam.lens = lens
    cam.sensor_fit = "HORIZONTAL"
    cam.sensor_width = 36
    o = bpy.data.objects.new("cam", cam)
    bpy.context.collection.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = o
    return o


def main():
    glb = arg("--glb", os.path.join(L.MODELS, "MRI_Realista_Modular.glb"))
    out = arg("--out", os.path.join(L.SHOTS, "preview.png"))
    view = arg("--view", "hero")
    samples = int(arg("--samples", "48"))
    res = arg("--res", "1000x640")

    L.reset()
    if glb and os.path.exists(glb):
        L.import_glb(glb)
        L.log("piezas importadas:", len(L.meshes()))
    suite = arg("--suite", "")
    setup_world()
    setup_lights()
    if suite and os.path.exists(suite):
        bpy.ops.import_scene.gltf(filepath=suite)
        L.log("sala importada")
    else:
        add_floor()
    setup_camera(view)

    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    try:
        sc.cycles.device = "CPU"
    except Exception:
        pass
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    sc.render.resolution_x, sc.render.resolution_y = [int(v) for v in res.split("x")]
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.render.image_settings.file_format = "PNG"
    sc.render.filepath = out

    for tf in ("Khronos PBR Neutral", "AgX", "Filmic"):
        try:
            sc.view_settings.view_transform = tf
            L.log("view transform:", tf)
            break
        except TypeError:
            continue

    os.makedirs(os.path.dirname(out), exist_ok=True)
    L.log("renderizando", out, view, samples, "spp")
    bpy.ops.render.render(write_still=True)
    L.log("RENDER_OK", out, round(os.path.getsize(out) / 1024.0, 1), "KB")


main()
sys.exit(0)
