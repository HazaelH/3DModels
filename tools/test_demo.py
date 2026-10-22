import sys
from playwright.sync_api import sync_playwright

URL = "http://127.0.0.1:8100/demo/index.html"
fails = []
errors = []


def check(name, ok, detail=""):
    print(("  OK   " if ok else "  FALLA") + "  " + name + (("  " + str(detail)) if detail else ""))
    if not ok:
        fails.append(name)


with sync_playwright() as p:
    b = p.chromium.launch(args=["--use-gl=angle", "--use-angle=d3d11"])
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    pg.goto(URL, wait_until="networkidle")
    pg.wait_for_function("window.__viewer && window.__viewer.parts.size === 32", timeout=60000)
    pg.wait_for_timeout(1500)

    n = pg.evaluate("window.__viewer.parts.size")
    check("32 piezas", n == 32, n)

    # --- clic 3D sobre la pantalla de consola en la seccion del tunel
    pg.evaluate("document.querySelector('#sistema').scrollIntoView({block:'center'})")
    pg.wait_for_timeout(2200)
    pt = pg.evaluate("""() => {
      const p = window.__viewer.parts.get('MRI_Console_Screen');
      return window.__viewer.project(p.home);
    }""")
    check("pantalla proyectada en pantalla", 0 < pt["x"] < 1440 and 0 < pt["y"] < 900, pt)
    before = pg.evaluate("window.__viewer.parts.get('MRI_Console_Screen').node.position.toArray()")
    pg.mouse.click(pt["x"], pt["y"])
    pg.wait_for_timeout(900)
    opened = pg.evaluate("document.querySelector('#card').classList.contains('is-open')")
    name = pg.evaluate("document.querySelector('#card-name').textContent")
    after = pg.evaluate("window.__viewer.parts.get('MRI_Console_Screen').node.position.toArray()")
    moved = sum(abs(a - c) for a, c in zip(before, after))
    check("el clic abre la ficha", opened and len(name) > 2 and name != "Pieza", name)
    check("el clic no mueve la pieza", moved < 1e-5, round(moved, 7))
    pg.keyboard.press("Escape")

    # --- explosion
    pg.evaluate("document.querySelector('#piezas').scrollIntoView({block:'center'})")
    pg.wait_for_timeout(2800)
    dist = pg.evaluate("""() => {
      let s = 0;
      for (const p of window.__viewer.parts.values()) s += p.node.position.distanceTo(p.base);
      return s;
    }""")
    check("explosion separa las piezas", dist > 2.0, round(dist, 2))

    # --- simulacion completa
    pg.evaluate("document.querySelector('#simulacion').scrollIntoView({block:'center'})")
    pg.wait_for_timeout(1800)
    pg.click("#sim-play")
    pg.wait_for_function(
        "window.__viewer.simState.playing && window.__viewer.simState.t > 1.0",
        timeout=10000,
    )
    s = pg.evaluate("window.__viewer.simState")
    check("la simulacion arranca", s["playing"] is True and s["t"] > 1.0, round(s["t"], 2))
    check("fase inicial", s["phase"] not in ("En espera",), s["phase"])

    pg.wait_for_function("!window.__viewer.simState.playing", timeout=45000)
    s = pg.evaluate("window.__viewer.simState")
    check("la simulacion termina", (not s["playing"]) and abs(s["t"] - s["total"]) < 0.05, round(s["t"], 2))
    check("fase final", s["phase"] == "Exploración completada", s["phase"])
    pct = pg.evaluate("document.querySelector('#sim-time').textContent")
    check("progreso al 100 %", pct.strip() == "100 %", pct)

    off = pg.evaluate("""() => {
      const p = window.__viewer.parts.get('MRI_Table_Surface');
      return p.node.position.z - p.base.z;
    }""")
    check("la mesa vuelve a casa", abs(off) < 0.002, round(off, 4))

    check("sin errores de consola", len(errors) == 0, errors[:3])
    b.close()

print("")
print("RESULTADO:", "TODO OK" if not fails else ("FALLAN %d" % len(fails)))
sys.exit(1 if fails else 0)
