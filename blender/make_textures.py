"""Diagnostico y regeneracion de normal maps.

Un normal map cuya media se acerca a (0.5, 0.5, 0.5) se convierte en (0,0,0)
al reducirse: la superficie se renderiza negra. Aqui se mide y se generan
variantes con componente Z sana.

Uso:
    blender -b -P blender/make_textures.py
"""
import os
import sys

import bpy
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m3t_lib as L  # noqa: E402


def stats(img):
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, img.channels)
    rgb = px[:, :, :3]
    n = rgb * 2.0 - 1.0
    length = np.linalg.norm(n, axis=2)
    nz = np.divide(n[:, :, 2], length, out=np.zeros_like(length), where=length > 1e-6)
    return {
        "size": [w, h],
        "mean_rgb": [round(float(rgb[:, :, i].mean()), 4) for i in range(3)],
        "mean_z": round(float(nz.mean()), 4),
        "pct_z_below_02": round(float((nz < 0.2).mean() * 100), 1),
        "pct_degenerate": round(float((length < 0.2).mean() * 100), 1),
    }


def make_weave(size=512, threads=96, amp=0.42):
    """Tejido tipo tafetan: urdimbre + trama, con la Z bien dominante."""
    u = np.arange(size, dtype=np.float32) / size
    v = np.arange(size, dtype=np.float32) / size
    uu, vv = np.meshgrid(u, v)
    tau = 2.0 * np.pi * threads
    # tafetan: hilos alternos en cuadricula de 2x2
    warp = np.sin(tau * uu)
    weft = np.sin(tau * vv)
    checker = 0.5 + 0.5 * np.sign(np.sin(np.pi * threads * uu) * np.sin(np.pi * threads * vv))
    height = amp * (warp * checker + weft * (1.0 - checker))
    # derivadas -> normal
    du = np.gradient(height, axis=1) * size
    dv = np.gradient(height, axis=0) * size
    strength = 2.2
    nx = -du * strength
    ny = -dv * strength
    nz = np.ones_like(nx) * 1.0
    ln = np.sqrt(nx * nx + ny * ny + nz * nz)
    nx, ny, nz = nx / ln, ny / ln, nz / ln
    rgb = np.stack([(nx * 0.5 + 0.5), (ny * 0.5 + 0.5), (nz * 0.5 + 0.5)], axis=2)
    return rgb


def save_png(rgb, path):
    h, w, _ = rgb.shape
    img = bpy.data.images.new(os.path.basename(path), w, h, alpha=False)
    img.colorspace_settings.name = "Non-Color"      # antes de escribir pixeles
    rgba = np.ones((h, w, 4), dtype=np.float32)
    rgba[:, :, :3] = rgb
    img.pixels.foreach_set(rgba.ravel())
    img.filepath_raw = path
    img.file_format = "PNG"
    img.save()
    bpy.data.images.remove(img)


def main():
    L.reset()
    L.import_glb()
    print("--- normal maps actuales ---")
    for name in ("T_fabric_normal", "T_plastic_normal", "T_metal_normal"):
        img = bpy.data.images.get(name)
        if img is None:
            print("  FALTA", name)
            continue
        s = stats(img)
        print("  %-20s %s" % (name, s))

    out = os.path.join(L.ROOT, "textures", "T_fabric_normal_v2.png")
    rgb = make_weave()
    save_png(rgb, out)
    n = rgb * 2.0 - 1.0
    ln = np.linalg.norm(n, axis=2)
    nz = n[:, :, 2] / np.maximum(ln, 1e-6)
    print("--- tejido nuevo ---")
    print("  %s z media %.3f  z<0.2 %.1f%%  tamano %d KB" % (
        out, float(nz.mean()), float((nz < 0.2).mean() * 100),
        os.path.getsize(out) // 1024))
    print("TEXTURES_OK")


main()
sys.exit(0)
