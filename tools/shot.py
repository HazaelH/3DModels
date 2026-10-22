"""Captura el visor con Chromium (Playwright) y reporta errores de consola.

Uso:
    python tools/shot.py http://127.0.0.1:8100/mri-viewer.html shots/web_hero.png 1600 900
"""
import sys

from playwright.sync_api import sync_playwright

url = sys.argv[1]
out = sys.argv[2]
w = int(sys.argv[3]) if len(sys.argv) > 3 else 1600
h = int(sys.argv[4]) if len(sys.argv) > 4 else 900
wait_ms = int(sys.argv[5]) if len(sys.argv) > 5 else 2500

errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(args=[
        "--use-gl=angle", "--use-angle=d3d11", "--enable-unsafe-swiftshader",
    ])
    page = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=1)
    page.on("console", lambda m: errors.append(("console", m.type, m.text))
            if m.type in ("error", "warning") else None)
    page.on("pageerror", lambda e: errors.append(("pageerror", str(e))))
    page.goto(url, wait_until="load")
    try:
        page.wait_for_function(
            "() => window.__ready === true || (window.__parts && window.__parts.length > 0)",
            timeout=25000)
    except Exception as exc:  # noqa: BLE001
        errors.append(("wait", str(exc)[:120]))
    page.wait_for_timeout(wait_ms)
    info = page.evaluate("""() => {
        const r = { parts: window.__parts ? window.__parts.length : -1,
                    cam: window.__camera ? window.__camera.position.toArray().map(v=>+v.toFixed(2)) : null,
                    dist: window.__camera ? +window.__camera.position.length().toFixed(2) : null,
                    renderer: window.__THREE ? 'three' : '-' };
        return r;
    }""")
    # Preferir el buffer WebGL: el compositor headless devuelve a veces un frame stale
    data = None
    try:
        if page.evaluate("typeof window.__grab === 'function'"):
            data = page.evaluate("window.__grab()")
    except Exception as exc:  # noqa: BLE001
        errors.append(("grab", str(exc)[:120]))
    if data and data.startswith("data:image/png;base64,"):
        import base64
        with open(out, "wb") as fh:
            fh.write(base64.b64decode(data.split(",", 1)[1]))
    else:
        page.screenshot(path=out)
    browser.close()

print("SHOT", out, "parts", info.get("parts"), "cam", info.get("cam"), "dist", info.get("dist"))
for e in errors[:12]:
    print("ERR", e)
