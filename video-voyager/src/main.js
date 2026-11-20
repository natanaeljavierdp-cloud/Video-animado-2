import * as THREE from 'three';
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass } from 'three/addons/postprocessing/RenderPass.js';
import { UnrealBloomPass } from 'three/addons/postprocessing/UnrealBloomPass.js';
import { OutputPass } from 'three/addons/postprocessing/OutputPass.js';
import { ShaderPass } from 'three/addons/postprocessing/ShaderPass.js';
import { TTFLoader } from 'three/addons/loaders/TTFLoader.js';
import { Font } from 'three/addons/loaders/FontLoader.js';
import { W as WW, H, updateLabels, FONT } from './lib.js';
import { buildWorld, plan, applyScene } from './scenes.js';
import { buildChunks, drawSubs } from './subs.js';

const ff = new FontFace('Nunito', 'url(/node_modules/@fontsource/nunito/files/nunito-latin-900-normal.woff2)', { weight: '900' });
document.fonts.add(await ff.load());
const ttf = await new Promise((res, rej) => new TTFLoader().load('/node_modules/@fontsource/nunito/files/nunito-latin-900-normal.woff', res, undefined, rej));
const font = new Font(ttf);
const land = await (await fetch('/data/land.json')).json();
const words = await (await fetch('/words.json')).json();
const T = parseFloat(new URLSearchParams(location.search).get('T') || '93.65');

const glc = document.createElement('canvas'); glc.width = WW; glc.height = H;
const renderer = new THREE.WebGLRenderer({ canvas: glc, antialias: false, preserveDrawingBuffer: true, powerPreference: 'high-performance' });
renderer.setPixelRatio(1); renderer.setSize(WW, H, false);
renderer.shadowMap.enabled = true; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
renderer.toneMapping = THREE.NoToneMapping;
const scene = new THREE.Scene();
const camera = new THREE.PerspectiveCamera(40, WW / H, 0.03, 4000);
const rt = new THREE.WebGLRenderTarget(WW, H, { type: THREE.HalfFloatType, samples: 4 });
const composer = new EffectComposer(renderer, rt);
composer.addPass(new RenderPass(scene, camera));
const bloom = new UnrealBloomPass(new THREE.Vector2(WW, H), 0.6, 0.45, 1.0);
composer.addPass(bloom);
composer.addPass(new OutputPass());
const grain = new ShaderPass({
  uniforms: { tDiffuse: { value: null }, time: { value: 0 }, amt: { value: 1 } },
  vertexShader: 'varying vec2 vUv; void main(){ vUv = uv; gl_Position = projectionMatrix*modelViewMatrix*vec4(position,1.0);} ',
  fragmentShader: `uniform sampler2D tDiffuse; uniform float time; uniform float amt; varying vec2 vUv;
  float h(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7)))*43758.5453); }
  float n(vec2 p){ vec2 i=floor(p), f=fract(p); f=f*f*(3.0-2.0*f); return mix(mix(h(i),h(i+vec2(1,0)),f.x), mix(h(i+vec2(0,1)),h(i+vec2(1,1)),f.x), f.y); }
  float fbm(vec2 p){ float s=0.0, a=0.5; for(int i=0;i<5;i++){ s+=a*n(p); p*=2.03; a*=0.5; } return s; }
  void main(){
    vec4 c = texture2D(tDiffuse, vUv);
    vec2 px = vUv*vec2(1080.0,1920.0);
    float paper = fbm(px*0.012) * 0.6 + fbm(px*0.09 + 7.0) * 0.4;
    float fib = n(vec2(px.x*0.6, px.y*0.03)) * 0.5 + n(vec2(px.x*0.03, px.y*0.6)) * 0.5;
    float g = h(px + fract(time*7.31)*311.0) - 0.5;
    vec3 col = c.rgb;
    float l = dot(col, vec3(0.299,0.587,0.114));
    col = mix(col, vec3(l), 0.06);                       // colores algo apagados
    col *= 0.955 + 0.075*paper + 0.025*fib;              // textura de papel
    col += g * 0.045 * amt;                              // grano
    col = mix(col, col*vec3(1.02,1.0,0.96), 0.5);        // tono cálido
    vec2 q = vUv - 0.5; col *= 1.0 - dot(q,q)*0.28;      // viñeta suave
    gl_FragColor = vec4(col, 1.0);
  }`,
});
composer.addPass(grain);

const world = buildWorld(scene, camera, { land, font });
const chunks = buildChunks(words);
window.__chunks = chunks;
const out = document.getElementById('out');
const ctx = out.getContext('2d');

function renderAt(t) {
  const pl = plan(t);
  let modeA = 'space', best = -1;
  pl.forEach(([fn, a], i) => {
    const mode = applyScene(world, fn, t, T);
    updateLabels(camera);
    grain.uniforms.time.value = t;
    composer.render();
    ctx.globalAlpha = a;
    ctx.drawImage(glc, 0, 0);
    const wgt = i === 0 ? 1 - (pl[1] ? pl[1][1] : 0) : a;
    if (wgt > best) { best = wgt; modeA = mode; }
  });
  ctx.globalAlpha = 1;
  drawSubs(ctx, chunks, t, modeA, FONT);
}
window.renderFrame = (t, q = 0.93) => { renderAt(t); return out.toDataURL('image/jpeg', q); };
window.renderOnly = (t) => { renderAt(t); return true; };
window.ready = true;
window.pick = (t, x, y) => {
  renderAt(t);
  const rc = new THREE.Raycaster(); rc.setFromCamera(new THREE.Vector2(x, y), camera);
  return rc.intersectObjects(scene.children, true).filter((h) => h.object.visible && !h.object.userData.isOutline).slice(0, 4)
    .map((h) => `${h.object.geometry.type} ${JSON.stringify(h.object.geometry.parameters || {}).slice(0, 120)} col=${h.object.material.color ? h.object.material.color.getHexString() : '-'} pos=${h.object.position.toArray().map((v) => v.toFixed(2))}`);
};
