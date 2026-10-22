# MERIDIAN 3T — Demo 3D web

Maqueta interactiva de un sistema de resonancia magnética **MERIDIAN 3T** (3.0 T) para web. HTML/CSS/JS puro, Three.js 0.170 vía *import map*, sin frameworks, sin build, sin backend y sin login. El objetivo es mostrar el equipo descompuesto (32 piezas), con vista explosiva, anotaciones, ficha técnica, simulación del flujo paciente (entrar/sentar/tumbar/escáner/salir) y una ficha PDF comercial.

## Estado actual

- **F1 · Modelo**: `models/MRI_Realista_Modular.glb` con **32 piezas** (contrato estricto). ~5,06 MB.
- **F1.5 · Detalle clave**: bobina de cabeza separada (`models/head_coil.glb`) para no romper el contrato de 32 nodos; consola/mesa con mayor detalle.
- **F2 · Landing**: `demo/` (página única con scroll). Visor 3D sticky, selección de piezas, explosión, hotspots/anotaciones, ficha lateral, simulación completa. 
- **Paciente**: `models/patient.glb` (5,30 MB) con animación *baked* (Mixamo/Ch16) y pelo reconstruido tipo "shell" (scalp-duplicate + dome crown) en color mate oscuro, altura/cabello correctos, sin clipping con bore/bobina/mesa.
- **Suite/sala**: `models/suite.glb` (oculta hasta la sección "Instalación").
- **Tests**: `tools/test_demo.py` **12/12 OK**, `tools/test_viewer.py` **13/13 OK**. Sin errores de consola.
- **F3/F4/F5**: pendientes (compresión Draco/KTX2, miniaturas nuevas, vídeo, etc.)

> **Nota**: Este demo utiliza datos ficticios. "MERIDIAN 3T" es un nombre de maqueta.

## Estructura del proyecto

```text
meridian-3t/
├── assets/                # assets generales (si aplica)
├── blender/               # scripts para regenerar modelos/sala/paciente
│   ├── build_patient_mixamo.py  # reconstrucción paciente + pelo (shell + crown dome)
│   ├── build_head_coil.py       # generación bobina de cabeza
│   ├── build_suite.py           # construcción sala
│   ├── m3t_lib.py               # utilidades Blender
│   ├── realism_pass.py          # pase F1/F1.5 sobre MRI_v1
│   └── out/                     # .blend e informes
├── demo/                  # landing principal (lo que se debe servir)
│   ├── index.html         # entrada (import map Three.js 0.170)
│   └── assets/
│       ├── css/main.css
│       ├── data/specs.js  # fuente única: 32 piezas, grupos, descripciones, specs
│       └── js/
│           ├── main.js    # scroll, UI, simulación, fichas
│           └── viewer.js  # escena Three.js, carga GLB, poses, explosión, simulación
├── maniqui/               # referencias/recursos maniquí
├── models/                # GLB listos para web
│   ├── MRI_Realista_Modular.glb  # 32 piezas
│   ├── head_coil.glb             # bobina de cabeza separada (COIL_Base/COIL_Top)
│   ├── patient.glb               # paciente animado (Ch16, Mixamo baked)
│   ├── suite.glb                 # sala
│   ├── mannequin.glb             # variante antigua (referencia)
│   └── _src/MRI_v1.glb           # original, nunca sobrescribir
├── onepager/              # ficha comercial
│   └── MERIDIAN-3T-ficha.pdf
├── preview.html           # banco de pruebas rápido
├── mri-viewer.html        # visor anterior (comparación)
├── shots/                 # capturas
├── textures/              # PNG origen
├── thumbs/                # miniaturas (pendientes regenerar con nuevos materiales)
└── tools/                 # utilidades/tests/captura
    ├── make_screen.py
    ├── shot.py
    ├── test_demo.py       # tests landing (12/12)
    └── test_viewer.py     # tests visor (13/13)
```

## Requisitos

- **Navegador moderno** con WebGL 2 (Chrome/Edge/Firefox/Safari recientes).
- **Servidor HTTP local** para desarrollo (no funciona con `file://` por módulos ES e import map).
- **Blender 5.2** (solo si se quiere regenerar modelos/sala/paciente).
- **Python 3.x** (solo para tests/captura/headless).

## Arranque rápido (desarrollo)

Desde la raíz `meridian-3t/`:

```bash
# Servidor local
python -m http.server 8100 --directory .

# Abrir landing
start http://127.0.0.1:8100/demo/index.html
# o
http://127.0.0.1:8100/demo/index.html
```

**Preview rápido:**
```bash
start http://127.0.0.1:8100/preview.html?view=hero
start http://127.0.0.1:8100/preview.html?view=bore&nosuite=1
```

## Arquitectura del demo

### `demo/index.html`
- Import map a Three.js 0.170 (ESM).
- Canvas sticky `#scene`, UI por scroll, paneles laterales, card de pieza, loader.
- Enlace a `../onepager/MERIDIAN-3T-ficha.pdf`.

### `demo/assets/js/viewer.js` (motor 3D)
- Carga: `MRI_Realista_Modular.glb`, `suite.glb`, `patient.glb`, `head_coil.glb`.
- **Contrato 32 piezas**: lee `PIECES` de `specs.js`. Si falta alguna, avisa por consola. Valida también piezas deslizantes (`SLIDE_PARTS`).
- **Selección**: raycasting sobre `pickables`, highlight con emisión sutil, callback `onPick`.
- **Explosión**: direcciones radiales/laterales calculadas por centro de pieza; la mesa queda controlada por simulación cuando activa.
- **Simulación paciente** (26.5 s): timeline `SIM` con fases (preparar mesa → llegar/sentar/tumbar → colocar bobina → entrar/escáner/salir → levantarse/irse). 
  - Animación bakeada con `AnimationMixer` (clip único). `WALK_RATE` implícito en timing; paciente acompaña movimiento de mesa.
  - Fade in/out 1.20s / 23.80–24.25s.
  - Bobina de cabeza: se abre/cierra animando `COIL_Top` sobre bisagra (`COIL_LIFT`, rotación). Se sincroniza con posición real de `MRI_Head_Coil`.
  - Barrido RF con anillo/emisión pulsada en bore/consola.
- **Sala**: `suite.glb` aparece en sección "Instalación" con fade.
- **Iluminación**: Hemisphere + Directional (key/fill/rim), PMREM con RoomEnvironment, sombras PCFSoft.
- **Rendimiento**: `pixelRatio` limitado, antialias, tone mapping ACES Filmic.

### `demo/assets/js/main.js`
- Orquesta scroll, actualiza poses de cámara por sección (`data-pose`), muestra ficha de pieza, ficha técnica desde `specs.js`, controla simulación (botón play, fase/progreso).

### `demo/assets/data/specs.js`
**Fuente única** de verdad:
- Lista/orden de las 32 piezas con grupo, nombre visible, descripción, material/función.
- Anclas/hotspots para anotaciones.
- Datos de ficha técnica mostrados en la landing.
- Debe mantenerse alineado con nombres reales en `MRI_Realista_Modular.glb`.

## Paciente, pelo y bobina (detalles técnicos)

### Pelo reconstruido (sin gorra)
El pelo se reconstruye como **cáscara duplicada del cuero cabelludo**:
1. Duplicar parte superior del cráneo/skin -> `hair_shell` cortada por encima de la línea del cabello.
2. Relleno de corona: agrupación por bucle de frontera (loop más alto), generar **dome de 3 anillos**, unir al `Ch16_Body1`.
3. Material mate oscuro: `(0.020, 0.012, 0.007)`, `roughness ~0.95`, `specular ~0.10` (sin brillo plástico).
4. Altura ajustada: línea frontal ~1.660–1.682 m, laterales ~1.635 m, trasera ~1.575 m; grosor 1.5 mm (borde) → 6 mm (corona), centro levemente elevado.
5. Resultado: cabello oscuro, visible, natural, sin corona calva, sin aspecto de maniquí.

Script: `blender/build_patient_mixamo.py`. El GLB final se exporta con **armature + objeto TRS + acción fusionada** para animación bakeada correcta en Three.js.

### Bobina de cabeza
- Modelada aparte en Blender (`blender/build_head_coil.py`), exportada como `models/head_coil.glb` con nodos `COIL_Base`, `COIL_Top` (origen en bisagra).
- En `viewer.js`: se oculta el aro auxiliar de `MRI_Head_Coil` del equipo modular, se adjunta `head_coil.glb` como sibling copiando posición/orientación del nodo real cada frame.
- Animación de apertura/cierre en simulación sincronizada con entrada/salida de mesa.

### Simulación
- Duración: **26.5 s**. Timings en `SIM` (tableOut/in/scan/out/coilClose/Open/fade/home).
- Mesa corre sobre raíles (`MRI_Table_*` deslizantes). Paciente acompaña cuando está sobre mesa.
- Exit fade 23.80–24.25 s. Sin movimientos erráticos, sin flotación, sin clipping.
- Coil clearance verificado; tests pasan.

## Regeneración (Blender)

Requiere Blender 5.2 instalado. Ejecutar desde raíz `meridian-3t/`.

### Equipo modular + sala
```bat
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b -P blender\realism_pass.py
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b -P blender\build_suite.py
```

`realism_pass.py` parte siempre de `models/_src/MRI_v1.glb` y escribe `models/MRI_Realista_Modular.glb` (no modifica el original). Valida **exactamente 32 piezas** antes de exportar (abortando si falta alguna). También valida piezas deslizantes.

Por etapas:
```bat
blender -b -P blender\realism_pass.py -- --stage bevel,materials
blender -b -P blender\realism_pass.py -- --stage textures,details,export
```

### Paciente + pelo
```bat
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b -P blender\build_patient_mixamo.py
```
Revisa el script para rutas de fuente Mixamo (si se actualiza) y exporta `models/patient.glb` con animación bakeada.

### Bobina de cabeza
```bat
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b -P blender\build_head_coil.py
```
Exporta `models/head_coil.glb`.

### Lo que hace `realism_pass.py` (resumen)
1. Soldadura + normales hacia fuera (GLB import traía caras desconectadas). Bisel 3.2 mm + normales ponderadas (22k → ~42k tris aprox).
2. Reinyección de texturas desde `textures/` (normal/roughness corregidos).
3. PBR: clearcoat, anisotropía, sheen, emisión (anillo túnel/consola), `KHR_materials_*`.
4. Paleta clínica con contraste.
5. Detalle por pieza sin romper nodos (aros, juntas, tornillos, costuras, rótulos `MERIDIAN`/`3.0 T`).
6. Mejoras F1.5: consola/mesa mecánica.
7. Exporta contrato 32 piezas.

## Tests

```bash
# Tests landing/demo
python tools/test_demo.py http://127.0.0.1:8100/demo/index.html

# Tests visor anterior
python tools/test_viewer.py http://127.0.0.1:8100/mri-viewer.html
```

Los tests validan: presencia de 32 piezas, mapeo, explosión, interacción básica, carga de modelos, etc. Estado actual: **ambos verdes**.

## Integración / embedding

### Iframe directo
```html
<iframe 
  src="https://tu-dominio.com/meridian-3t/demo/index.html" 
  width="100%" 
  height="800" 
  style="border:0" 
  loading="lazy"
  allow="fullscreen">
</iframe>
```

### Ruta directa
Servir todo el directorio `meridian-3t/` estáticamente. Entradas válidas: `demo/index.html` (recomendada), `preview.html`, `mri-viewer.html`.

### API JS expuesta (`viewer.js`)
`createViewer(canvas, { onPick })` devuelve:
- `setPose({cam, target, explode, room})`
- `select(name)` / selección por click
- `prepareSim()` / `playSim()` / `resetSim()`
- `simState` ({active, playing, t, done, total, phase})
- `project(v3)`, `parts`, `dispose()`

<<<<<<< HEAD
Ver `demo/assets/js/main.js` para uso real.

## Hosting estático (producción)

- **Servir sobre HTTP(S)**. No `file://`.
- **MIME types**: `.glb` → `model/gltf-binary`, `.gltf` → `model/gltf+json`, `.js` → `text/javascript` (módulos), `.css` → `text/css`, `.json` → `application/json`.
- **Caché**: considerar `Cache-Control` para GLB/JS/CSS (versionar si cambian). Para iteración, `no-cache` o hash en nombre.
- **CSP**: si hay CSP restrictiva, permitir `https://cdn.jsdelivr.net` para Three.js (import map). También `fonts.googleapis.com`/`fonts.gstatic.com` si se mantienen Google Fonts.
- **Compresión**: gzip/br en servidor ayuda (GLB ya binarios).
- **Tamaño**: `MRI_Realista_Modular.glb` ~5.06 MB, `patient.glb` ~5.30 MB, `head_coil.glb` ~0.136 MB, `suite.glb` ~0.059 MB. Ver sección "Optimizaciones" abajo.

### Despliegue local con servidor simple
```bash
# Python
python -m http.server 8080 --directory C:/ruta/a/meridian-3t

# Node (opcional)
npx serve C:/ruta/a/meridian-3t
```

## Offline / autoalojamiento
El demo usa **Three.js desde CDN** (`cdn.jsdelivr.net`). Para funcionar 100% offline, descargar Three.js 0.170 y actualizar `demo/index.html` import map a rutas locales (ej. `./assets/vendor/three/...`).

## Optimizaciones pendientes (F4)
- **Draco**: geometría comprimida (significativa reducción).
- **KTX2 + Basis Universal**: texturas comprimidas GPU-friendly.
- **WebP/AVIF**: donde aplique.
- **Miniaturas**: regenerar `thumbs/` con materiales actuales (32 piezas).
- **glTFpack/glTF-Transform**: limpiar, weld, deduplicate.

## Troubleshooting

| Problema | Causa | Solución |
|---|---|---|
| Canvas en blanco / módulos fallan | Abierto con `file://` | Usar servidor HTTP local. |
| Piezas no aparecen / "pieza ausente" | Nombre no coincide con contrato 32 | Revisar `specs.js` vs nodos GLB. `realism_pass.py` valida contrato. |
| Paciente sin animación / T-pose raro | Acción no bakeada o mixer mal inicializado | Verificar `patient.glb` tiene animación; revisar `viewer.js` (loopOnce/clampWhenFinished). |
| Pelo raro/altura incorrecta | Shell mal cortado | Regenerar con `build_patient_mixamo.py`. Revisar altura en Blender. |
| Bobina no sigue mesa / se ve doble | Nodo `MRI_Head_Coil` no encontrado o no ocultado | Comprobar carga `head_coil.glb`, lógica en `viewer.js` líneas ~209-257. |
| Texto pixelado/tiling en captura headless | Artefacto Chromium/ANGLE (software) | Capturar a 1280×720 o usar GPU. No es bug de código. |
| Suite tapa escena fuera de sección | Lógica de visibilidad | Aparece solo con `want.room>0.02` (sección Instalación). |
| Sombras raras / z-fighting | Bias/shadow map | Ajustar `shadow.bias`/`normalBias` en `viewer.js` si necesario. |

## Discrepancias conocidas
- **onepager/MERIDIAN-3T-ficha.pdf**: puede tener cifras/triángulos/tiempos distintos a valores actuales (modelo evolucionado). Tratar como ficha comercial de maqueta; fuente viva = `demo/assets/data/specs.js` + este README.
- **mannequin.glb**: antiguo/low-poly, no usado en simulación actual (se usa `patient.glb` con Ch16).
- **thumbs/**: desactualizados respecto a materiales F1.5.

## Migración / ubicación

- **Ubicación actual del demo MERIDIAN 3T**: `C:\Users\hazae\PymeTech\demos\meridian-3t\` (aquí se encuentra todo lo funcional: `demo/`, `models/`, `blender/`, `tools/`, etc.).
- **`C:\Users\hazae\ExpoCredito`**: contiene duplicados/archivos más antiguos de algunos assets MRI, **no se han creado ni modificado archivos nuevos en ExpoCredito en esta sesión**. No hay nada generado aquí que requiera migración; la tarea solicitada era únicamente **actualizar/crear este README** con documentación completa.

## Créditos / Licencias
- **Three.js**: MIT License (https://github.com/mrdoob/three.js)
- **Google Fonts** (Exo 2, Jost, IBM Plex Mono): OFL
- **Mixamo**: usado únicamente para desarrollo/bake de animación (`Ch16`). No se redistribuyen assets con licencia restrictiva fuera de fines de maqueta; revisar términos si se reutiliza en otro contexto.
- **Modelado/maquetación**: proyecto interno PymeTech para demo MERIDIAN 3T.
- **GLTF/GLB**: formatos estándares.

---
