"""Prueba del visor con el modelo nuevo.

Verifica:
  1. se cargan 32 piezas (las primitivas del GLB se agrupan por nodo)
  2. al hacer clic NO se mueve la pieza y se abre la ficha correcta
  3. explotar / restablecer devuelve las piezas a su sitio
  4. la simulacion completa corre y deja la mesa en su posicion
  5. no hay errores de consola

Uso:
    python tools/test_viewer.py [url] [ancho] [alto]
"""
import sys

from playwright.sync_api import sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8100/mri-viewer.html"
W = int(sys.argv[2]) if len(sys.argv) > 2 else 1600
H = int(sys.argv[3]) if len(sys.argv) > 3 else 900

fails = []
errors = []


def check(name, ok, detail=""):
    print(("  OK   " if ok else "  FALLA") + "  " + name + (("  " + str(detail)) if detail else ""))
    if not ok:
        fails.append(name)


with sync_playwright() as p:
    b = p.chromium.launch(args=["--use-gl=angle", "--use-angle=d3d11",
                                "--enable-unsafe-swiftshader"])
    pg = b.new_page(viewport={"width": W, "height": H})
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.goto(URL, wait_until="load")
    pg.wait_for_function("window.__parts && window.__parts.length > 0", timeout=60000)
    pg.wait_for_timeout(2500)

    n = pg.evaluate("window.__parts.length")
    check("32 piezas agrupadas", n == 32, n)

    names = pg.evaluate("window.__parts.map(p => p.name).sort()")
    check("nombres MRI_* unicos", len(set(names)) == 32 and all(x.startswith("MRI_") for x in names))

    # --- clic sobre el colchon (pieza solida y visible)
    pt = pg.evaluate("window.__project('MRI_Table_Cushion')")
    check("proyeccion del colchon", pt is not None and 0 < pt[0] < W and 0 < pt[1] < H, pt)

    before = pg.evaluate("window.__byName['MRI_Table_Cushion'].mesh.position.toArray()")
    pg.mouse.click(pt[0], pt[1])
    pg.wait_for_timeout(1200)
    sel = pg.evaluate("window.__selectedName()")
    after = pg.evaluate("window.__byName['MRI_Table_Cushion'].mesh.position.toArray()")
    moved = sum(abs(a - c) for a, c in zip(before, after))
    check("clic abre la ficha correcta", sel == "MRI_Table_Cushion", sel)
    check("el clic no mueve la pieza", moved < 1e-4, round(moved, 6))
    check("la ficha tiene texto", pg.evaluate("document.getElementById('title').textContent.length") > 2,
          pg.evaluate("document.getElementById('title').textContent"))

    # --- una pieza con 3 materiales (cubierta frontal)
    n_mats = pg.evaluate("window.__byName['MRI_Front_Cover'].mats.length")
    check("cubierta frontal con varios materiales", n_mats >= 2, n_mats)

    pg.keyboard.press("Escape")
    pg.wait_for_timeout(700)

    # --- explotar / restablecer
    pg.evaluate("document.getElementById('explode').click()")
    pg.wait_for_timeout(2600)
    dist = pg.evaluate("""() => {
        let s = 0;
        for (const p of window.__parts) s += p.mesh.position.distanceTo(p.home);
        return s;
    }""")
    check("explotar separa las piezas", dist > 3.0, round(dist, 2))

    pg.evaluate("document.getElementById('reset').click()")
    pg.wait_for_timeout(3200)
    back = pg.evaluate("""() => {
        let m = 0;
        for (const p of window.__parts) m = Math.max(m, p.mesh.position.distanceTo(p.home));
        return m;
    }""")
    check("restablecer vuelve al sitio", back < 0.02, round(back, 4))

    # --- simulacion completa (19.8 s)
    pg.evaluate("document.getElementById('simPlay').click()")
    pg.wait_for_timeout(21000)
    sim = pg.evaluate("""() => ({
        t: +window.__sim.t.toFixed(2),
        z: +window.__slideZ().toFixed(3),
        active: window.__sim.active,
        visible: window.__patient.pivot.visible,
    })""")
    check("simulacion termina", sim["t"] > 19.6, sim)
    check("la mesa vuelve a casa", abs(sim["z"]) < 0.01, sim["z"])
    check("el paciente se retira", sim["visible"] is False, sim["visible"])

    check("sin errores de consola", len(errors) == 0, errors[:3])
    b.close()

print("")
print("RESULTADO:", "TODO OK" if not fails else ("FALLAN %d" % len(fails)))
sys.exit(1 if fails else 0)
