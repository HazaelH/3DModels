import bpy, sys, math
sys.path.insert(0, r"C:\Users\hazae\PymeTech\demos\meridian-3t\blender")
import m3t_lib as L

def tri(o):
    dg = bpy.context.evaluated_depsgraph_get(); ev = o.evaluated_get(dg); me = ev.to_mesh(); me.calc_loop_triangles()
    n = len(me.loop_triangles); ev.to_mesh_clear(); return n

L.reset(); L.import_glb()
o = L.obj("MRI_Base_Plinth")

# A) cubo nuevo de referencia
bpy.ops.mesh.primitive_cube_add(size=1.0, location=(5,5,5))
c = bpy.context.object
m = c.modifiers.new("B","BEVEL"); m.width=0.02; m.segments=2
print("A cubo nuevo con bisel:", tri(c))

# B) la pieza, limit NONE
m = o.modifiers.new("B2","BEVEL")
print("B affect:", m.affect, "offset:", m.offset_type, "harden:", m.harden_normals, "clamp:", m.use_clamp_overlap)
m.width = 0.0032; m.segments = 2; m.limit_method = "NONE"
print("B limit NONE:", tri(o))
m.limit_method = "ANGLE"; m.angle_limit = math.radians(30)
print("B limit ANGLE 30:", tri(o))

# C) ancho grande
m.width = 0.02
print("B width 20mm:", tri(o))

# D) sin clamp
m.use_clamp_overlap = False; m.width = 0.0032
print("D sin clamp:", tri(o))

# E) datos de la malla
me = o.data
print("E verts", len(me.vertices), "edges", len(me.edges), "polys", len(me.polygons))
print("E atributos:", [a.name for a in me.attributes])
print("E tiene custom normals:", me.has_custom_normals if hasattr(me,'has_custom_normals') else 'n/a')
print("E sharp edges:", sum(1 for e in me.edges if e.use_edge_sharp))
