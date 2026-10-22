"""Utilidades compartidas por los scripts de Blender del proyecto MERIDIAN 3T.

Todo se ejecuta en modo headless:  blender -b -P script.py
"""
import bpy
import bmesh
import math
import os
import sys
from mathutils import Vector

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = os.path.join(ROOT, "models")
OUT = os.path.join(ROOT, "blender", "out")
SHOTS = os.path.join(ROOT, "shots")
SRC_GLB = os.path.join(MODELS, "_src", "MRI_v1.glb")

# Las 32 piezas que el visor conoce por nombre. Si alguna falta, el visor y las
# 32 miniaturas se rompen en silencio: por eso se valida antes de exportar.
PARTS = [
    "MRI_Gantry_Core", "MRI_Top_Panel", "MRI_Front_Cover", "MRI_Rear_Cover",
    "MRI_Side_Panel_L", "MRI_Side_Panel_R", "MRI_Bore_Tunnel", "MRI_Bore_Trim",
    "MRI_Accent_Ring", "MRI_Bore_Light_Ring", "MRI_Base_Plinth", "MRI_Leveling_Feet",
    "MRI_Table_Base", "MRI_Table_Column", "MRI_Table_Carriage", "MRI_Table_Surface",
    "MRI_Table_Cushion", "MRI_Table_Rail_L", "MRI_Table_Rail_R", "MRI_Table_Headrest",
    "MRI_Table_ControlPad", "MRI_Head_Coil", "MRI_Console_Base", "MRI_Console_Body",
    "MRI_Console_Screen", "MRI_Console_Tray", "MRI_Emergency_Button",
    "MRI_Handle_L", "MRI_Handle_R", "MRI_Vent_Grille_L", "MRI_Vent_Grille_R",
    "MRI_Alignment_Laser",
]

# Piezas que se deslizan al túnel durante la simulación (las valida el visor).
SLIDE = ["MRI_Table_Surface", "MRI_Table_Cushion", "MRI_Table_Headrest",
         "MRI_Table_Rail_L", "MRI_Table_Rail_R", "MRI_Table_ControlPad",
         "MRI_Head_Coil"]


def log(*args):
    print("[m3t]", *args)


def reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path=SRC_GLB):
    bpy.ops.import_scene.gltf(filepath=path)
    log("importado", os.path.basename(path), "objetos:", len(bpy.data.objects))


def meshes():
    return [o for o in bpy.data.objects if o.type == "MESH"]


def obj(name):
    o = bpy.data.objects.get(name)
    if o is None:
        raise RuntimeError("falta el objeto " + name)
    return o


def activate(o):
    for sel in bpy.context.selected_objects:
        sel.select_set(False)
    o.select_set(True)
    bpy.context.view_layer.objects.active = o


def apply_all_modifiers(o):
    activate(o)
    for m in list(o.modifiers):
        try:
            bpy.ops.object.modifier_apply(modifier=m.name)
        except RuntimeError as exc:
            log("AVISO no se pudo aplicar", m.name, "en", o.name, exc)


def shade_smooth_all(o):
    for p in o.data.polygons:
        p.use_smooth = True


def _set(obj, **pairs):
    """Asigna solo los atributos que existan: los nombres cambian entre versiones."""
    for key, value in pairs.items():
        if not hasattr(obj, key):
            continue
        try:
            setattr(obj, key, value)
        except (TypeError, ValueError):
            pass


def add_bevel(o, width, segments=2, angle=30.0):
    m = o.modifiers.new("BEVEL", "BEVEL")
    _set(m,
         width=width,
         segments=segments,
         limit_method="ANGLE",
         angle_limit=math.radians(angle),
         harden_normals=True,
         use_clamp_overlap=True,   # Blender 5.x
         clamp_overlap=True,       # Blender 4.x
         miter_outer="MITER_ARC",
         profile=0.5)
    return m


def add_weighted_normal(o):
    m = o.modifiers.new("WN", "WEIGHTED_NORMAL")
    _set(m, weight=60, keep_sharp=True, mode="FACE_AREA")
    return m


def weld(o, dist=1e-5):
    """El glTF importa las caras desconectadas (un cubo llega con 24 vertices).
    Sin soldar, el bisel por angulo no reconoce ninguna arista."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    before = len(bm.verts)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=dist)
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()
    return before, len(o.data.vertices)


def recalc_outside(o):
    """Normales coherentes hacia fuera: el GLB trae piezas invertidas y el
    culling (que el visor ya aplica) las dejaba negras."""
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()


def bevel_object(o, max_width=0.0032):
    dims = [d for d in o.dimensions if d > 0.0001]
    if not dims:
        return 0
    weld(o)
    recalc_outside(o)
    width = max(0.0008, min(max_width, min(dims) * 0.12))
    add_bevel(o, width)
    shade_smooth_all(o)
    add_weighted_normal(o)
    apply_all_modifiers(o)
    return width


def principled(mat):
    if not mat.use_nodes:
        mat.use_nodes = True
    return next((n for n in mat.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)


def set_in(mat, key, value):
    """Cambia una entrada del Principled solo si no está conectada a una textura."""
    b = principled(mat)
    if b is None or key not in b.inputs:
        return False
    sock = b.inputs[key]
    if sock.is_linked:
        return False
    if isinstance(value, (tuple, list)) and len(value) == 3:
        value = (value[0], value[1], value[2], 1.0)
    sock.default_value = value
    return True


def new_material(name, base, metallic=0.0, roughness=0.5, coat=0.0, coat_rough=0.1,
                 sheen=0.0, emission=None, emission_strength=0.0):
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    b = principled(mat)
    b.inputs["Base Color"].default_value = (base[0], base[1], base[2], 1.0)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = roughness
    if "Coat Weight" in b.inputs:
        b.inputs["Coat Weight"].default_value = coat
        b.inputs["Coat Roughness"].default_value = coat_rough
    if "Sheen Weight" in b.inputs:
        b.inputs["Sheen Weight"].default_value = sheen
    if emission is not None and "Emission Color" in b.inputs:
        b.inputs["Emission Color"].default_value = (emission[0], emission[1], emission[2], 1.0)
        b.inputs["Emission Strength"].default_value = emission_strength
    mat.use_backface_culling = True
    return mat


def assign(o, mat):
    if mat.name not in [m.name for m in o.data.materials if m]:
        o.data.materials.append(mat)


# ---------------------------------------------------------------- geometría
def _mesh_from_bm(name, bm):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(o)
    return o


def annulus(name, r_in, r_out, y, thickness=0.01, segments=72):
    """Anillo plano en el plano XZ (eje Y), centrado en (0,·,1.05) del bore."""
    bm = bmesh.new()
    zc = 1.05
    loops = []
    for yy in (y, y + thickness):
        inner, outer = [], []
        for i in range(segments):
            a = 2 * math.pi * i / segments
            c, s = math.cos(a), math.sin(a)
            inner.append(bm.verts.new((r_in * c, yy, zc + r_in * s)))
            outer.append(bm.verts.new((r_out * c, yy, zc + r_out * s)))
        loops.append((inner, outer))
    (i0, o0), (i1, o1) = loops
    for i in range(segments):
        j = (i + 1) % segments
        bm.faces.new((o0[i], o0[j], o1[j], o1[i]))      # borde exterior
        bm.faces.new((i0[j], i0[i], i1[i], i1[j]))      # borde interior
        bm.faces.new((i0[i], i0[j], o0[j], o0[i]))      # cara frontal
        bm.faces.new((o1[i], o1[j], i1[j], i1[i]))      # cara trasera
    bm.normal_update()
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return _mesh_from_bm(name, bm)


def torus(name, major, minor, y, major_seg=64, minor_seg=10, zc=1.05):
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=False, radius=minor, segments=minor_seg)
    # construir toro a mano (el operador torus_add no acepta orientación fiable)
    bm.free()
    bm = bmesh.new()
    grid = []
    for i in range(major_seg):
        a = 2 * math.pi * i / major_seg
        ca, sa = math.cos(a), math.sin(a)
        ring = []
        for j in range(minor_seg):
            b = 2 * math.pi * j / minor_seg
            rb = minor * math.cos(b)
            ring.append(bm.verts.new(((major + rb) * ca, y + minor * math.sin(b), zc + (major + rb) * sa)))
        grid.append(ring)
    for i in range(major_seg):
        i2 = (i + 1) % major_seg
        for j in range(minor_seg):
            j2 = (j + 1) % minor_seg
            bm.faces.new((grid[i][j], grid[i2][j], grid[i2][j2], grid[i][j2]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return _mesh_from_bm(name, bm)


def box(name, size, loc):
    bm = bmesh.new()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co.x *= size[0]
        v.co.y *= size[1]
        v.co.z *= size[2]
        v.co += Vector(loc)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return _mesh_from_bm(name, bm)


def cylinder(name, radius, depth, loc, axis="Y", segments=32):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=segments,
                          radius1=radius, radius2=radius, depth=depth)
    # create_cone nace con el eje en Z: rotar al eje pedido
    if axis == "Y":
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0),
                         matrix=__import__("mathutils").Matrix.Rotation(math.radians(90), 3, "X"))
    elif axis == "X":
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0),
                         matrix=__import__("mathutils").Matrix.Rotation(math.radians(90), 3, "Y"))
    for v in bm.verts:
        v.co += Vector(loc)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return _mesh_from_bm(name, bm)


def text_mesh(name, body, size, loc, rot_z=0.0, extrude=0.0006, align="CENTER"):
    bpy.ops.object.text_add(location=loc)
    t = bpy.context.object
    t.name = name
    t.data.body = body
    t.data.size = size
    t.data.extrude = extrude
    t.data.align_x = align
    t.data.align_y = "CENTER"
    t.rotation_euler = (math.radians(90), 0, rot_z)   # el texto nace en XY: ponerlo de pie
    activate(t)
    bpy.ops.object.convert(target="MESH")
    return bpy.context.object


def join_into(target, others, keep_materials=True):
    """Une geometría de detalle dentro de la pieza destino: el nodo sigue llamándose MRI_*."""
    others = [o for o in others if o and o.name in bpy.data.objects]
    if not others:
        return
    for sel in bpy.context.selected_objects:
        sel.select_set(False)
    for o in others:
        o.select_set(True)
    target.select_set(True)
    bpy.context.view_layer.objects.active = target
    bpy.ops.object.join()
    log("join ->", target.name, "tris", len(target.data.loop_triangles))


def project_uv(o, axis="Y", sign=-1.0):
    """Proyecta UV sobre las caras que miran en un eje (pantallas y teclados:
    el UV del GLB venia girado 90 grados y la textura salia estirada)."""
    me = o.data
    if not me.uv_layers:
        me.uv_layers.new(name="UVMap")
    uvl = me.uv_layers.active.data
    idx = {"X": 0, "Y": 1, "Z": 2}
    a = idx[axis]
    others = [i for i in (0, 1, 2) if i != a]
    co_all = [v.co for v in me.vertices]
    lo = [min(c[i] for c in co_all) for i in others]
    hi = [max(c[i] for c in co_all) for i in others]
    span = [max(1e-6, hi[0] - lo[0]), max(1e-6, hi[1] - lo[1])]
    hits = 0
    for poly in me.polygons:
        if poly.normal[a] * sign < 0.9:
            continue
        for li in poly.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uvl[li].uv = ((co[others[0]] - lo[0]) / span[0],
                          (co[others[1]] - lo[1]) / span[1])
        hits += 1
    return hits


def reshape_world(o, center, scale):
    """Escala la malla alrededor de un punto del mundo (bake en vertices)."""
    mw = o.matrix_world.copy()
    inv = mw.inverted()
    c = Vector(center)
    for v in o.data.vertices:
        w = mw @ v.co
        v.co = inv @ Vector((c.x + (w.x - c.x) * scale[0],
                             c.y + (w.y - c.y) * scale[1],
                             c.z + (w.z - c.z) * scale[2]))
    o.data.update()


def translate_world(o, delta):
    mw = o.matrix_world.copy()
    inv = mw.inverted()
    d = Vector(delta)
    for v in o.data.vertices:
        v.co = inv @ ((mw @ v.co) + d)
    o.data.update()


def export_glb(path, compress=False):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    kw = dict(
        filepath=path,
        export_format="GLB",
        export_apply=False,
        use_selection=False,
        export_yup=True,
        export_animations=False,
        export_skins=False,
        export_morph=False,
        export_materials="EXPORT",
        export_image_format="AUTO",
        export_cameras=False,
        export_lights=False,
        export_extras=True,
        export_normals=True,
        export_tangents=True,       # necesario para anisotropía en three.js
    )
    try:
        bpy.ops.export_scene.gltf(**kw)
    except TypeError as exc:
        log("export: argumento no soportado, reintento minimo:", exc)
        bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", export_yup=True)
    size = os.path.getsize(path) / 1024.0
    log("exportado", path, round(size, 1), "KB")


def validate_names(stage="export"):
    names = {o.name for o in meshes()}
    missing = [n for n in PARTS if n not in names]
    if missing:
        raise RuntimeError("FALTAN PIEZAS en " + stage + ": " + ", ".join(missing))
    extra = sorted(n for n in names if n.startswith("MRI_") and n not in PARTS)
    log("validacion OK:", len(names), "mallas, 32 piezas presentes")
    if extra:
        log("AVISO nodos MRI_ extra:", extra)
    slide_missing = [n for n in SLIDE if n not in names]
    if slide_missing:
        raise RuntimeError("FALTAN piezas deslizantes: " + ", ".join(slide_missing))
    return True


def save_blend(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=path)
    log("blend guardado", path, round(os.path.getsize(path) / 1024.0, 1), "KB")


def tri_count():
    total = 0
    for o in meshes():
        o.data.calc_loop_triangles()
        total += len(o.data.loop_triangles)
    return total
