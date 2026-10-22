# MERIDIAN 3T — demo 3D para web

Visor y sala de resonancia magnética modelados en Blender y exportados a glTF
para web. Este repositorio contiene el **pase de realismo (F1)**: la geometría,
los materiales, la sala y las herramientas para regenerarlo todo.

```
meridian-3t/
  models/
    MRI_Realista_Modular.glb    equipo: 32 piezas, 60 588 triángulos
    suite.glb                   sala: suelo, mamparos, puerta, plafones
    mannequin.glb               paciente animado (carga diferida)
    _src/MRI_v1.glb             GLB original, nunca se sobrescribe
  blender/
    m3t_lib.py                  utilidades (importar, bisel, UV, exportar)
    realism_pass.py             bisel + materiales + texturas + detalle
    build_suite.py              construye la sala
    render_preview.py           render de comprobación (Cycles CPU)
    out/                        meridian_3t.blend, suite.blend, informes
  tools/
    shot.py                     captura WebGL con Chromium
    test_viewer.py              prueba del visor (32 piezas, clic, explosión, simulación)
    make_screen.py              genera la UI de la consola
  textures/                     PNG de origen (los buenos)
  thumbs/                       miniaturas por pieza (F1: pendientes de regenerar)
  shots/                        capturas de seguimiento
  preview.html                  banco de pruebas del modelo (three.js 0.170)
  mri-viewer.html               visor completo anterior (referencia para F2)
  onepager/                     ficha PDF comercial
```

## Regenerar el modelo

```bat
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b -P blender\realism_pass.py
"C:\Program Files\Blender Foundation\Blender 5.2\blender.exe" -b -P blender\build_suite.py
```

`realism_pass.py` trabaja siempre sobre `models/_src/MRI_v1.glb` y escribe
`models/MRI_Realista_Modular.glb`, así que se puede repetir sin perder nada.

Etapas por separado:

```bat
blender -b -P blender\realism_pass.py -- --stage bevel,materials
blender -b -P blender\realism_pass.py -- --stage textures,details,export
```

## Ver y probar

```bat
python -m http.server 8100 --directory .
python tools\test_viewer.py http://127.0.0.1:8100/mri-viewer.html
python tools\shot.py "http://127.0.0.1:8100/preview.html" shots\hero.png 1280 720
```

`preview.html` acepta `?view=hero|front|bore` y `?nosuite=1` / `?nomri=1`.

## Contrato del modelo

El visor y las fichas dependen de los **32 nombres**. `realism_pass.py` valida
que estén todos antes de exportar y aborta si falta alguno:

`MRI_Gantry_Core, MRI_Top_Panel, MRI_Front_Cover, MRI_Rear_Cover,
MRI_Side_Panel_L/R, MRI_Bore_Tunnel, MRI_Bore_Trim, MRI_Accent_Ring,
MRI_Bore_Light_Ring, MRI_Base_Plinth, MRI_Leveling_Feet, MRI_Table_Base,
MRI_Table_Column, MRI_Table_Carriage, MRI_Table_Surface, MRI_Table_Cushion,
MRI_Table_Rail_L/R, MRI_Table_Headrest, MRI_Table_ControlPad, MRI_Head_Coil,
MRI_Console_Base, MRI_Console_Body, MRI_Console_Screen, MRI_Console_Tray,
MRI_Emergency_Button, MRI_Handle_L/R, MRI_Vent_Grille_L/R, MRI_Alignment_Laser`

Las 7 piezas que se deslizan al túnel (`SLIDE`) también se validan.

## Qué hizo el pase de realismo

1. **Bisel real**: el GLB importado traía las caras desconectadas (un cubo con
   24 vértices), lo que dejaba el modificador de bisel sin aristas que
   reconocer. Ahora se suelda, se recalculan normales hacia fuera, y se aplica
   bisel de 3,2 mm + normales ponderadas.  22 812 → 42 300 triángulos.
2. **Texturas recuperadas**: el GLB original embebía los *normal maps* en negro
   y los *roughness* en magenta (255,0,255), es decir, todo el equipo salía con
   rugosidad cero y normales invertidas. Se reinyectan los PNG de `textures/`.
3. **PBR completo**: clearcoat en paneles pintados, anisotropía en el aluminio,
   sheen en el colchón, emisión en el anillo del túnel y en la consola.
   Exportado como `KHR_materials_clearcoat / anisotropy / sheen / emissive_strength`.
4. **Paleta con contraste**: blanco clínico 0.66, cubiertas 0.42, base 0.04,
   aro teal 0.02/0.40/0.47. El equipo deja de ser un bloque blanco.
5. **Detalle unido a cada pieza** (sin romper los 32 nodos): aro grafito del
   túnel, garganta oscura, juntas de goma, 16 tornillos, costuras del liner,
   faldón de bancada, rótulos `MERIDIAN` y `3.0 T` en geometría extruida.
6. **Sala**: 10 × 10 × 3,1 m, vinilo, mamparos con juntas cada 75 cm, zócalo
   sanitario, puerta con ventana, ventana de control y cinco plafones LED.
   Materiales con *backface culling*: desde fuera de la sala las paredes no
   tapan la cámara.
7. **Consola**: textura de UI clínica generada (`tools/make_screen.py`) y UV de
   la pantalla reproyectadas (venían giradas 90°).
8. **F1.5 · consola y mesa**: bisel y carcasa del monitor (el GLB lo modelaba
   como una losa de 22 cm), teclado con teclas, trackball, seta de emergencia
   amarilla/roja, rejillas laterales, rodapié de goma y cable de red. En la mesa:
   paneles de acceso con junta y tornillos, tapa de servicio, moldura, tres
   camisas telescópicas con junta cromada, carenados del carro y cadena de
   cables. Todo unido a los nodos existentes: siguen siendo 32 piezas.
9. **Bobina de cabeza**: pieza nueva en Blender (`blender/build_head_coil.py`),
   exportada aparte como `models/head_coil.glb` (2 nodos: `COIL_Base` y
   `COIL_Top`, este último con el origen en la bisagra). Así el contrato de 32
   nodos del equipo no se toca. 64 288 triángulos en total.

## Landing (F2)

`demo/` es el prototipo del one-page: HTML + CSS + JS sin frameworks, three.js
0.170 por import map.

```bat
python -m http.server 8100 --directory .
start http://127.0.0.1:8100/demo/index.html
```

- `demo/assets/js/viewer.js`: escena, cámara guiada por scroll, 32 piezas
  seleccionables, explosión, anotaciones y simulación.
- `demo/assets/js/main.js`: recorrido por secciones, ficha de pieza, ficha
  técnica y estado de la simulación.
- `demo/assets/data/specs.js`: **fuente única** de especificaciones, textos de
  las 32 piezas y anclas de las anotaciones.
- El visor antiguo (`mri-viewer.html`) sigue disponible para comparar; la
  simulación del landing usa el mismo criterio (clip del maniquí, mesa que
  entra, bobina que se cierra y barrido de RF).

## Estado

- **F1 · modelo**: hecho. 32 piezas, 64 288 triángulos, 4,9 MB de GLB.
- **F1.5 · piezas clave**: hecho. Bobina de cabeza como GLB aparte, consola y
  pedestal de mesa con detalle mecánico. `tools/test_viewer.py` en verde.
- **F2 · landing**: prototipo hecho en `demo/`. Sticky canvas, narrativa por
  scroll, explosión, ficha por pieza y simulación de exploración.
- **F3 · extras** (radiografía, corte, AR): pendientes.
- **F4 · compresión**: pendiente — Draco + KTX2/WebP bajarían el GLB de 4,9 MB
  a ~1,2 MB. Ahora mismo las 6 texturas van en PNG sin comprimir.
- **F5 · presentación**: ficha PDF hecha; vídeo pendiente.

### Pendientes conocidos

- `thumbs/` son del modelo anterior: hay que regenerarlas con los materiales
  nuevos (32 miniaturas para la ficha de pieza del landing).
- El maniquí de la simulación es un asset low-poly aparte (`mannequin.glb`); se
  ve crudo en primeros planos. Sustituirlo o retocarlo es trabajo de F3.
- El render headless por software produce artefactos de *tiling* a 1600×900;
  capturar a 1280×720 o menos.
- Todas las cifras (4 500 kg, 60 kVA…) son de demostración y viven en
  `demo/assets/data/specs.js`.
