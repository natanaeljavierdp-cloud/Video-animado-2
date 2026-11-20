// Modelos 3D (todos procedurales): Tierra, Luna, planetas, Sol, Voyager 1,
// reloj, bombillo, módem, monitor, mesa, antena DSN, nubes, árboles, texto 3D.
import * as THREE from 'three';
import { TextGeometry } from 'three/addons/geometries/TextGeometry.js';
import { toon, rod, dishGeo, outlineAll, shadows, hdr, GOLD, V, radialTex } from './lib.js';

const tex = (c) => { const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; return t; };
const canvas = (w, h) => { const c = document.createElement('canvas'); c.width = w; c.height = h; return c; };
function rng(seed) { let s = seed >>> 0; return () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296); }

// ------------------------------------------------------------------ Tierra
export function makeEarth(land) {
  const c = canvas(2048, 1024), x = c.getContext('2d');
  x.fillStyle = '#4A87C9'; x.fillRect(0, 0, 2048, 1024);
  // degradado suave de océano (más claro en ecuador)
  const g = x.createLinearGradient(0, 0, 0, 1024);
  g.addColorStop(0, 'rgba(30,60,120,0.25)'); g.addColorStop(0.5, 'rgba(120,190,240,0.18)'); g.addColorStop(1, 'rgba(30,60,120,0.25)');
  x.fillStyle = g; x.fillRect(0, 0, 2048, 1024);
  const P = (lon, lat) => [(lon + 180) / 360 * 2048, (90 - lat) / 180 * 1024];
  const path = (ring) => { x.beginPath(); ring.forEach(([lo, la], i) => { const [px, py] = P(lo, la); i ? x.lineTo(px, py) : x.moveTo(px, py); }); x.closePath(); };
  x.lineJoin = 'round';
  for (const ring of land) { path(ring); x.fillStyle = '#8CC65A'; x.fill(); }
  for (const ring of land) { path(ring); x.strokeStyle = '#4E8A3A'; x.lineWidth = 3; x.stroke(); }
  // zonas áridas sencillas (Sahara, Arabia, Australia central)
  x.save();
  for (const ring of land) { path(ring); } x.clip();
  x.fillStyle = 'rgba(214,190,120,0.75)';
  [[10, 23, 22, 9], [45, 23, 10, 6], [133, -25, 12, 7], [-112, 33, 6, 5]].forEach(([lo, la, rw, rh]) => {
    const [px, py] = P(lo, la); x.beginPath(); x.ellipse(px, py, rw / 360 * 2048, rh / 180 * 1024, 0, 0, Math.PI * 2); x.fill();
  });
  x.restore();
  // casquetes polares
  x.fillStyle = '#F4F7FA';
  x.fillRect(0, 0, 2048, 30); x.fillRect(0, 1024 - 70, 2048, 70);
  const earth = new THREE.Group();
  const body = new THREE.Mesh(new THREE.SphereGeometry(1, 72, 48), toon(0xffffff, { map: tex(c) }));
  earth.add(body);
  // nubes de caricatura
  const cc = canvas(1024, 512), cx = cc.getContext('2d'); const r = rng(11);
  cx.fillStyle = '#fff';
  for (let i = 0; i < 70; i++) {
    const px = r() * 1024, py = 70 + r() * 372, s = 8 + r() * 18;
    for (let k = 0; k < 5; k++) { cx.beginPath(); cx.ellipse(px + (k - 2) * s * 0.9, py + (k % 2 ? -s * 0.3 : s * 0.15), s * (1.0 + (k == 2) * 0.4), s * 0.75, 0, 0, Math.PI * 2); cx.fill(); }
  }
  const ct = new THREE.CanvasTexture(cc);
  const clouds = new THREE.Mesh(new THREE.SphereGeometry(1.022, 64, 40), toon(0xffffff, { alphaMap: ct, transparent: true, depthWrite: false }));
  clouds.userData.outline = false; clouds.castShadow = false;
  earth.add(clouds);
  // atmósfera (fresnel)
  const atm = new THREE.Mesh(new THREE.SphereGeometry(1.12, 48, 32), new THREE.ShaderMaterial({
    vertexShader: 'varying vec3 vN; varying vec3 vV; void main(){ vec4 mv = modelViewMatrix*vec4(position,1.0); vN = normalize(normalMatrix*normal); vV = normalize(-mv.xyz); gl_Position = projectionMatrix*mv; }',
    fragmentShader: 'uniform float op; varying vec3 vN; varying vec3 vV; void main(){ float f = pow(1.0 - abs(dot(vN, vV)), 2.2); gl_FragColor = vec4(vec3(0.45,0.75,1.0)*f*1.3, f*op); }',
    uniforms: { op: { value: 0.9 } }, side: THREE.BackSide, transparent: true, depthWrite: false, blending: THREE.AdditiveBlending,
  }));
  atm.userData.outline = false;
  earth.add(atm);
  outlineAll(body);
  body.castShadow = false; body.receiveShadow = true;
  earth.userData = { body, clouds, atm };
  return earth;
}
// posición sobre la esfera (radio 1) — lon/lat en grados, en el marco local de la Tierra
export function lonlat(lon, lat, r = 1) {
  const la = THREE.MathUtils.degToRad(lat), lo = THREE.MathUtils.degToRad(lon);
  // SphereGeometry: u=0 en -X ... x = -cos(phi)sin(theta); con nuestro mapeo lon=-180 en u=0
  return V(-Math.cos(lo + Math.PI) * Math.cos(la) * r, Math.sin(la) * r, Math.sin(lo + Math.PI) * Math.cos(la) * r);
}

// ------------------------------------------------------------------ planetas
function planetTex(kind) {
  const c = canvas(512, 256), x = c.getContext('2d'); const r = rng(kind.length * 7 + 3);
  if (kind === 'moon') {
    x.fillStyle = '#C3C3CB'; x.fillRect(0, 0, 512, 256);
    for (let i = 0; i < 60; i++) { const s = 4 + r() * 16; x.fillStyle = r() > 0.5 ? '#A6A6B2' : '#B3B3BE'; x.beginPath(); x.arc(r() * 512, 30 + r() * 196, s, 0, 7); x.fill(); }
    x.fillStyle = 'rgba(150,150,165,0.6)'; [[120, 90, 50], [300, 140, 40], [400, 80, 30]].forEach(([a, b, s]) => { x.beginPath(); x.ellipse(a, b, s, s * 0.7, 0, 0, 7); x.fill(); });
  } else if (kind === 'mars') {
    x.fillStyle = '#D9774D'; x.fillRect(0, 0, 512, 256);
    for (let i = 0; i < 25; i++) { x.fillStyle = 'rgba(150,70,45,0.45)'; x.beginPath(); x.ellipse(r() * 512, 40 + r() * 176, 15 + r() * 40, 8 + r() * 18, 0, 0, 7); x.fill(); }
    x.fillStyle = '#F4EDE6'; x.fillRect(0, 0, 512, 14); x.fillRect(0, 244, 512, 12);
  } else if (kind === 'jupiter') {
    const cols = ['#E7D3B0', '#C99B6D', '#EFE2C8', '#B9805A', '#E9D6B6', '#D3AA7E', '#F1E6D0', '#BF8A60'];
    let y = 0; let i = 0; while (y < 256) { const h = 14 + r() * 26; x.fillStyle = cols[i++ % cols.length]; x.fillRect(0, y, 512, h); y += h; }
    x.fillStyle = '#C8664A'; x.beginPath(); x.ellipse(340, 160, 34, 16, 0, 0, 7); x.fill();
  } else if (kind === 'saturn') {
    const cols = ['#EAD9A8', '#D9C089', '#F1E5BE', '#CFB37A'];
    let y = 0; let i = 0; while (y < 256) { const h = 18 + r() * 30; x.fillStyle = cols[i++ % cols.length]; x.fillRect(0, y, 512, h); y += h; }
  }
  return tex(c);
}
export function makePlanet(kind, radius) {
  const g = new THREE.Group();
  const m = new THREE.Mesh(new THREE.SphereGeometry(1, 48, 32), toon(0xffffff, { map: planetTex(kind) }));
  g.add(m);
  if (kind === 'saturn') {
    const c = canvas(256, 8), x = c.getContext('2d');
    const gr = x.createLinearGradient(0, 0, 256, 0);
    gr.addColorStop(0, 'rgba(220,200,150,0.0)'); gr.addColorStop(0.1, 'rgba(225,205,160,0.9)'); gr.addColorStop(0.45, 'rgba(200,175,125,0.95)');
    gr.addColorStop(0.55, 'rgba(120,100,70,0.3)'); gr.addColorStop(0.62, 'rgba(230,214,170,0.95)'); gr.addColorStop(1, 'rgba(230,214,170,0.0)');
    x.fillStyle = gr; x.fillRect(0, 0, 256, 8);
    const rg = new THREE.RingGeometry(1.35, 2.3, 96, 1);
    // uv radial
    const pos = rg.attributes.position, uv = rg.attributes.uv;
    for (let i = 0; i < pos.count; i++) { const rr = Math.hypot(pos.getX(i), pos.getY(i)); uv.setXY(i, (rr - 1.35) / 0.95, 0.5); }
    const ring = new THREE.Mesh(rg, new THREE.MeshToonMaterial({ map: tex(c), transparent: true, side: THREE.DoubleSide, depthWrite: false }));
    ring.rotation.x = -Math.PI / 2 + 0.45; ring.userData.outline = false;
    g.add(ring);
  }
  outlineAll(m);
  g.scale.setScalar(radius);
  return g;
}
export function makeSun() {
  const g = new THREE.Group();
  const core = new THREE.Mesh(new THREE.SphereGeometry(1, 32, 24), new THREE.MeshBasicMaterial({ color: hdr(0xFFE08A, 6), toneMapped: false }));
  core.userData.outline = false; g.add(core);
  const halo = new THREE.Sprite(new THREE.SpriteMaterial({ map: radialTex(), color: hdr(0xFFD27A, 1.2), blending: THREE.AdditiveBlending, depthWrite: false, transparent: true, toneMapped: false }));
  halo.scale.setScalar(9); g.add(halo);
  return g;
}

// ------------------------------------------------------------------ Voyager 1
export function makeVoyager() {
  const g = new THREE.Group();
  const mBus = toon(0x9C9A95), mDark = toon(0x55585F), mWhite = toon(0xF1EEE6), mBoom = toon(0x7E8088);
  const mInst = toon(0xD9D4C8), mGold = toon(0xE2B34A, { emissive: new THREE.Color(0x6A4A10), emissiveIntensity: 0.6 });
  // bus decagonal
  const bus = new THREE.Mesh(new THREE.CylinderGeometry(0.5, 0.5, 0.3, 10), mBus); g.add(bus);
  const busTop = new THREE.Mesh(new THREE.CylinderGeometry(0.42, 0.46, 0.06, 10), mDark); busTop.position.y = 0.18; g.add(busTop);
  const busBot = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.22, 0.16, 10), mDark); busBot.position.y = -0.23; g.add(busBot);
  // plato (boresight +Y)
  const dish = new THREE.Mesh(dishGeo(0.95, 0.5, 0.035), mWhite); dish.position.y = 0.2; g.add(dish);
  const feed = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.07, 0.25, 12), mInst); feed.position.y = 0.35; g.add(feed);
  const focus = V(0, 0.2 + 0.5, 0);
  const sub = new THREE.Mesh(new THREE.CylinderGeometry(0.11, 0.04, 0.05, 16), mWhite); sub.position.copy(focus); g.add(sub);
  for (let i = 0; i < 3; i++) {
    const a = i * Math.PI * 2 / 3 + 0.3;
    g.add(rod(V(Math.cos(a) * 0.78, 0.2 + 0.78 * 0.78 / 2, Math.sin(a) * 0.78), focus, 0.012, mBoom, 6));
  }
  // brazo de ciencia (-X) con plataforma de instrumentos
  const sciDir = V(-1, -0.1, -0.12).normalize();
  const sciEnd = sciDir.clone().multiplyScalar(2.0);
  g.add(rod(sciDir.clone().multiplyScalar(0.45), sciEnd, 0.03, mBoom));
  const lights = [];
  const lightMat = () => new THREE.MeshBasicMaterial({ color: hdr(0x7CFF8A, 3), toneMapped: false });
  const inst = (pos, size, mat = mInst) => { const b = new THREE.Mesh(new THREE.BoxGeometry(...size), mat); b.position.copy(pos); g.add(b); return b; };
  const addLight = (pos) => { const l = new THREE.Mesh(new THREE.SphereGeometry(0.035, 12, 8), lightMat()); l.position.copy(pos); l.userData.outlineK = 0.6; g.add(l); lights.push(l); return l; };
  const p1 = sciDir.clone().multiplyScalar(0.85); inst(p1, [0.2, 0.16, 0.2]); addLight(p1.clone().add(V(0, 0.12, 0)));
  const p2 = sciDir.clone().multiplyScalar(1.3); const c2 = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.09, 0.22, 14), mDark); c2.position.copy(p2); c2.rotation.z = Math.PI / 2; g.add(c2); addLight(p2.clone().add(V(0, 0.13, 0)));
  const plat = inst(sciEnd.clone().add(V(-0.05, -0.12, 0)), [0.34, 0.24, 0.3], mDark);
  addLight(plat.position.clone().add(V(0.05, 0.16, 0.1)));
  const cam1 = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 0.42, 14), mInst); cam1.position.copy(plat.position).add(V(-0.05, -0.05, 0.25)); cam1.rotation.x = Math.PI / 2; g.add(cam1);
  const cam2 = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.26, 14), mInst); cam2.position.copy(plat.position).add(V(0.1, -0.05, 0.22)); cam2.rotation.x = Math.PI / 2; g.add(cam2);
  addLight(plat.position.clone().add(V(-0.16, 0.16, -0.08)));
  const p3 = sciDir.clone().multiplyScalar(1.65); inst(p3.clone().add(V(0, 0.1, 0)), [0.14, 0.12, 0.16]); addLight(p3.clone().add(V(0, 0.2, 0)));
  // brazo RTG (+X): tres cilindros con aletas, conectados por cable
  const rtgDir = V(1, -0.12, 0.22).normalize();
  g.add(rod(rtgDir.clone().multiplyScalar(0.45), rtgDir.clone().multiplyScalar(2.05), 0.03, mBoom));
  const rtgs = [];
  const rtgShell = toon(0x5E616B, { transparent: true });
  const finMat = toon(0x6E717B, { transparent: true });
  const coreMat = new THREE.MeshBasicMaterial({ color: hdr(0xFF8A3D, 2.5), toneMapped: false });
  for (let i = 0; i < 3; i++) {
    const u = new THREE.Group();
    u.position.copy(rtgDir.clone().multiplyScalar(1.05 + i * 0.42));
    u.quaternion.setFromUnitVectors(V(0, 1, 0), rtgDir);
    const cyl = new THREE.Mesh(new THREE.CylinderGeometry(0.1, 0.1, 0.36, 18), rtgShell); u.add(cyl);
    const cap1 = new THREE.Mesh(new THREE.CylinderGeometry(0.115, 0.115, 0.03, 18), rtgShell); cap1.position.y = 0.18; u.add(cap1);
    const cap2 = cap1.clone(); cap2.position.y = -0.18; u.add(cap2);
    for (let f = 0; f < 6; f++) {
      const a = f * Math.PI / 3;
      const fin = new THREE.Mesh(new THREE.BoxGeometry(0.15, 0.32, 0.018), finMat);
      fin.position.set(Math.cos(a) * 0.17, 0, Math.sin(a) * 0.17); fin.rotation.y = -a; u.add(fin);
    }
    const core = new THREE.Mesh(new THREE.CylinderGeometry(0.055, 0.055, 0.26, 16), coreMat); core.userData.outline = false; core.visible = false; u.add(core);
    g.add(u); rtgs.push({ u, core });
  }
  // cable RTG -> bus
  const cablePts = [rtgDir.clone().multiplyScalar(1.05).add(V(0, 0.07, -0.08)), rtgDir.clone().multiplyScalar(0.7).add(V(0, 0.07, -0.06)), rtgDir.clone().multiplyScalar(0.48).add(V(0, 0.05, 0)), V(0.3, 0.02, 0.05), V(0.0, 0.03, 0.12)];
  const cableCurve = new THREE.CatmullRomCurve3(cablePts);
  const cable = new THREE.Mesh(new THREE.TubeGeometry(cableCurve, 40, 0.014, 6), toon(0x3C4A63)); cable.userData.outlineK = 0.5; g.add(cable);
  // cable bus -> instrumentos
  const sciCurve = new THREE.CatmullRomCurve3([V(0.0, 0.03, 0.12), V(-0.3, 0.05, 0.06), sciDir.clone().multiplyScalar(0.5).add(V(0, 0.06, 0.04)), sciDir.clone().multiplyScalar(1.2).add(V(0, 0.07, 0.03)), sciDir.clone().multiplyScalar(1.9).add(V(0, 0.07, 0.02))]);
  const sciCable = new THREE.Mesh(new THREE.TubeGeometry(sciCurve, 40, 0.014, 6), toon(0x3C4A63)); sciCable.userData.outlineK = 0.5; g.add(sciCable);
  // magnetómetro: brazo largo y fino
  const magDir = V(-0.25, -0.35, 1).normalize();
  g.add(rod(V(0, -0.1, 0.4), magDir.clone().multiplyScalar(4.6), 0.013, mBoom, 6));
  [1.6, 3.0, 4.55].forEach((d) => { const s = new THREE.Mesh(new THREE.CylinderGeometry(0.035, 0.035, 0.12, 10), mInst); s.position.copy(magDir.clone().multiplyScalar(d)); s.quaternion.setFromUnitVectors(V(0, 1, 0), magDir); g.add(s); });
  // antenas de radio en V
  g.add(rod(V(0.1, -0.3, -0.2), V(1.6, -2.6, -1.4), 0.008, mBoom, 5));
  g.add(rod(V(-0.1, -0.3, -0.2), V(-1.2, -2.7, -1.6), 0.008, mBoom, 5));
  // disco de oro en una cara del bus (+Z)
  const dc = canvas(512, 512), dx = dc.getContext('2d');
  const dg = dx.createRadialGradient(256, 256, 0, 256, 256, 256);
  dg.addColorStop(0, '#F6D77A'); dg.addColorStop(1, '#D7A63E'); dx.fillStyle = dg; dx.fillRect(0, 0, 512, 512);
  for (let r = 70; r < 250; r += 5) { dx.strokeStyle = r % 10 ? 'rgba(150,100,20,0.25)' : 'rgba(255,240,190,0.35)'; dx.lineWidth = 2; dx.beginPath(); dx.arc(256, 256, r, 0, 7); dx.stroke(); }
  dx.fillStyle = '#E9C25E'; dx.beginPath(); dx.arc(256, 256, 62, 0, 7); dx.fill(); dx.strokeStyle = 'rgba(140,90,20,0.6)'; dx.lineWidth = 4; dx.stroke();
  dx.fillStyle = '#8A5E18'; dx.beginPath(); dx.arc(256, 256, 8, 0, 7); dx.fill();
  const faceMat = toon(0xffffff, { map: tex(dc), emissive: new THREE.Color(0x5A3C08), emissiveIntensity: 0.7 });
  const disk = new THREE.Group();
  const dBody = new THREE.Mesh(new THREE.CylinderGeometry(0.17, 0.17, 0.02, 48), [mGold, faceMat, mGold]);
  dBody.rotation.x = Math.PI / 2; disk.add(dBody);
  // brillo que barre el disco
  const glint = new THREE.Mesh(new THREE.CircleGeometry(0.17, 48), new THREE.ShaderMaterial({
    uniforms: { ph: { value: 0 }, op: { value: 1 } },
    vertexShader: 'varying vec2 vP; void main(){ vP = position.xy/0.17; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0);} ',
    fragmentShader: 'uniform float ph; uniform float op; varying vec2 vP; void main(){ float d = vP.x*0.8+vP.y*0.6 - ph; float b = exp(-d*d*28.0); float r = length(vP); float rings = 0.5+0.5*sin(r*90.0); gl_FragColor = vec4(vec3(1.0,0.9,0.6)*b*(0.7+0.3*rings)*2.2, b*op); }',
    transparent: true, depthWrite: false, blending: THREE.AdditiveBlending, toneMapped: false,
  }));
  glint.position.z = 0.0115; glint.userData.outline = false; disk.add(glint);
  disk.position.set(0, -0.01, 0.485);
  g.add(disk);
  // panel solar "fantasma" (para la escena 4)
  outlineAll(g);
  shadows(g, true, true);
  g.userData = { dish, lights, rtgs, rtgShell, finMat, cableCurve, sciCurve, disk, glint, rtgDir, sciDir };
  return g;
}

// ------------------------------------------------------------------ panel solar pequeño (escena 4)
export function makePanel() {
  const g = new THREE.Group();
  const c = canvas(256, 256), x = c.getContext('2d');
  x.fillStyle = '#2B4F8C'; x.fillRect(0, 0, 256, 256);
  x.strokeStyle = '#8FB2E8'; x.lineWidth = 4;
  for (let i = 0; i <= 4; i++) { x.beginPath(); x.moveTo(i * 64, 0); x.lineTo(i * 64, 256); x.stroke(); x.beginPath(); x.moveTo(0, i * 64); x.lineTo(256, i * 64); x.stroke(); }
  const m = new THREE.Mesh(new THREE.BoxGeometry(1, 0.05, 1), [toon(0x8C93A3), toon(0x8C93A3), toon(0xffffff, { map: tex(c), transparent: true }), toon(0x8C93A3), toon(0x8C93A3), toon(0x8C93A3)]);
  g.add(m);
  g.add(rod(V(0, -0.02, 0), V(0, -0.5, 0), 0.02, toon(0x7E8088)));
  outlineAll(g);
  g.userData = { m };
  return g;
}

// ------------------------------------------------------------------ reloj despertador
export function makeClock() {
  const g = new THREE.Group();
  const red = toon(0xE7675B), face = toon(0xFFF8EA), ink = toon(0x2B2F3A), metal = toon(0xC9CCD3);
  const body = new THREE.Mesh(new THREE.CylinderGeometry(1, 1, 0.42, 48), red); body.rotation.x = Math.PI / 2; g.add(body);
  const f = new THREE.Mesh(new THREE.CylinderGeometry(0.84, 0.84, 0.06, 48), face); f.rotation.x = Math.PI / 2; f.position.z = 0.2; g.add(f);
  for (let i = 0; i < 12; i++) {
    const a = i * Math.PI / 6; const big = i % 3 === 0;
    const tk = new THREE.Mesh(new THREE.BoxGeometry(big ? 0.07 : 0.045, big ? 0.17 : 0.1, 0.03), ink);
    tk.position.set(Math.sin(a) * 0.68, Math.cos(a) * 0.68, 0.24); tk.rotation.z = -a; tk.userData.outlineK = 0.4; g.add(tk);
  }
  const hourP = new THREE.Group(); hourP.position.z = 0.25; g.add(hourP);
  const hh = new THREE.Mesh(new THREE.BoxGeometry(0.09, 0.45, 0.03), ink); hh.position.y = 0.2; hourP.add(hh);
  const minP = new THREE.Group(); minP.position.z = 0.28; g.add(minP);
  const mh = new THREE.Mesh(new THREE.BoxGeometry(0.06, 0.66, 0.03), toon(0xE7675B)); mh.position.y = 0.3; minP.add(mh);
  const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.07, 0.06, 16), ink); cap.rotation.x = Math.PI / 2; cap.position.z = 0.3; g.add(cap);
  for (const s of [-1, 1]) {
    const bell = new THREE.Mesh(new THREE.SphereGeometry(0.32, 24, 16, 0, Math.PI * 2, 0, Math.PI / 2), red);
    bell.position.set(s * 0.62, 0.78, -0.02); bell.rotation.z = -s * 0.55; g.add(bell);
    const leg = rod(V(s * 0.5, -0.8, 0), V(s * 0.75, -1.2, 0), 0.06, metal); g.add(leg);
  }
  const knob = new THREE.Mesh(new THREE.SphereGeometry(0.09, 12, 8), metal); knob.position.set(0, 1.08, 0); g.add(knob);
  outlineAll(g);
  g.userData = { hourP, minP };
  return g;
}

// ------------------------------------------------------------------ bombillo
export function makeBulb() {
  const g = new THREE.Group();
  const glass = toon(0xFFF1B8, { emissive: new THREE.Color(0xFFC93C), emissiveIntensity: 0 });
  const pts = [];
  for (let i = 0; i <= 20; i++) { const a = -Math.PI / 2 + i / 20 * Math.PI * 1.25; pts.push(new THREE.Vector2(Math.max(0.001, Math.cos(a) * 0.5), Math.sin(a) * 0.5 + 0.5)); }
  pts.push(new THREE.Vector2(0.22, 1.05)); pts.push(new THREE.Vector2(0.2, 1.15)); pts.push(new THREE.Vector2(0.001, 1.15));
  const bulb = new THREE.Mesh(new THREE.LatheGeometry(pts, 40), glass); g.add(bulb);
  const metal = toon(0xB9BCC4);
  for (let i = 0; i < 4; i++) { const r = new THREE.Mesh(new THREE.CylinderGeometry(0.21, 0.21, 0.08, 24), metal); r.position.y = 1.18 + i * 0.09; g.add(r); }
  const tip = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.06, 0.08, 16), toon(0x55585F)); tip.position.y = 1.56; g.add(tip);
  outlineAll(g);
  g.rotation.z = Math.PI; // rosca hacia arriba
  g.userData = { glass };
  return g;
}

// ------------------------------------------------------------------ módem viejo + barra de progreso
export function makeModem() {
  const g = new THREE.Group();
  const beige = toon(0xE6DCC3), dark = toon(0x4A4F5A);
  const body = new THREE.Mesh(new THREE.BoxGeometry(1.7, 0.34, 1.1), beige); body.position.y = 0.2; g.add(body);
  const top = new THREE.Mesh(new THREE.BoxGeometry(1.6, 0.06, 1.0), toon(0xDCD0B4)); top.position.y = 0.39; g.add(top);
  const panel = new THREE.Mesh(new THREE.BoxGeometry(1.4, 0.13, 0.04), dark); panel.position.set(0, 0.2, 0.56); g.add(panel);
  for (let i = 0; i < 4; i++) { const s = new THREE.Mesh(new THREE.BoxGeometry(0.9, 0.02, 0.05), dark); s.position.set(0, 0.43, -0.3 + i * 0.16); s.userData.outline = false; g.add(s); }
  const leds = [];
  const cols = [0xFF5A4A, 0x6CFF7A, 0x6CFF7A, 0xFFC93C, 0x6CFF7A, 0xFF5A4A];
  for (let i = 0; i < 6; i++) {
    const l = new THREE.Mesh(new THREE.SphereGeometry(0.035, 12, 8), new THREE.MeshBasicMaterial({ color: hdr(cols[i], 3), toneMapped: false }));
    l.position.set(-0.5 + i * 0.2, 0.2, 0.59); l.userData.outline = false; l.userData.base = cols[i]; g.add(l); leds.push(l);
  }
  for (const sx of [-0.7, 0.7]) for (const sz of [-0.4, 0.4]) { const f = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.07, 0.05, 10), dark); f.position.set(sx, 0.02, sz); g.add(f); }
  // cable de teléfono enrollado
  const coil = []; for (let i = 0; i <= 120; i++) { const a = i * 0.5; coil.push(V(-0.86 - i * 0.012, 0.2 + Math.sin(a) * 0.05, -0.2 + Math.cos(a) * 0.05)); }
  const cc = new THREE.Mesh(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(coil), 200, 0.012, 5), toon(0xD8D2C4)); cc.userData.outline = false; g.add(cc);
  // barra de progreso 3D
  const bar = new THREE.Group(); bar.position.set(0, 1.0, 0);
  const frame = new THREE.Mesh(new THREE.BoxGeometry(1.9, 0.26, 0.2), toon(0xffffff)); bar.add(frame);
  const track = new THREE.Mesh(new THREE.BoxGeometry(1.76, 0.14, 0.21), toon(0x2E3440)); track.userData.outline = false; bar.add(track);
  const fill = new THREE.Mesh(new THREE.BoxGeometry(1, 0.14, 0.22), new THREE.MeshBasicMaterial({ color: hdr(GOLD, 1.6), toneMapped: false })); fill.userData.outline = false;
  fill.geometry.translate(0.5, 0, 0); fill.position.x = -0.88; bar.add(fill);
  g.add(bar);
  outlineAll(g);
  shadows(g, true, true);
  g.userData = { leds, bar, fill };
  return g;
}

// ------------------------------------------------------------------ monitor con gráficas
export function makeMonitor() {
  const g = new THREE.Group();
  const dark = toon(0x3A3F4B);
  const frame = new THREE.Mesh(new THREE.BoxGeometry(2.0, 1.35, 0.14), dark); frame.position.y = 1.05; g.add(frame);
  const c = canvas(640, 400);
  const t = tex(c);
  const screen = new THREE.Mesh(new THREE.PlaneGeometry(1.8, 1.15), new THREE.MeshBasicMaterial({ map: t, toneMapped: false }));
  screen.position.set(0, 1.05, 0.072); screen.userData.outline = false; g.add(screen);
  g.add(rod(V(0, 0.38, -0.02), V(0, 0.05, -0.02), 0.07, dark));
  const base = new THREE.Mesh(new THREE.BoxGeometry(0.8, 0.06, 0.45), dark); base.position.y = 0.03; g.add(base);
  outlineAll(g);
  shadows(g, true, true);
  g.userData = { canvas: c, tex: t };
  return g;
}
export function drawScreen(g, p) {
  // p: 0..1 progreso de los datos
  const c = g.userData.canvas, x = c.getContext('2d');
  x.fillStyle = '#16203A'; x.fillRect(0, 0, 640, 400);
  x.strokeStyle = 'rgba(140,170,220,0.18)'; x.lineWidth = 2;
  for (let i = 1; i < 8; i++) { x.beginPath(); x.moveTo(i * 80, 20); x.lineTo(i * 80, 380); x.stroke(); }
  for (let i = 1; i < 5; i++) { x.beginPath(); x.moveTo(20, i * 80); x.lineTo(620, i * 80); x.stroke(); }
  // curva 1 (dorada)
  const n = Math.floor(clampN(p) * 120);
  x.lineWidth = 6; x.lineJoin = 'round'; x.strokeStyle = '#FFC93C'; x.beginPath();
  for (let i = 0; i <= n; i++) { const X = 30 + i * 4.8, Y = 200 - Math.sin(i * 0.11) * 60 - Math.sin(i * 0.37) * 18 + i * 0.25; i ? x.lineTo(X, Y) : x.moveTo(X, Y); }
  x.stroke();
  // curva 2 (verde)
  x.strokeStyle = '#6CF08A'; x.beginPath();
  for (let i = 0; i <= n; i++) { const X = 30 + i * 4.8, Y = 300 - i * 0.9 - Math.sin(i * 0.2) * 14; i ? x.lineTo(X, Y) : x.moveTo(X, Y); }
  x.stroke();
  // barras
  const nb = Math.floor(clampN(p * 1.2) * 8);
  for (let i = 0; i < nb; i++) { x.fillStyle = i % 2 ? '#5EA8F0' : '#FF8A5C'; const h = 40 + ((i * 37) % 60); x.fillRect(470 + i * 18, 110 - h * 0.6, 12, h * 0.6); }
  // punto parpadeante
  if (n > 0) { const X = 30 + n * 4.8, Y = 200 - Math.sin(n * 0.11) * 60 - Math.sin(n * 0.37) * 18 + n * 0.25; x.fillStyle = '#fff'; x.beginPath(); x.arc(X, Y, 9, 0, 7); x.fill(); }
  g.userData.tex.needsUpdate = true;
}
const clampN = (v) => Math.max(0, Math.min(1, v));

// ------------------------------------------------------------------ mesa
export function makeDesk() {
  const g = new THREE.Group();
  const wood = toon(0xC98F5A), legM = toon(0x8B5E3C);
  const top = new THREE.Mesh(new THREE.BoxGeometry(4.2, 0.14, 1.8), wood); top.position.y = 1.0; g.add(top);
  for (const sx of [-1.9, 1.9]) for (const sz of [-0.75, 0.75]) { const l = new THREE.Mesh(new THREE.BoxGeometry(0.14, 1.0, 0.14), legM); l.position.set(sx, 0.5, sz); g.add(l); }
  outlineAll(g); shadows(g, true, true);
  return g;
}

// ------------------------------------------------------------------ antena DSN
export function makeDSN() {
  const g = new THREE.Group();
  const conc = toon(0xDAD5C9), white = toon(0xF4F1EA), grey = toon(0xA9A59C);
  const glowM = toon(0xF4F1EA, { emissive: new THREE.Color(0xFFC93C), emissiveIntensity: 0 });
  const ped = new THREE.Mesh(new THREE.CylinderGeometry(0.9, 1.05, 1.6, 8), conc); ped.position.y = 0.8; g.add(ped);
  const turret = new THREE.Group(); turret.position.y = 1.6; g.add(turret);
  const tb = new THREE.Mesh(new THREE.BoxGeometry(1.7, 0.5, 1.3), grey); tb.position.y = 0.25; turret.add(tb);
  for (const s of [-1, 1]) { const arm = new THREE.Mesh(new THREE.BoxGeometry(0.22, 1.5, 0.6), grey); arm.position.set(s * 0.75, 1.1, 0); turret.add(arm); }
  const elev = new THREE.Group(); elev.position.y = 1.7; turret.add(elev);
  const dish = new THREE.Mesh(dishGeo(2.6, 1.45, 0.08, 56), glowM); dish.position.y = 0.35; elev.add(dish);
  const back = new THREE.Mesh(new THREE.CylinderGeometry(0.9, 0.35, 0.6, 12), grey); back.position.y = 0.1; elev.add(back);
  const hub = new THREE.Mesh(new THREE.CylinderGeometry(0.3, 0.35, 0.5, 16), white); hub.position.y = 0.55; elev.add(hub);
  const fy = 0.35 + 1.45;
  const sub = new THREE.Mesh(new THREE.CylinderGeometry(0.32, 0.08, 0.14, 20), white); sub.position.y = fy; elev.add(sub);
  for (let i = 0; i < 4; i++) { const a = i * Math.PI / 2 + Math.PI / 4; elev.add(rod(V(Math.cos(a) * 1.9, 0.35 + 1.9 * 1.9 / 5.8, Math.sin(a) * 1.9), V(0, fy, 0), 0.035, grey, 6)); }
  // pequeña luz roja de baliza
  outlineAll(g); shadows(g, true, true);
  g.userData = { turret, elev, glowM, focusLocal: V(0, fy, 0) };
  return g;
}

// ------------------------------------------------------------------ nubes, arbustos, árboles
export function makeCloud(seed = 1) {
  const g = new THREE.Group(); const r = rng(seed * 97 + 5);
  const m = toon(0xffffff);
  const puffs = [[0, 0, 0, 1.0], [1.1, -0.15, 0.1, 0.8], [-1.05, -0.2, 0, 0.75], [0.45, 0.45, -0.1, 0.8], [-0.4, 0.35, 0.15, 0.7]];
  puffs.forEach(([x, y, z, s]) => { const p = new THREE.Mesh(new THREE.SphereGeometry(s * (0.9 + r() * 0.2), 20, 14), m); p.position.set(x, y, z); g.add(p); });
  outlineAll(g);
  return g;
}
export function makeTree(seed = 1) {
  const g = new THREE.Group(); const r = rng(seed * 31 + 7);
  const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.16, 1.0, 8), toon(0x8B5E3C)); trunk.position.y = 0.5; g.add(trunk);
  const leaf = toon(r() > 0.5 ? 0x5DB547 : 0x4FA442);
  const a = new THREE.Mesh(new THREE.SphereGeometry(0.7, 16, 12), leaf); a.position.y = 1.4; g.add(a);
  const b = new THREE.Mesh(new THREE.SphereGeometry(0.5, 16, 12), leaf); b.position.set(0.4, 1.2, 0.1); g.add(b);
  outlineAll(g); shadows(g, true, true);
  return g;
}

// ------------------------------------------------------------------ notas y marcos (sonidos e imágenes)
export function makeNote() {
  const g = new THREE.Group(); const m = toon(0xFFD36A, { emissive: new THREE.Color(0x6A4A10), emissiveIntensity: 0.4 });
  const h = new THREE.Mesh(new THREE.SphereGeometry(0.12, 16, 12), m); h.scale.set(1.3, 1, 0.8); g.add(h);
  g.add(rod(V(0.13, 0.02, 0), V(0.13, 0.5, 0), 0.025, m));
  const fl = new THREE.Mesh(new THREE.BoxGeometry(0.2, 0.06, 0.05), m); fl.position.set(0.22, 0.47, 0); fl.rotation.z = -0.5; g.add(fl);
  outlineAll(g);
  return g;
}
export function makeFrame() {
  const g = new THREE.Group();
  const c = canvas(128, 96), x = c.getContext('2d');
  const sk = x.createLinearGradient(0, 0, 0, 96); sk.addColorStop(0, '#5EB0F0'); sk.addColorStop(1, '#BFE6FA'); x.fillStyle = sk; x.fillRect(0, 0, 128, 96);
  x.fillStyle = '#FFD23F'; x.beginPath(); x.arc(98, 26, 12, 0, 7); x.fill();
  x.fillStyle = '#7DCB52'; x.beginPath(); x.moveTo(0, 96); x.quadraticCurveTo(40, 40, 80, 70); x.quadraticCurveTo(110, 50, 128, 62); x.lineTo(128, 96); x.fill();
  const fr = new THREE.Mesh(new THREE.BoxGeometry(0.62, 0.48, 0.05), [toon(0xE2B34A), toon(0xE2B34A), toon(0xE2B34A), toon(0xE2B34A), toon(0xffffff, { map: tex(c) }), toon(0xE2B34A)]);
  g.add(fr);
  outlineAll(g);
  return g;
}

// ------------------------------------------------------------------ texto 3D (Nunito Black extruido)
const geoCache = new Map();
export function text3D(font, str, size, mat) {
  const key = str + '|' + size;
  let geo = geoCache.get(key);
  if (!geo) {
    geo = new TextGeometry(str, { font, size, depth: size * 0.28, curveSegments: 5, bevelEnabled: true, bevelThickness: size * 0.04, bevelSize: size * 0.025, bevelSegments: 2 });
    geo.computeBoundingBox(); geo.center();
    geoCache.set(key, geo);
  }
  const m = new THREE.Mesh(geo, mat);
  return m;
}
