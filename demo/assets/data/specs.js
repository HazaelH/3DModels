/* Datos de la maqueta MERIDIAN 3T.
   Todos los valores son FICTICIOS: el producto no existe. Se centralizan aquí
   para que la ficha técnica, el landing y el PDF puedan beber de la misma fuente. */

export const PRODUCT = {
  name: "MERIDIAN 3T",
  claim: "Resonancia magnética de 3.0 T",
  ring: 70,          // cm de túnel
  channels: 32,      // canales de RF
  tris: 64288,       // triángulos del modelo GLB
  glb: "4.9 MB",
};

export const SPECS = [
  ["Campo magnético", "3.0 T", "imán superconductor"],
  ["Diámetro del túnel", "70 cm", "bore útil"],
  ["Apertura frontal", "92 cm", "cara al paciente"],
  ["Homogeneidad", "±0.05 ppm", "40 cm DSV"],
  ["Gradiente", "45 mT/m · 200 T/m/s", "conjunto de gradientes"],
  ["Canales de RF", "32", "bobina de cabeza incluida"],
  ["Peso del imán", "4 500 kg", "sin criostato"],
  ["Peso total en sala", "6 800 kg", "equipo + mesa"],
  ["Mesa de paciente", "227 kg · 200 kg", "carga máxima"],
  ["Ruido acústico", "< 78 dB(A)", "secuencia silenciosa"],
  ["Alimentación", "400 V · 60 kVA", "trifásica"],
  ["Helio líquido", "1 500 L", "0 % boil-off"],
  ["Sala requerida", "4.5 × 5.0 × 2.9 m", "mínimo"],
  ["Modelo 3D", "64 288 triángulos", "GLB · 4.9 MB"],
];

/* Las 32 piezas del GLB. La clave es el nombre exacto del nodo. */
export const PIECES = {
  MRI_Gantry_Core:        ["Gantry", "Núcleo del gantry", "Estructura que sostiene el imán y el túnel, rigidizada frente a vibraciones.", "Acero y composite", "Soporte estructural"],
  MRI_Top_Panel:          ["Gantry", "Panel superior", "Cubre la parte alta del gantry y aloja la ventilación del conjunto.", "ABS blanco", "Cubierta"],
  MRI_Front_Cover:        ["Gantry", "Cubierta frontal", "Cara visible al paciente: integra el aro de luz y la rotulación del equipo.", "ABS blanco", "Cubierta"],
  MRI_Rear_Cover:         ["Gantry", "Cubierta trasera", "Cierra el gantry por la zona técnica y da acceso al criostato.", "ABS blanco", "Cubierta"],
  MRI_Side_Panel_L:       ["Gantry", "Panel lateral izquierdo", "Carena desmontable que deja acceso a la electrónica de gradientes.", "ABS gris", "Cubierta"],
  MRI_Side_Panel_R:       ["Gantry", "Panel lateral derecho", "Carena desmontable con el mismo acceso de servicio que el lado izquierdo.", "ABS gris", "Cubierta"],
  MRI_Bore_Tunnel:        ["Gantry", "Túnel del bore", "Superficie interior de 70 cm que rodea al paciente durante la exploración.", "Liner clínico", "Túnel"],
  MRI_Bore_Trim:          ["Gantry", "Aro del túnel", "Flange mecanizado que remata el bore y fija el liner interior.", "Aluminio cepillado", "Remate"],
  MRI_Accent_Ring:        ["Gantry", "Anillo de acento", "Guía visual del túnel: iluminación indirecta que orienta al paciente.", "Policarbonato", "Iluminación"],
  MRI_Bore_Light_Ring:    ["Gantry", "Aro de luz", "Iluminación clínica del túnel, regulable según la secuencia.", "LED clínico", "Iluminación"],
  MRI_Base_Plinth:        ["Gantry", "Bancada", "Base que reparte el peso del imán y aísla la vibración del suelo.", "Acero y hormigón", "Estructura"],
  MRI_Leveling_Feet:      ["Gantry", "Patas niveladoras", "Cuatro apoyos regulables para nivelar el equipo en la sala.", "Acero", "Nivelación"],
  MRI_Alignment_Laser:    ["Gantry", "Láser de alineación", "Referencia luminosa para centrar al paciente en el isocentro.", "Módulo láser", "Posicionamiento"],

  MRI_Table_Base:         ["Mesa", "Base de mesa", "Pedestal fijo con paneles de servicio, rodapié y paso de cables.", "ABS y acero", "Estructura"],
  MRI_Table_Column:       ["Mesa", "Columna telescópica", "Tres camisas superpuestas que elevan la mesa hasta la altura de trabajo.", "Acero y ABS", "Elevación"],
  MRI_Table_Carriage:     ["Mesa", "Carro", "Guías y motor que desplazan la mesa hacia el túnel y la devuelven.", "Aluminio", "Desplazamiento"],
  MRI_Table_Surface:      ["Mesa", "Superficie de mesa", "Plataforma de fibra compatible con bobinas y accesorios.", "Fibra y ABS", "Apoyo"],
  MRI_Table_Cushion:      ["Mesa", "Colchón", "Espuma viscoelástica de 60 mm con funda impermeable.", "Espuma y PU", "Confort"],
  MRI_Table_Rail_L:       ["Mesa", "Guía lateral izquierda", "Riel para bobinas y accesorios de posicionamiento.", "Aluminio", "Anclaje"],
  MRI_Table_Rail_R:       ["Mesa", "Guía lateral derecha", "Riel de anclaje rápido para bobinas flexibles.", "Aluminio", "Anclaje"],
  MRI_Table_Headrest:     ["Mesa", "Reposa-cabezas", "Soporte anatómico que fija la cabeza del paciente.", "Espuma y ABS", "Posicionamiento"],
  MRI_Table_ControlPad:   ["Mesa", "Mando de mesa", "Controles de movimiento y parada junto al paciente.", "ABS y acero", "Control"],
  MRI_Head_Coil:          ["Bobinas", "Bobina de cabeza", "Array de 32 canales que se cierra sobre el paciente antes de entrar.", "Policarbonato", "Radiofrecuencia"],

  MRI_Console_Base:       ["Consola", "Base de consola", "Pedestal con rodapié de goma y paso de cables al suelo técnico.", "ABS y acero", "Estructura"],
  MRI_Console_Body:       ["Consola", "Cuerpo de consola", "Aloja el puesto de control y la electrónica de interfaz.", "ABS blanco", "Estructura"],
  MRI_Console_Screen:     ["Consola", "Monitor clínico", "Pantalla con protocolos, planificación y monitorización del estudio.", "Panel IPS", "Interfaz"],
  MRI_Console_Tray:       ["Consola", "Bandeja de control", "Teclado, trackball y parada de emergencia al alcance del operador.", "ABS", "Interfaz"],
  MRI_Emergency_Button:   ["Consola", "Parada de emergencia", "Seta roja que detiene el movimiento de mesa y el gradiente.", "Policarbonato", "Seguridad"],
  MRI_Handle_L:           ["Gantry", "Asa izquierda", "Agarre para el personal durante el traslado del paciente.", "Aluminio", "Manejo"],
  MRI_Handle_R:           ["Gantry", "Asa derecha", "Agarre de manejo en el lado derecho del gantry.", "Aluminio", "Manejo"],
  MRI_Vent_Grille_L:      ["Gantry", "Rejilla de ventilación izquierda", "Salida de aire del sistema de refrigeración.", "ABS", "Refrigeración"],
  MRI_Vent_Grille_R:      ["Gantry", "Rejilla de ventilación derecha", "Salida de aire del circuito de refrigeración.", "ABS", "Refrigeración"],
};

/* Anclas de las anotaciones, en coordenadas de three.js: (x, y, z). */
export const HOTSPOTS = [
  { id: "bore",   label: "Túnel de 70 cm",       pos: [0.40, 1.50, 0.58] },
  { id: "coil",   label: "Bobina de 32 canales", pos: [0.00, 1.18, 1.15] },
  { id: "table",  label: "Mesa de 227 kg",       pos: [0.00, 0.93, 2.05] },
  { id: "console",label: "Consola del operador", pos: [1.86, 1.30, 2.02] },
];
