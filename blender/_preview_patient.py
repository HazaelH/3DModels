"""Preview rÃ¡pido del paciente: 3 vistas + frontal del rostro."""
import os
import sys
import math

import bpy
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build_patient as P  # noqa: E402

OUT = os.path.join(HERE, "out")
os.makedirs(OUT, exist_ok=True)


def setup_scene():
    sc = bpy.context.scene
    try:
        sc.render.engine = "BLENDER_EEVEE"
    except TypeError:
        sc.render.engine = "BLENDER_EEVEE_NEXT"
    sc.render.resolution_x = 720
    sc.render.resolution_y = 900
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.world = bpy.data.worlds.new("W")
    sc.world.use_nodes = True
    bg = sc.world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.035, 0.045, 0.055, 1)
    bg.inputs[1].default_value = 1.2

    key = bpy.data.lights.new("K", "AREA")
    key.energy = 420
    key.size = 2.2
    ko = bpy.data.objects.new("K", key)
    ko.location = (1.8, 2.6, 2.6)
    ko.rotation_euler = (math.radians(52), 0, math.radians(212))
    bpy.context.collection.objects.link(ko)

    fill = bpy.data.lights.new("F", "AREA")
    fill.energy = 160
    fill.size = 3.0
    fo = bpy.data.objects.new("F", fill)
    fo.location = (-2.6, 1.2, 1.8)
    fo.rotation_euler = (math.radians(72), 0, math.radians(115))
    bpy.context.collection.objects.link(fo)

    rim = bpy.data.lights.new("R", "AREA")
    rim.energy = 260
    rim.size = 1.6
    ro = bpy.data.objects.new("R", rim)
    ro.location = (-0.6, -2.4, 2.2)
    ro.rotation_euler = (math.radians(62), 0, math.radians(-15))
    bpy.context.collection.objects.link(ro)

    cam = bpy.data.cameras.new("C")
    cam.lens = 70
    co = bpy.data.objects.new("C", cam)
    bpy.context.collection.objects.link(co)
    sc.camera = co

    # suelo
    bpy.ops.mesh.primitive_plane_add(size=8, location=(0, 0, 0))
    mat = bpy.data.materials.new("floor")
    mat.use_nodes = True
    b = next(n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = (0.06, 0.07, 0.08, 1)
    b.inputs["Roughness"].default_value = 0.7
    bpy.context.object.data.materials.append(mat)
    return co


def look_at(cam, target, dist, angle_deg, height):
    a = math.radians(angle_deg)
    cam.location = Vector((target[0] + dist * math.sin(a),
                           target[1] - dist * math.cos(a),
                           height))
    d = Vector(target) - cam.location
    cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()


def render(cam, name, target, dist, angle, height, res=(720, 900), lens=70):
    bpy.context.scene.render.resolution_x, bpy.context.scene.render.resolution_y = res
    cam.data.lens = lens
    look_at(cam, target, dist, angle, height)
    bpy.context.scene.render.filepath = os.path.join(OUT, name)
    bpy.ops.render.render(write_still=True)
    print("RENDER", name)


def main():
    P.build_all()
    cam = setup_scene()
    render(cam, "pat_front.png", (0, 0, 0.9), 3.6, 180, 1.2, (600, 900), 80)
    render(cam, "pat_side.png", (0, 0, 0.9), 3.6, 100, 1.2, (600, 900), 80)
    render(cam, "pat_34.png", (0, 0, 0.9), 3.4, 215, 1.35, (600, 900), 80)
    render(cam, "pat_face.png", (0, 0.02, 1.60), 0.72, 160, 1.64, (700, 700), 85)


main()
