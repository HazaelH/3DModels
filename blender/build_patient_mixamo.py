# -*- coding: utf-8 -*-
# MERIDIAN 3T - paciente realista con mocap (Mixamo Ch16)
# Genera models/patient.glb con una unica accion horneada de ~27 s.
#
# Uso:
#   blender -b --factory-startup --python blender/build_patient_mixamo.py
#
# Convenciones (Blender -> three): (x, y, z) -> (x, z, -y)
#   - El paciente camina hacia +Y, se gira 180 y se sienta en el borde del pie
#     de la mesa (y = -3.10), se tumba con la cabeza hacia +Y, se escanea y
#     deshace el camino.  La mesa, cuando esta "fuera", esta +0.42 en Z(three),
#     por eso las posiciones del clip estan autoradas con la mesa fuera.

import bpy
import bmesh
import math
import os
import time
from mathutils import Quaternion, Vector

T0 = time.time()

ROOT = r"C:\Users\hazae\PymeTech\demos\meridian-3t"
MANIQUI = os.path.join(ROOT, "maniqui")
OUT_GLB = os.path.join(ROOT, "models", "patient.glb")

FPS = 30
DUR = 26.5
N_FRAMES = int(round(DUR * FPS))          # 795
# El clip Walking es "in place" y su zancada natural ronda 1.5 m/s (medida
# sobre los dedos en contacto).  El paciente recorre 1.0 m en 0.65 s (1.54 m/s)
# y lo reproducimos al 0.91: los pies quedan plantados y el paso es natural.
WALK_RATE = 0.91

# --- clips -----------------------------------------------------------------
# "Laying Idle" no se usa: su bucle flexiona las rodillas y levanta un brazo,
# poco adecuado para una exploracion.  El reposo es el ultimo frame de
# "Lying Down" con una respiracion procedural muy leve.  "Idle" tampoco se usa:
# su cabeza mira 9 grados hacia arriba.  El primer frame de "Sitting" esta de
# pie, con la cabeza nivelada; sirve de espera.  "Sitting" 1 -> "Lying" 50
# hace el gesto de sentarse en el borde de la mesa.
CLIPS = [
    ("Sitting",    "Sitting.fbx"),
    ("Walking",    "Walking.fbx"),
    ("Lying",      "Lying Down.fbx"),
    ("SitStand",   "Sit To Stand.fbx"),
]

# --- linea de tiempo de las clips (segundos) -------------------------------
# hold 0-1.4 / caminar 1.4-2.05 / fundido a idle 1.95-2.35 / giro 2.05-2.50
# sentarse 2.50-3.70 / tumbarse 3.70-8.30 / reposo 8.30-17.70
# incorporarse 17.70-21.10 / preparar pie 21.10-21.40 / levantarse 21.40-23.70
# paso a walk 23.70-23.90 / salir 23.90-24.70 / hold final
T_HOLD_END = 1.40
T_WALK_IN_A = 1.30
T_WALK_IN_B = 1.60
T_WALK_END = 2.05
T_WALK_IDLE_A = 1.95
T_WALK_IDLE_B = 2.35
T_TURN_A = 2.05
T_TURN_B = 2.50
T_SIT_END = 3.70
T_SEATED = 5.00
T_LIE_END = 8.30
T_SITUP_START = 17.70
T_SITUP_END = 21.10
T_STAND_PREP_END = 21.40
T_STAND_END = 23.70
T_WALK_PREP_END = 23.90
T_WALKOUT_END = 24.70

# --- trayectoria del objeto armature (metros, Blender) ---------------------
# (t, x, y, z, rotZ grados, easing)
# easing: 'lin' o 'smooth'
ROOT_KEYS = [
    (0.0,             0.0, -4.35, 0.00, 180.0, "lin"),
    (T_HOLD_END,      0.0, -4.35, 0.00, 180.0, "lin"),
    (T_WALK_END,      0.0, -3.35, 0.00, 180.0, "lin"),   # caminar
    (T_TURN_A,        0.0, -3.35, 0.00, 180.0, "lin"),
    (T_TURN_B,        0.0, -3.35, 0.00,   0.0, "smooth"),# giro
    (T_SIT_END,       0.0, -3.35, 0.00,   0.0, "lin"),   # de pie junto a la mesa
    (T_SEATED,        0.0, -2.84, 0.32,   0.0, "smooth"),# sentarse en el borde
    (T_LIE_END,       0.0, -2.19, 0.32,   0.0, "smooth"),# tumbarse
    (T_SITUP_START,   0.0, -2.19, 0.32,   0.0, "lin"),   # reposo
    (T_SITUP_END,     0.0, -3.10, 0.32,   0.0, "smooth"),# incorporarse
    (T_STAND_PREP_END,0.0, -3.13, 0.47,   0.0, "smooth"),
    (T_STAND_END,     0.0, -3.13, 0.00,   0.0, "lin"),   # z se ajusta aparte
    (T_WALK_PREP_END, 0.0, -3.595,0.00,   0.0, "smooth"),
    (T_WALKOUT_END,   0.0, -4.80, 0.00,   0.0, "lin"),   # salir
    (DUR,             0.0, -4.80, 0.00,   0.0, "lin"),
]

# --- utilidades -------------------------------------------------------------
def smooth(u):
    u = max(0.0, min(1.0, u))
    return u * u * (3.0 - 2.0 * u)

def lerp(a, b, u):
    return a + (b - a) * u

def root_at(t):
    """Devuelve (x,y,z,rotZ) del objeto en el instante t."""
    if t <= ROOT_KEYS[0][0]:
        k = ROOT_KEYS[0]
        return k[1], k[2], k[3], k[4]
    for i in range(len(ROOT_KEYS) - 1):
        a = ROOT_KEYS[i]
        b = ROOT_KEYS[i + 1]
        if a[0] <= t <= b[0]:
            span = b[0] - a[0]
            u = 0.0 if span <= 1e-9 else (t - a[0]) / span
            if b[5] == "smooth":
                u = smooth(u)
            x = lerp(a[1], b[1], u)
            y = lerp(a[2], b[2], u)
            z = lerp(a[3], b[3], u)
            rz = lerp(a[4], b[4], u)
            # al levantarse, los pies bajan al suelo al inicio (la mesa ya esta
            # retirada); asi no queda flotando mientras se incorpora.
            if a[0] == T_STAND_PREP_END or (a[0] < T_STAND_END and b[0] == T_STAND_END):
                z = 0.47 * (1.0 - smooth((t - T_STAND_PREP_END) / 0.90))
            return x, y, z, rz
    k = ROOT_KEYS[-1]
    return k[1], k[2], k[3], k[4]

# --- estado de clips por frame ---------------------------------------------
def clip_state(t):
    """(clipA, srcA, clipB, srcB, w)"""
    # de pie (primer frame de Sitting: cabeza nivelada, brazos relajados)
    if t < T_WALK_IN_A:
        return "Sitting", 1.0, None, 0.0, 0.0
    # arranque de la marcha (fundido corto desde la posicion de pie)
    if t < T_WALK_IN_B:
        u = max(0.0, t - T_HOLD_END) * FPS * WALK_RATE
        w = smooth((t - T_WALK_IN_A) / (T_WALK_IN_B - T_WALK_IN_A))
        return "Sitting", 1.0, "Walking", 1.0 + u, w
    # caminar
    if t < T_WALK_IDLE_A:
        u = ((t - T_HOLD_END) * FPS * WALK_RATE) % 31.0
        return "Walking", 1.0 + u, None, 0.0, 0.0
    # fundido caminar -> de pie
    if t < T_WALK_IDLE_B:
        u = ((t - T_HOLD_END) * FPS * WALK_RATE) % 31.0
        w = smooth((t - T_WALK_IDLE_A) / (T_WALK_IDLE_B - T_WALK_IDLE_A))
        return "Walking", 1.0 + u, "Sitting", 1.0, w
    # giro (de pie)
    if t < T_TURN_B:
        return "Sitting", 1.0, None, 0.0, 0.0
    # de pie junto a la mesa
    if t < T_SIT_END:
        return "Sitting", 1.0, None, 0.0, 0.0
    # sentarse en el borde (de pie -> posicion sentada del clip de tumbarse)
    if t < T_SEATED:
        w = smooth((t - T_SIT_END) / (T_SEATED - T_SIT_END))
        return "Sitting", 1.0, "Lying", 50.0, w
    # tumbarse
    if t < T_LIE_END:
        u = (t - T_SEATED) / (T_LIE_END - T_SEATED)
        return "Lying", 50.0 + u * 123.0, None, 0.0, 0.0
    # reposo supino: se mantiene el ultimo frame del clip de tumbarse
    if t < T_SITUP_START:
        return "Lying", 173.0, None, 0.0, 0.0
    # incorporarse (lying reverse hasta el frame sentado)
    if t < T_SITUP_END:
        u = (t - T_SITUP_START) / (T_SITUP_END - T_SITUP_START)
        return "Lying", 173.0 - u * 123.0, None, 0.0, 0.0
    # preparar pie
    if t < T_STAND_PREP_END:
        w = smooth((t - T_SITUP_END) / (T_STAND_PREP_END - T_SITUP_END))
        return "Lying", 50.0, "SitStand", 1.0, w
    # levantarse
    if t < T_STAND_END:
        u = (t - T_STAND_PREP_END) / (T_STAND_END - T_STAND_PREP_END)
        return "SitStand", 1.0 + u * 68.0, None, 0.0, 0.0
    # preparar salida
    if t < T_WALK_PREP_END:
        w = smooth((t - T_STAND_END) / (T_WALK_PREP_END - T_STAND_END))
        return "SitStand", 69.0, "Walking", 1.0, w
    # salir andando
    if t < T_WALKOUT_END:
        u = ((t - T_WALK_PREP_END) * FPS * WALK_RATE) % 31.0
        return "Walking", 1.0 + u, None, 0.0, 0.0
    # hold final (ya oculto)
    return "Sitting", 1.0, None, 0.0, 0.0

# ===========================================================================
# 1. personaje
# ===========================================================================
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = FPS

bpy.ops.import_scene.fbx(filepath=os.path.join(MANIQUI, "character.fbx"))
scene.render.fps = FPS

objects = {o.name: o for o in bpy.data.objects}
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
print("[char] armature", arm.name, "bones", len(arm.data.bones))

# La malla de la cabeza esta abierta por la coronilla (el gorro quirurgico la
# tapaba).  El pelo se construye duplicando la piel y cerrando ese hueco.
cap = bpy.data.objects.get("Ch16_Cap")
if cap:
    bpy.data.objects.remove(cap, do_unlink=True)
# Las pestañas 3D obligan a PNG con alfa (20 MB).  A distancia de simulacion no
# aportan nada: las pestañas ya estan pintadas en la textura de la cara.
lashes = bpy.data.objects.get("Ch16_Eyelashes")
if lashes:
    bpy.data.objects.remove(lashes, do_unlink=True)

body = bpy.data.objects["Ch16_Body1"]
shirt = bpy.data.objects["Ch16_Shirt"]
pants = bpy.data.objects["Ch16_Pants"]
shoes = bpy.data.objects["Ch16_Shoes"]
mask = bpy.data.objects["Ch16_Mask"]

# --- materiales -------------------------------------------------------------
def set_input(nt, bsdf, name, value):
    if name in bsdf.inputs:
        s = bsdf.inputs[name]
        for l in list(s.links):
            nt.links.remove(l)
        s.default_value = value

def opaque(mat):
    for attr, val in (("blend_method", "OPAQUE"),):
        try:
            setattr(mat, attr, val)
        except Exception:
            pass
    try:
        mat.surface_render_method = "DITHERED"
    except Exception:
        pass

def tune(mat, rough, spec, metal=0.0, kill_alpha=False, keep_blend=False):
    if not mat or not mat.use_nodes:
        return
    nt = mat.node_tree
    bsdf = nt.nodes.get("Principled BSDF")
    if not bsdf:
        return
    set_input(nt, bsdf, "Metallic", metal)
    set_input(nt, bsdf, "Roughness", rough)
    set_input(nt, bsdf, "Specular IOR Level", spec)
    if kill_alpha and "Alpha" in bsdf.inputs:
        s = bsdf.inputs["Alpha"]
        for l in list(s.links):
            nt.links.remove(l)
        s.default_value = 1.0
    if not keep_blend:
        opaque(mat)

mat_body = bpy.data.materials.get("Ch16_Body")
tune(mat_body, 0.55, 0.35, 0.0, kill_alpha=True)

mat_scrub = mat_body.copy()
mat_scrub.name = "Scrubs_Matte"
tune(mat_scrub, 0.90, 0.18, 0.0, kill_alpha=True)
for o in (shirt, pants):
    o.data.materials.clear()
    o.data.materials.append(mat_scrub)

mat_body1 = bpy.data.materials.get("Ch16_body1")
tune(mat_body1, 0.80, 0.25, 0.0, kill_alpha=True)

mat_lash = bpy.data.materials.get("Ch16_eyelashes")
if mat_lash:
    tune(mat_lash, 0.60, 0.30, 0.0, kill_alpha=False, keep_blend=True)
    try:
        mat_lash.blend_method = "CLIP"
        mat_lash.alpha_threshold = 0.5
    except Exception:
        pass

mat_slip = bpy.data.materials.new("Slippers")
mat_slip.use_nodes = True
sb = mat_slip.node_tree.nodes.get("Principled BSDF")
sb.inputs["Base Color"].default_value = (0.58, 0.61, 0.63, 1.0)
sb.inputs["Roughness"].default_value = 0.95
sb.inputs["Metallic"].default_value = 0.0
try:
    sb.inputs["Specular IOR Level"].default_value = 0.15
except Exception:
    pass
shoes.data.materials.clear()
shoes.data.materials.append(mat_slip)

print("[char] materials:",
      [m.name for m in (mat_body, mat_scrub, mat_body1, mat_lash, mat_slip) if m])

# --- pelo: casquete corto que sigue el craneo --------------------------------
def add_hair_shell(body, arm):
    vg = body.vertex_groups.get("mixamorig:Head")
    if not vg:
        print("[hair] sin grupo Head")
        return
    head_idx = vg.index

    # linea de nacimiento: frente alta, entradas en las sienes, nuca baja
    def front_line(x):
        ax = min(1.0, abs(x) / 0.078)
        return 1.660 + (1.682 - 1.660) * smooth(ax)

    def hairline(x, y):
        if y < -0.10:
            return front_line(x)
        if y < -0.04:
            f = front_line(x)
            return f + (1.635 - f) * smooth((y + 0.10) / 0.06)
        if y < 0.01:
            return 1.635
        if y < 0.05:
            return 1.635 + (1.575 - 1.635) * smooth((y - 0.01) / 0.04)
        return 1.575

    hair = body.copy()
    hair.data = body.data.copy()
    hair.name = "Hair_Shell"
    bpy.context.collection.objects.link(hair)
    mw = body.matrix_world.copy()
    inv = mw.inverted()
    bm = bmesh.new()
    bm.from_mesh(hair.data)
    bm.normal_update()

    # recortar todo lo que queda por debajo de la linea de nacimiento
    drop = []
    for f in bm.faces:
        c = mw @ f.calc_center_median()
        if c.z < hairline(c.x, c.y):
            drop.append(f)
    bmesh.ops.delete(bm, geom=drop, context='FACES')
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context='VERTS')

    # localizar el contorno de la coronilla: el borde del hueco mas alto (la
    # linea de nacimiento queda mucho mas abajo y no debe rellenarse)
    bm.edges.ensure_lookup_table()
    boundary = [e for e in bm.edges if len(e.link_faces) == 1]
    adj = {}
    for e in boundary:
        for v in e.verts:
            adj.setdefault(v, []).append(e)
    seen = set()
    loops = []
    for e0 in boundary:
        if e0 in seen:
            continue
        stack = [e0]
        comp = []
        while stack:
            e = stack.pop()
            if e in seen:
                continue
            seen.add(e)
            comp.append(e)
            for v in e.verts:
                for e2 in adj.get(v, []):
                    if e2 not in seen:
                        stack.append(e2)
        loops.append(comp)
    crown_edges = []
    if loops:
        def loop_z(comp):
            zs = [(mw @ v.co).z for e in comp for v in e.verts]
            return sum(zs) / len(zs)
        crown_edges = max(loops, key=loop_z)
    print("[hair] loops", [len(c) for c in loops],
          "crown z avg %.3f" % (sum((mw @ v.co).z for e in crown_edges
                                    for v in e.verts) / max(1, 2 * len(crown_edges))))
    filled = 0
    fill_center = None
    fill_top = 1.70
    if crown_edges:
        res = bmesh.ops.holes_fill(bm, edges=crown_edges, sides=0)
        fill_faces = [f for f in res.get("faces", []) if f.is_valid]
        dl = bm.verts.layers.deform.active
        for f in fill_faces:
            rim = list(f.verts)
            n = len(rim)
            if n < 3:
                continue
            rp = [mw @ v.co for v in rim]
            cx = sum(p.x for p in rp) / n
            cy = sum(p.y for p in rp) / n
            cz = sum(p.z for p in rp) / n
            height = 0.026
            ring_s = (0.68, 0.36)
            rings = []
            for s in ring_s:
                ring = []
                for p in rp:
                    q = Vector((cx + (p.x - cx) * s,
                                cy + (p.y - cy) * s,
                                cz + height * (1.0 - s * s)))
                    ring.append(bm.verts.new(inv @ q))
                rings.append(ring)
            c = bm.verts.new(inv @ Vector((cx, cy, cz + height)))
            for v in [vv for ring in rings for vv in ring] + [c]:
                if dl is not None:
                    v[dl][head_idx] = 1.0
            new_faces = []
            for i in range(n):
                j = (i + 1) % n
                new_faces.append(bm.faces.new((rim[i], rim[j], rings[0][j], rings[0][i])))
            for r in range(len(rings) - 1):
                a, b = rings[r], rings[r + 1]
                for i in range(n):
                    j = (i + 1) % n
                    new_faces.append(bm.faces.new((a[i], a[j], b[j], b[i])))
            a = rings[-1]
            for i in range(n):
                j = (i + 1) % n
                new_faces.append(bm.faces.new((a[i], a[j], c)))
            bmesh.ops.delete(bm, geom=[f], context='FACES_ONLY')
            bm.normal_update()
            if new_faces and sum((nf.normal.z for nf in new_faces), 0.0) < 0:
                for nf in new_faces:
                    nf.normal_flip()
            fill_center = c
            fill_top = cz + height
            filled = len(new_faces)

    # ningun vertice por debajo de la linea (picos de sienes y nuca)
    for v in bm.verts:
        p = mw @ v.co
        h = hairline(p.x, p.y)
        if p.z < h:
            p.z = h
            v.co = inv @ p

    # volumen: casi nulo en el borde y 6 mm en la coronilla
    bm.normal_update()
    for v in bm.verts:
        p = mw @ v.co
        h = max(0.0, p.z - hairline(p.x, p.y))
        f = min(1.0, h / 0.035)
        off = 0.0015 + f * (0.006 - 0.0015)
        v.co += v.normal * (off * 100.0)

    # el centro de la calota siempre arriba (evita que el hueco quede hundido)
    if fill_center is not None:
        p = mw @ fill_center.co
        p.z = max(p.z, fill_top + 0.004)
        fill_center.co = inv @ p

    bm.to_mesh(hair.data)
    bm.free()

    mat_hair = bpy.data.materials.new("Hair_Short")
    mat_hair.use_nodes = True
    bsdf = mat_hair.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (0.020, 0.012, 0.007, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.95
    bsdf.inputs["Metallic"].default_value = 0.0
    try:
        bsdf.inputs["Specular IOR Level"].default_value = 0.10
    except Exception:
        pass
    try:
        mat_hair.use_backface_culling = False
    except Exception:
        pass
    hair.data.materials.clear()
    hair.data.materials.append(mat_hair)
    for poly in hair.data.polygons:
        poly.use_smooth = True
        poly.material_index = 0

    bpy.ops.object.select_all(action='DESELECT')
    hair.select_set(True)
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.join()

    zs = [(body.matrix_world @ v.co).z for v in body.data.vertices]
    print("[hair] verts %d faces %d fill %d z %.4f..%.4f" %
          (len(body.data.vertices), len(body.data.polygons), filled,
           min(zs), max(zs)))

add_hair_shell(body, arm)

# --- texturas 2k ------------------------------------------------------------
for img in list(bpy.data.images):
    try:
        w, h = img.size
    except Exception:
        continue
    if w > 2048 or h > 2048:
        nw = 2048 if w >= h else max(1, int(round(w * 2048 / h)))
        nh = 2048 if h >= w else max(1, int(round(h * 2048 / w)))
        try:
            img.scale(nw, nh)
            img.pack()
            print("[tex]", img.name, nw, nh)
        except Exception as e:
            print("[tex] fallo", img.name, e)

# --- postura en reposo ------------------------------------------------------
arm.rotation_mode = "QUATERNION"
REST_Q = arm.rotation_quaternion.copy()
for pb in arm.pose.bones:
    pb.rotation_mode = "QUATERNION"
BONES = [pb.name for pb in arm.pose.bones]
print("[char] rest quat", tuple(round(v, 4) for v in REST_Q))

# ===========================================================================
# 2. importar clips y muestrear
# ===========================================================================
def purge_orphans():
    for _ in range(3):
        for coll in (bpy.data.meshes, bpy.data.materials, bpy.data.images,
                     bpy.data.armatures, bpy.data.actions, bpy.data.textures,
                     bpy.data.collections):
            for block in list(coll):
                try:
                    if block.users == 0:
                        coll.remove(block)
                except Exception:
                    pass

ACTIONS = {}
for key, fn in CLIPS:
    before = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(MANIQUI, fn))
    scene.render.fps = FPS
    new = [o for o in bpy.data.objects if o not in before]
    new_arm = next((o for o in new if o.type == "ARMATURE"), None)
    act = new_arm.animation_data.action if (new_arm and new_arm.animation_data) else None
    if not act:
        raise RuntimeError("sin action en " + fn)
    act.name = key
    act.use_fake_user = True
    ACTIONS[key] = act
    print("[clip]", key, "frames", tuple(act.frame_range))
    for o in new:
        bpy.data.objects.remove(o, do_unlink=True)
    purge_orphans()
    print("        objetos", len(bpy.data.objects), "acciones", len(bpy.data.actions))

# muestrear
CACHE = {}
for key, act in ACTIONS.items():
    f0 = int(round(act.frame_range[0]))
    f1 = int(round(act.frame_range[1]))
    # reset de la pose
    for pb in arm.pose.bones:
        pb.location = (0.0, 0.0, 0.0)
        pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
        pb.scale = (1.0, 1.0, 1.0)
    arm.animation_data_create()
    arm.animation_data.action = act
    arm.animation_data.action_slot = act.slots[0]
    loc = {b: [] for b in BONES}
    quat = {b: [] for b in BONES}
    scl = {b: [] for b in BONES}
    for f in range(f0, f1 + 1):
        scene.frame_set(f)
        for pb in arm.pose.bones:
            loc[pb.name].append(tuple(pb.location))
            quat[pb.name].append(tuple(pb.rotation_quaternion))
            scl[pb.name].append(tuple(pb.scale))
    CACHE[key] = {
        "f0": f0, "f1": f1,
        "loc": loc, "quat": quat, "scale": scl,
    }
    print("[sample]", key, f0, f1, "frames", f1 - f0 + 1, "t", round(time.time() - T0, 1))

# ===========================================================================
# 3. hornear accion unica
# ===========================================================================
def pose_at(key, src, out_loc, out_quat, out_scale):
    """Escribe en los dicts la pose interpolada del clip key en src (frame)."""
    c = CACHE[key]
    f0, f1 = c["f0"], c["f1"]
    x = max(f0, min(f1, src))
    i0 = int(math.floor(x))
    i1 = min(i0 + 1, f1)
    u = x - i0
    a0 = i0 - f0
    a1 = i1 - f0
    for b in BONES:
        l0 = c["loc"][b][a0]
        l1 = c["loc"][b][a1]
        q0 = Quaternion(c["quat"][b][a0])
        q1 = Quaternion(c["quat"][b][a1])
        s0 = c["scale"][b][a0]
        s1 = c["scale"][b][a1]
        if u <= 0.0:
            out_loc[b] = l0
            out_quat[b] = q0
            out_scale[b] = s0
        else:
            if q0.dot(q1) < 0.0:
                q1 = Quaternion((-q1.w, -q1.x, -q1.y, -q1.z))
            q = q0.slerp(q1, u)
            out_loc[b] = (lerp(l0[0], l1[0], u), lerp(l0[1], l1[1], u), lerp(l0[2], l1[2], u))
            out_quat[b] = q
            out_scale[b] = (lerp(s0[0], s1[0], u), lerp(s0[1], s1[1], u), lerp(s0[2], s1[2], u))

# buffers
loc_buf = {b: [] for b in BONES}
quat_buf = {b: [] for b in BONES}
scale_buf = {b: [] for b in BONES}
obj_loc = []
obj_quat = []

qa = {}
qb = {}
la = {}
lb = {}
sa = {}
sb = {}

base_q = Quaternion((math.cos(math.pi / 4.0), math.sin(math.pi / 4.0), 0.0, 0.0))  # Rx(+90)

for f in range(N_FRAMES + 1):
    t = f / FPS
    keyA, srcA, keyB, srcB, w = clip_state(t)
    pose_at(keyA, srcA, la, qa, sa)
    if keyB is not None and w > 0.0:
        pose_at(keyB, srcB, lb, qb, sb)
    else:
        w = 0.0

    # respiracion procedural durante el reposo supino (el clip de reposo
    # flexionaba las rodillas): se suma un giro minimo a la columna.
    breath = 0.0
    if T_LIE_END <= t < T_SITUP_START:
        env = smooth((t - T_LIE_END) / 0.9) * (1.0 - smooth((t - (T_SITUP_START - 0.9)) / 0.9))
        breath = 0.020 * env * math.sin(2.0 * math.pi * (t - T_LIE_END) / 4.2)

    for b in BONES:
        q0 = qa[b]
        s0 = sa[b]
        l0 = la[b]
        if w > 0.0:
            q1 = qb[b]
            if q0.dot(q1) < 0.0:
                q1 = Quaternion((-q1.w, -q1.x, -q1.y, -q1.z))
            q = q0.slerp(q1, w)
            l = (lerp(l0[0], lb[b][0], w), lerp(l0[1], lb[b][1], w), lerp(l0[2], lb[b][2], w))
            s = (lerp(s0[0], sb[b][0], w), lerp(s0[1], sb[b][1], w), lerp(s0[2], sb[b][2], w))
        else:
            q = q0
            l = l0
            s = s0
        if breath != 0.0:
            if b.endswith("Spine1"):
                q = q @ Quaternion((1.0, 0.0, 0.0), breath * 0.62)
            elif b.endswith("Spine2"):
                q = q @ Quaternion((1.0, 0.0, 0.0), breath * 0.38)
        loc_buf[b].append(l)
        quat_buf[b].append((q.w, q.x, q.y, q.z))
        scale_buf[b].append(s)

    x, y, z, rz = root_at(t)
    obj_loc.append((x, y, z))
    qz = Quaternion((0.0, 0.0, 1.0), math.radians(rz))
    q = qz @ base_q
    obj_quat.append((q.w, q.x, q.y, q.z))

# continuidad de signo
def fix_signs(buf):
    n = len(buf)
    if n == 0:
        return
    prev = buf[0]
    for i in range(1, n):
        q = buf[i]
        d = prev[0] * q[0] + prev[1] * q[1] + prev[2] * q[2] + prev[3] * q[3]
        if d < 0.0:
            q = (-q[0], -q[1], -q[2], -q[3])
            buf[i] = q
        prev = q

for b in BONES:
    fix_signs(quat_buf[b])
fix_signs(obj_quat)

# crear accion
arm.animation_data.action = None
for pb in arm.pose.bones:
    pb.location = (0.0, 0.0, 0.0)
    pb.rotation_quaternion = (1.0, 0.0, 0.0, 0.0)
    pb.scale = (1.0, 1.0, 1.0)
arm.location = (0.0, 0.0, 0.0)
arm.rotation_quaternion = REST_Q

act = bpy.data.actions.new("Sim")
act.use_fake_user = True
slot = act.slots.new(id_type="OBJECT", name="Sim")
layer = act.layers.new("Layer")
strip = layer.strips.new(type="KEYFRAME")
bag = strip.channelbag(slot, ensure=True)

nkeys = N_FRAMES + 1
frames = list(range(nkeys))

def add_fcurve(path, index, values, group=""):
    fc = bag.fcurves.new(path, index=index, group_name=group)
    fc.keyframe_points.add(nkeys)
    co = [0.0] * (2 * nkeys)
    for i, v in enumerate(values):
        co[2 * i] = float(frames[i])
        co[2 * i + 1] = float(v)
    fc.keyframe_points.foreach_set("co", co)
    try:
        fc.keyframe_points.foreach_set("interpolation", [1] * nkeys)
    except Exception:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    fc.update()
    return fc

for b in BONES:
    p = 'pose.bones["%s"]' % b
    for i in range(3):
        add_fcurve(p + ".location", i, [v[i] for v in loc_buf[b]], b)
    for i in range(4):
        add_fcurve(p + ".rotation_quaternion", i, [v[i] for v in quat_buf[b]], b)
    for i in range(3):
        add_fcurve(p + ".scale", i, [v[i] for v in scale_buf[b]], b)

for i in range(3):
    add_fcurve("location", i, [v[i] for v in obj_loc], "Object")
for i in range(4):
    add_fcurve("rotation_quaternion", i, [v[i] for v in obj_quat], "Object")

act.use_frame_range = True
act.frame_start = 0.0
act.frame_end = float(N_FRAMES)

arm.animation_data.action = act
arm.animation_data.action_slot = slot
scene.frame_start = 0
scene.frame_end = N_FRAMES
scene.frame_set(0)
print("[bake] fcurves", len(bag.fcurves), "keys", nkeys, "t", round(time.time() - T0, 1))

# eliminar acciones fuente
for key, a in ACTIONS.items():
    try:
        bpy.data.actions.remove(a)
    except Exception as e:
        print("[actions] no se pudo borrar", key, e)
purge_orphans()
print("[actions] quedan", [a.name for a in bpy.data.actions])

# ===========================================================================
# 4. exportar
# ===========================================================================
os.makedirs(os.path.dirname(OUT_GLB), exist_ok=True)
bpy.ops.export_scene.gltf(
    filepath=OUT_GLB,
    export_format="GLB",
    use_selection=False,
    export_apply=False,
    export_animations=True,
    export_animation_mode="ACTIONS",
    export_frame_range=True,
    export_force_sampling=True,
    export_yup=True,
    export_skins=True,
    export_morph=False,
    export_materials="EXPORT",
    export_texcoords=True,
    export_normals=True,
    export_image_format="JPEG",
    export_image_quality=90,
    export_cameras=False,
    export_lights=False,
)
print("[export]", OUT_GLB, os.path.getsize(OUT_GLB), "bytes")
print("[done] t", round(time.time() - T0, 1))
