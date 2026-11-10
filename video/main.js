// =============================================================
//  Sandoval Legal — secuencia motion graphic de 15 s
//  Todo se calcula a partir del tiempo t (determinista):
//  renderAt(t) dibuja exactamente el mismo fotograma siempre.
// =============================================================
import * as THREE from 'three';
import { RoomEnvironment } from 'three/addons/environments/RoomEnvironment.js';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';

const W = 1920, H = 1080, DURATION = 15;
const GOLD = 0xc9a45c, GOLD_LIGHT = 0xdcc08a, NAVY = 0x0b1f3a, NAVY_DEEP = 0x071629, CREAM = 0xf7f3ec;

// ---------- utilidades ----------
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const range = (t, a, b) => clamp((t - a) / (b - a));
const lerp = (a, b, k) => a + (b - a) * k;
const E = {
  inOut: (x) => (x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2),
  inOut5: (x) => (x < 0.5 ? 16 * x ** 5 : 1 - Math.pow(-2 * x + 2, 5) / 2),
  out: (x) => 1 - Math.pow(1 - x, 3),
  out5: (x) => 1 - Math.pow(1 - x, 5),
  expoOut: (x) => (x >= 1 ? 1 : 1 - Math.pow(2, -10 * x)),
  in: (x) => x * x * x,
  back: (x) => { const c1 = 1.5, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); },
};
function rng(seed) { // mulberry32
  return () => { seed |= 0; seed = (seed + 0x6d2b79f5) | 0; let t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
}

// ---------- render ----------
const canvas = document.getElementById('gl');
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(1);
renderer.setSize(W, H, false);
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.toneMappingExposure = 1.05;

const scene = new THREE.Scene();
scene.background = new THREE.Color(NAVY_DEEP);
scene.fog = new THREE.FogExp2(NAVY_DEEP, 0.045);
const pmrem = new THREE.PMREMGenerator(renderer);
scene.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;

const camera = new THREE.PerspectiveCamera(38, W / H, 0.05, 200);

const composer = new EffectComposer(renderer);
composer.setSize(W, H);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(W, H), 0.75, 0.5, 0.78);
composer.addPass(bloom);
composer.addPass(new OutputPass());

// ---------- luces ----------
scene.add(new THREE.HemisphereLight(0x5a78a8, 0x05101f, 0.4));
const key = new THREE.SpotLight(0xffd9a0, 140, 40, Math.PI / 5, 0.6, 1.6);
key.position.set(5, 8, 7); scene.add(key, key.target);
const rim = new THREE.DirectionalLight(0x6f9bff, 1.4); rim.position.set(-6, 3, -6); scene.add(rim);
const glow = new THREE.PointLight(GOLD, 30, 14, 1.5); scene.add(glow);

// ---------- materiales ----------
const goldMat = new THREE.MeshStandardMaterial({ color: GOLD, metalness: 1, roughness: 0.22, envMapIntensity: 1.4 });
const marbleMat = new THREE.MeshStandardMaterial({ color: 0x8f8676, metalness: 0.1, roughness: 0.62, envMapIntensity: 0.5 });

// Suelo reflectante oscuro
const floor = new THREE.Mesh(new THREE.CircleGeometry(40, 64),
  new THREE.MeshStandardMaterial({ color: 0x06111f, metalness: 0.3, roughness: 0.55, envMapIntensity: 0.15 }));
floor.rotation.x = -Math.PI / 2; floor.position.y = -2.25; scene.add(floor);

// ---------- 1 · Rombo 3D (octaedro) ----------
const octa = new THREE.Group();
const octaMesh = new THREE.Mesh(new THREE.OctahedronGeometry(1.15, 0), goldMat);
const octaEdges = new THREE.LineSegments(new THREE.EdgesGeometry(octaMesh.geometry),
  new THREE.LineBasicMaterial({ color: GOLD_LIGHT, transparent: true }));
octaEdges.scale.setScalar(1.48);
octa.add(octaMesh, octaEdges); octa.position.y = 0.3; scene.add(octa);

// ---------- 2 · Columnas clásicas (torno) ----------
function columnGeometry() {
  const p = [];
  const add = (r, y) => p.push(new THREE.Vector2(r, y));
  add(0, -2.25); add(0.62, -2.25); add(0.62, -2.05); add(0.52, -2.0); add(0.55, -1.9); add(0.44, -1.8);
  for (let i = 0; i <= 12; i++) { const y = -1.8 + (i / 12) * 3.4; add(0.44 - 0.06 * (i / 12) ** 1.5, y); }
  add(0.5, 1.68); add(0.46, 1.78); add(0.66, 1.92); add(0.66, 2.1); add(0, 2.1);
  const g = new THREE.LatheGeometry(p, 48);
  // acanaladuras: desplazamiento radial en el fuste
  const pos = g.attributes.position;
  for (let i = 0; i < pos.count; i++) {
    const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
    if (y > -1.78 && y < 1.66) {
      const a = Math.atan2(z, x), f = 1 - 0.035 * Math.max(0, Math.cos(a * 16));
      pos.setX(i, x * f); pos.setZ(i, z * f);
    }
  }
  g.computeVertexNormals();
  return g;
}
const colGeo = columnGeometry();
const columns = [-2.5, 0, 2.5].map((x) => { const m = new THREE.Mesh(colGeo, marbleMat); m.position.x = x; scene.add(m); return m; });
const lintel = new THREE.Mesh(new THREE.BoxGeometry(6.8, 0.28, 1.5), marbleMat); scene.add(lintel);

// ---------- 3 · Balanza ----------
const scales = new THREE.Group(); scene.add(scales);
const post = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.09, 3.4, 24), goldMat); post.position.y = -0.4;
const foot = new THREE.Mesh(new THREE.CylinderGeometry(0.75, 0.9, 0.18, 48), goldMat); foot.position.y = -2.1;
const knob = new THREE.Mesh(new THREE.SphereGeometry(0.16, 32, 16), goldMat); knob.position.y = 1.45;
const beam = new THREE.Group(); beam.position.y = 1.3;
const bar = new THREE.Mesh(new THREE.CylinderGeometry(0.045, 0.045, 4.2, 16), goldMat); bar.rotation.z = Math.PI / 2;
beam.add(bar);
const pans = [-1, 1].map((s) => {
  const hang = new THREE.Group(); hang.position.x = 2.05 * s; beam.add(hang);
  const bowlPts = []; for (let i = 0; i <= 16; i++) { const a = (i / 16) * Math.PI / 2; bowlPts.push(new THREE.Vector2(Math.sin(a) * 0.72, -Math.cos(a) * 0.22)); }
  const bowl = new THREE.Mesh(new THREE.LatheGeometry(bowlPts, 48), goldMat); bowl.position.y = -1.55;
  hang.add(bowl);
  for (let k = 0; k < 3; k++) {
    const a = (k / 3) * Math.PI * 2, end = new THREE.Vector3(Math.cos(a) * 0.68, -1.4, Math.sin(a) * 0.68);
    const len = end.length();
    const chain = new THREE.Mesh(new THREE.CylinderGeometry(0.012, 0.012, len, 6), goldMat);
    chain.position.copy(end).multiplyScalar(0.5);
    chain.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), end.clone().normalize());
    hang.add(chain);
  }
  return hang;
});
scales.add(post, foot, knob, beam);

// ---------- 4 · Portal (anillo) ----------
const ring = new THREE.Mesh(new THREE.TorusGeometry(2.7, 0.055, 24, 160), goldMat); ring.position.set(0, 0.3, 0); scene.add(ring);
const ring2 = new THREE.Mesh(new THREE.TorusGeometry(3.05, 0.012, 8, 160),
  new THREE.MeshBasicMaterial({ color: GOLD_LIGHT, transparent: true })); ring2.position.copy(ring.position); scene.add(ring2);

// ---------- Nube de partículas que se transforma ----------
const N = 7000;
const R = rng(7);
const shapes = {};
function buildShape(fn) { const a = new Float32Array(N * 3); for (let i = 0; i < N; i++) { const v = fn(i); a[i * 3] = v[0]; a[i * 3 + 1] = v[1]; a[i * 3 + 2] = v[2]; } return a; }
const sampleSeg = (a, b, k) => [lerp(a[0], b[0], k), lerp(a[1], b[1], k), lerp(a[2], b[2], k)];
const jitter = (v, s) => [v[0] + (R() - 0.5) * s, v[1] + (R() - 0.5) * s, v[2] + (R() - 0.5) * s];

shapes.dust = buildShape(() => { const r = 2.5 + Math.pow(R(), 0.6) * 12, th = R() * Math.PI * 2, ph = Math.acos(2 * R() - 1);
  return [r * Math.sin(ph) * Math.cos(th), r * Math.cos(ph) * 0.6, r * Math.sin(ph) * Math.sin(th)]; });

{ const s = 1.7, V = [[s, 0, 0], [-s, 0, 0], [0, s, 0], [0, -s, 0], [0, 0, s], [0, 0, -s]];
  const edges = []; for (let i = 0; i < 6; i++) for (let j = i + 1; j < 6; j++) { const d = V[i].map((x, k) => x - V[j][k]); if (Math.hypot(...d) < s * 1.5) edges.push([V[i], V[j]]); }
  shapes.octa = buildShape((i) => {
    if (i % 10 < 7) { const e = edges[i % edges.length]; return jitter(sampleSeg(e[0], e[1], R()), 0.04); }
    const r = 2.1 + R() * 2.2, a = R() * Math.PI * 2; return [Math.cos(a) * r, (R() - 0.5) * 0.25, Math.sin(a) * r]; // anillo de polvo
  }); }

shapes.temple = buildShape((i) => {
  const k = i % 10;
  if (k < 6) { // fustes (contornos brillantes)
    const x = [-2.5, 0, 2.5][i % 3], a = R() * Math.PI * 2, rr = 0.5 + R() * 0.04;
    return [x + Math.cos(a) * rr, -2.2 + R() * 4.3, Math.sin(a) * rr];
  }
  if (k < 9) { // frontón triangular
    const P = [[-3.6, 2.4, 0.8], [0, 3.55, 0.8], [3.6, 2.4, 0.8]], e = R() < 0.36 ? [P[0], P[2]] : R() < 0.5 ? [P[0], P[1]] : [P[1], P[2]];
    return jitter(sampleSeg(e[0], e[1], R()), 0.05);
  }
  return [(R() - 0.5) * 16, -2.2 + R() * 0.05, (R() - 0.5) * 10]; // polvo en el suelo
});

shapes.halo = buildShape((i) => { const a = R() * Math.PI * 2, band = i % 3, r = [3.3, 3.55, 4.4][band] + (R() - 0.5) * (band === 2 ? 1.2 : 0.06);
  return [Math.cos(a) * r, -0.3 + (R() - 0.5) * (band === 2 ? 0.6 : 0.05) + band * 0.05, Math.sin(a) * r]; });

shapes.portal = buildShape((i) => { const a = R() * Math.PI * 2, tunnel = i % 4 === 0;
  if (tunnel) { const z = -R() * 9, r = 2.4 + R() * 1.2; return [Math.cos(a) * r, 0.3 + Math.sin(a) * r, z]; }
  const r = 2.9 + (R() - 0.5) * 0.35; return [Math.cos(a) * r, 0.3 + Math.sin(a) * r, (R() - 0.5) * 0.3]; });

{ const cz = -8, cy = 0.85;
  const diamond = (s) => [[0, cy + s, cz], [s, cy, cz], [0, cy - s, cz], [-s, cy, cz]];
  const D1 = diamond(0.78), D2 = diamond(0.6);
  shapes.logo = buildShape((i) => {
    const k = i % 10;
    if (k < 8) { const D = k < 5 ? D1 : D2, e = (i >> 2) % 4; return jitter(sampleSeg(D[e], D[(e + 1) % 4], R()), k < 5 ? 0.012 : 0.02); }
    const a = R() * Math.PI * 2, r = 1.4 + Math.pow(R(), 2) * 5; return [Math.cos(a) * r, cy + Math.sin(a) * r * 0.62, cz - 1 - R() * 3];
  }); }

// datos por partícula
const delay = new Float32Array(N), wob = new Float32Array(N * 3);
for (let i = 0; i < N; i++) {
  delay[i] = R() * 0.38;
  const th = R() * Math.PI * 2, ph = Math.acos(2 * R() - 1), m = 0.6 + R() * 1.6;
  wob[i * 3] = Math.sin(ph) * Math.cos(th) * m; wob[i * 3 + 1] = Math.cos(ph) * m; wob[i * 3 + 2] = Math.sin(ph) * Math.sin(th) * m;
}
const pGeo = new THREE.BufferGeometry();
const pPos = new Float32Array(N * 3), pCol = new Float32Array(N * 3);
const palette = [new THREE.Color(GOLD), new THREE.Color(GOLD_LIGHT), new THREE.Color(0xfff1d0), new THREE.Color(0x9fb6d9)];
for (let i = 0; i < N; i++) { const r = R(), c = palette[r < 0.45 ? 0 : r < 0.8 ? 1 : r < 0.94 ? 2 : 3]; c.toArray(pCol, i * 3); }
pGeo.setAttribute('position', new THREE.BufferAttribute(pPos, 3));
pGeo.setAttribute('color', new THREE.BufferAttribute(pCol, 3));
const sprite = (() => { const c = document.createElement('canvas'); c.width = c.height = 64; const g = c.getContext('2d');
  const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32); gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.25, 'rgba(255,255,255,.75)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
  g.fillStyle = gr; g.fillRect(0, 0, 64, 64); return new THREE.CanvasTexture(c); })();
const pMat = new THREE.PointsMaterial({ size: 0.055, map: sprite, vertexColors: true, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending });
const points = new THREE.Points(pGeo, pMat); points.frustumCulled = false; scene.add(points);

// Transformaciones dependientes del tiempo para cada forma
const M = { dust: new THREE.Matrix4(), octa: new THREE.Matrix4(), temple: new THREE.Matrix4(), halo: new THREE.Matrix4(), portal: new THREE.Matrix4(), logo: new THREE.Matrix4() };
const octaAngle = (t) => t * 0.55 + 0.4;
function shapeMatrices(t) {
  M.dust.makeRotationY(t * 0.05);
  M.octa.compose(new THREE.Vector3(0, 0.3, 0), new THREE.Quaternion().setFromEuler(new THREE.Euler(0, octaAngle(t), 0)), new THREE.Vector3(1, 1, 1));
  M.temple.identity();
  M.halo.makeRotationY(t * 0.45);
  M.portal.compose(new THREE.Vector3(0, 0.3, 0), new THREE.Quaternion().setFromEuler(new THREE.Euler(0, 0, -t * 0.6)), new THREE.Vector3(1, 1, 1)).multiply(new THREE.Matrix4().makeTranslation(0, -0.3, 0));
  M.logo.makeTranslation(0, Math.sin(t * 1.3) * 0.02, 0);
}
// [forma, inicio, fin]
const morphs = [['dust', 'octa', 0.35, 2.5], ['octa', 'temple', 2.85, 4.9], ['temple', 'halo', 6.3, 7.9], ['halo', 'portal', 9.6, 10.9], ['portal', 'logo', 11.6, 13.3]];
const va = new THREE.Vector3(), vb = new THREE.Vector3();
function updateParticles(t) {
  shapeMatrices(t);
  let A = 'dust', B = 'dust', u = 0, amp = 1.2;
  for (const [a, b, t0, t1] of morphs) { if (t >= t0) { A = a; B = b; u = range(t, t0, t1); } }
  const a = shapes[A], b = shapes[B], ma = M[A], mb = M[B];
  for (let i = 0; i < N; i++) {
    const p = E.inOut(clamp((u - delay[i]) / 0.62));
    va.fromArray(a, i * 3).applyMatrix4(ma);
    vb.fromArray(b, i * 3).applyMatrix4(mb);
    const s = Math.sin(Math.PI * p) * amp, j = i * 3;
    const breathe = 0.03 * Math.sin(t * 2 + i);
    pPos[j] = lerp(va.x, vb.x, p) + wob[j] * s + breathe;
    pPos[j + 1] = lerp(va.y, vb.y, p) + wob[j + 1] * s + breathe;
    pPos[j + 2] = lerp(va.z, vb.z, p) + wob[j + 2] * s;
  }
  pGeo.attributes.position.needsUpdate = true;
  pMat.opacity = 0.95 * range(t, 0, 0.7);
  pMat.size = 0.05 + 0.02 * range(t, 11, 12.5) - 0.022 * range(t, 12.6, 13.6);
}

// ---------- Cámara: spline de Hermite con tangentes suaves ----------
const camKeys = [
  // t,    posición              objetivo            fov
  [0.0, [0.8, 0.1, 12.5], [0, 0.3, 0], 34],
  [2.6, [-1.3, 0.7, 6.3], [0, 0.3, 0], 38],
  [3.8, [-4.4, -0.9, 7.2], [0, 0.5, 0], 40],
  [5.3, [1.8, -1.6, 8.6], [0, 0.9, 0], 38],
  [6.7, [5.2, 0.9, 7.4], [0, 0.6, 0], 38],
  [8.3, [1.6, 3.4, 6.6], [0, 0.2, 0], 40],
  [9.7, [-1.0, 1.4, 7.0], [0, 0.4, 0], 40],
  [10.8, [0, 0.35, 4.3], [0, 0.3, -3], 46],
  [11.8, [0, 0.3, -0.9], [0, 0.4, -8], 50],
  [13.2, [0, 0.3, -1.9], [0, 0.55, -8], 36],
  [15.0, [0, 0.3, -2.6], [0, 0.55, -8], 34],
];
function hermite(keys, idx, t) {
  let k = 0; while (k < keys.length - 2 && t > keys[k + 1][0]) k++;
  const k0 = keys[Math.max(0, k - 1)], k1 = keys[k], k2 = keys[k + 1], k3 = keys[Math.min(keys.length - 1, k + 2)];
  const dt = k2[0] - k1[0], s = clamp((t - k1[0]) / dt);
  const val = (key) => key[idx];
  const out = [];
  const dim = Array.isArray(k1[idx]) ? k1[idx].length : 1;
  for (let d = 0; d < dim; d++) {
    const g = (key) => (dim === 1 ? val(key) : val(key)[d]);
    // tangentes (Catmull-Rom no uniforme); cero en los extremos
    const m1 = k === 0 ? 0 : ((g(k2) - g(k0)) / (k2[0] - k0[0])) * dt;
    const m2 = k + 1 === keys.length - 1 ? 0 : ((g(k3) - g(k1)) / (k3[0] - k1[0])) * dt;
    const s2 = s * s, s3 = s2 * s;
    out.push((2 * s3 - 3 * s2 + 1) * g(k1) + (s3 - 2 * s2 + s) * m1 + (-2 * s3 + 3 * s2) * g(k2) + (s3 - s2) * m2);
  }
  return dim === 1 ? out[0] : out;
}
function updateCamera(t) {
  const p = hermite(camKeys, 1, t), g = hermite(camKeys, 2, t);
  // micro-movimiento "a mano"
  const hx = Math.sin(t * 1.7) * 0.025 + Math.sin(t * 3.1) * 0.012, hy = Math.cos(t * 1.3) * 0.02;
  camera.position.set(p[0] + hx, p[1] + hy, p[2]);
  camera.lookAt(g[0], g[1], g[2]);
  camera.rotateZ(Math.sin(t * 0.6) * 0.012 + (t > 10.4 && t < 12.2 ? Math.sin(range(t, 10.4, 12.2) * Math.PI) * 0.12 : 0));
  camera.fov = hermite(camKeys, 3, t);
  camera.updateProjectionMatrix();
}

// ---------- Objetos 3D a lo largo del tiempo ----------
function updateObjects(t) {
  // 1 · rombo
  const oIn = E.back(range(t, 0.9, 2.5)), oOut = E.in(range(t, 2.75, 3.3));
  const os = Math.max(0.0001, oIn * (1 - oOut));
  octa.visible = os > 0.001; octa.scale.setScalar(os);
  octa.rotation.set(Math.sin(t * 0.8) * 0.12, octaAngle(t) + oOut * 3, 0);
  octaEdges.material.opacity = 0.9;

  // 2 · columnas (suben escalonadas y se hunden)
  columns.forEach((c, i) => {
    const up = E.out5(range(t, 3.25 + i * 0.22, 4.6 + i * 0.22)), down = E.inOut(range(t, 6.15 + i * 0.12, 7.2 + i * 0.12));
    c.position.y = lerp(-4.6, 0, up) - 4.6 * down; c.visible = up > 0 && down < 1;
    c.rotation.y = (1 - up) * 1.2;
  });
  const lu = E.out5(range(t, 4.2, 5.3)), ld = E.inOut(range(t, 6.0, 6.8));
  lintel.position.set(0, lerp(6, 2.24, lu) + 5 * ld, 0); lintel.visible = lu > 0 && ld < 1;

  // 3 · balanza: sube, oscila y se equilibra
  const sUp = E.out5(range(t, 6.7, 7.9)), sOut = E.inOut(range(t, 9.75, 10.55));
  scales.visible = sUp > 0 && sOut < 1;
  scales.position.y = lerp(-5, 0, sUp) - 5 * sOut;
  scales.rotation.y = lerp(-0.9, 0, sUp) + t * 0.08;
  const lt = Math.max(0, t - 7.3);
  const tilt = (t < 7.3 ? 0.32 : 0.32 * Math.exp(-lt * 1.35) * Math.cos(lt * 4.2));
  beam.rotation.z = tilt; pans.forEach((p) => (p.rotation.z = -tilt));

  // 4 · portal
  const rIn = E.out5(range(t, 9.5, 10.7)), rOut = range(t, 12.0, 12.8);
  ring.visible = rIn > 0 && rOut < 1; ring2.visible = ring.visible;
  ring.scale.setScalar(Math.max(0.0001, rIn)); ring2.scale.setScalar(Math.max(0.0001, lerp(0.4, 1, rIn)));
  ring.rotation.set(0, 0, t * 0.4); ring2.material.opacity = 0.7 * rIn * (1 - rOut);

  // luces
  glow.position.set(Math.sin(t * 0.7) * 2, 1.2, t < 11.5 ? 2.2 : -6.5);
  glow.intensity = 28 + 10 * Math.sin(t * 2.2);
  key.target.position.set(0, 0, t < 11.5 ? 0 : -8);
  floor.visible = t < 11.4;
  bloom.strength = 0.7 + 0.35 * Math.sin(range(t, 10.4, 12.4) * Math.PI) + 0.25 * E.out(range(t, 12.8, 14));
  scene.fog.density = lerp(0.045, 0.02, range(t, 11, 13));
}

// =============================================================
//  Tipografía cinética
// =============================================================
const $ = (id) => document.getElementById(id);
function split(el, text, cls = 'ch') { el.textContent = ''; return [...text].map((c) => { const s = document.createElement('span'); s.className = cls; s.textContent = c; el.appendChild(s); return s; }); }
function words(el, text) { el.textContent = ''; return text.split(' ').map((w) => { const s = document.createElement('span'); s.className = 'w'; s.textContent = w; el.appendChild(s); return s; }); }
const style = (el, o, tf, blur = 0) => { el.style.opacity = o.toFixed(3); el.style.transform = tf; el.style.filter = blur > 0.05 ? `blur(${blur.toFixed(2)}px)` : 'none'; };

const t1c = split($('t1'), 'CADA CASO');
const t2c = split($('t2b'), 'historia.');
const t3list = ['JUSTICIA', 'CLARIDAD', 'COMPROMISO'].map((w) => { const d = document.createElement('div'); d.className = 't3word'; $('t3words').appendChild(d); return split(d, w); });
const t4a = words($('t4a'), 'Comprometidos con tus derechos,');
const t4b = words($('t4b'), 'EN CADA PASO DEL CAMINO');
const t5c = split($('t5name'), 'SANDOVAL LEGAL');

function updateType(t) {
  // 1 · CADA CASO — letras que suben desenfocadas y el tracking se comprime
  $('t1').style.display = t > 0.3 && t < 3.3 ? '' : 'none';
  $('t1').style.letterSpacing = `${lerp(0.75, 0.3, E.out(range(t, 0.5, 3.1)))}em`;
  t1c.forEach((s, i) => {
    const a = E.out5(range(t, 0.6 + i * 0.06, 1.5 + i * 0.06)), b = E.in(range(t, 2.55 + i * 0.03, 3.05 + i * 0.03));
    style(s, a * (1 - b), `translate3d(0,${(1 - a) * 90 - b * 120}px,0) rotateX(${(1 - a) * -70}deg)`, (1 - a) * 14 + b * 18);
  });

  // 2 · TIENE UNA / historia.
  $('t2').style.display = t > 3.4 && t < 6.6 ? '' : 'none';
  { const a = E.out5(range(t, 3.6, 4.3)), b = E.inOut(range(t, 5.9, 6.35));
    style($('t2a'), 1, `translateY(${(1 - a) * 110 + b * 110}%)`);
    $('t2a').style.letterSpacing = `${lerp(1.1, 0.62, E.out(range(t, 3.6, 5.8)))}em`; }
  $('t2b').style.transform = `translateX(${lerp(-20, 30, range(t, 3.8, 6.4))}px) scale(${lerp(1, 1.05, range(t, 3.8, 6.4))})`;
  t2c.forEach((s, i) => {
    const a = E.out5(range(t, 3.9 + i * 0.065, 4.8 + i * 0.065)), b = E.in(range(t, 5.95 + i * 0.025, 6.4 + i * 0.025));
    style(s, a * (1 - b), `translate3d(${b * 60}px,${(1 - a) * 60}px,${(1 - a) * -300}px) rotateY(${(1 - a) * 80}deg)`, (1 - a) * 10 + b * 16);
  });

  // 3 · palabras con escala y desenfoque desde el centro
  $('t3').style.display = t > 6.8 && t < 10.3 ? '' : 'none';
  const slots = [[7.0, 8.0], [8.05, 9.05], [9.1, 10.15]];
  let cur = 0;
  t3list.forEach((chars, w) => {
    const [t0, t1] = slots[w]; if (t >= t0) cur = w;
    const mid = (chars.length - 1) / 2;
    chars.forEach((s, i) => {
      const d = Math.abs(i - mid) * 0.035;
      const a = E.expoOut(range(t, t0 + d, t0 + 0.55 + d)), b = E.in(range(t, t1 - 0.3 + d * 0.5, t1 + d * 0.5));
      style(s, a * (1 - b), `translateY(${-b * 40}px) scale(${lerp(1.7, 1, a) * lerp(1, 0.85, b)})`, (1 - a) * 16 + b * 12);
    });
  });
  $('t3count').textContent = `0${cur + 1} — 03`;
  $('t3count').style.opacity = (range(t, 7.0, 7.4) * (1 - range(t, 9.9, 10.2))).toFixed(3);
  { const r = E.inOut(range(t, 7.0, 7.7)), f = 1 - range(t, 9.9, 10.2);
    const pulse = slots.reduce((m, [t0]) => Math.max(m, 1 - range(t, t0, t0 + 0.6)), 0) * (t > 7.7 ? 1 : 0);
    $('t3rule').style.transform = `scaleX(${(r * (0.75 + 0.25 * (1 - pulse))).toFixed(3)})`; $('t3rule').style.opacity = f.toFixed(3); }

  // 4 · frase de cierre durante el vuelo a través del portal
  $('t4').style.display = t > 10.4 && t < 12.6 ? '' : 'none';
  const exit = range(t, 11.85, 12.45);
  $('t4').style.transform = `scale(${1 + E.in(exit) * 0.55})`;
  $('t4').style.opacity = (1 - E.in(exit)).toFixed(3);
  $('t4').style.filter = exit > 0.02 ? `blur(${(exit * 10).toFixed(2)}px)` : 'none';
  t4a.forEach((s, i) => { const a = E.out5(range(t, 10.55 + i * 0.12, 11.3 + i * 0.12));
    style(s, a, `translate3d(0,0,${(1 - a) * -700}px)`, (1 - a) * 12); });
  t4b.forEach((s, i) => { const a = E.out5(range(t, 11.0 + i * 0.07, 11.6 + i * 0.07));
    style(s, a, `translateY(${(1 - a) * 30}px)`, (1 - a) * 8); });

  // 5 · logotipo
  const center = new THREE.Vector3(0, 0.85, -8).project(camera);
  const sx = (center.x * 0.5 + 0.5) * W, sy = (-center.y * 0.5 + 0.5) * H;
  const dist = camera.position.distanceTo(new THREE.Vector3(0, 0.85, -8));
  const fScale = (1 / Math.tan(THREE.MathUtils.degToRad(camera.fov / 2))) / dist; // tamaño en pantalla proporcional
  { const a = E.out5(range(t, 12.9, 13.8));
    $('logoS').style.display = t > 12.8 ? '' : 'none';
    style($('logoS'), a, `translate(${sx.toFixed(1)}px,${sy.toFixed(1)}px) scale(${(fScale * 4.3 * lerp(0.7, 1, a)).toFixed(4)})`, (1 - a) * 12); }
  $('t5').style.display = t > 12.9 ? '' : 'none';
  $('t5').style.transform = `scale(${lerp(1.0, 1.035, range(t, 13, 15))})`;
  const mid = (t5c.length - 1) / 2;
  $('t5name').style.letterSpacing = `${lerp(0.9, 0.14, E.out5(range(t, 13.05, 14.4)))}em`;
  t5c.forEach((s, i) => { const a = E.out(range(t, 13.1 + Math.abs(i - mid) * 0.045, 13.9 + Math.abs(i - mid) * 0.045));
    style(s, a, `translateY(${(1 - a) * 16}px)`, (1 - a) * 10); });
  { const a = E.inOut(range(t, 13.7, 14.45));
    $('t5l').style.transform = `scaleX(${a.toFixed(3)})`; $('t5r').style.transform = `scaleX(${a.toFixed(3)})`;
    const b = E.out(range(t, 13.9, 14.6)); style($('t5tag'), b, `translateY(${(1 - b) * 10}px)`, (1 - b) * 6); }
}

// =============================================================
//  Transiciones de formas 2D (SVG)
// =============================================================
const diamondPath = (cx, cy, r) => `M${cx},${cy - r} L${cx + r},${cy} L${cx},${cy + r} L${cx - r},${cy} Z`;
const pillsG = $('pills');
const PILLS = 7;
const pills = Array.from({ length: PILLS }, () => { const r = document.createElementNS('http://www.w3.org/2000/svg', 'rect'); pillsG.appendChild(r); return r; });
const shapePts = (fn, n = 96) => Array.from({ length: n }, (_, i) => fn(i / n));
function updateShapes(t) {
  // 1→2 · rombo que cubre y se abre
  const cover = E.inOut5(range(t, 2.8, 3.35)), open = E.inOut5(range(t, 3.3, 3.95));
  const big = 1500;
  $('diamondFill').setAttribute('d', cover > 0 && open < 1 ? diamondPath(960, 540, cover * big) : '');
  $('hole').setAttribute('d', open > 0 ? diamondPath(960, 540, open * big) : '');
  const lineR = t < 3.35 ? cover * big + 18 : open * big - 18;
  const lv = t > 2.8 && t < 3.95;
  $('diamondLine').setAttribute('d', lv ? diamondPath(960, 540, Math.max(0, lineR)) : '');
  $('diamondLine2').setAttribute('d', lv ? diamondPath(960, 540, Math.max(0, lineR * 0.82)) : '');

  // 2→3 · barras redondeadas que barren verticalmente
  const pw = 1920 / PILLS;
  pills.forEach((r, i) => {
    const d = Math.abs(i - (PILLS - 1) / 2) * 0.05;
    const inn = E.inOut5(range(t, 6.15 + d, 6.6 + d)), out = E.inOut5(range(t, 6.6 + d, 7.1 + d));
    const vis = inn > 0 && out < 1;
    const top = lerp(1080 + 40, -40, inn), bottom = lerp(1080 + 40, -40, out) + 1160;
    r.setAttribute('x', (i * pw - 1).toFixed(1)); r.setAttribute('width', (pw + 2).toFixed(1));
    r.setAttribute('y', vis ? top.toFixed(1) : -9999); r.setAttribute('height', vis ? Math.max(0, Math.min(bottom, 1120) - top).toFixed(1) : 0);
    r.setAttribute('rx', (pw / 2).toFixed(1));
    r.setAttribute('fill', i % 2 ? '#0b1f3a' : '#071629');
    r.setAttribute('stroke', '#c9a45c'); r.setAttribute('stroke-width', '1.5');
  });

  // 4→5 · círculo que se transforma en rombo
  const m = $('morph');
  if (t > 11.55 && t < 13.6) {
    const c = new THREE.Vector3(0, 0.85, -8).project(camera);
    const cx = (c.x * 0.5 + 0.5) * W, cy = (-c.y * 0.5 + 0.5) * H;
    const grow = E.out5(range(t, 11.55, 12.2)), mk = E.inOut(range(t, 12.2, 12.95)), fade = range(t, 13.0, 13.6);
    const rC = lerp(700, 330, grow), rD = lerp(330, 205, mk);
    const pts = shapePts((u) => {
      const a = u * Math.PI * 2 - Math.PI / 2;
      const ci = [Math.cos(a), Math.sin(a)];
      // rombo en coordenadas polares: |x|+|y| = 1
      const k = 1 / (Math.abs(Math.cos(a)) + Math.abs(Math.sin(a)));
      const di = [Math.cos(a) * k, Math.sin(a) * k];
      const r = lerp(rC, rD, mk);
      return [cx + lerp(ci[0], di[0], mk) * r, cy + lerp(ci[1], di[1], mk) * r];
    });
    m.setAttribute('d', 'M' + pts.map((p) => p.map((v) => v.toFixed(1)).join(',')).join(' L') + ' Z');
    m.setAttribute('opacity', (grow * (1 - fade)).toFixed(3));
    m.setAttribute('transform', `rotate(${(1 - mk) * -45} ${cx.toFixed(1)} ${cy.toFixed(1)})`);
  } else m.setAttribute('d', '');
}

// ---------- grano, viñeta, bandas ----------
const grain = $('grain').getContext('2d');
const gImg = grain.createImageData(480, 270);
function updateFilm(t) {
  const r = rng(Math.floor(t * 30) + 11), d = gImg.data;
  for (let i = 0; i < d.length; i += 4) { const v = (r() * 255) | 0; d[i] = d[i + 1] = d[i + 2] = v; d[i + 3] = 255; }
  grain.putImageData(gImg, 0, 0);
  const b = E.inOut(range(t, 0, 1.2));
  $('barTop').style.transform = `scaleY(${b})`; $('barBot').style.transform = `scaleY(${b})`;
  $('fade').style.opacity = (1 - E.out(range(t, 0, 0.8)) + E.in(range(t, 14.55, 15))).toFixed(3);
}

// =============================================================
//  API pública y vista previa
// =============================================================
function renderAt(t) {
  t = clamp(t, 0, DURATION);
  updateCamera(t);
  updateObjects(t);
  updateParticles(t);
  composer.render();
  updateType(t);
  updateShapes(t);
  updateFilm(t);
}
window.renderAt = renderAt;
window.DURATION = DURATION;

const capture = new URLSearchParams(location.search).has('capture');
const stage = $('stage');
function fit() { if (capture) return; const s = Math.min(innerWidth / W, innerHeight / H); stage.style.transform = `translate(${(innerWidth - W * s) / 2}px,${(innerHeight - H * s) / 2}px) scale(${s})`; }
addEventListener('resize', fit); fit();

document.fonts.ready.then(() => {
  window.READY = true;
  if (capture) { document.body.classList.add('capture'); renderAt(0); return; }
  let playing = true, start = performance.now(), cur = 0;
  const btn = $('play'), scrub = $('scrub'), clock = $('clock');
  btn.onclick = () => { playing = !playing; btn.textContent = playing ? '❚❚' : '▶'; start = performance.now() - cur * 1000; };
  scrub.oninput = () => { cur = +scrub.value; start = performance.now() - cur * 1000; renderAt(cur); clock.textContent = `${cur.toFixed(2)} s`; };
  (function loop() {
    if (playing) { cur = ((performance.now() - start) / 1000) % DURATION; renderAt(cur); scrub.value = cur; clock.textContent = `${cur.toFixed(2)} s`; }
    requestAnimationFrame(loop);
  })();
});
