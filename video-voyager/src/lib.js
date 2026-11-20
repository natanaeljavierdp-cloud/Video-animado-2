// Utilidades compartidas: materiales toon, contorno (casco invertido), easing,
// interpolación de cámara, partículas de energía, anillos de radio, etiquetas.
import * as THREE from 'three';
import { mergeVertices } from 'three/addons/utils/BufferGeometryUtils.js';

export const W = 1080, H = 1920;

// ------------------------------------------------------------------ easing
export const clamp = (x, a = 0, b = 1) => (x < a ? a : x > b ? b : x);
export const lin = (t, a, b) => (b > a ? clamp((t - a) / (b - a)) : t >= a ? 1 : 0);
export const sm = (x) => { x = clamp(x); return x * x * (3 - 2 * x); };
export const eio = (x) => { x = clamp(x); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
export const eout = (x) => { x = clamp(x); return 1 - Math.pow(1 - x, 3); };
export const ein = (x) => { x = clamp(x); return x * x * x; };
export const eback = (x) => { x = clamp(x); const c1 = 1.9, c3 = c1 + 1; return 1 + c3 * Math.pow(x - 1, 3) + c1 * Math.pow(x - 1, 2); };
export const P = (t, a, d = 0.5, f = eout) => f(lin(t, a, a + d));
export const lerp = (a, b, u) => a + (b - a) * u;
// pop in at a, pop out at b
export const pop = (t, a, b = 1e9, din = 0.45, dout = 0.3) => eback(lin(t, a, a + din)) * (1 - eio(lin(t, b, b + dout)));
export const V = (x, y, z) => new THREE.Vector3(x, y, z);

// ------------------------------------------------------------------ colours
export const hdr = (hex, k) => new THREE.Color(hex).multiplyScalar(k);
export const GOLD = 0xFFC93C;

let gradMap = null;
export function toonGrad() {
  if (!gradMap) {
    const d = new Uint8Array([120, 120, 120, 255, 188, 188, 188, 255, 236, 236, 236, 255, 255, 255, 255, 255]);
    gradMap = new THREE.DataTexture(d, 4, 1, THREE.RGBAFormat);
    gradMap.minFilter = gradMap.magFilter = THREE.NearestFilter;
    gradMap.needsUpdate = true;
  }
  return gradMap;
}
export function toon(color, o = {}) {
  return new THREE.MeshToonMaterial({ color, gradientMap: toonGrad(), ...o });
}
export function glowMat(hex = GOLD, k = 5) {
  return new THREE.MeshBasicMaterial({ color: hdr(hex, k), toneMapped: false });
}

// ------------------------------------------------------------------ outlines
const OUT_VS = `
uniform float thick; uniform vec2 res;
void main(){
  vec4 clip = projectionMatrix * modelViewMatrix * vec4(position, 1.0);
  vec3 vn = normalize(normalMatrix * normal);
  vec4 cn = projectionMatrix * vec4(vn, 0.0);
  vec2 d = cn.xy; float l = length(d); if (l > 1e-6) d /= l;
  clip.xy += d * thick * 2.0 / res * clip.w;
  gl_Position = clip;
}`;
const OUT_FS = `uniform vec3 col; uniform float op; void main(){ gl_FragColor = vec4(col, op); }`;
const ogCache = new WeakMap();
function outlineGeo(g) {
  if (ogCache.has(g)) return ogCache.get(g);
  const g2 = new THREE.BufferGeometry();
  g2.setAttribute('position', g.attributes.position.clone());
  if (g.index) g2.setIndex(g.index.clone());
  const m = mergeVertices(g2, 1e-4);
  m.computeVertexNormals();
  m.computeBoundingSphere();
  ogCache.set(g, m);
  return m;
}
const _v = new THREE.Vector3(), _s = new THREE.Vector3();
export const OUTLINE = { base: 2.6, color: new THREE.Color(0x15161c) };
export function addOutline(mesh, k = 1) {
  const geo = outlineGeo(mesh.geometry);
  const mat = new THREE.ShaderMaterial({
    uniforms: { thick: { value: 2 }, res: { value: new THREE.Vector2(W, H) }, col: { value: OUTLINE.color }, op: { value: 1 } },
    vertexShader: OUT_VS, fragmentShader: OUT_FS, side: THREE.BackSide,
  });
  const o = new THREE.Mesh(geo, mat);
  o.userData.isOutline = true;
  o.castShadow = false; o.receiveShadow = false;
  o.onBeforeRender = (r, s, cam) => {
    // grosor constante en pantalla, que se desvanece en objetos diminutos
    o.getWorldPosition(_v); o.getWorldScale(_s);
    const rad = geo.boundingSphere.radius * Math.max(_s.x, _s.y, _s.z);
    const dist = Math.max(0.001, _v.distanceTo(cam.position));
    const px = rad / (dist * Math.tan(THREE.MathUtils.degToRad(cam.fov / 2))) * (H / 2);
    mat.uniforms.thick.value = OUTLINE.base * k * sm((px - 1.5) / 16);
    const pm = mesh.material;
    const op = pm.opacity !== undefined ? pm.opacity : 1;
    mat.uniforms.op.value = op;
    mat.transparent = op < 0.999;
    mat.depthWrite = op >= 0.999;
  };
  mesh.add(o);
  return o;
}
export function outlineAll(root, k = 1) {
  const list = [];
  root.traverse((m) => { if (m.isMesh && !m.userData.isOutline && m.userData.outline !== false) list.push(m); });
  list.forEach((m) => addOutline(m, m.userData.outlineK || k));
}
export function shadows(root, cast = true, recv = true) {
  root.traverse((m) => { if (m.isMesh && !m.userData.isOutline) { m.castShadow = cast; m.receiveShadow = recv; } });
}

// ------------------------------------------------------------------ geometry helpers
export function rod(a, b, r, mat, seg = 8) {
  const d = new THREE.Vector3().subVectors(b, a);
  const L = d.length();
  const m = new THREE.Mesh(new THREE.CylinderGeometry(r, r, L, seg), mat);
  m.position.copy(a).addScaledVector(d, 0.5);
  m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.normalize());
  return m;
}
// plato parabólico sólido (con grosor) para que el contorno funcione
export function dishGeo(R, f, th = 0.04, seg = 48) {
  const pts = [];
  const n = 16;
  for (let i = 0; i <= n; i++) { const r = Math.max(0.002, R * i / n); pts.push(new THREE.Vector2(r, r * r / (4 * f))); }
  const d = R * R / (4 * f);
  pts.push(new THREE.Vector2(R + th * 0.6, d));
  for (let i = n; i >= 0; i--) { const r = Math.max(0.002, R * i / n); pts.push(new THREE.Vector2(r, r * r / (4 * f) - th)); }
  pts.reverse();
  const g = new THREE.LatheGeometry(pts, seg);
  g.computeVertexNormals();
  return g;
}

// ------------------------------------------------------------------ camera
export function hermite(keys, t) {
  // keys: [[time, x, y, z], ...]  — Catmull-Rom no uniforme, extremos con velocidad 0
  const n = keys.length;
  if (t <= keys[0][0]) return V(keys[0][1], keys[0][2], keys[0][3]);
  if (t >= keys[n - 1][0]) return V(keys[n - 1][1], keys[n - 1][2], keys[n - 1][3]);
  let i = 0; while (i < n - 2 && t >= keys[i + 1][0]) i++;
  const k0 = keys[i], k1 = keys[i + 1];
  const h = k1[0] - k0[0], u = (t - k0[0]) / h;
  const tan = (j) => {
    if (j <= 0 || j >= n - 1) return [0, 0, 0];
    const a = keys[j - 1], b = keys[j + 1], dt = b[0] - a[0];
    return [(b[1] - a[1]) / dt, (b[2] - a[2]) / dt, (b[3] - a[3]) / dt];
  };
  const m0 = tan(i), m1 = tan(i + 1);
  const u2 = u * u, u3 = u2 * u;
  const h00 = 2 * u3 - 3 * u2 + 1, h10 = u3 - 2 * u2 + u, h01 = -2 * u3 + 3 * u2, h11 = u3 - u2;
  const o = [];
  for (let c = 1; c <= 3; c++) o.push(h00 * k0[c] + h10 * h * m0[c - 1] + h01 * k1[c] + h11 * h * m1[c - 1]);
  return V(o[0], o[1], o[2]);
}
export function K(t, v) { return [t, v.x, v.y, v.z]; }

// ------------------------------------------------------------------ energy dots (instanced)
export class Dots {
  constructor(scene, max = 900) {
    const g = new THREE.SphereGeometry(1, 12, 8);
    this.mat = new THREE.MeshBasicMaterial({ color: 0xffffff, toneMapped: false });
    this.mesh = new THREE.InstancedMesh(g, this.mat, max);
    this.mesh.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(max * 3), 3);
    this.mesh.frustumCulled = false;
    this.mesh.userData.outline = false;
    this.max = max; this.n = 0;
    this.m = new THREE.Matrix4(); this.q = new THREE.Quaternion(); this.c = new THREE.Color();
    scene.add(this.mesh);
    // halo suave aditivo
    const tex = radialTex();
    this.halo = new THREE.InstancedMesh(new THREE.PlaneGeometry(1, 1), new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false }), max);
    this.halo.instanceColor = new THREE.InstancedBufferAttribute(new Float32Array(max * 3), 3);
    this.halo.frustumCulled = false; this.halo.userData.outline = false;
    this.halo.visible = false; scene.add(this.halo);
  }
  clear() { this.n = 0; }
  add(p, r, color = GOLD, k = 6, a = 1, cam = null) {
    if (this.n >= this.max || r <= 0 || a <= 0) return;
    this.m.compose(p, this.q.identity(), _s.set(r, r, r));
    this.mesh.setMatrixAt(this.n, this.m);
    this.c.set(color).multiplyScalar(k * a);
    this.mesh.setColorAt(this.n, this.c);
    if (cam) this.q.copy(cam.quaternion);
    this.m.compose(p, this.q, _s.set(r * 7, r * 7, r * 7));
    this.halo.setMatrixAt(this.n, this.m);
    this.c.set(color).multiplyScalar(0.55 * a);
    this.halo.setColorAt(this.n, this.c);
    this.n++;
  }
  commit() {
    this.mesh.count = this.n; this.halo.count = this.n;
    this.mesh.instanceMatrix.needsUpdate = true; this.mesh.instanceColor.needsUpdate = true;
    this.halo.instanceMatrix.needsUpdate = true; this.halo.instanceColor.needsUpdate = true;
  }
  // puntitos que recorren una curva (CatmullRomCurve3 o similar con getPointAt)
  along(curve, t, o = {}) {
    const { speed = 1, spacing = 0.06, r = 0.04, reveal = 1, start = 0, color = GOLD, k = 6, a = 1, cam = null, fadeEnd = 0, alt = null } = o;
    const L = 1;
    const ph = t * speed;
    let kk = Math.ceil((0 - ph) / spacing);
    for (let guard = 0; guard < 400; guard++, kk++) {
      const s = ph + kk * spacing;
      if (s > reveal) break;
      if (s < start) continue;
      let aa = a;
      if (fadeEnd > 0) aa *= clamp((reveal - s) / fadeEnd);
      const c = alt && (kk & 1) ? alt : color;
      this.add(curve.getPointAt(clamp(s / L)), r, c, k, aa, cam);
    }
  }
}
let _rt = null;
export function radialTex() {
  if (_rt) return _rt;
  const c = document.createElement('canvas'); c.width = c.height = 128;
  const x = c.getContext('2d');
  const g = x.createRadialGradient(64, 64, 0, 64, 64, 64);
  g.addColorStop(0, 'rgba(255,255,255,1)'); g.addColorStop(0.25, 'rgba(255,255,255,0.45)'); g.addColorStop(1, 'rgba(255,255,255,0)');
  x.fillStyle = g; x.fillRect(0, 0, 128, 128);
  _rt = new THREE.CanvasTexture(c);
  return _rt;
}

// ------------------------------------------------------------------ radio rings
const RING_FS = `
uniform vec3 col; uniform float w; uniform float op; varying vec2 vUv;
void main(){
  float r = length(vUv * 2.0 - 1.0);
  float aa = 0.012 + w * 0.3;
  float a = smoothstep(1.0 - w - aa, 1.0 - w, r) * (1.0 - smoothstep(1.0 - aa, 1.0, r));
  float g = exp(-pow((r - (1.0 - w * 0.5)) / (w * 2.5 + 0.03), 2.0)) * 0.35;
  gl_FragColor = vec4(col * (a + g), (a + g) * op);
}`;
export class Rings {
  constructor(scene, max = 40) {
    this.pool = [];
    const geo = new THREE.PlaneGeometry(2, 2);
    for (let i = 0; i < max; i++) {
      const m = new THREE.Mesh(geo, new THREE.ShaderMaterial({
        uniforms: { col: { value: hdr(GOLD, 4) }, w: { value: 0.05 }, op: { value: 1 } },
        vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
        fragmentShader: RING_FS, transparent: true, depthWrite: false, side: THREE.DoubleSide, blending: THREE.AdditiveBlending, toneMapped: false,
      }));
      m.visible = false; m.userData.outline = false; m.frustumCulled = false;
      scene.add(m); this.pool.push(m);
    }
    this.n = 0;
  }
  clear() { this.n = 0; this.pool.forEach((m) => (m.visible = false)); }
  add(pos, dir, radius, width, op, k = 4) {
    if (this.n >= this.pool.length || op <= 0.001) return;
    const m = this.pool[this.n++];
    m.visible = true; m.position.copy(pos);
    m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), dir);
    m.scale.setScalar(radius);
    m.material.uniforms.w.value = width; m.material.uniforms.op.value = op;
    m.material.uniforms.col.value.set(GOLD).multiplyScalar(k);
  }
}

// ------------------------------------------------------------------ labels (pill sprites, tamaño fijo en pantalla)
export const FONT = '"Nunito"';
export function pillCanvas(text, o = {}) {
  const { size = 64, bg = '#ffffff', fg = '#1D2A44', border = '#C9D6E8' } = o;
  const c = document.createElement('canvas');
  const x = c.getContext('2d');
  x.font = `900 ${size}px ${FONT}`;
  const tw = x.measureText(text).width;
  const h = size * 1.6, w = tw + size * 1.2, pad = 14;
  c.width = Math.ceil(w + pad * 2); c.height = Math.ceil(h + pad * 2 + 8);
  const r = h / 2;
  const rr = (X, Y) => { x.beginPath(); x.moveTo(X + r, Y); x.arcTo(X + w, Y, X + w, Y + h, r); x.arcTo(X + w, Y + h, X, Y + h, r); x.arcTo(X, Y + h, X, Y, r); x.arcTo(X, Y, X + w, Y, r); x.closePath(); };
  rr(pad, pad + 8); x.fillStyle = 'rgba(0,0,0,0.22)'; x.fill();
  rr(pad, pad); x.fillStyle = bg; x.fill(); x.lineWidth = 6; x.strokeStyle = '#15161c'; x.stroke();
  x.font = `900 ${size}px ${FONT}`; x.fillStyle = fg; x.textAlign = 'center'; x.textBaseline = 'middle';
  x.fillText(text, pad + w / 2, pad + h / 2 + size * 0.04);
  return c;
}
export const LABELS = [];
export function label(scene, text, o = {}) {
  const c = pillCanvas(text, o);
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace;
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, sizeAttenuation: false, depthTest: false, depthWrite: false, transparent: true }));
  s.renderOrder = 10; s.userData.outline = false;
  s.userData.px = c.height; s.userData.aspect = c.width / c.height; s.userData.k = 1;
  s.visible = false;
  scene.add(s); LABELS.push(s);
  return s;
}
export function updateLabels(cam) {
  const f = 2 * Math.tan(THREE.MathUtils.degToRad(cam.fov / 2)) / H;
  for (const s of LABELS) {
    const h = s.userData.px * s.userData.k * f;
    s.scale.set(h * s.userData.aspect, h, 1);
  }
}
