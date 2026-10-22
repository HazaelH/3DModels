"""Pase de realismo MERIDIAN 3T.

Trabaja sobre el GLB original (models/_src/MRI_v1.glb), nunca lo sobrescribe,
y escribe models/MRI_Realista_Modular.glb + blender/out/meridian_3t.blend.

Etapas (se pueden ejecutar por separado con --stage):
    bevel      bisel + normales ponderadas en las 32 piezas
    materials  PBR: clearcoat, anisotropia, sheen, emision, paleta con contraste
    details    detalle fino unido dentro de las piezas (el nodo conserva su nombre)
    export     valida los 32 nombres y exporta

Uso:
    blender -b -P blender/realism_pass.py -- --stage bevel,materials,details,export
"""
import os
import sys
import math

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import m3t_lib as L  # noqa: E402

GRAPHITE = (0.055, 0.060, 0.072)
LABEL = (0.045, 0.048, 0.055)
STEEL = (0.52, 0.54, 0.57)


# ------------------------------------------------------------------ bevel
def stage_bevel():
    L.log("--- etapa bevel ---")
    total_before = L.tri_count()
    report = []
    for o in sorted(L.meshes(), key=lambda x: x.name):
        o.data.calc_loop_triangles()
        t0 = len(o.data.loop_triangles)
        w = L.bevel_object(o, max_width=0.0032)
        o.data.calc_loop_triangles()
        t1 = len(o.data.loop_triangles)
        report.append((o.name, t0, t1, round(w * 1000, 2)))
    L.log("bevel:", total_before, "->", L.tri_count())
    for name, t0, t1, w in report:
        L.log("  %-24s %6d -> %6d  (%.1f mm)" % (name, t0, t1, w))


# -------------------------------------------------------------- materiales
def stage_materials():
    L.log("--- etapa materials ---")
    m = bpy.data.materials

    def mat(name):
        x = m.get(name)
        if x is None:
            L.log("AVISO material ausente:", name)
        return x

    # Paleta con contraste: la carcasa clara no puede ser 0.88 (se quema en ACES)
    palette = {
        # carcasa principal: blanco clinico (0.66: con ACES, mas se quema)
        "MRI_White_ABS":  (0.660, 0.672, 0.685),
        # cubiertas: gris claro diferenciado, es lo que da volumen al gantry
        "MRI_Grey_Panel": (0.420, 0.442, 0.470),
        # consola, mesa: gris medio
        "MRI_Light_Grey": (0.500, 0.515, 0.535),
        # bancada y rejillas
        "MRI_Medium_Grey": (0.175, 0.190, 0.212),
        # patas y laser
        "MRI_Dark_Base":  (0.040, 0.044, 0.052),
        # aro teal: el unico saturado
        "MRI_Accent":     (0.020, 0.400, 0.470),
        # interior del bore
        "MRI_Bore_Liner": (0.300, 0.315, 0.335),
        # colchon: azul clinico
        "MRI_Cushion":    (0.165, 0.300, 0.430),
        "MRI_Emergency_Red": (0.480, 0.030, 0.030),
        "MRI_Screen":     (0.010, 0.011, 0.014),
    }
    for name, rgb in palette.items():
        x = mat(name)
        if x:
            L.set_in(x, "Base Color", rgb)

    # Laca de panel: clearcoat en todos los plasticos pintados
    coats = {
        "MRI_White_ABS":  (0.55, 0.14),
        "MRI_Grey_Panel": (0.70, 0.09),
        "MRI_Light_Grey": (0.45, 0.14),
        "MRI_Medium_Grey": (0.40, 0.18),
        "MRI_Dark_Base":  (0.25, 0.25),
        "MRI_Accent":     (0.60, 0.06),
        "MRI_Bore_Liner": (0.35, 0.10),
        "MRI_Emergency_Red": (0.50, 0.12),
    }
    for name, (cw, cr) in coats.items():
        x = mat(name)
        if x:
            L.set_in(x, "Coat Weight", cw)
            L.set_in(x, "Coat Roughness", cr)

    # Aluminio cepillado: anisotropia (KHR_materials_anisotropy)
    alu = mat("MRI_Brushed_Alu")
    if alu:
        L.set_in(alu, "Anisotropic", 0.65)
        L.set_in(alu, "Coat Weight", 0.0)

    # Colchon: sheen textil
    cu = mat("MRI_Cushion")
    if cu:
        L.set_in(cu, "Sheen Weight", 0.70)
        L.set_in(cu, "Sheen Roughness", 0.32)
        L.set_in(cu, "Sheen Tint", (0.62, 0.74, 0.92, 1.0))
        # el tejido a 512 px se marca demasiado: bajar la fuerza del normal map
        for node in cu.node_tree.nodes:
            if node.type == "NORMAL_MAP" and "Strength" in node.inputs:
                node.inputs["Strength"].default_value = 0.12

    # Normal maps: a fuerza 1.0 el ruido de 512 px se convierte en grano visible.
    # En primeros planos (tunel) el plastico parecia porexpan: muy por debajo de 0.1.
    for name, strength in (("MRI_White_ABS", 0.05), ("MRI_Grey_Panel", 0.08),
                           ("MRI_Light_Grey", 0.06), ("MRI_Medium_Grey", 0.11),
                           ("MRI_Bore_Liner", 0.09), ("MRI_Accent", 0.15),
                           ("MRI_Brushed_Alu", 0.12)):
        x = mat(name)
        if not x:
            continue
        for node in x.node_tree.nodes:
            if node.type == "NORMAL_MAP" and "Strength" in node.inputs:
                node.inputs["Strength"].default_value = strength

    # Emisiones
    for name, strength in (("MRI_Bore_Light", 7.0), ("MRI_Screen", 4.5)):
        x = mat(name)
        if x:
            L.set_in(x, "Emission Strength", strength)

    # Todos los materiales cerrados: una cara (mejor rendimiento y coincide con three.js).
    # El liner del bore es un tubo abierto: debe verse por dentro, asi que no se cull.
    for x in m:
        x.use_backface_culling = True
    liner = mat("MRI_Bore_Liner")
    if liner:
        liner.use_backface_culling = False

    L.log("materiales actualizados:", len(m))


# ----------------------------------------------------------------- detalle
def _mat(name, **kw):
    x = bpy.data.materials.get(name)
    if x is None:
        x = L.new_material(name, **kw)
    return x


def _m(name, fallback):
    return bpy.data.materials.get(name) or fallback


def _ball(name, r, loc, u=20, v=12):
    import bmesh as _bm
    from mathutils import Vector as _V
    bm = _bm.new()
    _bm.ops.create_uvsphere(bm, u_segments=u, v_segments=v, radius=r)
    for vert in bm.verts:
        vert.co += _V(loc)
    return L._mesh_from_bm(name, bm)


def detail_console(graphite, steel, rubber):
    """Consola: bisel de monitor, teclado, trackball, rejillas, rodapie y cable.

    Todo se une a las piezas existentes (MRI_Console_*), asi que el contrato de
    32 nodos no cambia. Medidas reales de la consola del GLB:
      cuerpo  x 1.610..2.090   y -2.190..-1.710   z 0.075..1.025
      pantalla x 1.620..2.080  y -2.110..-1.890  z 0.964..1.316
      bandeja x 1.630..2.070   y -2.380..-2.080  z 0.965..0.995
    """
    L.log("--- consola: detalle mecanico ---")
    light = _m("MRI_Light_Grey", graphite)
    white = _m("MRI_White_ABS", light)
    led = _mat("MRI_LED", base=(0.02, 0.24, 0.21), emission=(0.18, 0.95, 0.80),
               emission_strength=4.0, roughness=0.30)
    yellow = _mat("MRI_Safety_Yellow", base=(0.86, 0.62, 0.04), roughness=0.44)
    red = _mat("MRI_Emergency_Red", base=(0.60, 0.025, 0.025), roughness=0.36, coat=0.30)

    body = L.obj("MRI_Console_Body")
    screen = L.obj("MRI_Console_Screen")
    # el GLB modela el monitor como una losa de 22 cm: lo adelgazo dejando la
    # cara frontal en su sitio (las UV ya estan proyectadas y no cambian)
    L.reshape_world(screen, (1.850, -2.110, 1.140), (1.0, 0.40, 1.0))
    tray = L.obj("MRI_Console_Tray")
    base = L.obj("MRI_Console_Base")
    boton = L.obj("MRI_Emergency_Button")

    # ---- 1) bisel del monitor: da espesor y cubre el borde de la textura
    bez = []
    yf = -2.110                      # cara frontal de la pantalla (mira a -Y)
    z0, z1 = 0.966, 1.316
    x0, x1 = 1.620, 2.080
    def add(lista, name, size, loc, mat):
        b = L.box(name, size, loc)
        L.assign(b, mat)
        lista.append(b)
        return b
    add(bez, "BEZEL_L", (0.028, 0.020, z1 - z0), (x0 + 0.012, yf - 0.008, (z0 + z1) / 2), graphite)
    add(bez, "BEZEL_R", (0.028, 0.020, z1 - z0), (x1 - 0.012, yf - 0.008, (z0 + z1) / 2), graphite)
    add(bez, "BEZEL_T", (x1 - x0, 0.020, 0.026), ((x0 + x1) / 2, yf - 0.008, z1 - 0.012), graphite)
    add(bez, "BEZEL_B", (x1 - x0, 0.022, 0.048), ((x0 + x1) / 2, yf - 0.009, z0 + 0.023), graphite)
    # carcasa del monitor: tapa los cantos (el UV de la pantalla se veia de perfil)
    add(bez, "MON_L", (0.006, 0.096, z1 - z0), (x0 - 0.002, -2.066, (z0 + z1) / 2), graphite)
    add(bez, "MON_R", (0.006, 0.096, z1 - z0), (x1 + 0.002, -2.066, (z0 + z1) / 2), graphite)
    add(bez, "MON_T", (x1 - x0 + 0.010, 0.096, 0.006), ((x0 + x1) / 2, -2.066, z1 + 0.002), graphite)
    add(bez, "MON_B", (x1 - x0 + 0.010, 0.006, z1 - z0), ((x0 + x1) / 2, -2.025, (z0 + z1) / 2), graphite)
    # piloto de encendido y rotulo en la mentonera
    add(bez, "BEZEL_LED", (0.008, 0.004, 0.008), (2.052, yf - 0.020, z0 + 0.022), led)
    seam = L.box("BEZEL_SEAM", (x1 - x0 - 0.06, 0.004, 0.003), ((x0 + x1) / 2, yf - 0.020, z0 + 0.043))
    L.assign(seam, steel)
    bez.append(seam)
    try:
        t = L.text_mesh("BEZEL_MARK", "MERIDIAN", 0.013, (1.760, yf - 0.020, z0 + 0.022),
                        extrude=0.0004)
        L.assign(t, steel)
        bez.append(t)
    except Exception as exc:  # noqa: BLE001
        L.log("AVISO rotulo bisel:", exc)
    L.join_into(screen, bez)

    # ---- 2) collar de goma donde la pantalla sale del cuerpo
    collar = L.box("SCREEN_COLLAR", (0.492, 0.112, 0.010), (1.850, -2.055, 1.026))
    L.assign(collar, rubber)
    L.bevel_object(collar, max_width=0.0015)
    L.join_into(body, [collar])

    # ---- 3) cuerpo: costuras, tornillos, rejillas laterales y asa frontal
    det = []
    for x in (1.700, 2.000):
        add(det, "BODY_SEAM", (0.004, 0.006, 0.860), (x, -2.192, 0.530), graphite)
    for x in (1.642, 2.058):
        for z in (0.120, 0.900):
            add(det, "BODY_SCREW", (0.010, 0.006, 0.010), (x, -2.192, z), steel)
    add(det, "BODY_PULL", (0.240, 0.010, 0.034), (1.850, -2.196, 0.830), graphite)
    for sx, x in ((-1, 1.610), (1, 2.090)):
        for i in range(6):
            add(det, "CONSOLE_VENT", (0.007, 0.150, 0.010), (x, -2.020, 0.400 + 0.028 * i), graphite)
    L.join_into(body, det)

    # ---- 4) bandeja: teclado, trackball, botones y faldon frontal
    tr = []
    add(tr, "TRAY_LIP", (0.440, 0.018, 0.024), (1.850, -2.370, 0.999), graphite)
    add(tr, "KEYBOARD", (0.300, 0.112, 0.014), (1.775, -2.196, 1.004), light)
    for i in range(5):
        add(tr, "KEY_ROW", (0.272, 0.014, 0.006), (1.775, -2.244 + 0.0225 * i, 1.012), white)
    add(tr, "KEY_SPACE", (0.128, 0.014, 0.007), (1.775, -2.136, 1.012), white)
    add(tr, "BALL_CUP", (0.054, 0.054, 0.008), (2.000, -2.320, 1.000), graphite)
    ball = _ball("TRACKBALL", 0.021, (2.000, -2.320, 1.006))
    L.assign(ball, graphite)
    tr.append(ball)
    for dx in (-0.030, 0.030):
        add(tr, "BALL_KEY", (0.020, 0.014, 0.006), (2.000 + dx, -2.372, 1.000), white)
    # faldon que cierra la bandeja por delante y a los lados
    add(tr, "TRAY_APRON", (0.420, 0.018, 0.086), (1.850, -2.302, 0.936), light)
    for x in (1.652, 2.048):
        add(tr, "TRAY_SIDE", (0.016, 0.140, 0.086), (x, -2.290, 0.936), light)
    L.join_into(tray, tr)

    # ---- 5) base: rodapie de goma, gromet y cable de red
    bs = []
    add(bs, "CONSOLE_KICK", (0.558, 0.558, 0.026), (1.850, -1.950, 0.019), rubber)
    add(bs, "CABLE_GROMMET", (0.048, 0.014, 0.048), (1.720, -1.678, 0.070), graphite)
    g1 = L.cylinder("CABLE_A", 0.013, 0.110, (1.720, -1.630, 0.070), axis="Y", segments=12)
    L.assign(g1, rubber)
    bs.append(g1)
    g2 = L.cylinder("CABLE_B", 0.013, 0.074, (1.720, -1.580, 0.038), axis="Z", segments=12)
    L.assign(g2, rubber)
    bs.append(g2)
    L.join_into(base, bs)

    # ---- 6) seta de emergencia: base amarilla, collar negro y pulsador rojo
    c = boton.matrix_world.translation.copy()
    L.reshape_world(boton, (c.x, c.y, 1.025), (1.0, 1.0, 0.26))
    boton.data.materials.clear()
    boton.data.materials.append(yellow)
    em = []
    for r, h, z, mat in ((0.050, 0.012, 1.040, graphite),
                         (0.038, 0.014, 1.052, red),
                         (0.030, 0.008, 1.062, red)):
        b = L.cylinder("ESTOP_%02d" % int(z * 1000), r, h, (2.000, -2.180, z),
                       axis="Z", segments=28)
        L.assign(b, mat)
        em.append(b)
    L.join_into(boton, em)

    L.log("consola OK")


def detail_table(graphite, steel, rubber):
    """Base, columna y carro de la mesa: paneles de acceso, fuelles y carenados."""
    L.log("--- mesa: detalle mecanico ---")
    light = _m("MRI_Light_Grey", graphite)
    base = L.obj("MRI_Table_Base")
    column = L.obj("MRI_Table_Column")
    carriage = L.obj("MRI_Table_Carriage")

    det = []
    # ---- 1) paneles de acceso laterales con junta de goma y tornillos
    for sx in (-1, 1):
        x = sx * 0.316
        g = L.box("BASE_GASKET", (0.008, 0.440, 0.150), (x, -1.850, 0.118))
        L.assign(g, rubber)
        det.append(g)
        p = L.box("BASE_PANEL", (0.007, 0.400, 0.120), (sx * 0.3185, -1.850, 0.118))
        L.assign(p, light)
        det.append(p)
        for dy in (-0.170, 0.170):
            for dz in (-0.040, 0.040):
                s = L.cylinder("BASE_SCREW", 0.0055, 0.006,
                               (sx * 0.323, -1.850 + dy, 0.118 + dz), axis="X", segments=12)
                L.assign(s, steel)
                det.append(s)

    # ---- 2) moldura superior y tapa de servicio al pie de la mesa
    lip = L.box("BASE_LIP", (0.638, 0.968, 0.016), (0.0, -1.850, 0.210))
    L.assign(lip, light)
    L.bevel_object(lip, max_width=0.0016)
    det.append(lip)
    for sz, y in ((-1, -2.333), (1, -1.367)):
        hg = L.box("HATCH_GASKET", (0.300, 0.009, 0.132), (0.0, y + sz * 0.003, 0.112))
        L.assign(hg, rubber)
        det.append(hg)
        hp = L.box("HATCH", (0.268, 0.010, 0.100), (0.0, y + sz * 0.007, 0.112))
        L.assign(hp, light)
        det.append(hp)
        for dx in (-0.112, 0.112):
            s = L.cylinder("HATCH_SCREW", 0.006, 0.006, (dx, y + sz * 0.013, 0.112),
                           axis="Y", segments=12)
            L.assign(s, steel)
            det.append(s)
    L.join_into(base, det)

    # ---- 3) columna: tres camisas telescopicas con junta cromada
    col = []
    for size, z, mat in (((0.438, 0.558, 0.150), 0.302, light),
                         ((0.420, 0.540, 0.132), 0.430, light),
                         ((0.404, 0.524, 0.120), 0.556, light)):
        b = L.box("COLUMN_SLEEVE", size, (0.0, -1.850, z))
        L.assign(b, mat)
        L.bevel_object(b, max_width=0.0016)
        col.append(b)
        j = L.box("COLUMN_JOINT", (size[0] + 0.006, size[1] + 0.006, 0.010),
                  (0.0, -1.850, z + size[2] / 2 - 0.004))
        L.assign(j, steel)
        col.append(j)
    L.join_into(column, col)

    # ---- 4) carro: carenados laterales, banda de junta y cadena de cables
    car = []
    for sx in (-1, 1):
        c = L.box("CARRIAGE_COVER", (0.012, 1.620, 0.066), (sx * 0.176, -1.500, 0.735))
        L.assign(c, light)
        L.bevel_object(c, max_width=0.0014)
        car.append(c)
        j = L.box("CARRIAGE_JOINT", (0.006, 1.620, 0.008), (sx * 0.177, -1.500, 0.699))
        L.assign(j, graphite)
        car.append(j)
    for i in range(6):
        link = L.box("CABLE_LINK", (0.042, 0.036, 0.024),
                     (0.222, -1.588 + 0.042 * i, 0.662 - 0.004 * i))
        L.assign(link, graphite)
        car.append(link)
    L.join_into(carriage, car)

    L.log("mesa OK")


def stage_details():
    L.log("--- etapa details ---")
    graphite = _mat("MRI_Graphite", base=GRAPHITE, metallic=0.25, roughness=0.30,
                    coat=0.45, coat_rough=0.12)
    label = _mat("MRI_Label", base=LABEL, metallic=0.0, roughness=0.55)
    steel = _mat("MRI_Steel", base=STEEL, metallic=1.0, roughness=0.28)
    rubber = _mat("MRI_Rubber", base=(0.030, 0.031, 0.034), metallic=0.0, roughness=0.72)

    # 1. Aro grafito alrededor del túnel: el "ojo" del equipo.
    #    El flange cromado llega a r=0.419, la cubierta frontal a r=0.99.
    ring = L.annulus("DARK_SURROUND", 0.428, 0.600, y=-0.620, thickness=0.009, segments=80)
    L.assign(ring, graphite)
    L.bevel_object(ring, max_width=0.0018)
    L.join_into(L.obj("MRI_Front_Cover"), [ring])

    # 2. Junta de goma entre cubierta y gantry (línea de sombra)
    for r in (0.760, 0.905):
        seam = L.torus("SEAM_%.3f" % r, r, 0.0032, y=-0.6085, major_seg=96, minor_seg=8,
                       zc=1.05)
        L.assign(seam, rubber)
        L.join_into(L.obj("MRI_Front_Cover"), [seam])

    # 2b. Garganta oscura dentro de la boca: profundidad real del túnel
    throat = L.annulus("DARK_THROAT", 0.350, 0.420, y=-0.548, thickness=0.008, segments=80)
    L.assign(throat, graphite)
    L.join_into(L.obj("MRI_Front_Cover"), [throat])

    # 2c. Juntas del barril: rompen el gantry en tres segmentos fabricados
    barrel = []
    for y in (-0.552, -0.32, 0.32):
        seam = L.torus("BARREL_SEAM_%.3f" % y, 1.0015, 0.0038, y=y, major_seg=96,
                       minor_seg=8, zc=1.05)
        L.assign(seam, rubber)
        barrel.append(seam)
    L.join_into(L.obj("MRI_Gantry_Core"), barrel)

    # 3. Tornilleria del flange del túnel (16 tornillos)
    screws = []
    for i in range(16):
        a = 2 * math.pi * i / 16 + math.pi / 16
        x = 0.395 * math.cos(a)
        z = 1.05 + 0.395 * math.sin(a)
        s = L.cylinder("SCREW_%02d" % i, 0.0062, 0.010, (x, -0.626, z), axis="Y", segments=16)
        L.assign(s, steel)
        screws.append(s)
        slot = L.box("SLOT_%02d" % i, (0.0055, 0.0012, 0.0012), (x, -0.6315, z))
        L.assign(slot, graphite)
        screws.append(slot)
    L.join_into(L.obj("MRI_Bore_Trim"), screws)

    # 4. Costuras del liner del túnel: tres anillos finos dan profundidad
    seams = []
    for y in (-0.26, 0.02, 0.30):
        t = L.torus("LINER_SEAM_%.2f" % y, 0.3445, 0.0038, y=y, major_seg=72, minor_seg=8,
                    zc=1.05)
        L.assign(t, graphite)
        seams.append(t)
    L.join_into(L.obj("MRI_Bore_Tunnel"), seams)

    # 5. Faldón oscuro bajo la bancada (hueco de sombra)
    skirt = L.box("PLINTH_SKIRT", (1.732, 1.432, 0.030), (0.0, 0.0, 0.015))
    L.assign(skirt, graphite)
    L.bevel_object(skirt, max_width=0.0012)
    L.join_into(L.obj("MRI_Base_Plinth"), [skirt])

    # 6. Bajo la mesa: banda oscura que separa el colchon del suelo
    under = L.box("TABLE_UNDER", (0.620, 2.250, 0.028), (0.0, -1.700, 0.766))
    L.assign(under, graphite)
    L.bevel_object(under, max_width=0.0012)
    L.join_into(L.obj("MRI_Table_Surface"), [under])

    # 6b. Paneles laterales y rejillas: son placas PLANAS y atravesaban el barril
    #     curvo (de ahi la placa blanca suelta en el render). Se reencajan dentro.
    for name, dx in (("MRI_Side_Panel_L", 0.05), ("MRI_Side_Panel_R", -0.05)):
        o = L.obj(name)
        c = o.matrix_world.translation.copy()
        L.reshape_world(o, (c.x, 0.0, 1.05), (1.0, 0.80, 0.70))
        L.translate_world(o, (dx, 0.0, 0.0))
    for name, dx in (("MRI_Vent_Grille_L", 0.08), ("MRI_Vent_Grille_R", -0.08)):
        o = L.obj(name)
        c = o.matrix_world.translation.copy()
        L.reshape_world(o, (c.x, 0.0, 1.05), (1.0, 0.90, 0.90))
        L.translate_world(o, (dx, 0.0, 0.0))

    # 6c. Asas: barra vertical + dos soportes oscuros (antes eran dos palos sueltos;
    #     acortarlas las convertia en pastillas flotantes, asi que se mantiene el largo)
    for side in ("L", "R"):
        h = L.obj("MRI_Handle_" + side)
        cx = h.matrix_world.translation.x
        L.reshape_world(h, (cx, -0.635, 1.05), (1.18, 1.18, 1.0))
        mounts = []
        for z in (0.806, 1.294):
            b = L.cylinder("HANDLE_MOUNT", 0.033, 0.018, (cx, -0.648, z), axis="Y", segments=24)
            L.assign(b, graphite)
            L.bevel_object(b, max_width=0.0012)
            mounts.append(b)
        L.join_into(h, mounts)

    # 6d. Faldon de la base de la mesa (sobresale 4 mm: banda de goma, no coplanar)
    kick = L.box("TABLE_KICK", (0.640, 0.970, 0.036), (0.0, -1.850, 0.018))
    L.assign(kick, graphite)
    L.bevel_object(kick, max_width=0.0012)
    L.join_into(L.obj("MRI_Table_Base"), [kick])

    # 7. UV de las pantallas: el GLB las traia giradas 90 grados
    n1 = L.project_uv(L.obj("MRI_Console_Screen"), axis="Y", sign=-1.0)
    n2 = L.project_uv(L.obj("MRI_Table_ControlPad"), axis="Z", sign=1.0)
    L.log("uv pantallas: consola", n1, "caras, teclado", n2, "caras")

    # 8. Rotulacion frontal (geometria extruida, sin texturas)
    try:
        t1 = L.text_mesh("LABEL_MERIDIAN", "MERIDIAN", 0.072, (0.0, -0.6155, 1.735),
                         extrude=0.0008)
        L.assign(t1, label)
        t2 = L.text_mesh("LABEL_FIELD", "3.0 T", 0.090, (0.0, -0.6155, 0.395),
                         extrude=0.0008)
        L.assign(t2, label)
        L.join_into(L.obj("MRI_Front_Cover"), [t1, t2])
    except Exception as exc:  # noqa: BLE001
        L.log("AVISO rotulacion omitida:", exc)

    # 9. Consola y mesa: detalle mecanico (bisel, teclado, paneles, camisas)
    detail_table(graphite, steel, rubber)
    detail_console(graphite, steel, rubber)

    L.log("details OK; tris:", L.tri_count())


# ------------------------------------------------------------------ texturas
# El GLB de origen trae las 6 texturas degradadas (normal maps negros, roughness
# magenta). Los PNG de textures/ son los buenos: se reinyectan antes de exportar.
IMG_MAP = {
    "T_plastic_normal": ("T_plastic_normal.png", "Non-Color"),
    "T_plastic_rough":  ("T_plastic_rough.png", "Non-Color"),
    "T_metal_normal":   ("T_metal_normal.png", "Non-Color"),
    "T_metal_rough":    ("T_metal_rough.png", "Non-Color"),
    "T_fabric_normal":  ("T_fabric_normal.png", "Non-Color"),
    "T_screen":         ("T_screen_v2.png", "sRGB"),
}


def stage_textures():
    L.log("--- etapa texturas ---")
    replaced = 0
    for name, (fname, cs) in IMG_MAP.items():
        old = bpy.data.images.get(name)
        path = os.path.join(L.ROOT, "textures", fname)
        if not os.path.exists(path):
            L.log("AVISO textura ausente:", path)
            continue
        new = bpy.data.images.load(path, check_existing=False)
        new.name = name + "_src"
        new.colorspace_settings.name = cs
        hits = 0
        for mat in bpy.data.materials:
            if not mat.use_nodes:
                continue
            for node in mat.node_tree.nodes:
                if node.type == "TEX_IMAGE" and node.image is old:
                    node.image = new
                    hits += 1
        if old is not None:
            bpy.data.images.remove(old)
        L.log("  %-20s -> %s nodos, %dx%d" % (name, hits, new.size[0], new.size[1]))
        replaced += 1
    L.log("texturas reinyectadas:", replaced)


# ------------------------------------------------------------------ export
def stage_export():
    L.log("--- etapa export ---")
    L.validate_names("antes de exportar")
    out = os.path.join(L.MODELS, "MRI_Realista_Modular.glb")
    L.export_glb(out)
    L.save_blend(os.path.join(L.OUT, "meridian_3t.blend"))
    L.log("total tris:", L.tri_count())


def parse():
    if "--stage" in sys.argv:
        return sys.argv[sys.argv.index("--stage") + 1].split(",")
    return ["bevel", "materials", "textures", "details", "export"]


def main():
    stages = parse()
    L.log("etapas:", stages)
    if "bevel" in stages:
        L.reset()
        L.import_glb()
    stage_map = {"bevel": None, "materials": stage_materials, "textures": stage_textures,
                 "details": stage_details, "export": stage_export}
    if "bevel" in stages:
        stage_bevel()
    for s in stages:
        fn = stage_map.get(s)
        if fn:
            fn()


main()
sys.exit(0)
