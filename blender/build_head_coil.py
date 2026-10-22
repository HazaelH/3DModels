"""Bobina de cabeza (RF) del MERIDIAN 3T â€” pieza independiente del GLB del equipo.

Se exporta como models/head_coil.glb con dos nodos:

  COIL_Base   la cuna que apoya en la mesa (origen en el centro de la base, z=0)
  COIL_Top    la cÃºpula, con el **origen en la bisagra** trasera: girando su
              rotation.x en three.js se abre y se cierra sobre el paciente.

Asi la simulacion la cierra como una visera en vez de dejar caer una rejilla
desde arriba. No toca los 32 nodos MRI_*: es un GLB aparte, igual que el maniqui.

    blender -b -P blender/build_head_coil.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m3t_lib as L  # noqa: E402

import bmesh  # noqa: E402
from mathutils import Vector  # noqa: E402

OUT = os.path.join(L.MODELS, "head_coil.glb")

# ---------------------------------------------------------------- medidas (m)
CRADLE_H = 0.045            # grosor de la cuna
A = 0.175                   # semiancho interior de la cupula
B = 0.255                   # altura interior de la cupula sobre el borde
HALF_Y = 0.190              # media longitud
HINGE = (0.0, HALF_Y + 0.012, 0.050)   # bisagra en el borde trasero


def set_origin(o, p):
    p = Vector(p)
    for v in o.data.vertices:
        v.co -= p
    o.data.update()
    o.location = p


def dome(name, a, b, z0, hy, seg=40):
    """Media boveda solida (elipse en XZ) cerrada en los dos extremos."""
    bm = bmesh.new()
    rings = []
    for yy in (-hy, hy):
        ring = [bm.verts.new((a * math.cos(math.pi * i / seg), yy,
                              z0 + b * math.sin(math.pi * i / seg)))
                for i in range(seg + 1)]
        rings.append(ring)
    for i in range(seg):
        bm.faces.new((rings[0][i], rings[0][i + 1], rings[1][i + 1], rings[1][i]))
    for k, yy in enumerate((-hy, hy)):
        c = bm.verts.new((0.0, yy, z0))
        for i in range(seg):
            bm.faces.new((rings[k][i], rings[k][i + 1], c))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return L._mesh_from_bm(name, bm)


def arc_band(name, a, b, z0, hy, th0, th1, off=0.003, thick=0.007, seg=14):
    """Banda curva pegada a la boveda: la tira de luz que se enciende al escanear."""
    bm = bmesh.new()
    rows = []
    for yy in (-hy, hy):
        outer, inner = [], []
        for i in range(seg + 1):
            th = th0 + (th1 - th0) * i / seg
            outer.append(bm.verts.new(((a + off) * math.cos(th), yy,
                                       z0 + (b + off) * math.sin(th))))
            inner.append(bm.verts.new(((a + off - thick) * math.cos(th), yy,
                                       z0 + (b + off - thick) * math.sin(th))))
        rows.append((outer, inner))
    (o0, i0), (o1, i1) = rows
    for i in range(seg):
        bm.faces.new((o0[i], o0[i + 1], o1[i + 1], o1[i]))      # cara exterior
        bm.faces.new((i0[i + 1], i0[i], i1[i], i1[i + 1]))      # cara interior
        bm.faces.new((i0[i], i0[i + 1], o0[i + 1], o0[i]))      # canto delantero
        bm.faces.new((o1[i], o1[i + 1], i1[i + 1], i1[i]))      # canto trasero
    bm.faces.new((o0[0], i0[0], i1[0], o1[0]))
    bm.faces.new((i0[seg], o0[seg], o1[seg], i1[seg]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return L._mesh_from_bm(name, bm)


def main():
    L.reset()

    shell = L.new_material("COIL_Shell", (0.760, 0.780, 0.800), roughness=0.30, coat=0.35)
    window = L.new_material("COIL_Window", (0.560, 0.630, 0.690), metallic=0.12,
                            roughness=0.08, coat=0.9, coat_rough=0.04)
    trim = L.new_material("COIL_Trim", (0.085, 0.095, 0.105), roughness=0.42)
    foam = L.new_material("COIL_Foam", (0.150, 0.160, 0.175), roughness=0.88)
    light = L.new_material("COIL_Light", (0.18, 0.70, 0.62), roughness=0.35,
                           emission=(0.22, 0.92, 0.80), emission_strength=5.0)

    # ------------------------------------------------------------ COIL_Base
    plate = L.box("base_plate", (0.360, 0.420, CRADLE_H), (0.0, 0.0, CRADLE_H * 0.5))
    L.assign(plate, shell)
    parts = []
    for sx in (-1, 1):
        parts.append(L.box("base_rail", (0.018, 0.390, 0.026),
                           (sx * 0.176, 0.0, CRADLE_H + 0.011)))
    parts.append(L.box("base_conn", (0.085, 0.052, 0.042), (0.0, HALF_Y + 0.020, CRADLE_H + 0.018)))
    parts.append(L.cylinder("base_cable", 0.012, 0.080, (0.0, HALF_Y + 0.060, CRADLE_H + 0.008),
                            axis="Y", segments=16))
    parts.append(L.box("base_pad", (0.250, 0.300, 0.008), (0.0, -0.010, CRADLE_H + 0.004)))
    for sx in (-1, 1):
        for sy in (-1, 1):
            parts.append(L.cylinder("base_screw", 0.0065, 0.006,
                                    (sx * 0.150, sy * 0.180, CRADLE_H + 0.002),
                                    axis="Z", segments=12))
    for p in parts:
        if p.name.startswith("base_pad"):
            L.assign(p, foam)
        elif p.name.startswith("base_rail"):
            L.assign(p, shell)
        else:
            L.assign(p, trim)
    L.join_into(plate, parts)
    L.bevel_object(plate, max_width=0.0040)
    plate.name = "COIL_Base"

    # ------------------------------------------------------------- COIL_Top
    cup = dome("top_dome", A, B, CRADLE_H, HALF_Y)

    # ventana superior: deja ver la cara del paciente durante la exploración
    bm = bmesh.new()
    bm.from_mesh(cup.data)
    kill = []
    for f in bm.faces:
        c = f.calc_center_median()
        if abs(c.x) < 0.088 and -0.105 < c.y < 0.065 and c.z > CRADLE_H + 0.165:
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bm.to_mesh(cup.data)
    bm.free()
    cup.data.update()
    sol = cup.modifiers.new("SOL", "SOLIDIFY")
    sol.thickness = 0.006
    sol.offset = 0.0
    L.activate(cup)
    bpy.ops.object.modifier_apply(modifier=sol.name)

    L.assign(cup, shell)

    band = arc_band("top_band", A, B, CRADLE_H, HALF_Y - 0.012,
                    math.radians(24), math.radians(38))
    L.assign(band, light)
    band2 = arc_band("top_band2", A, B, CRADLE_H, HALF_Y - 0.012,
                     math.radians(142), math.radians(156))
    L.assign(band2, light)

    extra = []
    # pestillos delanteros (lado cara)
    for sx in (-1, 1):
        extra.append(L.box("top_latch", (0.034, 0.026, 0.052),
                           (sx * 0.115, -HALF_Y - 0.004, CRADLE_H + 0.026)))
    # conector trasero y cable
    extra.append(L.box("top_conn", (0.070, 0.034, 0.040), (0.0, HALF_Y + 0.006, CRADLE_H + 0.055)))
    extra.append(L.cylinder("top_cable", 0.010, 0.060, (0.0, HALF_Y + 0.045, CRADLE_H + 0.040),
                            axis="Y", segments=12))
    # 4 tornillos en los laterales de la cupula
    for sx in (-1, 1):
        for sy in (-1, 1):
            extra.append(L.cylinder("top_screw", 0.0055, 0.006,
                                    (sx * (A * 0.86), sy * 0.095, CRADLE_H + 0.128),
                                    axis="X", segments=12))
    # placa oscura en el frontal: la ventana de la cara
    extra.append(L.box("top_visor", (0.150, 0.012, 0.090),
                       (0.0, -HALF_Y - 0.002, CRADLE_H + 0.120)))
    for p in extra:
        L.assign(p, window if p.name.startswith("top_visor") else trim)

    L.join_into(cup, extra + [band, band2])
    L.bevel_object(cup, max_width=0.0030)
    cup.name = "COIL_Top"

    set_origin(cup, HINGE)

    L.log("base tris", len(plate.data.loop_triangles), "top tris", len(cup.data.loop_triangles))
    L.log("bisagra", HINGE)
    L.export_glb(OUT)
    L.save_blend(os.path.join(L.OUT, "head_coil.blend"))
    L.log("nodos:", [o.name for o in bpy.data.objects if o.type == "MESH"])


if __name__ == "__main__":
    import bpy  # noqa: F401
    main()

