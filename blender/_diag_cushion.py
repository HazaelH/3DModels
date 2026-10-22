import bpy, sys, os
sys.path.insert(0, r"C:\Users\hazae\PymeTech\demos\meridian-3t\blender")
import m3t_lib as L
L.reset()
L.import_glb(r"C:\Users\hazae\PymeTech\demos\meridian-3t\models\MRI_Realista_Modular.glb")
base = bpy.data.materials["MRI_Cushion"]
variants = []
for tag in ("asis", "sinsheen", "sinnormal"):
    m = base.copy(); m.name = "V_" + tag
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    if tag != "asis":
        b.inputs["Sheen Weight"].default_value = 0.0
    if tag == "sinnormal":
        for l in list(b.inputs["Normal"].links):
            m.node_tree.links.remove(l)
    variants.append(m)
# tres cubos
for i, m in enumerate(variants):
    bpy.ops.mesh.primitive_cube_add(size=0.9, location=(-1.1 + i*1.1, 0, 0.55))
    c = bpy.context.object
    c.data.materials.append(m)
    bpy.ops.object.shade_smooth()
# ocultar el modelo MRI
for o in L.meshes():
    if not o.name.startswith("Cube"):
        o.hide_render = True
w = bpy.data.worlds.new("W"); bpy.context.scene.world = w; w.use_nodes = True
bg = next(n for n in w.node_tree.nodes if n.type == "BACKGROUND")
bg.inputs[0].default_value = (0.46, 0.51, 0.58, 1.0); bg.inputs[1].default_value = 0.55
def area(name, loc, target, power, size):
    d = bpy.data.lights.new(name, "AREA"); d.energy = power; d.size = size
    o = bpy.data.objects.new(name, d); bpy.context.collection.objects.link(o); o.location = loc
    from mathutils import Vector
    o.rotation_euler = (Vector(target)-Vector(loc)).to_track_quat("-Z","Y").to_euler()
area("k", (2.5,-3.5,3.0), (0,0,0.5), 620, 3.2)
area("f", (-3.5,-2.0,2.0), (0,0,0.5), 200, 4.0)
cam = bpy.data.cameras.new("c"); cam.lens = 35
co = bpy.data.objects.new("c", cam); bpy.context.collection.objects.link(co)
co.location = (0, -4.6, 1.0)
from mathutils import Vector
co.rotation_euler = (Vector((0,0,0.55))-Vector(co.location)).to_track_quat("-Z","Y").to_euler()
bpy.context.scene.camera = co
sc = bpy.context.scene
sc.render.engine = "CYCLES"; sc.cycles.samples = 24; sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 420, 200
sc.view_settings.view_transform = "Khronos PBR Neutral"
sc.render.filepath = r"C:\Users\hazae\PymeTech\demos\meridian-3t\shots\_diag_cushion.png"
bpy.ops.render.render(write_still=True)
print("DIAG_OK")
