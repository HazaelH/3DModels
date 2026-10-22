"""Genera la ficha PDF (A4, una cara) desde onepager/ficha.html.

Uso:
    python tools/make_pdf.py [url] [salida]

Necesita el servidor local (python -m http.server 8100).
"""
import sys

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8100/onepager/ficha.html"
OUT = sys.argv[2] if len(sys.argv) > 2 else "onepager/MERIDIAN-3T-ficha.pdf"
PREVIEW = "shots/onepager_preview.png"

errors = []

with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 794, "height": 1123}, device_scale_factor=2)
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.goto(URL, wait_until="networkidle")
    pg.evaluate("document.fonts.ready")
    pg.wait_for_timeout(700)
    pg.screenshot(path=PREVIEW)
    pg.emulate_media(media="print")
    pg.pdf(path=OUT, format="A4", print_background=True, prefer_css_page_size=True,
           margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
    b.close()

with open(OUT, "rb") as fh:
    raw = fh.read()
pages = raw.count(b"/Type /Page") - raw.count(b"/Type /Pages")
print("PDF  %s  %.1f KB  paginas %d" % (OUT, len(raw) / 1024.0, pages or 1))
print("vista previa", PREVIEW)
if errors:
    print("ERRORES", errors[:3])
