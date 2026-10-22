"""Paciente (maniquÃ­ clÃ­nico) del MERIDIAN 3T.

Genera models/patient.glb: una malla humana continua, con bata hospitalaria,
rig articulado y **una sola animaciÃ³n** que cubre toda la puesta en escena:

    llega andando -> se gira -> se sienta en el borde -> sube las piernas
    -> se tumba -> (quieto durante la exploraciÃ³n) -> se incorpora
    -> se levanta -> se marcha

El visor reproduce el clip y mueve la mesa/bobina con la misma lÃ­nea de tiempo.

    blender -b -P blender/build_patient.py
"""
import math
import os
import sys

import bmesh
import bpy
from mathutils import Matrix, Quaternion, Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m3t_lib as L  # noqa: E402

OUT = os.path.join(L.MODELS, "patient.glb")

TAU = math.tau
D2R = math.radians


# --------------------------------------------------------------------------
# materiales
# --------------------------------------------------------------------------
def mat(name, base, rough=0.5, metal=0.0, sheen=0.0, sss=0.0):
    m = L.new_material(name, base, metallic=metal, roughness=rough, sheen=sheen)
    b = L.principled(m)
    if b is not None:
        for key, val in (("Subsurface Weight", sss), ("Specular IOR Level", 0.45)):
            if key in b.inputs:
                b.inputs[key].default_value = val
    return m


# --------------------------------------------------------------------------
# geometrÃ­a
# --------------------------------------------------------------------------
def superellipse(n, seg):
    """Puntos unitarios de una superelipse (n=2 elipse, n>2 mÃ¡s cuadrada)."""
    pts = []
    for i in range(seg):
        a = TAU * i / seg
        c, s = math.cos(a), math.sin(a)
        x = math.copysign(abs(c) ** (2.0 / n), c)
        y = math.copysign(abs(s) ** (2.0 / n), s)
        pts.append((x, y))
    return pts


def loft(name, rings, seg=32, cap_a=True, cap_b=True, smooth=True, phase=0.0):
    """rings: (z, cx, cy, rx, ry, n). Crea un tubo cerrado y suave."""
    bm = bmesh.new()
    loops = []
    for i, r in enumerate(rings):
        if len(r) == 5:
            z, cx, cy, rx, ry = r
            n = 2.0
        else:
            z, cx, cy, rx, ry, n = r
        pts = superellipse(n, seg)
        loop = []
        for k, (ux, uy) in enumerate(pts):
            a = TAU * k / seg + phase
            # rotaciÃ³n ligera para que la costura no caiga en la cara
            ux, uy = math.cos(a), math.sin(a)
            ux = math.copysign(abs(ux) ** (2.0 / n), ux)
            uy = math.copysign(abs(uy) ** (2.0 / n), uy)
            loop.append(bm.verts.new((cx + rx * ux, cy + ry * uy, z)))
        loops.append(loop)

    for i in range(len(loops) - 1):
        a, b = loops[i], loops[i + 1]
        for k in range(seg):
            j = (k + 1) % seg
            bm.faces.new((a[k], a[j], b[j], b[k]))

    def cap(loop, z, cx, cy, up):
        c = bm.verts.new((cx, cy, z))
        for k in range(seg):
            j = (k + 1) % seg
            if up:
                bm.faces.new((loop[k], loop[j], c))
            else:
                bm.faces.new((loop[j], loop[k], c))

    if cap_a:
        z, cx, cy = rings[0][0], rings[0][1], rings[0][2]
        cap(loops[0], z, cx, cy, False)
    if cap_b:
        z, cx, cy = rings[-1][0], rings[-1][1], rings[-1][2]
        cap(loops[-1], z, cx, cy, True)

    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    o = L._mesh_from_bm(name, bm)
    if smooth:
        L.shade_smooth_all(o)
    return o


def ellipsoid(name, loc, scale, seg=24, rings=14, rot=None):
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1.0)
    for v in bm.verts:
        v.co.x *= scale[0]
        v.co.y *= scale[1]
        v.co.z *= scale[2]
        if rot:
            v.co = rot @ v.co
        v.co += Vector(loc)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    o = L._mesh_from_bm(name, bm)
    L.shade_smooth_all(o)
    return o


def tube_along(name, p0, p1, r0, r1, seg=12, bulge=0.0, axis=(0, 1, 0), smooth=True):
    """CÃ¡psula sencilla entre dos puntos (dedos, mango de la bola)."""
    p0, p1 = Vector(p0), Vector(p1)
    d = p1 - p0
    ln = d.length
    if ln < 1e-6:
        return None
    z = d.normalized()
    side = Vector(axis)
    if abs(z.dot(side)) > 0.95:
        side = Vector((1, 0, 0))
    side = (side - z * z.dot(side)).normalized()
    up = z.cross(side).normalized()
    bm = bmesh.new()
    rings = []
    steps = 6
    for i in range(steps + 1):
        t = i / steps
        r = r0 + (r1 - r0) * t + bulge * math.sin(math.pi * t)
        c = p0 + d * t
        loop = []
        for k in range(seg):
            a = TAU * k / seg
            loop.append(bm.verts.new(c + side * (r * math.cos(a)) + up * (r * math.sin(a))))
        rings.append(loop)
    for i in range(steps):
        a, b = rings[i], rings[i + 1]
        for k in range(seg):
            j = (k + 1) % seg
            bm.faces.new((a[k], a[j], b[j], b[k]))
    for loop, c, flip in ((rings[0], p0, True), (rings[-1], p1, False)):
        cv = bm.verts.new(c)
        for k in range(seg):
            j = (k + 1) % seg
            if flip:
                bm.faces.new((loop[j], loop[k], cv))
            else:
                bm.faces.new((loop[k], loop[j], cv))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    o = L._mesh_from_bm(name, bm)
    if smooth:
        L.shade_smooth_all(o)
    return o

# --------------------------------------------------------------------------
# cuerpo
# --------------------------------------------------------------------------
TORSO = [
    (0.820, 0.0, 0.000, 0.140, 0.100, 2.2),
    (0.870, 0.0, 0.000, 0.168, 0.122, 2.2),
    (0.920, 0.0, 0.000, 0.182, 0.133, 2.2),
    (0.970, 0.0, 0.000, 0.182, 0.132, 2.2),
    (1.020, 0.0, 0.002, 0.172, 0.124, 2.2),
    (1.070, 0.0, 0.004, 0.153, 0.108, 2.2),
    (1.120, 0.0, 0.004, 0.154, 0.110, 2.2),
    (1.175, 0.0, 0.004, 0.168, 0.118, 2.2),
    (1.230, 0.0, 0.004, 0.179, 0.124, 2.2),
    (1.285, 0.0, 0.003, 0.186, 0.121, 2.2),
    (1.340, 0.0, 0.002, 0.190, 0.113, 2.2),
    (1.390, 0.0, 0.001, 0.172, 0.102, 2.2),
    (1.430, 0.0, 0.004, 0.118, 0.090, 2.0),
    (1.462, 0.0, 0.006, 0.072, 0.070, 2.0),
]

HEAD = [
    (1.482, 0.0, 0.006, 0.024, 0.032, 2.0),
    (1.492, 0.0, 0.010, 0.034, 0.044, 2.0),
    (1.504, 0.0, 0.012, 0.044, 0.054, 2.0),
    (1.518, 0.0, 0.012, 0.054, 0.066, 2.0),
    (1.534, 0.0, 0.010, 0.062, 0.076, 2.0),
    (1.550, 0.0, 0.008, 0.069, 0.083, 2.0),
    (1.566, 0.0, 0.006, 0.073, 0.087, 2.0),
    (1.582, 0.0, 0.005, 0.076, 0.089, 2.0),
    (1.600, 0.0, 0.004, 0.078, 0.091, 2.0),
    (1.620, 0.0, 0.003, 0.078, 0.092, 2.0),
    (1.642, 0.0, 0.002, 0.076, 0.089, 2.0),
    (1.664, 0.0, 0.002, 0.071, 0.083, 2.0),
    (1.684, 0.0, 0.002, 0.062, 0.073, 2.0),
    (1.700, 0.0, 0.002, 0.048, 0.056, 2.0),
    (1.712, 0.0, 0.002, 0.028, 0.034, 2.0),
    (1.719, 0.0, 0.002, 0.010, 0.012, 2.0),
]


def build_body(cloth=None):
    skin = mat("PAT_Skin", (0.58, 0.355, 0.255), rough=0.52, sss=0.14)
    cloth = cloth or mat("PAT_Gown", (0.115, 0.215, 0.185), rough=0.87, sheen=0.35)
    sock = mat("PAT_Sock", (0.60, 0.63, 0.61), rough=0.92)
    lip = mat("PAT_Lips", (0.46, 0.22, 0.20), rough=0.42)
    hair = mat("PAT_Hair", (0.036, 0.026, 0.020), rough=0.62)
    brow = mat("PAT_Brow", (0.055, 0.040, 0.031), rough=0.7)

    parts = []
    torso = loft("torso", TORSO, seg=36)
    L.assign(torso, skin)
    parts.append(torso)

    head = loft("head", HEAD, seg=36)
    L.assign(head, skin)
    parts.append(head)

    neck = loft("neck", [
        (1.418, 0.0, 0.005, 0.070, 0.070),
        (1.450, 0.0, 0.006, 0.060, 0.063),
        (1.480, 0.0, 0.008, 0.054, 0.058),
        (1.512, 0.0, 0.008, 0.052, 0.056),
    ], seg=28)
    L.assign(neck, skin)
    parts.append(neck)

    for s in (-1, 1):
        side = "L" if s > 0 else "R"
        # hombro
        parts.append(ellipsoid("deltoid_" + side, (s * 0.184, 0.0, 1.374),
                               (0.057, 0.061, 0.067)))
        # brazo
        arm = loft("arm_" + side, [
            (0.900, s * 0.209, 0.000, 0.026, 0.023),
            (0.940, s * 0.208, 0.001, 0.031, 0.027),
            (0.990, s * 0.207, 0.002, 0.036, 0.031),
            (1.040, s * 0.206, 0.002, 0.039, 0.034),
            (1.090, s * 0.205, 0.002, 0.041, 0.036),
            (1.135, s * 0.204, 0.001, 0.038, 0.034),
            (1.160, s * 0.203, 0.000, 0.037, 0.033),
            (1.210, s * 0.201, 0.000, 0.040, 0.036),
            (1.270, s * 0.199, 0.000, 0.044, 0.039),
            (1.330, s * 0.197, 0.000, 0.047, 0.042),
            (1.390, s * 0.193, 0.000, 0.050, 0.045),
        ], seg=24)
        L.assign(arm, skin)
        parts.append(arm)
        # manga corta de la bata, alrededor del brazo
        sleeve = loft("sleeve_" + side, [
            (1.412, s * 0.215, 0.002, 0.068, 0.066),
            (1.390, s * 0.215, 0.001, 0.066, 0.064),
            (1.340, s * 0.215, 0.001, 0.061, 0.059),
            (1.280, s * 0.215, 0.000, 0.057, 0.055),
            (1.228, s * 0.215, 0.000, 0.059, 0.057),
        ], seg=24, cap_a=False, cap_b=False)
        L.assign(sleeve, cloth)
        parts.append(sleeve)
        parts.append(ellipsoid("elbow_" + side, (s * 0.204, 0.001, 1.140),
                               (0.039, 0.035, 0.044)))
        # mano
        hand = loft("hand_" + side, [
            (0.790, s * 0.209, 0.006, 0.036, 0.014),
            (0.812, s * 0.209, 0.005, 0.039, 0.016),
            (0.840, s * 0.209, 0.003, 0.040, 0.017),
            (0.868, s * 0.209, 0.001, 0.036, 0.017),
            (0.892, s * 0.209, 0.000, 0.030, 0.019),
            (0.910, s * 0.209, 0.000, 0.027, 0.022),
        ], seg=20)
        L.assign(hand, skin)
        parts.append(hand)
        for i, dx in enumerate((-0.024, -0.008, 0.008, 0.024)):
            ln = 0.052 - abs(dx) * 0.35
            f = tube_along("finger_%s%d" % (side, i),
                           (s * 0.209 + dx, 0.010, 0.795),
                           (s * 0.209 + dx * 1.05, 0.014, 0.795 - ln),
                           0.0072, 0.0060, seg=10, axis=(0, 1, 0))
            L.assign(f, skin)
            parts.append(f)
        thumb = tube_along("thumb_" + side,
                           (s * 0.177, 0.010, 0.840),
                           (s * 0.166, 0.040, 0.812),
                           0.0095, 0.0075, seg=10, axis=(0, 0, 1))
        L.assign(thumb, skin)
        parts.append(thumb)

        # pierna
        leg = loft("leg_" + side, [
            (0.085, s * 0.100, -0.004, 0.030, 0.032),
            (0.140, s * 0.100, -0.006, 0.035, 0.038),
            (0.220, s * 0.100, -0.008, 0.044, 0.048),
            (0.300, s * 0.100, -0.010, 0.051, 0.056),
            (0.380, s * 0.100, -0.012, 0.056, 0.062),
            (0.440, s * 0.100, -0.012, 0.058, 0.064),
            (0.480, s * 0.100, -0.004, 0.056, 0.058),
            (0.510, s * 0.100, 0.002, 0.055, 0.056),
            (0.560, s * 0.099, 0.004, 0.059, 0.060),
            (0.630, s * 0.098, 0.002, 0.066, 0.068),
            (0.710, s * 0.097, 0.000, 0.074, 0.078),
            (0.790, s * 0.096, 0.000, 0.080, 0.086),
            (0.870, s * 0.095, -0.002, 0.085, 0.090),
            (0.940, s * 0.095, -0.004, 0.086, 0.092),
        ], seg=26)
        L.assign(leg, skin)
        parts.append(leg)
        parts.append(ellipsoid("knee_" + side, (s * 0.100, 0.004, 0.500),
                               (0.056, 0.058, 0.062)))
        parts.append(ellipsoid("ankle_" + side, (s * 0.100, -0.002, 0.105),
                               (0.034, 0.040, 0.050)))
        # pie
        foot = ellipsoid("foot_" + side, (s * 0.102, 0.045, 0.042),
                         (0.045, 0.112, 0.043), seg=24, rings=14)
        for v in foot.data.vertices:
            if v.co.z < 0.004:
                v.co.z = 0.004
        toe = ellipsoid("toe_" + side, (s * 0.102, 0.135, 0.030),
                        (0.043, 0.040, 0.026), seg=20, rings=12)
        for v in toe.data.vertices:
            if v.co.z < 0.004:
                v.co.z = 0.004
        L.assign(foot, sock)
        L.assign(toe, sock)
        cuff = loft("sockcuff_" + side, [
            (0.088, s * 0.100, -0.002, 0.041, 0.047),
            (0.118, s * 0.100, -0.002, 0.043, 0.049),
            (0.146, s * 0.100, -0.002, 0.044, 0.049),
        ], seg=20, cap_a=False, cap_b=False)
        L.assign(cuff, sock)
        parts.extend([foot, toe, cuff])

    # separa los brazos 22 mm: quedan por fuera de la bata, sin atravesarla
    for o in parts:
        for sfx, sgn in (("L", 1), ("R", -1)):
            if o.name.endswith("_" + sfx) and o.name.split("_")[0] in (
                    "arm", "elbow", "hand", "finger", "thumb"):
                for v in o.data.vertices:
                    v.co.x += sgn * 0.022

    # nariz, orejas, labios, cejas
    nose = ellipsoid("nose", (0.0, 0.0855, 1.581), (0.0125, 0.018, 0.029), seg=20, rings=12)
    L.assign(nose, skin)
    parts.append(nose)
    for s in (-1, 1):
        parts.append(ellipsoid("ala_%d" % s, (s * 0.0135, 0.0865, 1.5625),
                               (0.0085, 0.0105, 0.0085), seg=14, rings=9))
        ear = ellipsoid("ear_%d" % s, (s * 0.080, 0.000, 1.582),
                        (0.008, 0.020, 0.030), seg=16, rings=10)
        L.assign(ear, skin)
        parts.append(ear)

    for o in parts:
        if not o.data.materials:
            L.assign(o, skin)

    lips = ellipsoid("lips", (0.0, 0.0862, 1.5455), (0.0215, 0.0075, 0.0072), seg=18, rings=10)
    L.assign(lips, lip)
    parts.append(lips)
    upper = ellipsoid("lip_up", (0.0, 0.0872, 1.5505), (0.0195, 0.0060, 0.0042), seg=16, rings=8)
    L.assign(upper, lip)
    parts.append(upper)

    for s in (-1, 1):
        b = ellipsoid("brow_%d" % s, (s * 0.031, 0.0845, 1.6065),
                      (0.022, 0.0045, 0.0032), seg=14, rings=8)
        L.assign(b, brow)
        parts.append(b)

    # párpados: dos conchas finas sobre el globo ocular
    for s in (-1, 1):
        up = ellipsoid("lid_up_%d" % s, (s * 0.028, 0.0837, 1.5885),
                       (0.0140, 0.0058, 0.0068), seg=16, rings=9)
        lo = ellipsoid("lid_lo_%d" % s, (s * 0.028, 0.0837, 1.5755),
                       (0.0130, 0.0050, 0.0042), seg=16, rings=9)
        L.assign(up, skin)
        L.assign(lo, skin)
        parts.extend([up, lo])

    # unir toda la piel en una malla
    body = parts[0]
    body.name = "PAT_Body"
    L.join_into(body, parts[1:])
    return body

def build_gown(cloth=None):
    cloth = cloth or mat("PAT_Gown", (0.115, 0.215, 0.185), rough=0.87, sheen=0.35)
    rings = [
        (0.800, 0.0, 0.004, 0.213, 0.174, 2.1),
        (0.850, 0.0, 0.002, 0.210, 0.170, 2.1),
        (0.900, 0.0, 0.000, 0.205, 0.165, 2.1),
        (0.950, 0.0, 0.000, 0.198, 0.158, 2.1),
        (0.960, 0.0, 0.000, 0.203, 0.157, 2.1),
        (1.020, 0.0, 0.002, 0.194, 0.148, 2.1),
        (1.080, 0.0, 0.004, 0.182, 0.136, 2.1),
        (1.140, 0.0, 0.004, 0.184, 0.136, 2.1),
        (1.200, 0.0, 0.004, 0.206, 0.146, 2.1),
        (1.240, 0.0, 0.004, 0.212, 0.148, 2.1),
        (1.280, 0.0, 0.004, 0.214, 0.150, 2.1),
        (1.320, 0.0, 0.002, 0.216, 0.150, 2.1),
        (1.360, 0.0, 0.001, 0.220, 0.144, 2.1),
        (1.395, 0.0, 0.001, 0.252, 0.140, 2.1),
        (1.420, 0.0, 0.001, 0.250, 0.138, 2.1),
        (1.440, 0.0, 0.002, 0.213, 0.126, 2.1),
        (1.456, 0.0, 0.004, 0.152, 0.104, 2.1),
        (1.468, 0.0, 0.005, 0.101, 0.083, 2.1),
        (1.478, 0.0, 0.006, 0.071, 0.068, 2.1),
    ]
    g = loft("gown", rings, seg=40, cap_a=False, cap_b=False)
    # pliegues suaves: la tela deja de ser un tubo
    for v in g.data.vertices:
        a = math.atan2(v.co.y, v.co.x)
        amp = 0.0045 * smoothstep(1.36, 1.18, v.co.z) + 0.0022 * smoothstep(1.12, 0.82, v.co.z)
        r = amp * math.sin(a * 7.0 + v.co.z * 9.0)
        v.co.x += math.cos(a) * r
        v.co.y += math.sin(a) * r
    L.assign(g, cloth)
    L.weld(g)
    sol = g.modifiers.new("SOL", "SOLIDIFY")
    sol.thickness = 0.004
    sol.offset = 1.0
    L.activate(g)
    bpy.ops.object.modifier_apply(modifier=sol.name)
    return g


def build_hair():
    hair_mat = mat("PAT_Hair", (0.036, 0.026, 0.020), rough=0.62)
    rings = [
        (1.548, 0.0, 0.000, 0.079, 0.092),
        (1.572, 0.0, 0.001, 0.084, 0.096),
        (1.596, 0.0, 0.002, 0.086, 0.100),
        (1.618, 0.0, 0.002, 0.086, 0.100),
        (1.642, 0.0, 0.002, 0.083, 0.096),
        (1.664, 0.0, 0.002, 0.075, 0.087),
        (1.684, 0.0, 0.002, 0.066, 0.077),
        (1.700, 0.0, 0.002, 0.052, 0.061),
        (1.714, 0.0, 0.002, 0.031, 0.037),
        (1.722, 0.0, 0.002, 0.010, 0.012),
    ]
    h = loft("hair", rings, seg=32, cap_a=False, cap_b=True)
    bm = bmesh.new()
    bm.from_mesh(h.data)
    kill = []
    for f in bm.faces:
        c = f.calc_center_median()
        if c.y > 0.030 and c.z < 1.676:
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bm.to_mesh(h.data)
    bm.free()
    h.data.update()
    L.assign(h, hair_mat)
    back = ellipsoid("hair_back", (0.0, -0.036, 1.618),
                     (0.076, 0.054, 0.092), seg=24, rings=14)
    L.assign(back, hair_mat)
    L.join_into(h, [back])
    return h


def build_eyes():
    white = mat("PAT_EyeWhite", (0.70, 0.70, 0.67), rough=0.25)
    iris = mat("PAT_Iris", (0.08, 0.15, 0.13), rough=0.22)
    pupil = mat("PAT_Pupil", (0.008, 0.008, 0.008), rough=0.15)

    objs = []
    for s in (-1, 1):
        e = ellipsoid("eye_%d" % s, (s * 0.028, 0.0762, 1.5815),
                      (0.0112, 0.0106, 0.0108), seg=20, rings=12)
        L.assign(e, white)
        ir = ellipsoid("iris_%d" % s, (s * 0.028, 0.0858, 1.5815),
                       (0.0066, 0.0022, 0.0066), seg=18, rings=9)
        L.assign(ir, iris)
        pu = ellipsoid("pupil_%d" % s, (s * 0.028, 0.0874, 1.5815),
                       (0.0032, 0.0016, 0.0032), seg=14, rings=8)
        L.assign(pu, pupil)
        objs += [e, ir, pu]
    out = objs[0]
    out.name = "PAT_Eyes"
    L.join_into(out, objs[1:])
    return out


def build_all():
    L.reset()
    cloth = mat("PAT_Gown", (0.115, 0.215, 0.185), rough=0.87, sheen=0.35)
    body = build_body(cloth)
    gown = build_gown(cloth)
    hair = build_hair()
    eyes = build_eyes()
    L.log("verts cuerpo", len(body.data.vertices), "bata", len(gown.data.vertices),
          "pelo", len(hair.data.vertices), "ojos", len(eyes.data.vertices))
    return body, gown, hair, eyes






# --------------------------------------------------------------------------
# rig
# --------------------------------------------------------------------------
BONES = [
    ("root",       (0.000, 0.000, 0.940), (0.000, 0.140, 0.940), None),
    ("hips",       (0.000, 0.000, 0.900), (0.000, 0.000, 1.020), "root"),
    ("spine",      (0.000, 0.000, 1.020), (0.000, 0.000, 1.180), "hips"),
    ("chest",      (0.000, 0.000, 1.180), (0.000, 0.000, 1.400), "spine"),
    ("neck",       (0.000, 0.006, 1.400), (0.000, 0.010, 1.520), "chest"),
    ("head",       (0.000, 0.010, 1.520), (0.000, 0.010, 1.700), "neck"),
    ("upperarm.L", (0.193, 0.000, 1.395), (0.204, 0.001, 1.140), "chest"),
    ("lowerarm.L", (0.204, 0.001, 1.140), (0.209, 0.000, 0.900), "upperarm.L"),
    ("hand.L",     (0.209, 0.000, 0.900), (0.209, 0.000, 0.790), "lowerarm.L"),
    ("upperarm.R", (-0.193, 0.000, 1.395), (-0.204, 0.001, 1.140), "chest"),
    ("lowerarm.R", (-0.204, 0.001, 1.140), (-0.209, 0.000, 0.900), "upperarm.R"),
    ("hand.R",     (-0.209, 0.000, 0.900), (-0.209, 0.000, 0.790), "lowerarm.R"),
    ("thigh.L",    (0.095, 0.000, 0.940), (0.100, 0.005, 0.500), "hips"),
    ("shin.L",     (0.100, 0.005, 0.500), (0.100, -0.002, 0.090), "thigh.L"),
    ("foot.L",     (0.100, -0.002, 0.090), (0.100, 0.120, 0.045), "shin.L"),
    ("thigh.R",    (-0.095, 0.000, 0.940), (-0.100, 0.005, 0.500), "hips"),
    ("shin.R",     (-0.100, 0.005, 0.500), (-0.100, -0.002, 0.090), "thigh.R"),
    ("foot.R",     (-0.100, -0.002, 0.090), (-0.100, 0.120, 0.045), "shin.R"),
]

CHAIN = ["hips", "spine", "chest", "neck", "head"]
LIMBS = ["upperarm.L", "lowerarm.L", "hand.L", "upperarm.R", "lowerarm.R", "hand.R",
         "thigh.L", "shin.L", "foot.L", "thigh.R", "shin.R", "foot.R"]


def build_rig():
    arm = bpy.data.armatures.new("PAT_Arm")
    rig = bpy.data.objects.new("PAT_Rig", arm)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode="EDIT")
    for name, h, t, parent in BONES:
        b = arm.edit_bones.new(name)
        b.head = h
        b.tail = t
        b.roll = 0.0
        if parent:
            b.parent = arm.edit_bones[parent]
            b.use_connect = False
    bpy.ops.object.mode_set(mode="OBJECT")
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
    L.log("huesos", len(arm.bones))
    return rig


# --------------------------------------------------------------------------
# pesos
# --------------------------------------------------------------------------
def seg_dist(p, a, b):
    ab = b - a
    t = 0.0 if ab.length_squared < 1e-9 else max(0.0, min(1.0, (p - a).dot(ab) / ab.length_squared))
    return (p - (a + ab * t)).length


def smoothstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / max(1e-6, b - a)))
    return t * t * (3 - 2 * t)


def weight_body(o, rig):
    segs = {name: (Vector(h), Vector(t)) for name, h, t, _ in BONES if name not in ("root",)}
    groups = {}
    for name in segs:
        groups[name] = o.vertex_groups.new(name=name)

    for v in o.data.vertices:
        p = v.co
        ws = {}
        for name, (a, b) in segs.items():
            if name in CHAIN or name == "head":
                w = 1.0 / (seg_dist(p, a, b) + 0.020) ** 3
                if name == "head":
                    w *= 0.10 + 0.90 * smoothstep(1.475, 1.545, p.z)
                    w *= 1.0 + 1.4 * smoothstep(1.60, 1.66, p.z)
                elif name == "neck":
                    w *= 0.10 + 0.90 * smoothstep(1.43, 1.50, p.z) * (1 - smoothstep(1.54, 1.62, p.z))
                elif name == "hips":
                    w *= 0.25 + 0.75 * (1 - smoothstep(0.90, 1.06, p.z))
                elif name == "chest":
                    w *= 0.30 + 0.70 * smoothstep(1.08, 1.22, p.z)
                elif name == "spine":
                    w *= 0.35 + 0.65 * (1 - abs(p.z - 1.10) / 0.30) if abs(p.z - 1.10) < 0.30 else 0.0
            elif name.startswith(("upperarm", "lowerarm", "hand")):
                side = 1.0 if name.endswith(".L") else -1.0
                if p.x * side < 0.105:
                    continue
                w = 1.0 / (seg_dist(p, a, b) + 0.020) ** 3
                w *= 0.55 * smoothstep(0.105, 0.165, abs(p.x))
                if name.startswith("hand"):
                    w *= 1.6
            elif name.startswith(("thigh", "shin", "foot")):
                side = 1.0 if name.endswith(".L") else -1.0
                if p.x * side < 0.0:
                    continue
                w = 1.0 / (seg_dist(p, a, b) + 0.022) ** 3
                w *= 0.75 * smoothstep(0.0, 0.05, abs(p.x))
                if name.startswith("foot"):
                    w *= 1.5 + 2.0 * (1 - smoothstep(0.05, 0.14, p.z))
            else:
                continue
            if w > 0:
                ws[name] = w
        if not ws:
            ws["hips"] = 1.0
        top = sorted(ws.items(), key=lambda kv: -kv[1])[:4]
        tot = sum(w for _, w in top)
        for name, w in top:
            groups[name].add([v.index], w / tot, "REPLACE")

    mod = o.modifiers.new("ARM", "ARMATURE")
    mod.object = rig
    o.parent = rig


def bin_gown(o, rig):
    """La bata se ata al tronco: sin influencia de brazos, para que no se estire."""
    names = ["hips", "spine", "chest", "neck"]
    groups = {n: o.vertex_groups.new(name=n) for n in names}
    for v in o.data.vertices:
        z = v.co.z
        if z <= 1.02:
            w = {"hips": 1.0}
        elif z <= 1.16:
            t = smoothstep(1.02, 1.16, z)
            w = {"hips": 1 - t, "spine": t}
        elif z <= 1.26:
            t = smoothstep(1.16, 1.26, z)
            w = {"spine": 1 - t, "chest": t}
        elif z <= 1.42:
            w = {"chest": 1.0}
        else:
            t = smoothstep(1.42, 1.47, z)
            w = {"chest": 1 - t, "neck": t}
        for n, val in w.items():
            if val > 0:
                groups[n].add([v.index], val, "REPLACE")
    mod = o.modifiers.new("ARM", "ARMATURE")
    mod.object = rig
    o.parent = rig


def rigid_to(o, rig, bone):
    vg = o.vertex_groups.new(name=bone)
    vg.add([v.index for v in o.data.vertices], 1.0, "REPLACE")
    mod = o.modifiers.new("ARM", "ARMATURE")
    mod.object = rig
    o.parent = rig

# --------------------------------------------------------------------------
# animación
# --------------------------------------------------------------------------
def body_q(fwd, up):
    f = Vector(fwd).normalized()
    u = Vector(up).normalized()
    x = f.cross(u).normalized()
    u = x.cross(f).normalized()
    return Matrix((x, f, u)).transposed().to_quaternion()


def base_dirs():
    d = {n: Vector((0, 0, 1)) for n in CHAIN}
    for s, sfx in ((1, "L"), (-1, "R")):
        d["upperarm." + sfx] = Vector((s * 0.055, 0.02, -1))
        d["lowerarm." + sfx] = Vector((s * 0.045, 0.06, -1))
        d["hand." + sfx] = Vector((s * 0.03, 0.08, -1))
        d["thigh." + sfx] = Vector((s * 0.02, 0.00, -1))
        d["shin." + sfx] = Vector((s * 0.01, 0.03, -1))
        d["foot." + sfx] = Vector((s * 0.005, 1, -0.10))
    return d


def sit_dirs():
    d = base_dirs()
    for s, sfx in ((1, "L"), (-1, "R")):
        d["thigh." + sfx] = Vector((0.95, -0.02 + s * 0.02, -0.28))
        d["shin." + sfx] = Vector((0.06, 0.12 - s * 0.02, -1))
        d["foot." + sfx] = Vector((0, 1, 0.10))
        d["upperarm." + sfx] = Vector((s * -0.12, -0.05, -1))
        d["lowerarm." + sfx] = Vector((s * -0.08, 0.05, -1))
        d["hand." + sfx] = Vector((s * -0.05, 0.10, -1))
    d["chest"] = Vector((0, -0.06, 1))
    d["neck"] = Vector((0, -0.02, 1))
    return d


def legs_up_dirs():
    d = base_dirs()
    for s, sfx in ((1, "L"), (-1, "R")):
        d["thigh." + sfx] = Vector((s * 0.035, 0.99, 0.02))
        d["shin." + sfx] = Vector((s * 0.025, 1, 0.0))
        d["foot." + sfx] = Vector((0, 0.05, 1))
        d["upperarm." + sfx] = Vector((s * -0.09, 0.05, -1))
        d["lowerarm." + sfx] = Vector((s * -0.07, 0.25, -1))
        d["hand." + sfx] = Vector((s * -0.05, 0.35, -1))
    return d


def lying_dirs():
    d = base_dirs()
    for s, sfx in ((1, "L"), (-1, "R")):
        d["thigh." + sfx] = Vector((s * -0.05, 0.0, -1))
        d["shin." + sfx] = Vector((s * -0.03, 0.02, -1))
        d["foot." + sfx] = Vector((0, 1, 0.0))
        # tumbado, los brazos caen hacia los pies y un poco hacia fuera
        d["upperarm." + sfx] = Vector((s * -0.13, 0.0, -1))
        d["lowerarm." + sfx] = Vector((s * -0.10, 0.02, -1))
        d["hand." + sfx] = Vector((s * -0.07, 0.04, -1))
    d["head"] = Vector((0, 0.035, 1))
    return d


def seated_dirs():
    d = sit_dirs()
    for s, sfx in ((1, "L"), (-1, "R")):
        d["thigh." + sfx] = Vector((0.14, 0.02 + s * 0.02, -1))
        d["shin." + sfx] = Vector((0.04, 0.10, -1))
        d["foot." + sfx] = Vector((0, 1, 0.05))
    return d


class Pose:
    def __init__(self, hip, fwd, up, dirs):
        self.hip = Vector(hip)
        self.q = body_q(fwd, up)
        self.dirs = {k: (self.q @ Vector(v)).normalized() for k, v in dirs.items()}


def situp_dirs(fwd, up):
    """Piernas estiradas sobre la mesa mientras el tronco se incorpora.

    Las direcciones se dan en mundo y se llevan al marco del cuerpo para que
    la interpolacion entre poses no levante las piernas en el aire.
    """
    q = body_q(fwd, up).inverted()
    d = base_dirs()
    for s, sfx in ((1, "L"), (-1, "R")):
        d["thigh." + sfx] = q @ Vector((s * 0.02, -1.0, 0.03))
        d["shin." + sfx] = q @ Vector((s * 0.01, -1.0, -0.02))
        d["foot." + sfx] = q @ Vector((0, -1.0, 0.18))
        d["upperarm." + sfx] = q @ Vector((s * 0.10, 0.10, -1.0))
        d["lowerarm." + sfx] = q @ Vector((s * 0.06, 0.22, -1.0))
        d["hand." + sfx] = q @ Vector((s * 0.04, 0.26, -1.0))
    return d


def walk_dirs(phase):
    d = base_dirs()
    s = math.sin(phase * TAU)
    c = math.cos(phase * TAU)
    knee = 0.55 * max(0.0, s)
    d["thigh.L"] = Vector((0.02, 0.42 * s, -0.92))
    d["thigh.R"] = Vector((-0.02, -0.42 * s, -0.92))
    d["shin.L"] = Vector((0.01, 0.42 * s - knee, -1.0))
    d["shin.R"] = Vector((-0.01, -0.42 * s - 0.55 * max(0.0, -s), -1.0))
    d["foot.L"] = Vector((0, 1, -0.10 - 0.10 * c))
    d["foot.R"] = Vector((0, 1, -0.10 + 0.10 * c))
    d["upperarm.L"] = Vector((0.055, -0.30 * s, -1))
    d["upperarm.R"] = Vector((-0.055, 0.30 * s, -1))
    d["lowerarm.L"] = Vector((0.045, -0.22 * s + 0.10, -1))
    d["lowerarm.R"] = Vector((-0.045, 0.22 * s + 0.10, -1))
    d["chest"] = Vector((0, 0.05, 1))
    d["neck"] = Vector((0, 0.02, 1))
    return d


def build_beats():
    b = []

    def add(t, hip, fwd, up, dirs):
        b.append((t, Pose(hip, fwd, up, dirs)))

    # --- llega andando desde el pie de la mesa
    x0, y0, y1 = -0.72, -3.36, -2.04
    steps = 8
    for i in range(steps + 1):
        t = 1.85 * i / steps
        u = i / steps
        hip = (x0 - 0.02 * u, y0 + (y1 - y0) * u, 0.940 + 0.012 * abs(math.sin(u * TAU * 2)))
        add(t, hip, (0, 1, 0), (0, 0, 1), walk_dirs(u * 2.0))

    # --- se gira hacia la mesa y luego de espaldas al gantry
    add(2.08, (-0.70, -1.98, 0.940), (-1, 0.25, 0), (0, 0, 1), base_dirs())
    add(2.40, (-0.62, -1.92, 0.940), (0, -1, 0), (0, 0, 1), base_dirs())
    add(2.78, (-0.46, -1.84, 0.945), (0, -1, 0), (0, 0, 1), base_dirs())
    add(3.08, (-0.34, -1.80, 0.950), (0, -1, 0), (0, 0, 1), base_dirs())

    # --- se sienta en el borde
    add(3.62, (-0.26, -1.78, 1.035), (0, -1, 0), (0, 0, 1), sit_dirs())
    add(4.05, (-0.25, -1.78, 1.035), (0, -1, 0), (0, 0, 1), sit_dirs())

    # --- sube las piernas y se tumba
    add(5.20, (0.0, -1.76, 1.035), (0, -1, 0), (0, 0, 1), legs_up_dirs())
    add(5.70, (0.0, -1.76, 1.035), (0, -1, 0.35), (0, 0.35, 1), legs_up_dirs())
    add(6.90, (0.0, -1.76, 1.035), (0, 0, 1), (0, 1, 0), lying_dirs())
    add(7.40, (0.0, -1.76, 1.035), (0, 0, 1), (0, 1, 0), lying_dirs())
    add(14.90, (0.0, -1.76, 1.035), (0, 0, 1), (0, 1, 0), lying_dirs())

    # --- se incorpora: primero el tronco, con las piernas aún en la mesa
    add(15.70, (-0.08, -1.75, 1.035), (0, -1, 0.55), (0, 0.55, 1), situp_dirs((0, -1, 0.55), (0, 0.55, 1)))
    add(16.35, (-0.18, -1.74, 1.035), (0, -1, 0), (0, 0, 1), situp_dirs((0, -1, 0), (0, 0, 1)))

    # --- gira las piernas fuera de la mesa
    add(16.95, (-0.26, -1.73, 1.035), (0, -1, 0), (0, 0, 1), sit_dirs())

    # --- baja las piernas y se levanta
    add(17.55, (-0.30, -1.72, 1.035), (0, -1, 0), (0, 0, 1), seated_dirs())
    add(18.20, (-0.52, -1.72, 0.940), (0, -1, 0), (0, 0, 1), base_dirs())

    # --- se marcha
    steps = 8
    for i in range(steps + 1):
        t = 18.45 + 1.95 * i / steps
        u = i / steps
        hip = (-0.56, -1.72 - 1.85 * u, 0.940 + 0.012 * abs(math.sin(u * TAU * 2)))
        add(t, hip, (0, -1, 0), (0, 0, 1), walk_dirs(u * 2.0))

    return b



def pose_at(beats, t):
    if t <= beats[0][0]:
        return beats[0][1]
    if t >= beats[-1][0]:
        return beats[-1][1]
    for i in range(len(beats) - 1):
        t0, p0 = beats[i]
        t1, p1 = beats[i + 1]
        if t0 <= t <= t1:
            u = 0.0 if t1 <= t0 else (t - t0) / (t1 - t0)
            u = u * u * (3 - 2 * u)
            p = Pose.__new__(Pose)
            p.hip = p0.hip.lerp(p1.hip, u)
            p.q = p0.q.slerp(p1.q, u)
            p.dirs = {k: p0.dirs[k].slerp(p1.dirs[k], u) for k in p0.dirs}
            return p
    return beats[-1][1]


def aim(pb, direction):
    bpy.context.view_layer.update()
    m = pb.matrix.copy()
    head = m.translation.copy()
    cur = (m.to_3x3() @ Vector((0, 1, 0))).normalized()
    tgt = Vector(direction).normalized()
    q = cur.rotation_difference(tgt)
    rot = Matrix.Translation(head) @ q.to_matrix().to_4x4() @ Matrix.Translation(-head)
    pb.matrix = rot @ m
    bpy.context.view_layer.update()


def apply_pose(rig, pose):
    for pb in rig.pose.bones:
        pb.location = (0, 0, 0)
        pb.rotation_quaternion = (1, 0, 0, 0)
    root = rig.pose.bones["root"]
    root.location = pose.hip - Vector((0, 0, 0.940))
    root.rotation_quaternion = pose.q
    bpy.context.view_layer.update()
    for n in CHAIN + LIMBS:
        aim(rig.pose.bones[n], pose.dirs[n])


def animate(rig):
    sc = bpy.context.scene
    sc.render.fps = 24
    sc.frame_start = 0
    sc.frame_end = int(21.0 * 24)
    acts = {}
    beats = build_beats()
    total = 21.0
    for f in range(0, sc.frame_end + 1):
        t = f / 24.0
        pose = pose_at(beats, min(t, total))
        sc.frame_set(f)
        apply_pose(rig, pose)
        for pb in rig.pose.bones:
            pb.keyframe_insert("rotation_quaternion", frame=f)
        rig.pose.bones["root"].keyframe_insert("location", frame=f)
    act = rig.animation_data.action
    act.name = "Patient"
    curves = []
    if hasattr(act, "fcurves"):
        curves = list(act.fcurves)
    else:
        for layer in act.layers:
            for strip in layer.strips:
                try:
                    bags = list(strip.channelbags)
                except AttributeError:
                    bags = []
                for bag in bags:
                    curves.extend(bag.fcurves)
    for fc in curves:
        for kp in fc.keyframe_points:
            kp.interpolation = "LINEAR"
    L.log("accion", act.name, "frames", sc.frame_end, "curvas", len(curves))
    return act

def export_patient():
    kw = dict(filepath=OUT, export_format="GLB", use_selection=False,
              export_apply=False, export_yup=True, export_animations=True,
              export_skins=True, export_materials="EXPORT", export_normals=True,
              export_texcoords=True, export_tangents=False, export_cameras=False,
              export_lights=False, export_extras=True, export_frame_range=True,
              export_force_sampling=True, export_animation_mode="ACTIONS")
    try:
        bpy.ops.export_scene.gltf(**kw)
    except TypeError as exc:
        L.log("export: reintento", exc)
        bpy.ops.export_scene.gltf(filepath=OUT, export_format="GLB", export_yup=True,
                                 export_animations=True, export_skins=True)
    L.log("patient.glb", round(os.path.getsize(OUT) / 1024.0, 1), "KB")


def main():
    body, gown, hair, eyes = build_all()
    rig = build_rig()
    weight_body(body, rig)
    bin_gown(gown, rig)
    rigid_to(hair, rig, "head")
    rigid_to(eyes, rig, "head")
    animate(rig)
    bpy.context.scene.frame_set(0)
    export_patient()
    L.save_blend(os.path.join(L.OUT, "patient.blend"))


if __name__ == "__main__":
    main()







