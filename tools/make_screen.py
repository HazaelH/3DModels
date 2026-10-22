"""Genera la pantalla de la consola (UI clinica) como textura 512x384.

Uso:
    python tools/make_screen.py
"""
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "textures", "T_screen_v2.png")

W, H = 512, 384
BG = (10, 18, 28)
PANEL = (14, 26, 38)
LINE = (28, 46, 62)
TXT = (196, 212, 226)
DIM = (110, 132, 150)
MINT = (61, 223, 196)
AMBER = (240, 169, 62)


def font(name, size):
    for path in (r"C:\Windows\Fonts\%s" % name,):
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except Exception:
                pass
    return ImageFont.load_default()


def main():
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    f_small = font("consola.ttf", 11)
    f_txt = font("consola.ttf", 13)
    f_big = font("consola.ttf", 22)
    f_ui = font("segoeui.ttf", 12)

    # barra superior
    d.rectangle([0, 0, W, 30], fill=PANEL)
    d.rectangle([0, 30, W, 31], fill=LINE)
    d.rectangle([10, 10, 18, 20], fill=MINT)
    d.text((26, 8), "MERIDIAN 3T", font=f_ui, fill=TXT)
    d.text((150, 9), "B0 3.0 T", font=f_small, fill=DIM)
    d.text((270, 9), "PACIENTE  GARCIA, M.", font=f_small, fill=DIM)
    d.text((452, 9), "14:32", font=f_small, fill=DIM)
    d.ellipse([490, 11, 498, 19], fill=MINT)

    # columna de protocolos
    d.text((12, 40), "PROTOCOLO", font=f_small, fill=DIM)
    protos = [("T2 TSE  AX", True), ("T1 SE   SAG", False),
              ("DWI b1000", False), ("T2* GRE", False)]
    y = 58
    for name, active in protos:
        if active:
            d.rectangle([8, y - 3, 150, y + 15], fill=(20, 48, 52))
            d.rectangle([8, y - 3, 10, y + 15], fill=MINT)
        d.text((18, y), name, font=f_small, fill=MINT if active else TXT)
        y += 24

    d.text((12, 168), "SECUENCIA", font=f_small, fill=DIM)
    d.text((12, 182), "SE  TR 4000", font=f_small, fill=TXT)
    d.text((12, 196), "TE   98 ms", font=f_small, fill=TXT)
    d.text((12, 210), "FA   120", font=f_small, fill=TXT)
    d.text((12, 224), "FOV  220 mm", font=f_small, fill=TXT)
    d.text((12, 238), "SL   24  x 4 mm", font=f_small, fill=TXT)

    d.text((12, 276), "PESO", font=f_small, fill=DIM)
    d.text((12, 292), "78 kg", font=f_small, fill=TXT)
    d.text((12, 308), "SEDACION  NO", font=f_small, fill=TXT)

    # area de imagen: corte axial estilizado
    cx, cy, rx, ry = 258, 196, 66, 82
    d.rectangle([166, 40, 350, 352], fill=(6, 12, 18))
    # rejilla tenue
    for gx in range(166, 351, 23):
        d.line([gx, 40, gx, 352], fill=(12, 22, 30))
    for gy in range(40, 353, 23):
        d.line([166, gy, 350, gy], fill=(12, 22, 30))
    # craneo / cerebro / ventriculos
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(198, 208, 218))
    d.ellipse([cx - rx + 6, cy - ry + 6, cx + rx - 6, cy + ry - 6], fill=(96, 108, 120))
    d.ellipse([cx - 44, cy - 58, cx + 44, cy + 58], fill=(126, 138, 150))
    d.ellipse([cx - 34, cy - 44, cx + 34, cy + 44], fill=(140, 152, 164))
    d.ellipse([cx - 11, cy - 22, cx - 2, cy + 10], fill=(40, 52, 64))
    d.ellipse([cx + 2, cy - 22, cx + 11, cy + 10], fill=(40, 52, 64))
    d.ellipse([cx - 6, cy - 34, cx + 6, cy - 24], fill=(40, 52, 64))
    # foco / linea de corte
    d.line([166, cy, 350, cy], fill=(61, 223, 196))
    d.line([cx, 40, cx, 352], fill=(61, 223, 196))
    d.text((172, 44), "AX  T2", font=f_small, fill=MINT)
    d.text((292, 336), "SL 12/24", font=f_small, fill=DIM)

    # columna derecha: metricas
    d.text((360, 40), "SENAL", font=f_small, fill=DIM)
    d.text((360, 56), "SNR", font=f_small, fill=DIM)
    d.text((360, 70), "42.6", font=f_big, fill=MINT)
    d.text((360, 104), "SAR", font=f_small, fill=DIM)
    d.text((360, 118), "1.8", font=f_txt, fill=TXT)
    d.text((360, 136), "W/kg", font=f_small, fill=DIM)

    # ECG
    d.text((360, 166), "ECG", font=f_small, fill=DIM)
    d.rectangle([360, 180, 500, 230], fill=(6, 12, 18))
    pts = []
    for i in range(0, 140, 2):
        t = i / 140.0
        base = 205 - (12 * ((t * 3) % 1.0))
        spike = -26 if 0.30 < (t * 3) % 1.0 < 0.36 else 0
        pts.append((360 + i, base + spike))
    d.line(pts, fill=MINT, width=1)

    # estado y progreso
    d.text((360, 250), "ESTADO", font=f_small, fill=DIM)
    d.text((360, 266), "ADQUIRIENDO", font=f_small, fill=AMBER)
    d.rectangle([360, 290, 500, 296], fill=(20, 32, 44))
    d.rectangle([360, 290, 360 + int(140 * 0.62), 296], fill=MINT)
    d.text((360, 302), "62 %  ·  CORTE 15/24", font=f_small, fill=DIM)

    # pie
    d.rectangle([0, H - 26, W, H], fill=PANEL)
    d.rectangle([0, H - 26, W, H - 25], fill=LINE)
    d.text((12, H - 19), "ESTUDIO  RM-2026-0417", font=f_small, fill=DIM)
    d.text((300, H - 19), "TEMP 18.4 C   HELIO 64 %", font=f_small, fill=DIM)

    img.save(OUT, optimize=True)
    print("SCREEN_OK", OUT, os.path.getsize(OUT) // 1024, "KB")


main()
