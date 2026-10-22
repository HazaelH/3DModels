import bpy, math, sys
from mathutils import Vector

p = r"C:\Users\hazae\PymeTech\demos\meridian-3t\blender\out\head_coil.blend"
bpy.ops.wm.open_mainfile(filepath=p)
sc = bpy.context.scene
sc.render.engine = "BLENDER_EEVEE"
sc.render.resolution_x = 900
sc.render.resolution_y = 650
sc.render.film_transparent = False
w = bpy.data.worlds.new("W"); sc.world = w; w.use_nodes = True; next(n for n in w.node_tree.nodes if n.type == "BACKGROUND").inputs[0].default_value = (0.05, 0.06, 0.07, 1)

# suelo
bpy.ops.mesh.primitive_plane_add(size=4, location=(0, 0, 0))


cam_data = bpy.data.cameras.new("C")
cam = bpy.data.objects.new("C", cam_data)
sc.collection.objects.link(cam)
cam.location = (0.75, -1.05, 1.15)
d = Vector((0, 0, 0.18)) - cam.location
cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
cam_data.lens = 55
sc.camera = cam

key = bpy.data.lights.new("K", "AREA")
key.energy = 300
key.size = 2.0
ko = bpy.data.objects.new("K", key)
sc.collection.objects.link(ko)
ko.location = (1.4, -1.0, 2.2)
ko.rotation_euler = (Vector((0, 0, 0.2)) - ko.location).to_track_quat("-Z", "Y").to_euler()

fill = bpy.data.lights.new("F", "AREA")
fill.energy = 90
fill.size = 3.0
fo = bpy.data.objects.new("F", fill)
sc.collection.objects.link(fo)
fo.location = (-1.6, -0.4, 1.4)
fo.rotation_euler = (Vector((0, 0, 0.2)) - fo.location).to_track_quat("-Z", "Y").to_euler()

sc.render.filepath = r"C:\Users\hazae\PymeTech\demos\meridian-3t\blender\out\coil_check.png"
bpy.ops.render.render(write_still=True)
print("RENDERED")



