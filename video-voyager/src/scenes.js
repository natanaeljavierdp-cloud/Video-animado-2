// Coreografía: cada escena coloca objetos, luces y cámara en función del tiempo t
// (determinista: cualquier fotograma se puede renderizar de forma independiente).
import * as THREE from 'three';
import {
  V, K, clamp, lin, sm, eio, eout, ein, eback, P as PP, pop, lerp, hermite, hdr, GOLD, toon,
  Dots, Rings, label, outlineAll, shadows, addOutline,
} from './lib.js';
import {
  makeEarth, lonlat, makePlanet, makeSun, makeVoyager, makePanel, makeClock, makeBulb, makeModem, makeMonitor,
  drawScreen, makeDesk, makeDSN, makeCloud, makeTree, makeNote, makeFrame, text3D,
} from './models.js';

export const SPACE_BG = new THREE.Color(0x101C3D);

export function buildWorld(scene, camera, assets) {
  const W = {};
  W.scene = scene; W.camera = camera;
  const reg = [];
  const add = (o) => { scene.add(o); reg.push(o); return o; };
  W.reg = reg;

  // luces
  W.hemi = new THREE.HemisphereLight(0xDDE8FF, 0x6A6070, 1.0); scene.add(W.hemi);
  W.sun = new THREE.DirectionalLight(0xFFF4E0, 2.0); W.sun.castShadow = true;
  W.sun.shadow.mapSize.set(2048, 2048); W.sun.shadow.bias = -0.0004; W.sun.shadow.normalBias = 0.02; W.sun.shadow.radius = 4;
  scene.add(W.sun); scene.add(W.sun.target);

  // estrellas (siguen a la cámara)
  {
    const n = 1600, pos = new Float32Array(n * 3), sz = new Float32Array(n), ph = new Float32Array(n);
    let s = 12345; const r = () => ((s = (s * 1664525 + 1013904223) >>> 0) / 4294967296);
    for (let i = 0; i < n; i++) {
      const u = r() * 2 - 1, a = r() * Math.PI * 2, q = Math.sqrt(1 - u * u);
      pos.set([q * Math.cos(a) * 900, u * 900, q * Math.sin(a) * 900], i * 3);
      sz[i] = r() < 0.08 ? 4.5 + r() * 2.5 : 1.8 + r() * 2.0; ph[i] = r() * 6.28;
    }
    const g = new THREE.BufferGeometry();
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3));
    g.setAttribute('sz', new THREE.BufferAttribute(sz, 1));
    g.setAttribute('ph', new THREE.BufferAttribute(ph, 1));
    W.starMat = new THREE.ShaderMaterial({
      uniforms: { time: { value: 0 }, op: { value: 1 } },
      vertexShader: 'attribute float sz; attribute float ph; uniform float time; varying float vA; void main(){ vA = 0.65 + 0.35*sin(time*2.0+ph*3.0); gl_PointSize = sz; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0);} ',
      fragmentShader: 'uniform float op; varying float vA; void main(){ float d = length(gl_PointCoord-0.5); float a = smoothstep(0.5,0.1,d); gl_FragColor = vec4(vec3(1.0,0.97,0.88)*1.0, a*vA*op);} ',
      transparent: true, depthWrite: false,
    });
    W.stars = add(new THREE.Points(g, W.starMat));
    W.stars.frustumCulled = false; W.stars.renderOrder = -1;
  }

  // espacio
  W.earth = add(makeEarth(assets.land));
  W.moon = add(makePlanet('moon', 0.3));
  W.mars = add(makePlanet('mars', 0.5));
  W.jup = add(makePlanet('jupiter', 1.5));
  W.sat = add(makePlanet('saturn', 1.05));
  W.sunStar = add(makeSun());
  W.voy = add(makeVoyager());
  W.panel = add(makePanel());
  W.clock = add(makeClock());
  W.bulb = add(makeBulb());
  W.dsnSmall = ['us', 'es', 'au'].map(() => { const d = makeDSN(); d.scale.setScalar(0.075); W.earth.add(d); return d; });
  W.dsnSmall.forEach((d, i) => { d.userData.lonlat = [[-116.9, 35.4], [-4.25, 40.43], [148.98, -35.4]][i]; });
  W.notes = [makeNote(), makeNote(), makeFrame(), makeFrame(), makeNote()].map(add);

  // línea de distancia
  W.distLine = add(new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 1, 10), new THREE.MeshBasicMaterial({ color: new THREE.Color(1.4, 1.3, 1.1), toneMapped: false })));
  W.distLine.userData.outline = false;
  W.distCapA = add(new THREE.Mesh(new THREE.SphereGeometry(0.22, 16, 12), new THREE.MeshBasicMaterial({ color: hdr(GOLD, 2.5), toneMapped: false })));
  W.distCapB = add(W.distCapA.clone());

  // texto 3D
  W.font = assets.font;
  W.textMat = toon(0xFFC93C, { emissive: new THREE.Color(0x5A3C08), emissiveIntensity: 0.5 });
  W.textMatW = toon(0xFFFFFF);
  W.textCache = new Map();
  W.textHolder = add(new THREE.Group());
  W.textHolder2 = add(new THREE.Group());

  // haz de luz (escena 3)
  W.beam = add(new THREE.Mesh(new THREE.SphereGeometry(0.14, 20, 14), new THREE.MeshBasicMaterial({ color: hdr(0xFFF2B0, 8), toneMapped: false })));
  W.beam.userData.outline = false;

  // tierra firme (escenas 6b-7)
  W.G0 = V(0, -3000, 0);
  W.ground = add(new THREE.Group()); W.ground.position.copy(W.G0);
  {
    const g = new THREE.PlaneGeometry(400, 400, 120, 120); g.rotateX(-Math.PI / 2);
    const p = g.attributes.position;
    for (let i = 0; i < p.count; i++) {
      const x = p.getX(i), z = p.getZ(i), d = Math.hypot(x, z);
      p.setY(i, (d > 22 ? (d - 22) * 0.04 : 0) * (0.6 + 0.4 * Math.sin(x * 0.05) * Math.cos(z * 0.04)) + Math.sin(x * 0.11) * Math.cos(z * 0.09) * 0.25 * sm((d - 10) / 10));
    }
    g.computeVertexNormals();
    const grass = new THREE.Mesh(g, toon(0x9BD54F)); grass.receiveShadow = true; grass.userData.outline = false;
    W.ground.add(grass);
    // colinas lejanas
    [[-60, -80, 30, 0x86C64A], [40, -110, 42, 0x7DBB45], [-120, -20, 36, 0x8CCB50], [110, -40, 30, 0x86C64A], [0, -150, 50, 0x79B743], [-30, 120, 40, 0x86C64A], [120, 90, 38, 0x7DBB45]].forEach(([x, z, r, c]) => {
      const h = new THREE.Mesh(new THREE.SphereGeometry(r, 32, 16), toon(c)); h.position.set(x, -r * 0.62, z); h.scale.y = 0.75; W.ground.add(h); addOutline(h, 0.8);
    });
    // cielo
    const sky = new THREE.Mesh(new THREE.SphereGeometry(600, 32, 16), new THREE.ShaderMaterial({
      vertexShader: 'varying vec3 vP; void main(){ vP = position; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0);} ',
      fragmentShader: 'varying vec3 vP; void main(){ float h = clamp(normalize(vP).y, 0.0, 1.0); vec3 top = vec3(0.24,0.60,0.88); vec3 hor = vec3(0.76,0.89,0.97); gl_FragColor = vec4(mix(hor, top, pow(h, 0.55)), 1.0);} ',
      side: THREE.BackSide, depthWrite: false,
    }));
    sky.userData.outline = false; sky.renderOrder = -2; W.ground.add(sky);
    W.clouds = [];
    [[-18, 16, -30, 2.6], [14, 19, -40, 3.0], [30, 13, -10, 2.2], [-30, 14, 10, 2.4], [5, 22, 30, 2.8], [-8, 12, -60, 3.4], [40, 18, 30, 2.5]].forEach(([x, y, z, s], i) => {
      const c = makeCloud(i + 1); c.position.set(x, y, z); c.scale.setScalar(s); c.userData.x0 = x; W.ground.add(c); W.clouds.push(c);
    });
    [[-9, -6], [-11, 3], [7, -10], [-6, -12], [16, -4], [-14, -14], [3, 15], [-4, 13], [19, 12]].forEach(([x, z], i) => { const tr = makeTree(i); tr.position.set(x, 0, z); tr.scale.setScalar(1.2 + (i % 3) * 0.3); W.ground.add(tr); });
    W.dsnBig = makeDSN(); W.dsnBig.scale.setScalar(1.6); W.ground.add(W.dsnBig);
    W.dsnBig.userData.turret.rotation.y = 0.9; W.dsnBig.userData.elev.rotation.x = -0.62;
    // mesa con módem y monitor
    W.deskG = new THREE.Group(); W.deskG.position.set(10, 0, 8); W.deskG.rotation.y = Math.atan2(10, 8); W.ground.add(W.deskG);
    W.desk = makeDesk(); W.deskG.add(W.desk);
    W.modem = makeModem(); W.modem.position.set(-1.1, 1.07, 0.1); W.modem.scale.setScalar(0.8); W.deskG.add(W.modem);
    W.monitor = makeMonitor(); W.monitor.position.set(0.9, 1.07, -0.15); W.monitor.rotation.y = -0.25; W.deskG.add(W.monitor);
    // cable de datos (antena -> monitor)
    W.ground.updateMatrixWorld(true);
    const mBack = W.monitor.localToWorld(V(0, 0.6, -0.1)).sub(W.G0);
    const leg = W.deskG.localToWorld(V(1.2, 0.0, -0.8)).sub(W.G0);
    W.dataCurve = new THREE.CatmullRomCurve3([V(0.8, 0.12, 1.2), V(3, 0.12, 3.2), V(6.5, 0.12, 5.0), leg.clone().setY(0.12), leg.clone().setY(0.95), mBack]);
    const cab = new THREE.Mesh(new THREE.TubeGeometry(W.dataCurve, 120, 0.06, 6), toon(0x3C4A63)); cab.userData.outlineK = 0.6; W.ground.add(cab); addOutline(cab, 0.6);
    W.loadLabel = label(scene, 'Descargando...', { size: 54 });
  }

  // partículas y anillos
  W.dots = new Dots(scene, 1200);
  W.rings = new Rings(scene, 40);

  // etiquetas
  W.L = {
    h24: label(scene, '24 horas', { size: 64 }),
    h48: label(scene, '48 horas', { size: 64 }),
    s1: label(scene, '1 segundo', { size: 60 }),
    h24b: label(scene, '24 horas', { size: 60 }),
    us: label(scene, 'Estados Unidos', { size: 52 }),
    es: label(scene, 'España', { size: 52 }),
    au: label(scene, 'Australia', { size: 52 }),
    rtg: label(scene, 'Pila nuclear', { size: 54, bg: '#FFE2C2' }),
  };
  W.labels = Object.values(W.L).concat([W.loadLabel]);

  // posiciones del mundo "espacio"
  W.E0 = V(0, 0, 0);
  W.PV = V(1.5, 24, -6);
  W.dE = W.E0.clone().sub(W.PV).normalize(); // de la sonda hacia la Tierra
  W.voy.position.copy(W.PV);
  W.voy.quaternion.setFromUnitVectors(V(0, 1, 0), W.dE);
  W.voy.updateMatrixWorld(true);
  W.planetPos = { moon: V(1.35, 3.3, -0.4), mars: V(-2.4, 8.6, -3.2), jup: V(3.6, 13.6, -7.5), sat: V(-3.3, 18.6, -4.6) };
  W.Efar = W.PV.clone().addScaledVector(W.dE, 120);
  return W;
}

// ------------------------------------------------------------------ helpers
const UP = V(0, 1, 0);
function lookCam(cam, pos, target, up = UP) {
  cam.position.copy(pos); cam.up.copy(up); cam.lookAt(target);
  cam.updateMatrixWorld(true);
}
function camLocal(cam, x, y, z) { return V(x, y, z).applyMatrix4(cam.matrixWorld); }
function setSun(W, dir, focus, R = 4, inten = 2.0) {
  W.sun.position.copy(focus).addScaledVector(dir.clone().normalize(), 40);
  W.sun.target.position.copy(focus); W.sun.target.updateMatrixWorld();
  const c = W.sun.shadow.camera; c.left = -R; c.right = R; c.top = R; c.bottom = -R; c.near = 1; c.far = 90; c.updateProjectionMatrix();
  W.sun.intensity = inten;
}
function show(o, s = 1) { o.visible = s > 0.002; if (o.visible && s !== null) o.scale.setScalar(Math.max(0.001, s)); }
function showLabel(L, pos, k) {
  L.visible = k > 0.01; if (!L.visible) return; L.position.copy(pos); L.userData.k = Math.max(0.01, k); L.material.opacity = clamp(k * 2);
}
function setText(W, holder, str, size, mat) {
  const key = str + '|' + size + '|' + mat.uuid;
  let m = W.textCache.get(key);
  if (!m) { m = text3D(W.font, str, size, mat); addOutline(m, 1.2); W.textCache.set(key, m); }
  if (holder.children[0] !== m) { holder.clear(); holder.add(m); }
}
function placeEarthAntennas(W, active = -1, glow = 0) {
  W.dsnSmall.forEach((d, i) => {
    const [lo, la] = d.userData.lonlat;
    const n = lonlat(lo, la, 1).normalize();
    d.position.copy(n.clone().multiplyScalar(0.985));
    d.quaternion.setFromUnitVectors(UP, n);
    d.userData.elev.rotation.x = -0.5;
    d.userData.glowM.emissiveIntensity = i === active ? glow : 0;
  });
}
function resetProbe(W) {
  const u = W.voy.userData;
  u.lights.forEach((l) => l.material.color.set(0x7CFF8A).multiplyScalar(3));
  u.rtgShell.opacity = 1; u.rtgShell.transparent = false; u.rtgShell.depthWrite = true; u.rtgShell.emissive.set(0x000000);
  u.finMat.opacity = 1; u.finMat.transparent = false; u.finMat.emissive.set(0x000000);
  u.rtgs.forEach((r) => (r.core.visible = false));
  u.glint.material.uniforms.op.value = 0;
}
function resetAll(W) {
  W.reg.forEach((o) => (o.visible = false));
  W.labels.forEach((l) => (l.visible = false));
  W.dots.clear(); W.rings.clear();
  W.scene.background = SPACE_BG;
  W.stars.visible = true; W.starMat.uniforms.op.value = 1;
  W.hemi.color.set(0xDDE8FF); W.hemi.groundColor.set(0x6A6070); W.hemi.intensity = 1.0;
  W.sun.color.set(0xFFF4E0);
  W.earth.position.set(0, 0, 0); W.earth.scale.setScalar(1); W.earth.rotation.set(0.41, 0, 0);
  W.earth.userData.atm.material.uniforms.op.value = 0.9;
  W.dsnSmall.forEach((d) => (d.visible = false));
  W.voy.position.copy(W.PV); W.voy.scale.setScalar(1);
  resetProbe(W);
  for (const [k, p] of Object.entries(W.planetPos)) W[k].position.copy(p);
  W.moon.scale.setScalar(0.3); W.mars.scale.setScalar(0.5); W.jup.scale.setScalar(1.5); W.sat.scale.setScalar(1.05);
  W.jup.rotation.y = 0.3;
}
function showPlanets(W, t) {
  ['moon', 'mars', 'jup', 'sat'].forEach((k) => { W[k].visible = true; W[k].rotation.y = t * 0.12 + k.length; });
}
function earthSpin(W, t) { W.earth.rotation.y = t * 0.22 - 1.2; W.earth.userData.clouds.rotation.y = t * 0.05; }
// punto de luz principal con estela
function comet(W, curve, u, r = 0.12, trail = 0.06, n = 14, cam = null) {
  for (let i = n; i >= 0; i--) {
    const uu = u - trail * i / n; if (uu < 0) continue;
    const f = 1 - i / n;
    W.dots.add(curve.getPointAt(clamp(uu)), r * (0.35 + 0.65 * f) * (i ? 0.8 : 1), GOLD, i ? 4 : 7, i ? 0.25 + 0.75 * f : 1, cam);
  }
}

// ================================================================== ESCENA 1 (0 – 9.4)
function s1(W, t) {
  const cam = W.camera; cam.fov = 40;
  W.earth.visible = true; earthSpin(W, t); showPlanets(W, t); W.voy.visible = true;
  const surf = W.dE.clone().multiplyScalar(-1).multiplyScalar(1.05); // punto de la Tierra que mira a la sonda
  const dishPt = W.PV.clone().addScaledVector(W.dE, 0.75);
  if (!W._c1) {
    const mid = W.E0.clone().lerp(W.PV, 0.5).add(V(1.6, 0, 1.2));
    W._c1 = new THREE.CatmullRomCurve3([surf, mid, dishPt]);
    W._c1r = new THREE.CatmullRomCurve3([dishPt, mid.clone().add(V(-0.5, 0, 0.4)), surf]);
  }
  const up1 = W._c1, back = W._c1r;
  const u1 = eio(lin(t, 0.95, 4.2));
  const u2 = eio(lin(t, 4.45, 6.6));
  // cámara
  const wide = V(9.5, 11.5, 37), wideL = V(0.6, 11.8, -3);
  let pos, look;
  if (t < 4.35) {
    const p0 = V(2.4, 0.2, 4.9), l0 = V(1.0, 1.25, 0);
    const d = up1.getPointAt(clamp(u1));
    const tg = up1.getTangentAt(clamp(u1));
    const fp = d.clone().add(V(2.0, -1.6, 3.6)).addScaledVector(tg, -1.0);
    const fl = d.clone().addScaledVector(tg, 2.5);
    const w = sm(lin(t, 0.9, 2.2));
    pos = p0.clone().lerp(fp, w); look = l0.clone().lerp(fl, w);
    // llegada: encuadra la sonda
    const a = sm(lin(t, 3.4, 4.35));
    pos.lerp(W.PV.clone().add(V(2.6, -1.9, 3.8)), a); look.lerp(W.PV.clone().add(V(0, -0.6, 0)), a);
  } else {
    const k0 = W.PV.clone().add(V(2.6, -1.9, 3.8));
    pos = hermite([K(4.35, k0), K(6.0, wide), K(7.6, wide.clone().add(V(-1.5, 0.5, -3))), K(9.4, W.PV.clone().add(V(3.0, -1.3, 3.2)))], t);
    look = hermite([K(4.35, W.PV.clone().add(V(0, -0.6, 0))), K(6.0, wideL), K(7.6, wideL.clone().add(V(0, 1.5, 0))), K(9.4, W.PV)], t);
  }
  lookCam(cam, pos, look);
  // señales
  if (t > 0.95 && t < 4.3) comet(W, up1, u1, 0.13, 0.08, 16, cam);
  if (t > 4.45 && t < 6.7) comet(W, back, u2, 0.13, 0.08, 16, cam);
  if (t > 4.1 && t < 4.7) { const f = lin(t, 4.1, 4.7); W.dots.add(dishPt, 0.25 + f * 0.4, GOLD, 5, 1 - f, cam); }
  if (t > 6.5 && t < 7.1) { const f = lin(t, 6.5, 7.1); W.dots.add(surf, 0.25 + f * 0.5, GOLD, 5, 1 - f, cam); }
  if (t > 7.0) {
    const a = sm(lin(t, 7.0, 7.6)) * (1 - sm(lin(t, 9.0, 9.6)));
    W.dots.along(up1, t, { speed: 0.22, spacing: 0.07, r: 0.09, a, cam });
    W.dots.along(back, t + 0.03, { speed: 0.22, spacing: 0.07, r: 0.09, a, cam, color: 0xFFE07A });
  }
  // reloj en el espacio de la cámara
  const ck = pop(t, 2.35, 7.3);
  if (ck > 0.01) {
    W.clock.visible = true;
    W.clock.position.copy(camLocal(cam, 0, -1.55, -7));
    W.clock.quaternion.copy(cam.quaternion);
    W.clock.rotateY(Math.sin(t * 1.3) * 0.35 + 0.15); W.clock.rotateX(-0.12);
    W.clock.scale.setScalar(0.62 * ck);
    const h = 24 * eio(lin(t, 2.6, 4.25)) + 24 * eio(lin(t, 4.6, 6.45));
    W.clock.userData.hourP.rotation.z = -h / 12 * Math.PI * 2;
    W.clock.userData.minP.rotation.z = -h * Math.PI * 2;
    showLabel(W.L.h24, camLocal(cam, 0, -2.75, -7), pop(t, 4.15, 6.25, 0.4, 0.2) * ck);
    showLabel(W.L.h48, camLocal(cam, 0, -2.75, -7), pop(t, 6.3, 7.25, 0.4, 0.2));
  }
  setSun(W, V(0.8, 0.3, 0.7), t < 4.3 ? W.E0.clone().lerp(W.PV, clamp(u1)) : W.PV, 3.5);
  return 'space';
}

// ================================================================== ESCENA 2 (9.4 – 23.75)
function s2(W, t) {
  const cam = W.camera; cam.fov = 40;
  W.earth.visible = true; earthSpin(W, t); showPlanets(W, t); W.voy.visible = true;
  const P0 = W.PV;
  // órbita alrededor de la sonda
  const th = lerp(0.82, 3.5, eio(lin(t, 9.4, 18.6)) * 0.9 + lin(t, 9.4, 18.6) * 0.1);
  const R = lerp(4.4, 3.3, sm(lin(t, 9.4, 12)));
  const hh = lerp(-1.3, 0.5, sm(lin(t, 9.4, 18)));
  const orb = P0.clone().add(V(Math.cos(th) * R, hh, Math.sin(th) * R));
  const wide = V(11, 11, 40), wideL = V(0.8, 11.5, -3);
  const pos = orb.clone().lerp(wide, eio(lin(t, 18.3, 21.6)));
  const look = P0.clone().lerp(wideL, eio(lin(t, 18.3, 21.6)));
  lookCam(cam, pos, look);
  // contador 1977 -> 2026
  const ck = pop(t, 11.45, 18.2);
  if (ck > 0.01) {
    const yr = Math.round(lerp(1977, 2026, eio(lin(t, 13.9, 16.1))));
    setText(W, W.textHolder, String(yr), 0.62, W.textMat);
    W.textHolder.visible = true;
    W.textHolder.position.copy(camLocal(cam, 0, -1.55, -5.2));
    W.textHolder.quaternion.copy(cam.quaternion); W.textHolder.rotateY(Math.sin(t * 1.1) * 0.3); W.textHolder.rotateX(-0.15);
    W.textHolder.scale.setScalar(ck);
  }
  // línea de distancia
  const gl = eio(lin(t, 20.7, 22.4));
  if (gl > 0.001) {
    const a = P0.clone().addScaledVector(W.dE, 0.9), b = W.dE.clone().multiplyScalar(-1.15);
    const e = a.clone().lerp(b, gl);
    const d = e.clone().sub(a);
    W.distLine.visible = true; W.distLine.position.copy(a).addScaledVector(d, 0.5);
    W.distLine.quaternion.setFromUnitVectors(UP, d.clone().normalize()); W.distLine.scale.set(1, d.length(), 1);
    W.distCapA.visible = true; W.distCapA.position.copy(a); W.distCapA.scale.setScalar(1);
    W.distCapB.visible = true; W.distCapB.position.copy(e); W.distCapB.scale.setScalar(1);
    // pulsos que recorren la línea
    for (let i = 0; i < 4; i++) { const u = ((t * 0.35 + i / 4) % 1); if (u < gl) W.dots.add(a.clone().lerp(b, u), 0.16, GOLD, 5, 1, cam); }
  }
  const dk = pop(t, 21.75, 24.5);
  if (dk > 0.01) {
    setText(W, W.textHolder2, '26.000.000.000 km', 0.36, W.textMatW);
    W.textHolder2.visible = true;
    W.textHolder2.position.copy(camLocal(cam, 0, -2.05, -8));
    W.textHolder2.quaternion.copy(cam.quaternion); W.textHolder2.rotateY(Math.sin(t * 0.9) * 0.18); W.textHolder2.rotateX(-0.1);
    W.textHolder2.scale.setScalar(dk);
  }
  setSun(W, V(0.8, 0.3, 0.7), P0, 3.5);
  return 'space';
}

// ================================================================== ESCENA 3 (23.75 – 32.6)
function s3(W, t) {
  const cam = W.camera; cam.fov = 42;
  W.earth.visible = true; earthSpin(W, t); showPlanets(W, t); W.voy.visible = true;
  const pp = W.planetPos;
  if (!W._c3) {
    const start = pp.moon.clone().normalize().multiplyScalar(1.05);
    const pts = [start, pp.moon.clone().add(V(0.45, -0.1, 0.35)), pp.mars.clone().add(V(0.9, 0.2, 0.6)), pp.jup.clone().add(V(-2.2, 0, 1.4)), pp.sat.clone().add(V(1.8, 0.3, 1.2)), W.PV.clone().addScaledVector(W.dE, 0.75)];
    W._c3 = new THREE.CatmullRomCurve3(pts, false, 'centripetal');
    // fracción de arco donde pasa la Luna
    let best = 0, bd = 1e9; for (let i = 0; i <= 400; i++) { const d = W._c3.getPointAt(i / 400).distanceTo(pts[1]); if (d < bd) { bd = d; best = i / 400; } }
    W._um = best;
  }
  const c = W._c3, um = W._um;
  let u = 0;
  if (t >= 26.42) {
    if (t < 28.15) { const f = lin(t, 26.42, 28.15); u = um * (0.35 * f * f + 0.65 * f); }
    else { const f = lin(t, 28.15, 31.3); u = um + (1 - um) * (1 - Math.pow(1 - f, 1.6)); }
  }
  const head = c.getPointAt(clamp(u)), tg = c.getTangentAt(clamp(u));
  // cámara
  const p0 = V(-2.2, -1.2, 3.6), l0 = V(0.6, 1.4, 0);
  const pS = hermite([K(23.75, V(-2.6, -1.6, 4.2)), K(26.4, p0)], t);
  const side = V(1, 0, 0.4).normalize();
  const chase = head.clone().addScaledVector(tg, -2.4).addScaledVector(side, 0.9).add(V(0, -0.2, 0.9));
  const chaseL = head.clone().addScaledVector(tg, 2.2);
  const settle = W.PV.clone().add(V(2.4, -2.4, 3.0)), settleL = W.PV.clone().add(V(0, -0.4, 0));
  const wc = sm(lin(t, 26.3, 27.1)), ws = sm(lin(t, 30.7, 31.8));
  const pos = pS.clone().lerp(chase, wc).lerp(settle, ws);
  const look = l0.clone().lerp(chaseL, wc).lerp(settleL, ws);
  lookCam(cam, pos, look);
  // haz
  if (t >= 25.2 && t < 31.35) {
    if (t < 26.42) { const f = lin(t, 25.2, 26.42); W.dots.add(head, 0.06 + 0.1 * f + 0.02 * Math.sin(t * 20), 0xFFF2B0, 6, f, cam); }
    else {
      W.beam.visible = true; W.beam.position.copy(head);
      W.beam.quaternion.setFromUnitVectors(UP, tg); W.beam.scale.set(1, 3.5, 1);
      for (let i = 1; i <= 26; i++) { const uu = u - i * 0.0035; if (uu < 0) break; const f = 1 - i / 26; W.dots.add(c.getPointAt(uu), 0.09 * f + 0.02, 0xFFE59A, 5, f, cam); }
    }
  }
  if (t > 31.3 && t < 32.2) { const f = lin(t, 31.3, 32.2); W.dots.add(c.getPointAt(1), 0.3 + f * 0.6, GOLD, 5, 1 - f, cam); }
  showLabel(W.L.s1, pp.moon.clone().add(V(0, 0.75, 0)), pop(t, 28.05, 29.6));
  showLabel(W.L.h24b, W.PV.clone().add(V(0, 1.6, 0)), pop(t, 31.15, 33.2));
  setSun(W, V(0.8, 0.3, 0.7), W.PV, 3.5);
  return 'space';
}

// ================================================================== ESCENA 4 (32.6 – 47.82)
function s4(W, t) {
  const cam = W.camera; cam.fov = 40;
  W.voy.visible = true;
  const vu = W.voy.userData;
  const P0 = W.PV;
  const rtgC = W.voy.localToWorld(vu.rtgDir.clone().multiplyScalar(1.05));
  const rtgMid = W.voy.localToWorld(vu.rtgDir.clone().multiplyScalar(1.45));
  const busC = W.voy.localToWorld(V(0, 0, 0));
  const sciC = W.voy.localToWorld(vu.sciDir.clone().multiplyScalar(1.5));
  // eje perpendicular al brazo RTG en el mundo
  const rtgAxis = vu.rtgDir.clone().applyQuaternion(W.voy.quaternion);
  const perp = V(0, 0, 1).cross(rtgAxis).normalize();
  const c0 = P0.clone().add(V(3.2, -1.0, 3.4)), l0 = P0.clone().add(V(-0.8, 0.9, -0.6));
  const cR = rtgC.clone().addScaledVector(perp, 1.15).add(V(0.2, -0.3, 0.7)), lR = rtgC.clone();
  const cB = rtgC.clone().lerp(busC, 0.6).add(V(0.4, -0.6, 1.4)), lB = rtgC.clone().lerp(busC, 0.65);
  const cS = sciC.clone().add(V(0.6, -0.5, 1.6)), lS = sciC.clone().add(V(0.1, 0.1, 0));
  const pos = hermite([K(32.6, c0), K(35.4, c0.clone().add(V(-0.3, 0.2, -0.5))), K(37.8, cR), K(40.4, cR.clone().addScaledVector(perp, -0.15).add(V(0, 0.05, -0.12))), K(42.8, cB), K(45.2, cS), K(47.82, cS.clone().add(V(-0.4, 0.3, -0.3)))], t);
  const look = hermite([K(32.6, l0), K(35.4, l0), K(37.8, lR), K(40.4, lR), K(42.8, lB), K(45.2, lS), K(47.82, lS)], t);
  lookCam(cam, pos, look);
  // Sol lejano: arriba a la izquierda del encuadre inicial
  if (!W._sun4) {
    const tmp = new THREE.PerspectiveCamera(40, 1080 / 1920); tmp.position.copy(c0); tmp.lookAt(l0); tmp.updateMatrixWorld(true);
    W._sun4 = V(-0.42, 0.62, -1).normalize().transformDirection(tmp.matrixWorld).multiplyScalar(160).add(c0);
  }
  const sunP = W._sun4;
  W.sunStar.visible = true; W.sunStar.position.copy(sunP); W.sunStar.scale.setScalar(1.1);
  const sunDir = sunP.clone().sub(P0).normalize();
  // luz solar débil que no alcanza
  if (t < 36.2) {
    const a = 1 - sm(lin(t, 35.4, 36.2));
    for (let i = 0; i < 9; i++) {
      const ph = ((t * 0.18 + i / 9) % 1);
      const p = sunP.clone().lerp(P0.clone().add(V(1.0, 1.1, 1.0)), ph);
      W.dots.add(p, 0.5 * (1 - ph) + 0.05, 0xFFE8A0, 3, a * (1 - ph) * 0.9, cam);
    }
  }
  const pk = pop(t, 34.3, 35.9);
  if (pk > 0.01) {
    W.panel.visible = true; W.panel.position.copy(P0).add(V(1.1, 1.25, 1.0));
    W.panel.lookAt(sunP); W.panel.rotateX(Math.PI / 2); W.panel.scale.setScalar(0.75 * pk);
  }
  // pila nuclear (RTG)
  const open = sm(lin(t, 38.3, 39.1)) * (1 - sm(lin(t, 43.6, 44.6)));
  const heat = sm(lin(t, 38.6, 39.6)) * (1 - 0.45 * sm(lin(t, 43.8, 46.5)));
  if (open > 0.001) {
    vu.rtgShell.transparent = true; vu.rtgShell.opacity = 1 - 0.72 * open; vu.rtgShell.depthWrite = open < 0.5;
    vu.finMat.transparent = true; vu.finMat.opacity = 1 - 0.6 * open;
  }
  vu.rtgShell.emissive.set(0xFF7A2E).multiplyScalar(0.35 * heat);
  vu.finMat.emissive.set(0xFF7A2E).multiplyScalar(0.45 * heat);
  vu.rtgs.forEach((r, i) => { r.core.visible = heat > 0.01; r.core.material.color.set(0xFF8A3D).multiplyScalar(0.5 + 2.6 * heat * (0.9 + 0.1 * Math.sin(t * 6 + i))); });
  // partículas de calor
  if (heat > 0.01 && t < 44.5) {
    vu.rtgs.forEach((r, ri) => {
      for (let i = 0; i < 7; i++) {
        const ph = (t * 0.9 + i / 7 + ri * 0.31) % 1;
        const a = i * 2.4 + ri;
        const loc = V(Math.cos(a) * (0.05 + ph * 0.3), (i % 3 - 1) * 0.1, Math.sin(a) * (0.05 + ph * 0.3));
        const p = r.u.localToWorld(loc);
        W.dots.add(p, 0.022 * (1 - ph * 0.5), 0xFF8A3D, 4, heat * (1 - ph), cam);
      }
    });
  }
  showLabel(W.L.rtg, rtgMid.clone().add(V(0, 0.75, 0)), pop(t, 37.2, 40.3));
  // electricidad por los cables
  const elec = sm(lin(t, 40.5, 41.3));
  if (elec > 0.001) {
    const cc = vu.cableCurve, sc = vu.sciCurve;
    if (!W._wc) {
      W._wc = new THREE.CatmullRomCurve3(cc.points.map((p) => W.voy.localToWorld(p.clone())));
      W._ws = new THREE.CatmullRomCurve3(sc.points.map((p) => W.voy.localToWorld(p.clone())));
    }
    const wear = sm(lin(t, 44.0, 46.8));
    const rev = eio(lin(t, 40.5, 42.0));
    W.dots.along(W._wc, t, { speed: 0.42, spacing: lerp(0.09, 0.2, wear), r: 0.022, reveal: rev, a: elec, cam, alt: 0xFFF2A0 });
    const rev2 = eio(lin(t, 42.0, 43.4));
    if (rev2 > 0) W.dots.along(W._ws, t, { speed: 0.3, spacing: lerp(0.06, 0.16, wear), r: 0.022, reveal: rev2, a: elec * (1 - 0.4 * wear), cam, alt: 0xFFF2A0 });
  }
  // instrumentos que se apagan uno a uno
  const offT = [45.15, null, 45.95, null, 46.75];
  vu.lights.forEach((l, i) => {
    const o = offT[i] ? sm(lin(t, offT[i], offT[i] + 0.35)) : 0;
    const on = new THREE.Color(0x7CFF8A).multiplyScalar(3), off = new THREE.Color(0x5A5E66);
    l.material.color.copy(on.lerp(off, o));
  });
  setSun(W, sunDir.clone().add(V(0.6, 0.2, 0.5)), P0, 3.5, 2.0);
  return 'space';
}

// ================================================================== ESCENA 5 (47.82 – 60.15)
function s5(W, t) {
  const cam = W.camera; cam.fov = 40;
  W.voy.visible = true; resetProbe(W);
  const vu = W.voy.userData; [0, 2, 4].forEach((i) => vu.lights[i].material.color.set(0x5A5E66));
  const P0 = W.PV, d = W.dE, Ef = W.Efar;
  W.earth.visible = true; W.earth.position.copy(Ef); earthSpin(W, t);
  W.earth.userData.atm.material.uniforms.op.value = 1.6;
  const side = V(1, 0, 0).cross(d).normalize(); const up2 = d.clone().cross(side).normalize();
  const focus = P0.clone().addScaledVector(d, 0.75);
  // cámara
  const c0 = P0.clone().addScaledVector(d, -2.6).addScaledVector(side, 1.6).addScaledVector(up2, 1.0);
  const l0 = P0.clone().addScaledVector(d, 5).addScaledVector(side, -0.2);
  const c1 = P0.clone().addScaledVector(d, -1.2).addScaledVector(side, 2.6).addScaledVector(up2, 0.4);
  const l1 = P0.clone().addScaledVector(d, 1.5).addScaledVector(side, 0.9);
  let pos = hermite([K(47.82, c0), K(50.5, c0.clone().addScaledVector(side, 0.4)), K(53.0, c1), K(54.3, c1.clone().addScaledVector(d, 0.6))], t);
  let look = hermite([K(47.82, l0), K(50.5, l0), K(53.0, l1), K(54.3, l1.clone().addScaledVector(d, 1.5))], t);
  // viaje con la señal
  const tr = eio(lin(t, 54.3, 59.4));
  const sAlong = lerp(0, 120 - 6.5, tr);
  const rideP = P0.clone().addScaledVector(d, sAlong).addScaledVector(side, lerp(2.6, 1.6, tr)).addScaledVector(up2, lerp(0.4, 1.0, tr));
  const rideL = rideP.clone().addScaledVector(d, 12).lerp(Ef, sm(lin(t, 56.5, 59.0)));
  const w = sm(lin(t, 54.1, 54.9));
  pos.lerp(rideP, w); look.lerp(rideL, w);
  lookCam(cam, pos, look);
  // anillos de radio
  if (t > 48.9) {
    const a0 = sm(lin(t, 48.9, 49.6));
    for (let k = 0; k < 40; k++) {
      const te = 48.9 + k * 0.42; if (te > t) break;
      const age = t - te; const s = age * 26; if (s > 121) continue;
      const rad = 0.75 + s * 0.085;
      const width = 0.16 / (1 + s * 0.11);
      const op = a0 / (1 + s * 0.045) * (s > 112 ? clamp((121 - s) / 9) : 1);
      W.rings.add(focus.clone().addScaledVector(d, s + 0.05), d, rad, width, op, 4 / (1 + s * 0.03));
    }
  }
  // bombillo de referencia
  const bk = pop(t, 52.55, 56.0);
  if (bk > 0.01) {
    W.bulb.visible = true; W.bulb.position.copy(P0).addScaledVector(side, 1.15).addScaledVector(d, 0.55).addScaledVector(up2, -0.35);
    W.bulb.quaternion.copy(cam.quaternion); W.bulb.rotateZ(Math.PI + Math.sin(t * 2) * 0.12);
    W.bulb.scale.setScalar(0.42 * bk);
    W.bulb.userData.glass.emissiveIntensity = 1.6 * sm(lin(t, 52.75, 53.1)) * (0.92 + 0.08 * Math.sin(t * 9));
  }
  setSun(W, side.clone().add(up2).add(d.clone().multiplyScalar(-0.3)), P0, 3.5);
  return 'space';
}

// ================================================================== ESCENA 6 (60.15 – 71.0) — el globo
function s6(W, t) {
  const cam = W.camera; cam.fov = 40;
  W.earth.visible = true; W.earth.userData.clouds.rotation.y = t * 0.05;
  const D = V(-1, 0.42, 0.25).normalize(); // dirección de la sonda
  const tilt = 0.41;
  if (W._ry6 === undefined) {
    // giro final: España mirando a la sonda
    let best = 0, bv = -9;
    for (let i = 0; i < 720; i++) {
      const ry = i / 720 * Math.PI * 2; W.earth.rotation.set(tilt, ry, 0); W.earth.updateMatrixWorld(true);
      const n = lonlat(-4.25, 40.43).applyQuaternion(W.earth.quaternion);
      const v = n.dot(D); if (v > bv) { bv = v; best = ry; }
    }
    W._ry6 = best;
  }
  const ryEnd = W._ry6;
  const spin = eio(lin(t, 67.1, 70.4));
  W.earth.rotation.set(tilt, ryEnd - Math.PI * 2 * (1 - spin), 0);
  W.earth.updateMatrixWorld(true);
  placeEarthAntennas(W);
  const ak = [61.4, 61.6, 61.8].map((a) => eback(lin(t, a, a + 0.5)));
  W.dsnSmall.forEach((d, i) => { d.visible = ak[i] > 0.01; d.scale.setScalar(0.075 * Math.max(0.01, ak[i])); });
  const wpos = (i) => W.dsnSmall[i].getWorldPosition(V(0, 0, 0));
  const wnor = (i) => { const [lo, la] = W.dsnSmall[i].userData.lonlat; return lonlat(lo, la).applyQuaternion(W.earth.quaternion).normalize(); };
  // cámara: recorre las tres antenas mientras se nombran
  const camDirFor = (lo, la) => lonlat(lo, la).applyQuaternion(W.earth.quaternion).normalize();
  const Cfix = V(0.9, 0.75, 6.3);
  const dist = 6.4;
  const lonK = [[60.15, -175], [62.0, -150], [64.55, -112], [65.55, -12], [66.4, 132], [67.1, 175]];
  const latK = [[60.15, 22], [64.55, 30], [65.55, 32], [66.4, -24], [67.1, -10]];
  const hk = (keys) => hermite(keys.map(([a, b]) => [a, b, 0, 0]), t).x;
  let pos = camDirFor(hk(lonK), hk(latK)).multiplyScalar(dist);
  const wv = sm(lin(t, 66.6, 67.8));
  pos = pos.lerp(Cfix, wv);
  let look = V(0, -0.25, 0);
  // inmersión hacia España
  const dv = eio(lin(t, 70.25, 71.25));
  if (dv > 0) {
    const ap = wpos(1), an = wnor(1);
    pos = pos.lerp(ap.clone().addScaledVector(an, 0.32).addScaledVector(D, 0.12), dv);
    look = look.lerp(ap, sm(lin(t, 70.25, 70.8)));
  }
  lookCam(cam, pos, look);
  // etiquetas de país (se ocultan si quedan detrás)
  const camD = cam.position.clone().normalize();
  ['us', 'es', 'au'].forEach((k, i) => {
    const t0 = [64.4, 65.45, 66.05][i];
    const n = wnor(i), face = sm((n.dot(camD) - 0.15) / 0.25);
    showLabel(W.L[k], wpos(i).addScaledVector(n, 0.32), pop(t, t0, 70.2) * face);
  });
  // señal de la sonda y relevo entre antenas
  if (t > 67.0) {
    const a = sm(lin(t, 67.0, 67.6));
    let best = -1, bv = 0.12;
    for (let i = 0; i < 3; i++) { const v = wnor(i).dot(D); if (v > bv) { bv = v; best = i; } }
    W.dsnSmall.forEach((d, i) => { d.userData.glowM.emissiveIntensity = i === best ? 1.2 * a : 0; });
    if (best >= 0) {
      const tgt = wpos(best).addScaledVector(wnor(best), 0.14);
      const from = tgt.clone().addScaledVector(D, 7);
      for (let k = 0; k < 16; k++) { const ph = (t * 1.3 + k / 16) % 1; W.dots.add(from.clone().lerp(tgt, ph), 0.035, GOLD, 6, a * sm(ph * 5), cam); }
      W.dots.add(tgt, 0.06 + 0.02 * Math.sin(t * 12), GOLD, 6, a, cam);
    }
  }
  setSun(W, V(0.6, 0.4, 0.9), V(0, 0, 0), 2);
  return 'space';
}

// ================================================================== ESCENA 6b + 7 (71.0 – 82.45) — tierra firme
function s7(W, t) {
  const cam = W.camera; cam.fov = 42;
  const G = W.G0;
  W.ground.visible = true; W.stars.visible = false;
  W.scene.background = new THREE.Color(0xBEE5F8);
  W.hemi.color.set(0xD8ECFF); W.hemi.groundColor.set(0x7A9A50); W.hemi.intensity = 1.15;
  W.sun.color.set(0xFFF6E6);
  W.clouds.forEach((c, i) => { c.position.x = c.userData.x0 + Math.sin(t * 0.05 + i) * 2 + t * 0.15; });
  const dsn = W.dsnBig; W.ground.updateMatrixWorld(true);
  const focus = dsn.userData.elev.localToWorld(dsn.userData.focusLocal.clone());
  const dishC = dsn.userData.elev.localToWorld(V(0, 0.6, 0));
  const skyDir = focus.clone().sub(dishC).normalize();
  // cámara
  const L = (x, y, z) => G.clone().add(V(x, y, z));
  const deskTop = W.deskG.localToWorld(V(0, 1.1, 0));
  const modemP = W.modem.localToWorld(V(0, 0.5, 0));
  const monP = W.monitor.localToWorld(V(0, 1.05, 0));
  const fwd = W.deskG.localToWorld(V(0, 0, 1)).sub(W.deskG.localToWorld(V(0, 0, 0))).normalize();
  const rightD = V(0, 1, 0).cross(fwd).normalize();
  const camModem = modemP.clone().addScaledVector(fwd, 3.0).addScaledVector(rightD, -0.6).add(V(0, 1.0, 0));
  const camMon = monP.clone().addScaledVector(fwd, 3.4).addScaledVector(rightD, -0.8).add(V(0, 0.6, 0));
  const pos = hermite([K(70.6, L(3, 34, 12)), K(72.2, L(14, 13, 15)), K(73.6, L(16, 7, 2)), K(74.7, L(17, 5.5, 8.5)), K(76.0, camModem), K(78.3, camModem.clone().addScaledVector(rightD, 0.25).add(V(0, -0.15, 0)).addScaledVector(fwd, -0.3)), K(80.0, camMon.clone().addScaledVector(rightD, -2.0).addScaledVector(fwd, 1.2).add(V(0, 0.8, 0))), K(82.45, camMon)], t);
  const look = hermite([K(70.6, L(0, 5, 0)), K(72.2, dishC), K(73.6, dishC), K(74.7, dishC.clone().lerp(deskTop, 0.5)), K(76.0, modemP.clone().add(V(0, 0.45, 0))), K(78.3, modemP.clone().add(V(0, 0.45, 0))), K(80.0, monP.clone().lerp(dishC, 0.25)), K(82.45, monP)], t);
  lookCam(cam, pos, look);
  // datos que bajan del cielo a la antena (lentos)
  const sky0 = focus.clone().addScaledVector(skyDir, 60);
  for (let k = 0; k < 7; k++) { const ph = (t * 0.06 + k / 7) % 1; W.dots.add(sky0.clone().lerp(focus, ph), 0.16, GOLD, 6, sm(ph * 6), cam); }
  dsn.userData.glowM.emissiveIntensity = 0.18 + 0.08 * Math.sin(t * 3);
  // módem
  W.modem.userData.leds.forEach((l, i) => {
    const on = Math.sin(Math.floor(t * 7 + i * 3.7) * 12.9898) * 43758.5 % 1;
    l.material.color.set(l.userData.base).multiplyScalar(Math.abs(on) > 0.45 ? 3 : 0.25);
  });
  W.modem.userData.fill.scale.x = 0.012 + 0.05 * lin(t, 75.0, 82.4);
  showLabel(W.loadLabel, W.modem.localToWorld(V(0, 1.55, 0)), pop(t, 75.4, 78.6));
  // cable de datos -> monitor
  const dc = new THREE.CatmullRomCurve3(W.dataCurve.points.map((p) => p.clone().add(G)));
  if (!W._dcw) W._dcw = dc;
  const rv = eio(lin(t, 78.4, 79.6));
  if (rv > 0) W.dots.along(W._dcw, t, { speed: 0.12, spacing: 0.035, r: 0.075, reveal: rv, cam, alt: 0xFFF2A0 });
  drawScreen(W.monitor, lin(t, 79.2, 82.4));
  setSun(W, V(0.7, 1.0, 0.45), cam.position.clone().lerp(look, 0.6), 16, 2.3);
  return 'ground';
}

// ================================================================== ESCENA 8 (82.45 – fin)
function s8(W, t, T) {
  const cam = W.camera; cam.fov = 40;
  W.voy.visible = true; resetProbe(W);
  const vu = W.voy.userData; [0, 2, 4].forEach((i) => vu.lights[i].material.color.set(0x5A5E66));
  const P0 = W.PV, Ef = W.Efar;
  W.earth.visible = true; W.earth.position.copy(Ef); earthSpin(W, t);
  W.earth.userData.atm.material.uniforms.op.value = 2.2;
  const diskP = W.voy.localToWorld(vu.disk.position.clone());
  const n = V(0, 0, 1).applyQuaternion(W.voy.quaternion).normalize();
  const sideN = n.clone().cross(W.dE).normalize();
  // brillo que barre el disco
  vu.glint.material.uniforms.op.value = 1;
  vu.glint.material.uniforms.ph.value = ((t - 83.6) % 2.2) / 2.2 * 3.2 - 1.6;
  const c0 = diskP.clone().addScaledVector(n, 1.0).addScaledVector(sideN, 0.35).addScaledVector(W.dE, -0.25);
  const c1 = diskP.clone().addScaledVector(n, 0.62).addScaledVector(sideN, 0.12).addScaledVector(W.dE, -0.1);
  const c2 = P0.clone().addScaledVector(n, 5).addScaledVector(sideN, 1.5).addScaledVector(W.dE, -2.5);
  const c3 = P0.clone().addScaledVector(n, 16).addScaledVector(sideN, 4).addScaledVector(W.dE, -9);
  const c4 = c3.clone().addScaledVector(n, 3).addScaledVector(W.dE, -2);
  const pos = hermite([K(82.2, c0), K(85.0, c1), K(86.6, c1.clone().addScaledVector(n, 0.25)), K(88.6, c2), K(90.6, c3), K(T, c4)], t);
  const lookA = hermite([K(82.2, diskP), K(86.6, diskP), K(88.6, P0), K(90.6, P0)], t);
  const look = lookA.clone().lerp(Ef, eio(lin(t, 89.6, 92.4)));
  lookCam(cam, pos, look, W.dE.clone().multiplyScalar(-1));
  // sonidos e imágenes que salen del disco
  W.notes.forEach((o, i) => {
    const t0 = 84.9 + i * 0.28; const f = lin(t, t0, t0 + 2.4);
    if (f <= 0 || f >= 1) return;
    o.visible = true;
    const a = i * 1.3 - 2.6;
    o.position.copy(diskP).addScaledVector(n, 0.1 + f * 0.9).addScaledVector(sideN, Math.cos(a) * f * 0.75).addScaledVector(W.dE, Math.sin(a) * f * 0.6 - f * 0.2);
    o.quaternion.copy(cam.quaternion); o.rotateY(Math.sin(t * 2 + i) * 0.5); o.rotateZ(Math.sin(t * 1.5 + i) * 0.3);
    o.scale.setScalar(0.26 * eback(lin(t, t0, t0 + 0.4)) * (1 - sm(lin(f, 0.75, 1))));
  });
  setSun(W, sideN.clone().add(n).add(W.dE.clone().multiplyScalar(-0.8)), P0, 3.5);
  return 'space';
}

// ------------------------------------------------------------------ línea de tiempo
const SC = [
  [0, 9.4, s1], [9.4, 23.75, s2], [23.75, 32.6, s3], [32.6, 47.82, s4], [47.82, 60.15, s5], [60.15, 71.0, s6], [71.0, 82.45, s7], [82.45, 1e9, s8],
];
const HALF = [0.35, 0.4, 0.4, 0.4, 0.45, 0.35, 0.45];
// devuelve [[fn, alpha], ...] (1 o 2 escenas a mezclar)
export function plan(t) {
  for (let i = 0; i < SC.length; i++) {
    const [a, b, fn] = SC[i];
    if (i < SC.length - 1) {
      const h = HALF[i];
      if (t >= b - h && t < b + h) return [[fn, 1], [SC[i + 1][2], sm((t - (b - h)) / (2 * h))]];
    }
    if (t >= a && t < b) return [[fn, 1]];
  }
  return [[SC[SC.length - 1][2], 1]];
}
export function applyScene(W, fn, t, T) {
  resetAll(W);
  const mode = fn(W, t, T);
  W.starMat.uniforms.time.value = t;
  W.stars.position.copy(W.camera.position);
  W.camera.updateProjectionMatrix();
  W.dots.commit();
  return mode;
}
