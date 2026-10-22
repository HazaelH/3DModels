import bpy, sys
sys.path.insert(0, r"C:\Users\hazae\PymeTech\demos\meridian-3t\blender")
import m3t_lib as L
L.reset(); L.import_glb(r"C:\Users\hazae\PymeTech\demos\meridian-3t\models\MRI_Realista_Modular.glb")
for name in ("MRI_Table_Surface","MRI_Table_Cushion","MRI_Table_Headrest","MRI_Console_Screen"):
    o = L.obj(name); me = o.data
    me.calc_loop_triangles()
    up = [p for p in me.polygons if p.normal.z > 0.9]
    dn = [p for p in me.polygons if p.normal.z < -0.9]
    zs = [v.co.z for v in me.vertices]
    print("==", name, "tris", len(me.loop_triangles), "polys", len(me.polygons))
    print("   z range", round(min(zs),3), "..", round(max(zs),3), "| caras arriba", len(up), "abajo", len(dn))
    if up: print("   z media caras arriba", round(sum(p.center.z for p in up)/len(up),3))
    print("   materiales", [(i, m.name if m else None) for i,m in enumerate(me.materials)])
    print("   indices de material usados", sorted(set(p.material_index for p in me.polygons)))
    # color base del material del colchon
mats = {m.name: m for m in bpy.data.materials}
for n in ("MRI_Cushion","MRI_Table_Surface","MRI_White_ABS"):
    pass
import bpy
for mn in ("MRI_Cushion","MRI_White_ABS"):
    m = bpy.data.materials.get(mn); b = next((x for x in m.node_tree.nodes if x.type=="BSDF_PRINCIPLED"), None)
    print("MAT", mn, "base", tuple(round(v,3) for v in b.inputs["Base Color"].default_value), "linked", b.inputs["Base Color"].is_linked)
