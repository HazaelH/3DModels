"""Renderiza fotogramas clave de la animación del paciente para revisarla."""
import math
import os
import sys

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_patient as P  # noqa: E402

OUT = os.path.join(HERE, "out", "poses")
os.makedirs(OUT, exist_ok=True)

# cámara parecida a la del visor (three -> blender: x, -z, y)
CAM = Vector((-3.6, -5.2, 2.15))
TGT = Vector((0.0, -1.2, 1.05))


def setup():
    sc = bpy.context.scene
    try:
        sc.render.engine = "BLENDER_EEVEE"
    except TypeError:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_x = 760
    sc.render.resolution_y = 620
    sc.render.film_transparent = False
    sc.world = bpy.data.worlds.new("W")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.035, 0.045, 0.055, 1)
    bg.inputs[1].default_value = 1.4

    for name, loc, energy, size in (
        ("K", (1.8, -2.6, 3.2), 700, 2.4),
        ("F", (-3.2, -3.0, 2.0), 260, 2.6),
        ("R", (0.6, 1.6, 2.2), 420, 1.8),
    ):
        li = bpy.data.lights.new(name, "AREA")
        li.energy = energy
        li.size = size
        o = bpy.data.objects.new(name, li)
        o.location = loc
        d = TGT - Vector(loc)
        o.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        bpy.context.collection.objects.link(o)

    cam = bpy.data.cameras.new("C")
    cam.lens = 46
    co = bpy.data.objects.new("C", cam)
    bpy.context.collection.objects.link(co)
    co.location = CAM
    co.rotation_euler = (TGT - CAM).to_track_quat("-Z", "Y").to_euler()
    sc.camera = co

    bpy.ops.mesh.primitive_plane_add(size=14, location=(0, -1.5, 0))
    mat = bpy.data.materials.new("floor")
    mat.use_nodes = True
    b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.05, 0.06, 0.07, 1)
    b.inputs["Roughness"].default_value = 0.7
    bpy.context.object.data.materials.append(mat)


def main():
    body, gown, hair, eyes = P.build_all()
    rig = P.build_rig()
    P.weight_body(body, rig)
    P.bin_gown(gown, rig)
    P.rigid_to(hair, rig, "head")
    P.rigid_to(eyes, rig, "head")
    P.animate(rig)
    setup()
    frames = [0, 24, 48, 66, 84, 104, 124, 138, 165, 380, 430, 470, 500]
    for f in frames:
        bpy.context.scene.frame_set(f)
        bpy.context.scene.render.filepath = os.path.join(OUT, "f%03d.png" % f)
        bpy.ops.render.render(write_still=True)
        print("RENDER", f)


main()
