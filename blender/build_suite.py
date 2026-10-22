"""Construye la sala de resonancia (suite.glb).

Va en un GLB aparte del producto: el visor puede mostrar el equipo solo o
instalado en su sala. Materiales con backface culling => desde fuera de la
sala no se ve la pared, asi la camara siempre tiene plano.

Uso:
    blender -b -P blender/build_suite.py
"""
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bpy  # noqa: E402
import m3t_lib as L  # noqa: E402

W, H, C = 10.0, 10.0, 3.10     # ancho, fondo, altura
WT = 0.06                       # espesor de muro


def mat(name, base, metallic=0.0, roughness=0.5, coat=0.0, emission=None, strength=0.0):
    m = L.new_material(name, base=base, metallic=metallic, roughness=roughness,
                       coat=coat, coat_rough=0.08, emission=emission,
                       emission_strength=strength)
    m.use_backface_culling = True
    return m


def main():
    L.reset()
    floor_m = mat("ENV_Floor", (0.115, 0.122, 0.134), metallic=0.0, roughness=0.20, coat=0.35)
    wall_m = mat("ENV_Wall", (0.215, 0.225, 0.240), roughness=0.55)
    seam_m = mat("ENV_Seam", (0.100, 0.108, 0.118), roughness=0.60)
    ceil_m = mat("ENV_Ceiling", (0.430, 0.440, 0.450), roughness=0.80)
    light_m = mat("ENV_Light", (0.95, 0.96, 0.97), roughness=0.4,
                  emission=(1.0, 0.985, 0.955), strength=10.0)
    door_m = mat("ENV_Door", (0.400, 0.415, 0.435), roughness=0.42, coat=0.2)
    glass_m = mat("ENV_Glass", (0.030, 0.045, 0.060), metallic=0.35, roughness=0.06, coat=0.6)
    skirt_m = mat("ENV_Skirt", (0.150, 0.160, 0.172), roughness=0.48)
    joint_m = mat("ENV_Joint", (0.030, 0.033, 0.037), roughness=0.55)
    steel_m = mat("ENV_Steel", (0.60, 0.62, 0.65), metallic=1.0, roughness=0.32)

    objs = []

    def add(name, size, loc, m):
        o = L.box(name, size, loc)
        L.assign(o, m)
        objs.append(o)
        return o

    # ---------------------------------------------------------- suelo / techo
    add("ENV_Floor", (W, H, 0.02), (0, 0, -0.01), floor_m)
    add("ENV_Ceiling", (W, H, 0.05), (0, 0, C + 0.025), ceil_m)

    # franjas del vinilo: dos juntas por eje (casi a ras, para que no reflecten)
    for x in (-2.5, 0.0, 2.5):
        add("ENV_FloorSeam_%s" % x, (0.014, H, 0.0015), (x, 0, 0.0006), joint_m)
    for y in (-2.5, 0.0, 2.5):
        add("ENV_FloorSeamY_%s" % y, (W, 0.014, 0.0015), (0, y, 0.0006), joint_m)

    # ------------------------------------------------------------- mamparos
    add("ENV_Wall_N", (W, WT, C), (0, H / 2, C / 2), wall_m)
    add("ENV_Wall_S", (W, WT, C), (0, -H / 2, C / 2), wall_m)
    add("ENV_Wall_E", (WT, H, C), (W / 2, 0, C / 2), wall_m)
    add("ENV_Wall_W", (WT, H, C), (-W / 2, 0, C / 2), wall_m)

    # juntas verticales cada 0.75 m: dan escala y ritmo de paneles
    step = 0.75
    n = int(W / step)
    for i in range(1, n):
        x = -W / 2 + i * step
        add("ENV_VSeam_N_%d" % i, (0.010, 0.012, C), (x, H / 2 - WT, C / 2), seam_m)
        add("ENV_VSeam_S_%d" % i, (0.010, 0.012, C), (x, -H / 2 + WT, C / 2), seam_m)
    n2 = int(H / step)
    for i in range(1, n2):
        y = -H / 2 + i * step
        add("ENV_VSeam_E_%d" % i, (0.012, 0.010, C), (W / 2 - WT, y, C / 2), seam_m)
        add("ENV_VSeam_W_%d" % i, (0.012, 0.010, C), (-W / 2 + WT, y, C / 2), seam_m)

    # zócalo sanitario
    add("ENV_Skirt_N", (W, 0.030, 0.095), (0, H / 2 - 0.045, 0.0475), skirt_m)
    add("ENV_Skirt_S", (W, 0.030, 0.095), (0, -H / 2 + 0.045, 0.0475), skirt_m)
    add("ENV_Skirt_E", (0.030, H, 0.095), (W / 2 - 0.045, 0, 0.0475), skirt_m)
    add("ENV_Skirt_W", (0.030, H, 0.095), (-W / 2 + 0.045, 0, 0.0475), skirt_m)

    # --------------------------------------------------------------- puerta
    dy = -H / 2 + WT
    add("ENV_DoorFrame", (1.26, 0.10, 2.22), (3.2, dy + 0.02, 1.11), steel_m)
    add("ENV_Door", (1.10, 0.07, 2.10), (3.2, dy + 0.06, 1.05), door_m)
    add("ENV_DoorHandle", (0.035, 0.05, 0.22), (2.75, dy + 0.12, 1.05), steel_m)
    # ventana de observacion en la puerta (cristal oscuro)
    add("ENV_DoorGlass", (0.42, 0.02, 0.80), (3.2, dy + 0.10, 1.55), glass_m)

    # ------------------------------------------- ventana de sala de control
    add("ENV_WinFrame", (0.10, 1.70, 1.20), (W / 2 - WT - 0.03, 1.4, 1.75), steel_m)
    add("ENV_Window", (0.03, 1.52, 1.02), (W / 2 - WT - 0.08, 1.4, 1.75), glass_m)

    # ------------------------------------------------- plafones de luz LED
    for i, (x, y, sx, sy) in enumerate([
        (0.0, 0.0, 2.40, 1.20),
        (-3.1, 2.6, 1.40, 0.50),
        (3.1, 2.6, 1.40, 0.50),
        (-3.1, -2.6, 1.40, 0.50),
        (3.1, -2.6, 1.40, 0.50),
    ]):
        add("ENV_LightPanel_%d" % i, (sx, sy, 0.03), (x, y, C - 0.015), light_m)
        # marco del plafon
        add("ENV_LightFrame_%d" % i, (sx + 0.10, sy + 0.10, 0.02), (x, y, C - 0.004), ceil_m)

    # --------------------------------------------------------------- union
    for o in objs:
        L.activate(o)
        for m in list(o.modifiers):
            pass
    # unir todo en un solo objeto (menos nodos, mejor rendimiento en web)
    target = L.obj("ENV_Floor")
    rest = [o for o in objs if o is not target]
    L.join_into(target, rest)
    target.name = "ENV_Room"

    L.log("tris sala:", L.tri_count())
    L.export_glb(os.path.join(L.MODELS, "suite.glb"))
    L.save_blend(os.path.join(L.OUT, "suite.blend"))


main()
sys.exit(0)
