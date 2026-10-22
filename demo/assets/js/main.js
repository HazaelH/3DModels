/* ==========================================================================
   MERIDIAN 3T — landing: scroll, anotaciones, ficha de pieza y simulación
   ========================================================================== */
import * as THREE from 'three';
import { createViewer } from './viewer.js';
import { PIECES, HOTSPOTS, SPECS } from '../data/specs.js';

const $ = (s, r = document) => r.querySelector(s);
const $$ = (s, r = document) => [...r.querySelectorAll(s)];

/* Poses de cámara por sección. [x, y, z] en metros, espacio three.js. */
const POSES = {
  hero:  { cam: [5.55, 2.55, 5.60], target: [-0.50, 0.85, 0.90], explode: 0, room: 0 },
  bore:  { cam: [3.10, 1.70, 4.00], target: [-0.30, 1.10, 0.30], explode: 0, room: 0 },
  parts: { cam: [6.80, 3.80, 6.60], target: [0.75, 0.95, 0.35], explode: 0.78, room: 0 },
  sim:   { cam: [-3.40, 2.15, 8.50], target: [-0.15, 0.90, 1.55], explode: 0, room: 0 },
  specs: { cam: [2.30, 2.05, 4.90], target: [0.40, 1.00, 0.45], explode: 0, room: 0 },
  room:  { cam: [3.85, 2.10, 3.95], target: [0.10, 0.90, 0.20], explode: 0, room: 1 },
  cta:   { cam: [4.60, 2.30, 5.60], target: [-0.10, 1.05, 0.55], explode: 0, room: 0 },
};

const sections = $$('[data-pose]').map((el) => ({
  el,
  id: el.dataset.pose,
  pose: POSES[el.dataset.pose],
}));

/* ------------------------------------------------------------- ficha técnica */
/* Dos columnas de 7 filas: cabe en pantalla sin scroll interno. */
const specGrid = $('#specs-grid');
const half = Math.ceil(SPECS.length / 2);
[SPECS.slice(0, half), SPECS.slice(half)].forEach((rows) => {
  const table = document.createElement('table');
  table.className = 'specs';
  table.innerHTML = '<tbody>' + rows.map(([k, v, n]) => (
    `<tr><td>${k}</td><td>${v}</td><td>${n}</td></tr>`
  )).join('') + '</tbody>';
  specGrid.appendChild(table);
});

/* --------------------------------------------------------------- anotaciones */
const hsWrap = $('#hotspots');
const hotspots = HOTSPOTS.map((h) => {
  const el = document.createElement('div');
  el.className = 'hotspot is-hidden';
  el.innerHTML = `<span class="hotspot__dot"></span><span class="hotspot__line"></span><span class="hotspot__label">${h.label}</span>`;
  hsWrap.appendChild(el);
  return { ...h, el, v: new THREE.Vector3(...h.pos) };
});

/* --------------------------------------------------------------- ficha pieza */
const card = $('#card');
const cardEls = {
  group: $('#card-group'), name: $('#card-name'), desc: $('#card-desc'),
  mat: $('#card-mat'), fn: $('#card-fn'),
};

function openCard(name) {
  const data = PIECES[name];
  if (!data) return;
  const [group, label, desc, mat, fn] = data;
  cardEls.group.textContent = group;
  cardEls.name.textContent = label;
  cardEls.desc.textContent = desc;
  cardEls.mat.textContent = mat;
  cardEls.fn.textContent = fn;
  card.classList.add('is-open');
  card.setAttribute('aria-hidden', 'false');
}

function closeCard() {
  card.classList.remove('is-open');
  card.setAttribute('aria-hidden', 'true');
}

$('#card-close').addEventListener('click', () => { closeCard(); viewer.select(null); });

/* ------------------------------------------------------------------- scroll */
const topbar = $('.topbar');
const progress = $('#progress');
let lastActive = '';

function scrollState() {
  const y = scrollY;
  const max = Math.max(1, document.documentElement.scrollHeight - innerHeight);
  progress.style.width = `${Math.min(100, (y / max) * 100)}%`;
  topbar.classList.toggle('is-stuck', y > 40);

  // índice continuo entre secciones
  const cy = y + innerHeight * 0.5;
  const centers = sections.map((s) => {
    const r = s.el.getBoundingClientRect();
    return r.top + scrollY + r.height * 0.5;
  });

  let i = 0;
  while (i < centers.length - 2 && cy > centers[i + 1]) i++;

  const a = sections[i], b = sections[i + 1] || sections[i];
  const span = Math.max(1, centers[i + 1] - centers[i]);
  const t = i + 1 < sections.length ? ease(clamp01((cy - centers[i]) / span)) : 1;

  const pose = lerpPose(a.pose, b.pose, t);
  viewer.setPose(pose);

  // estado de la sección activa
  const active = t < 0.5 ? a : b;
  if (active.id !== lastActive) {
    if (lastActive === 'sim') viewer.resetSim();
    if (active.id === 'sim') viewer.prepareSim();
    lastActive = active.id;
    closeCard();
    viewer.select(null);
  }
  document.body.classList.toggle('is-right', active.el.classList.contains('section--right'));

  const nearBore = active.id === 'bore';
  hsWrap.classList.toggle('is-on', nearBore);

  return { active: active.id, nearBore };
}

function ease(t) { return t * t * (3 - 2 * t); }
function clamp01(v) { return Math.min(1, Math.max(0, v)); }
function mix(a, b, t) { return a + (b - a) * t; }
function lerpPose(a, b, t) {
  return {
    cam: a.cam.map((v, i) => mix(v, b.cam[i], t)),
    target: a.target.map((v, i) => mix(v, b.target[i], t)),
    explode: mix(a.explode, b.explode, t),
    room: mix(a.room, b.room, t),
  };
}

/* ------------------------------------------------------------------ simulación */
const simBtn = $('#sim-play');
const simPhase = $('#sim-phase');
const simBar = $('#sim-bar');
const simTime = $('#sim-time');
let lastPhase = '';

simBtn.addEventListener('click', () => {
  closeCard();
  viewer.select(null);
  viewer.playSim();
  simBtn.innerHTML = '<svg viewBox="0 0 12 14" aria-hidden="true"><path d="M1 1l10 6-10 6z" fill="currentColor"/></svg> Reproducir de nuevo';
});

function simTick() {
  const s = viewer.simState;
  const pct = Math.round((s.t / (s.total || 21)) * 100);
  simBar.style.width = `${pct}%`;
  simTime.textContent = `${pct} %`;
  if (s.phase !== lastPhase) { simPhase.textContent = s.phase; lastPhase = s.phase; }
  requestAnimationFrame(simTick);
}

/* -------------------------------------------------------------------- inicio */
const loader = $('#loader');
let viewer = null;

try {
  viewer = await createViewer($('#scene'), {
    onPick: (name) => { if (name) openCard(name); else closeCard(); },
  });

  // anclas calculadas sobre la geometría real (centro de la pieza)
  const dynAnchor = { coil: ['MRI_Head_Coil', 0.10], table: ['MRI_Table_Cushion', 0.06] };
  for (const h of hotspots) {
    const d = dynAnchor[h.id];
    const part = d && viewer.parts.get(d[0]);
    if (part) h.v.copy(part.home).add(new THREE.Vector3(0, d[1], 0));
  }

  // primer estado antes de arrancar
  viewer.setPose(POSES.hero);
  window.__viewer = viewer;
  requestAnimationFrame(() => {
    scrollState();
    addEventListener('scroll', scrollState, { passive: true });
    addEventListener('resize', scrollState);
    addEventListener('keydown', (e) => {
      if (e.key === 'Escape') { closeCard(); viewer.select(null); }
    });

    // anotaciones: posición en pantalla
    const tick = () => {
      requestAnimationFrame(tick);
      if (!hsWrap.classList.contains('is-on')) {
        for (const h of hotspots) h.el.classList.add('is-hidden');
        return;
      }
      const rect = $('#scene').getBoundingClientRect();
      const leftLimit = innerWidth >= 1000 ? innerWidth * 0.36 : 24;
      for (const h of hotspots) {
        const p = viewer.project(h.v);
        const out = !p.visible || p.x < leftLimit || p.x > rect.right - 50 ||
                    p.y < rect.top + 90 || p.y > rect.bottom - 60;
        h.el.classList.toggle('is-hidden', out);
        if (out) continue;
        h.el.style.left = `${p.x}px`;
        h.el.style.top = `${p.y}px`;
        h.el.classList.toggle('flip', p.x > innerWidth * 0.66);
      }
    };
    tick();
    simTick();
    loader.classList.add('is-done');
  });
} catch (err) {
  console.error(err);
  loader.classList.add('is-done');
  document.body.insertAdjacentHTML('beforeend',
    '<p style="position:fixed;bottom:16px;left:16px;z-index:60;font:12px monospace;color:#F0A93E">' +
    'No se pudo cargar el visor 3D (WebGL o modelos).</p>');
}

/* -------------------------------------------------------------------- reveal */
const io = new IntersectionObserver((entries) => {
  for (const e of entries) if (e.isIntersecting) {
    e.target.classList.add('is-in');
    io.unobserve(e.target);
  }
}, { threshold: 0.25 });

$$('.panel, .hero__copy, .cta').forEach((el) => {
  el.classList.add('reveal');
  io.observe(el);
});
