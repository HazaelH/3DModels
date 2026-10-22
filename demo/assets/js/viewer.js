/* ==========================================================================
   MERIDIAN 3T — visor 3D del landing
   Escena única, cámara guiada por scroll, 32 piezas seleccionables y una
   simulación de exploración (maniquí + mesa + bobina de cabeza).
   ========================================================================== */
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { PIECES } from '../data/specs.js';

const MODEL = '../models/MRI_Realista_Modular.glb';const SUITE = '../models/suite.glb';
const PATIENT = '../models/patient.glb';
const COIL = '../models/head_coil.glb';

const SLIDE_PARTS = ['MRI_Table_Surface', 'MRI_Table_Cushion', 'MRI_Table_Headrest',
                     'MRI_Table_Rail_L', 'MRI_Table_Rail_R', 'MRI_Table_ControlPad',
                     'MRI_Head_Coil'];
const OUT = 0.42;            // mesa fuera, para cargar al paciente
const SCAN = 0.92;           // mesa dentro del túnel
const COIL_OFFSET = new THREE.Vector3(0, 0.050, -0.250); // MRI_Head_Coil -> bobina real
const COIL_LIFT = 0.045;      // la tapa se abre sobre su bisagra

const SIM = {
  total: 26.5,
  fadeIn: 1.20,
  fadeOut: 23.80,
  fadeOutEnd: 24.25,
  tableOut: [0.30, 1.20],
  coilClose: [8.40, 8.90],
  in: [9.00, 11.40],
  scan: [11.60, 14.60],
  out: [14.80, 17.20],
  coilOpen: [17.00, 17.40],
  home: [24.50, 25.90],
};

const clamp01 = (v) => Math.min(1, Math.max(0, v));
const ease = (t) => t * t * (3 - 2 * t);
const lerp = (a, b, t) => a + (b - a) * t;

export async function createViewer(canvas, { onPick } = {}) {
  /* ------------------------------------------------------------- renderer */
  const renderer = new THREE.WebGLRenderer({
    canvas, antialias: true, powerPreference: 'high-performance', alpha: false,
  });
  renderer.setPixelRatio(Math.min(devicePixelRatio, 1.75));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.12;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.setClearColor(0x0a0f14, 1);

  const scene = new THREE.Scene();
  scene.fog = new THREE.Fog(0x0a0f14, 9, 24);

  const camera = new THREE.PerspectiveCamera(34, 1, 0.05, 80);
  camera.position.set(3.2, 1.95, 4.5);

  /* ---------------------------------------------------------------- luces */
  scene.add(new THREE.HemisphereLight(0xdcecff, 0x0a1016, 0.75));

  const key = new THREE.DirectionalLight(0xffffff, 2.85);
  key.position.set(4.2, 6.0, 4.6);
  key.castShadow = true;
  key.shadow.mapSize.set(2048, 2048);
  key.shadow.camera.near = 0.5;
  key.shadow.camera.far = 18;
  key.shadow.camera.left = -4;
  key.shadow.camera.right = 4;
  key.shadow.camera.top = 4;
  key.shadow.camera.bottom = -3;
  key.shadow.bias = -0.0004;
  key.shadow.normalBias = 0.02;
  key.shadow.radius = 3;
  scene.add(key);

  const fill = new THREE.DirectionalLight(0xbcd6ea, 0.55);
  fill.position.set(-5, 3.2, 2.4);
  scene.add(fill);

  const rim = new THREE.DirectionalLight(0x9df3e2, 1.15);
  rim.position.set(-1.5, 3.0, -5.5);
  scene.add(rim);

  const pmrem = new THREE.PMREMGenerator(renderer);
  scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.05).texture;
  scene.environmentIntensity = 1.0;

  /* ---------------------------------------------------------------- suelo */
  const floor = new THREE.Mesh(
    new THREE.CircleGeometry(16, 72),
    new THREE.MeshStandardMaterial({ color: 0x111a23, roughness: 0.72, metalness: 0.05 })
  );
  floor.rotation.x = -Math.PI / 2;
  floor.receiveShadow = true;
  scene.add(floor);

  /* --------------------------------------------------------------- estado */
  const loader = new GLTFLoader();
  const machine = new THREE.Group();
  scene.add(machine);

  const parts = new Map();          // name -> { node, meshes, mats, home, dir }
  const pickables = [];
  const sliding = new Map();
  let suite = null, suiteMats = [];
  let patient = null, mixer = null, action = null, patMats = [];
  let coil = null, coilTop = null, coilTopBase = null, coilMats = [], headCoilNode = null;
  let sweep = null;

  const pose = { cam: camera.position.clone(), target: new THREE.Vector3(0, 1.0, 0.2), explode: 0, room: 0 };
  const want = { cam: pose.cam.clone(), target: pose.target.clone(), explode: 0, room: 0 };

  let selected = null;
  let explodeNow = 0;
  let sim = { active: false, t: 0, playing: false, done: false };
  let hovered = null;

  /* ------------------------------------------------------------- cargas */
  const load = (url) => new Promise((res, rej) => loader.load(url, res, undefined, rej));

  const mriGltf = await load(MODEL);

  const named = {};
  mriGltf.scene.traverse((o) => { named[o.name] = o; });

  for (const name of Object.keys(PIECES)) {
    const node = named[name];
    if (!node) { console.warn('pieza ausente', name); continue; }

    const box = new THREE.Box3().setFromObject(node);
    const home = box.getCenter(new THREE.Vector3());
    const meshes = [];
    const mats = [];
    const cache = new Map();

    node.traverse((o) => {
      if (!o.isMesh) return;
      o.castShadow = true;
      o.receiveShadow = true;
      const src = Array.isArray(o.material) ? o.material : [o.material];
      const out = src.map((m) => {
        if (!cache.has(m)) cache.set(m, m.clone());
        return cache.get(m);
      });
      o.material = Array.isArray(o.material) ? out : out[0];
      out.forEach((m) => { if (!mats.includes(m)) mats.push(m); });
      meshes.push(o);
      o.userData.part = name;
      pickables.push(o);
    });

    parts.set(name, { name, node, meshes, mats, home, base: node.position.clone(), dir: explodeDir(name, home) });
    if (SLIDE_PARTS.includes(name)) sliding.set(name, { node, base: node.position.clone() });
  }

  machine.add(mriGltf.scene);

  // suite (oculta hasta la sección de instalación)
  try {
    const sg = await load(SUITE);
    suite = sg.scene;
    suite.position.y = 0.004;      // evita z-fighting con el suelo del visor
    suite.visible = false;
    suite.traverse((o) => {
      if (!o.isMesh) return;
      o.material = o.material.clone();
      o.material.transparent = true;
      o.material.opacity = 0;
      o.material.depthWrite = false;
      suiteMats.push(o.material);
    });
    scene.add(suite);
  } catch (e) { console.warn('suite no disponible', e); }

  // paciente + bobina (para la simulación)
  try {
    const pg = await load(PATIENT);
    patient = new THREE.Group();
    const ps = pg.scene;
    ps.traverse((o) => {
      if (!o.isMesh) return;
      o.castShadow = true;
      o.receiveShadow = true;
      o.frustumCulled = false;           // la malla animada sale del bind-pose
      o.material = o.material.clone();
      o.material.transparent = false;
      o.material.opacity = 1;
      o.material.depthWrite = true;
      patMats.push(o.material);
    });
    patient.add(ps);
    patient.visible = false;
    scene.add(patient);

    mixer = new THREE.AnimationMixer(ps);
    const clip = pg.animations[0];
    action = mixer.clipAction(clip);
    action.loop = THREE.LoopOnce;
    action.clampWhenFinished = true;
    action.play();
    action.time = 0;
    mixer.update(0);
    patient.userData.dur = clip.duration;
    console.info('[sim] paciente', clip.duration.toFixed(2) + ' s');
  } catch (e) { console.warn('paciente no disponible', e); }

  try {
    const cg = await load(COIL);
    const head = parts.get('MRI_Head_Coil');
    headCoilNode = head ? head.node : null;

    // el aro auxiliar del GLB no se ve: lo sustituye la bobina detallada
    if (head) {
      for (const m of head.meshes) {
        const i = pickables.indexOf(m);
        if (i >= 0) pickables.splice(i, 1);
      }
      head.node.visible = false;
      head.node.castShadow = false;
      head.node.receiveShadow = false;
    }

    coil = new THREE.Group();
    cg.scene.traverse((o) => {
      if (!o.isMesh) return;
      o.castShadow = true;
      o.receiveShadow = true;
      o.material = o.material.clone();
      o.userData.part = 'MRI_Head_Coil';
      pickables.push(o);
      if (head) {
        head.meshes.push(o);
        if (!head.mats.includes(o.material)) head.mats.push(o.material);
      }
      if (/light/i.test(o.material.name)) {
        coilMats.push(o.material);
      }
    });
    coil.add(cg.scene);

    if (head && headCoilNode) {
      (headCoilNode.parent || machine).add(coil);
      coil.position.copy(headCoilNode.position).add(COIL_OFFSET);
      coil.updateWorldMatrix(true, false);
      head.home.setFromMatrixPosition(coil.matrixWorld);
      head.dir = explodeDir('MRI_Head_Coil', head.home);
    } else {
      coil.position.set(0, 0.990, 0.650);
      scene.add(coil);
    }

    coilTop = cg.scene.getObjectByName('COIL_Top');
    if (coilTop) coilTopBase = coilTop.position.clone();
    coil.visible = true;
  } catch (e) { console.warn('bobina no disponible', e); }

  // barrido de radiofrecuencia
  sweep = new THREE.Mesh(
    new THREE.TorusGeometry(0.34, 0.010, 8, 56),
    new THREE.MeshBasicMaterial({
      color: 0x74d0ff, transparent: true, opacity: 0,
      blending: THREE.AdditiveBlending, depthWrite: false,
    })
  );
  sweep.rotation.x = 0;
  sweep.position.set(0, 1.05, 0);
  sweep.visible = false;
  scene.add(sweep);

  /* --------------------------------------------------------------- tamaño */
  function resize() {
    const w = canvas.clientWidth || innerWidth;
    const h = canvas.clientHeight || innerHeight;
    const aspect = w / Math.max(1, h);
    // en pantallas verticales abrimos el fov para que quepa el equipo
    camera.fov = aspect < 0.95 ? 50 : aspect < 1.35 ? 40 : 34;
    if (canvas.width !== w * renderer.getPixelRatio()) {
      renderer.setSize(w, h, false);
    }
    camera.aspect = aspect;
    camera.updateProjectionMatrix();
  }
  addEventListener('resize', resize);
  resize();

  /* ------------------------------------------------------- cámara / poses */
  function setPose(next) {
    if (next.cam) want.cam.fromArray(next.cam);
    if (next.target) want.target.fromArray(next.target);
    if (next.explode !== undefined) want.explode = next.explode;
    if (next.room !== undefined) want.room = next.room;
  }

  /* ----------------------------------------------------------- selección */
  const ray = new THREE.Raycaster();
  const ndc = new THREE.Vector2();

  function partAt(clientX, clientY) {
    const r = canvas.getBoundingClientRect();
    ndc.set(((clientX - r.left) / r.width) * 2 - 1, -((clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    const hit = ray.intersectObjects(pickables, false)[0];
    return hit ? hit.object.userData.part : null;
  }

  function highlight(name) {
    for (const p of parts.values()) {
      const on = p.name === name;
      for (const m of p.mats) {
        if (!m.emissive) continue;
        if (on) {
          m.emissive.setHex(0x1fb79f);
          m.emissiveIntensity = 0.42;
        } else {
          m.emissive.setHex(m.userData.baseEmissive || 0x000000);
          m.emissiveIntensity = m.userData.baseEmissiveIntensity ?? 1;
        }
      }
    }
  }

  // guarda el emisivo original de cada material (antes de tocar nada)
  for (const p of parts.values()) {
    for (const m of p.mats) {
      m.userData.baseEmissive = m.emissive ? m.emissive.getHex() : 0;
      m.userData.baseEmissiveIntensity = m.emissiveIntensity ?? 1;
    }
  }

  function select(name) {
    selected = name;
    highlight(name);
  }

  let down = null;
  canvas.addEventListener('pointerdown', (e) => { down = [e.clientX, e.clientY]; });
  canvas.addEventListener('pointerup', (e) => {
    if (!down) return;
    const moved = Math.hypot(e.clientX - down[0], e.clientY - down[1]);
    down = null;
    if (moved > 6) return;
    const name = partAt(e.clientX, e.clientY);
    if (name) select(name); else select(null);
    onPick && onPick(name, e.clientX, e.clientY);
  });
  canvas.addEventListener('pointermove', (e) => {
    const name = partAt(e.clientX, e.clientY);
    if (name !== hovered) {
      hovered = name;
      canvas.style.cursor = name ? 'pointer' : 'default';
    }
  });

  /* ------------------------------------------------------------ simulación */
  /* Desplazamiento de la mesa: 0 = recogida, -OUT = fuera, +SCAN = dentro. */
  function tableOff(t) {
    const [a, b] = SIM.tableOut;
    if (t < b) return -OUT * ease(clamp01((t - a) / (b - a)));
    if (t < SIM.in[0]) return -OUT;
    if (t < SIM.in[1]) return lerp(-OUT, SCAN, ease(clamp01((t - SIM.in[0]) / (SIM.in[1] - SIM.in[0]))));
    if (t < SIM.out[0]) return SCAN;
    if (t < SIM.out[1]) return lerp(SCAN, -OUT, ease(clamp01((t - SIM.out[0]) / (SIM.out[1] - SIM.out[0]))));
    if (t < SIM.home[0]) return -OUT;
    if (t < SIM.home[1]) return lerp(-OUT, 0, ease(clamp01((t - SIM.home[0]) / (SIM.home[1] - SIM.home[0]))));
    return 0;
  }

  function setPatientFade(f) {
    if (!patMats.length) return;
    const trans = f < 0.999;
    for (const m of patMats) {
      if (m.transparent !== trans) {
        m.transparent = trans;
        m.depthWrite = !trans;
        m.needsUpdate = true;
      }
      m.opacity = f;
    }
  }

  function setEmissive(name, value) {
    const p = parts.get(name);
    if (!p) return;
    for (const m of p.mats) if (m.emissive) m.emissiveIntensity = value;
  }

  function simReset() {
    sim.active = false; sim.playing = false; sim.t = 0; sim.done = false;
    if (patient) { patient.visible = false; patient.position.set(0, 0, 0); }
    if (coilTop && coilTopBase) {
      coilTop.position.copy(coilTopBase);
      coilTop.rotation.x = 0;
    }
    for (const s of sliding.values()) s.node.position.copy(s.base);
    if (sweep) { sweep.visible = false; sweep.material.opacity = 0; }
    if (action) { action.time = 0; action.paused = false; mixer.update(0); }
    setPatientFade(1);
    setEmissive('MRI_Bore_Light_Ring', 0);
    setEmissive('MRI_Console_Screen', 1);
    setEmissive('MRI_Accent_Ring', 0);
  }

  function simPlay() {
    simReset();
    sim.active = true; sim.playing = true; sim.t = 0;
    if (patient) { patient.visible = true; setPatientFade(0); }
    updateSim(0);
  }

  /* Vista previa de la sección: bobina real cerrada sobre el cabezal. */
  function prepareSim() {
    if (sim.active) return;
    if (coilTop && coilTopBase) {
      coilTop.position.copy(coilTopBase);
      coilTop.rotation.x = 0;
    }
  }

  function updateSim(t) {
    const off = tableOff(t);

    // mesa: el cabezal, el colchón y la bobina viajan juntos
    for (const s of sliding.values()) s.node.position.z = s.base.z - off;

    // paciente: el clip ya trae la entrada, la sedestación y la salida
    if (patient) {
      const fade = t < SIM.fadeIn ? ease(clamp01(t / SIM.fadeIn))
        : t > SIM.fadeOut ? 1 - ease(clamp01((t - SIM.fadeOut) / (SIM.fadeOutEnd - SIM.fadeOut)))
        : 1;
      patient.visible = fade > 0.004;
      setPatientFade(fade);
      if (action) {
        action.time = Math.min(t, patient.userData.dur || t);
        mixer.update(0);
      }
      // mientras está sobre la mesa acompaña su recorrido
      const onTable = t >= SIM.in[0] && t <= SIM.out[1];
      patient.position.set(0, 0, onTable ? -(off + OUT) : 0);
    }

    // bobina de cabeza: se abre al sacar la mesa y se cierra al acoplarla
    if (coilTop && coilTopBase) {
      const down = ease(clamp01((t - SIM.coilClose[0]) / (SIM.coilClose[1] - SIM.coilClose[0])));
      const up = ease(clamp01((t - SIM.coilOpen[0]) / (SIM.coilOpen[1] - SIM.coilOpen[0])));
      const open = 1 - clamp01((off + OUT) / 0.20);     // 1 con la mesa fuera, 0 en casa
      const lift = open * (1 - down * (1 - up));       // 1 = abierta, 0 = cerrada
      coilTop.position.copy(coilTopBase);
      coilTop.position.y += COIL_LIFT * lift;
      coilTop.rotation.x = -0.60 * lift;               // bisagra en el extremo del túnel
    }

    // barrido y luces
    const scanning = t >= SIM.scan[0] && t <= SIM.scan[1];
    const pulse = scanning ? 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(t * 6.5)) : 0;
    setEmissive('MRI_Bore_Light_Ring', 0.4 + 7 * pulse);
    setEmissive('MRI_Console_Screen', 1.0 + 1.6 * pulse);
    setEmissive('MRI_Accent_Ring', 0.5 * pulse);
    for (const m of coilMats) m.emissiveIntensity = (m.userData.baseEmissiveIntensity || 1) * (0.35 + 2.2 * pulse);
    if (sweep) {
      sweep.visible = scanning;
      if (scanning) {
        sweep.material.opacity = 0.32;
        sweep.position.z = 0.55 - 1.1 * ((t - SIM.scan[0]) / (SIM.scan[1] - SIM.scan[0]));
      }
    }
  }

  function simPhase(t) {
    if (!sim.active) return 'En espera';
    if (t < SIM.tableOut[1]) return 'Preparando la mesa';
    if (t < 3.70) return 'El paciente llega';
    if (t < 5.00) return 'Sentándose en la mesa';
    if (t < 8.30) return 'Tumbándose';
    if (t < SIM.in[0]) return 'Colocando la bobina';
    if (t < SIM.scan[0]) return 'Entrando al túnel';
    if (t < SIM.scan[1]) return 'Adquiriendo imagen';
    if (t < SIM.coilOpen[0]) return 'Saliendo del túnel';
    if (t < SIM.coilOpen[1]) return 'Abriendo la bobina';
    if (t < 21.10) return 'Incorporándose';
    if (t < 21.40) return 'Sentado en el borde';
    if (t < 23.70) return 'Poniéndose de pie';
    if (t < SIM.fadeOutEnd) return 'El paciente se marcha';
    return 'Exploración completada';
  }

  /* ---------------------------------------------------------------- bucle */
  let last = performance.now() / 1000;
  let raf = 0;
  const camNow = camera.position.clone();
  const tgtNow = new THREE.Vector3(0, 1, 0);

  function frame() {
    raf = requestAnimationFrame(frame);
    const now = performance.now() / 1000;
    const dt = Math.min(now - last, 0.1);
    last = now;

    // cámara: amortiguado hacia la pose pedida
    const k = 1 - Math.pow(0.0015, dt);
    camNow.lerp(want.cam, k);
    tgtNow.lerp(want.target, k);
    camera.position.copy(camNow);
    camera.lookAt(tgtNow);

    // explosión (la mesa la controla la simulación cuando está activa)
    explodeNow += (want.explode - explodeNow) * (1 - Math.pow(0.004, dt));
    for (const p of parts.values()) {
      if (sim.active && sliding.has(p.name)) continue;
      p.node.position.copy(p.base).addScaledVector(p.dir, explodeNow);
    }

    // sala
    if (suite) {
      const vis = want.room > 0.02;
      suite.visible = vis;
      if (vis) for (const m of suiteMats) {
        const target = want.room;
        m.opacity += (target - m.opacity) * Math.min(1, dt * 4);
        m.depthWrite = m.opacity > 0.85;
      }
    }

    // simulación
    if (sim.playing) {
      sim.t += dt;
      if (sim.t >= SIM.total) { sim.t = SIM.total; sim.playing = false; sim.done = true; }
      updateSim(sim.t);
    }

    // la bobina detallada sigue al nodo de la pieza (mesa y vista explotada)
    if (coil && headCoilNode) {
      coil.position.copy(headCoilNode.position).add(COIL_OFFSET);
    }

    renderer.render(scene, camera);
  }
  frame();

  /* ---------------------------------------------------------------- API */
  return {
    setPose,
    select,
    resetSim: simReset,
    prepareSim,
    playSim: simPlay,
    get simState() {
      return { ...sim, total: SIM.total, phase: simPhase(sim.t) };
    },
    project(v3) {
      const v = v3.clone().project(camera);
      const r = canvas.getBoundingClientRect();
      return {
        x: r.left + (v.x * 0.5 + 0.5) * r.width,
        y: r.top + (-v.y * 0.5 + 0.5) * r.height,
        visible: v.z < 1 && v.z > -1,
      };
    },
    parts,
    dispose() { cancelAnimationFrame(raf); renderer.dispose(); },
  };
}

/* Dirección de explosión por pieza: radial en el gantry, lateral en mesa y
   consola. Se calcula con el centro real de cada pieza en el GLB. */
function explodeDir(name, home) {
  if (name.startsWith('MRI_Table_')) {
    if (/Column|Base/.test(name)) return new THREE.Vector3(0.22, -1.0, 0.1).normalize();
    if (/Carriage/.test(name)) return new THREE.Vector3(0.15, -0.55, 0.15).normalize();
    if (/Cushion|Surface/.test(name)) return new THREE.Vector3(0, 0.85, 0.05).normalize();
    return new THREE.Vector3(0.6, 0.2, 0.1).normalize();
  }
  if (name.startsWith('MRI_Console') || name === 'MRI_Emergency_Button') {
    return new THREE.Vector3(1.0, 0.22, 0.35).normalize();
  }
  if (name === 'MRI_Head_Coil') return new THREE.Vector3(0, 0.5, 1.0).normalize();

  const c = new THREE.Vector3(0, 1.05, 0);
  const dy = home.y > 1.35 ? 0.55 : home.y < 0.45 ? -0.55 : 0.05;
  const d = new THREE.Vector3((home.x - c.x) * 0.8, dy, (home.z - c.z) * 1.1);
  if (d.lengthSq() < 1e-4) d.set(0, 0, 1);
  return d.normalize();
}
