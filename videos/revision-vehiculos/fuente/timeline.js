// Sandoval Legal — "¿Te pueden revisar el vehículo sin motivo?"
// Deterministic timeline: window.renderFrame(t) paints the stage at time t (seconds).
(function(){
const $ = s => document.querySelector(s);
const clamp = (x,a=0,b=1)=>Math.max(a,Math.min(b,x));
const lerp = (a,b,u)=>a+(b-a)*u;
const eOut = u=>1-Math.pow(1-u,3);
const eInOut = u=>u<.5?4*u*u*u:1-Math.pow(-2*u+2,3)/2;
const eBack = u=>{const c1=1.70158,c3=c1+1;return 1+c3*Math.pow(u-1,3)+c1*Math.pow(u-1,2)};
const prog = (t,t0,d)=>clamp((t-t0)/d);

// ---------- ICONS (stroke, viewBox 64) ----------
const IC = {
 scale:`<path d="M32 8v44M20 55h24M24 52h16M9 17h46"/><circle cx="32" cy="10" r="2.5"/><path d="M9 17 3 33M9 17l6 16M55 17l-6 16M55 17l6 16"/><path d="M2 33h14a7 5 0 0 1-14 0zM48 33h14a7 5 0 0 1-14 0z"/>`,
 police:`<path d="M32 6 52 13v15c0 13-8.5 22-20 28C20.5 50 12 41 12 28V13z"/><path d="m32 19 3.5 7.2 7.9 1.1-5.7 5.6 1.3 7.8L32 37l-7 3.7 1.3-7.8-5.7-5.6 7.9-1.1z"/>`,
 military:`<path d="M12 34c0-13 9-21 20-21s20 8 20 21z"/><path d="M7 34h50"/><path d="M27 13c1-3 9-3 10 0"/><path d="m21 43 11 6 11-6M21 50l11 6 11-6"/>`,
 official:`<circle cx="32" cy="17" r="9"/><path d="M14 57c0-14 8-22 18-22s18 8 18 22"/><path d="m32 35-3 6 3 12 3-12z"/><path d="M26 35l6 6 6-6"/>`,
 force:`<path d="M32 4l5 14 13-7-5 14 15 3-13 8 9 12-15-3 1 15-10-11-10 11 1-15-15 3 9-12L4 28l15-3-5-14 13 7z"/>`,
 warn:`<path d="M32 7 60 55H4z"/><path d="M32 24v16"/><circle cx="32" cy="47" r="1.8" fill="#D6B270"/>`,
 car:`<path d="M6 42v-8l6-2 7-10h22l9 10 8 2v8z"/><circle cx="18" cy="43" r="5"/><circle cx="46" cy="43" r="5"/><path d="M21 22l-3 10h28l-7-10"/><path d="m35 26-4 6 5 3-4 6" stroke="#C4524A" stroke-width="3"/>`,
 person:`<circle cx="26" cy="17" r="9"/><path d="M8 57c0-14 8-22 18-22 6 0 10 2 13 6"/><rect x="38" y="38" width="20" height="20" rx="3"/><path d="M48 42v12M42 48h12" stroke="#C4524A" stroke-width="3"/>`,
 calm:`<path d="M8 22c6-5 10 5 16 0s10-5 16 0 10 5 16 0"/><path d="M8 34c6-5 10 5 16 0s10-5 16 0 10 5 16 0"/><path d="M8 46c6-5 10 5 16 0s10-5 16 0 10 5 16 0"/>`,
 wheel:`<circle cx="32" cy="32" r="24"/><circle cx="32" cy="32" r="6"/><path d="M8 30c8-3 16-4 24-4s16 1 24 4M28 37 17 53M36 37l11 16"/>`,
 ask:`<path d="M10 12h44a4 4 0 0 1 4 4v26a4 4 0 0 1-4 4H30l-12 10v-10h-8a4 4 0 0 1-4-4V16a4 4 0 0 1 4-4z"/><path d="M26 24a6 6 0 1 1 9 5c-2 1-3 2-3 5"/><circle cx="32" cy="39" r="1.6" fill="#D6B270"/>`,
 phone:`<rect x="18" y="6" width="28" height="52" rx="5"/><path d="M28 51h8"/><circle cx="32" cy="27" r="7" fill="#C4524A" stroke="#C4524A"/>`,
 check:`<path d="M16 33 27 44 49 20"/>`,
 cross:`<path d="M19 19l26 26M45 19 19 45"/>`,
 comment:`<path d="M8 12h48a4 4 0 0 1 4 4v24a4 4 0 0 1-4 4H26L14 56V44H8a4 4 0 0 1-4-4V16a4 4 0 0 1 4-4z"/><path d="M16 24h32M16 32h22"/>`,
 eye:`<path d="M4 32s10-16 28-16 28 16 28 16-10 16-28 16S4 32 4 32z"/><circle cx="32" cy="32" r="7"/>`,
 noentry:`<circle cx="32" cy="32" r="22"/><path d="M17 47 47 17"/>`,
};
const svg = (k,extra='')=>`<svg class="ico" viewBox="0 0 64 64" ${extra}>${IC[k]}</svg>`;

// ---------- BACKGROUNDS ----------
// x/y = object-position %, s = scale; br = brightness
const BGS = [
 {f:'04-luces-patrulla', t0:0,    t1:3.75, x0:30,x1:62, y0:50,y1:50, s0:1.12,s1:1.24, br:.85},
 {f:'01-parada-policial',t0:3.45, t1:7.85, x0:38,x1:52, y0:45,y1:45, s0:1.06,s1:1.16, br:.7},
 {f:'03-revision-vehiculo',t0:7.55,t1:25.6, x0:38,x1:62, y0:50,y1:50, s0:1.05,s1:1.25, br:.42, blur:1.5},
 {f:'07-mazo-justicia', t0:25.3, t1:32.95, x0:58,x1:70, y0:55,y1:55, s0:1.08,s1:1.2, br:.45},
 {f:'07b-mazo-escudo',  t0:32.6, t1:42.5, x0:30,x1:52, y0:50,y1:50, s0:1.04,s1:1.16, br:.36, blur:1},
 {f:'06-avenida-rd',    t0:42.2, t1:50.0, x0:50,x1:50, y0:40,y1:60, s0:1.3,s1:1.06, br:.5},
 {f:'02-conductor-volante',t0:49.75,t1:53.75, x0:28,x1:45, y0:50,y1:50, s0:1.06,s1:1.16, br:.5},
 {f:'05-celular-grabando',t0:53.45,t1:59.85, x0:42,x1:52, y0:45,y1:50, s0:1.08,s1:1.2, br:.5},
 {f:'06b-agentes-avenida',t0:59.5,t1:64, x0:35,x1:55, y0:50,y1:50, s0:1.1,s1:1.2, br:.32, blur:3},
];
const FADE = .45;
const bgWrap = $('#bgs');
BGS.forEach(b=>{const d=document.createElement('div');d.className='bg';d.innerHTML=`<img src="assets/${b.f}.jpg">`;bgWrap.appendChild(d);b.el=d;b.img=d.querySelector('img');});

// ---------- SCENES ----------
const content = $('#content');
const SC = {};
function scene(id,t0,t1){const d=document.createElement('div');d.className='scene';d.id=id;content.appendChild(d);SC[id]={el:d,t0,t1};return d;}
const ANIMS=[];
function el(parent,html,style,t0,type='up',d=.55,out=null,od=.35,cls=''){
  const e=document.createElement('div');e.className='el '+cls;e.innerHTML=html;e.style.cssText=style;parent.appendChild(e);
  ANIMS.push({e,t0,type,d,out,od});return e;
}

// ===== SCENE 1 — GANCHO (0 – 7.55)
const s1=scene('s1',0,7.55);
el(s1,`<div class="cinzel gold" style="font-size:30px;letter-spacing:.3em">CONTENIDO LEGAL · RD</div>`,'left:0;right:0;top:560px;text-align:center',.25,'fade',.6);
el(s1,`<div class="title" style="font-size:132px;line-height:1.02">¿REVISIÓN<br>SIN MOTIVO?</div>`,'left:0;right:0;top:620px;text-align:center',.35,'blur',.7);
el(s1,`<div style="width:520px;height:3px;margin:0 auto;background:linear-gradient(90deg,transparent,#D6B270,transparent)"></div>`,'left:0;right:0;top:925px',.9,'wipe',.6);
const prision = el(s1,`<div class="title gold" style="font-size:200px;letter-spacing:.02em;text-shadow:0 0 50px rgba(214,178,112,.55),0 8px 30px rgba(0,0,0,.8)">PRISIÓN</div>`,'left:0;right:0;top:985px;text-align:center',6.74,'slam',.22);
el(s1,`<div style="font-family:Mont;font-weight:600;font-size:38px;color:#F0E8D6">…para el agente que lo haga sin base legal</div>`,'left:0;right:0;top:1250px;text-align:center',7.0,'up',.4);

// ===== SCENE 2 — LA NORMA (7.55 – 25.3)
const s2=scene('s2',7.55,25.3);
el(s2,`<div class="card" style="width:960px;padding:34px 44px 30px;">
  <div style="display:flex;align-items:center;gap:26px">
    <div style="width:92px;height:92px;flex:none">${svg('scale')}</div>
    <div><div class="cinzel gold" style="font-size:66px;line-height:1">ARTÍCULO 276</div>
    <div style="font-family:Mont;font-weight:600;font-size:24px;color:#B9B9B9;letter-spacing:.2em;margin-top:6px">CÓDIGO PENAL · LEY 74-25</div></div>
  </div>
  <div style="height:2px;background:linear-gradient(90deg,#D6B270,rgba(214,178,112,0));margin:22px 0 18px"></div>
  <div class="quote" style="font-size:48px;line-height:1.15">“Revisión injustificada de vehículos de motor”</div>
  <div class="src" style="margin-top:16px">Fuente: Ley núm. 74-25, Código Penal de la República Dominicana</div>
 </div>`,'left:60px;top:345px',7.7,'up',.6);
// timeline
const tl = el(s2,`<div style="position:relative;width:960px;height:170px">
   <div style="position:absolute;left:70px;right:70px;top:38px;height:3px;background:rgba(185,185,185,.3)"></div>
   <div id="tlLine" style="position:absolute;left:70px;top:37px;height:5px;width:0;background:linear-gradient(90deg,#B9B9B9,#D6B270);box-shadow:0 0 14px rgba(214,178,112,.7)"></div>
   <div id="tlN1" style="position:absolute;left:0;top:0;width:440px;text-align:left">
     <div style="width:38px;height:38px;margin:20px 0 0 51px;border-radius:50%;background:#0B1526;border:4px solid #B9B9B9"></div>
     <div style="font-family:Cinzel;font-weight:700;font-size:26px;color:#B9B9B9;letter-spacing:.14em;margin-top:14px">PROMULGADA</div>
     <div style="font-family:Mont;font-weight:700;font-size:34px;color:#F0E8D6">3 de agosto de 2025</div></div>
   <div id="tlN2" style="position:absolute;right:0;top:0;width:300px;text-align:right">
     <div style="width:38px;height:38px;margin:20px 51px 0 auto;border-radius:50%;background:#D6B270;border:4px solid #F0E8D6;box-shadow:0 0 20px rgba(214,178,112,.9)"></div>
     <div style="font-family:Cinzel;font-weight:700;font-size:26px;color:#D6B270;letter-spacing:.14em;margin-top:14px">VIGENTE</div>
     <div style="font-family:Mont;font-weight:700;font-size:34px;color:#F0E8D6">agosto de 2026</div></div>
 </div>`,'left:60px;top:800px',10.3,'fade',.3);
el(s2,`<div class="cinzel gold" style="font-size:30px;letter-spacing:.3em">¿A QUIÉN APLICA?</div>`,'left:0;right:0;top:1010px;text-align:center',16.7,'up',.4);
[['police','POLICÍA',17.32],['military','MILITAR',18.22],['official','FUNCIONARIO',19.02]].forEach((a,i)=>{
  el(s2,`<div class="icirc" style="width:168px;height:168px;margin:0 auto"><div style="width:96px;height:96px">${svg(a[0])}</div></div>
    <div class="lbl" style="font-size:32px;margin-top:16px">${a[1]}</div>`,`left:${60+i*320}px;width:320px;top:1065px`,a[2],'pop',.45);
});
el(s2,`<div class="stamp" style="width:430px;font-size:46px;transform:rotate(-6deg)">FUERA<br>DE LA LEY</div>`,'left:75px;top:1380px',21.26,'stamp',.2);
el(s2,`<div class="stamp" style="width:430px;font-size:46px;transform:rotate(5deg)">SIN CAUSA<br>PROBABLE</div>`,'left:575px;top:1380px',23.56,'stamp',.2);

// ===== SCENE 3 — LA PENA (25.3 – 42.2)
const s3=scene('s3',25.3,42.2);
const A_OUT=32.45;
el(s3,`<div class="title" style="font-size:100px">¿LA SANCIÓN?</div>`,'left:0;right:0;top:350px;text-align:center',25.35,'blur',.55,A_OUT,.35);
el(s3,`<div class="card" style="width:960px;height:330px;padding:28px 30px">
   <div class="cinzel" style="font-size:28px;color:#B9B9B9;letter-spacing:.24em;text-align:center">PRISIÓN MENOR</div>
   <div style="display:flex;align-items:center;justify-content:center;gap:30px;margin-top:6px">
     <div style="text-align:center"><div id="cnt15" class="title gold" style="font-size:170px;line-height:1">0</div><div class="cinzel" style="font-size:42px">DÍAS</div></div>
     <div id="arrow" style="font-family:Mont;font-weight:800;font-size:110px;color:#B9B9B9;opacity:0">→</div>
     <div id="oneyear" style="text-align:center;opacity:0"><div class="title gold" style="font-size:170px;line-height:1">1</div><div class="cinzel" style="font-size:42px">AÑO</div></div>
   </div></div>`,'left:60px;top:540px',26.6,'up',.45,A_OUT,.35);
el(s3,`<div style="font-family:Mont;font-weight:600;font-size:36px;color:#F0E8D6;text-align:center">de prisión menor</div>`,'left:0;right:0;top:890px',28.4,'up',.35,A_OUT,.35);
el(s3,`<div class="card" style="width:960px;padding:26px 30px 30px;text-align:center">
   <div class="cinzel gold" style="font-size:46px;letter-spacing:.3em">MULTA</div>
   <div id="multaN" class="title" style="font-size:150px;line-height:1.05;opacity:0">1 a 2</div>
   <div id="multaT" style="font-family:Mont;font-weight:700;font-size:38px;color:#F0E8D6;opacity:0">salarios mínimos del sector público</div></div>`,'left:60px;top:990px',29.22,'up',.45,A_OUT,.35);
// part B
el(s3,`<div class="title gold" style="font-size:86px">CON AGRAVANTES</div>`,'left:0;right:0;top:350px;text-align:center',32.6,'blur',.5);
[['force','Fuerza<br>injustificada',33.0],['warn','Intimidación',34.48],['car','Daño al<br>vehículo',35.6],['person','Daño<br>personal',36.52]].forEach((a,i)=>{
  el(s3,`<div class="icirc" style="width:150px;height:150px;margin:0 auto"><div style="width:84px;height:84px">${svg(a[0])}</div></div>
   <div style="font-family:Mont;font-weight:700;font-size:28px;line-height:1.15;text-align:center;margin-top:14px;color:#F0E8D6">${a[1]}</div>`,`left:${60+i*240}px;width:240px;top:480px`,a[2],'pop',.45);
});
el(s3,`<div style="display:flex;align-items:center;justify-content:center;gap:16px"><div class="cinzel gold" style="font-size:44px;letter-spacing:.2em">LA PENA SUBE</div><div style="font-family:Mont;font-weight:800;font-size:54px;color:#D6B270">↑</div></div>`,'left:0;right:0;top:790px;text-align:center',37.7,'up',.35);
function barGroup(top,title,rows,t0){
  let h=`<div style="width:960px"><div class="cinzel" style="font-size:30px;color:#B9B9B9;letter-spacing:.2em;margin-bottom:12px">${title}</div>`;
  rows.forEach((r,i)=>{h+=`<div style="font-family:Mont;font-weight:600;font-size:28px;color:#F0E8D6;margin:${i?14:0}px 0 8px">${r.l}</div>
   <div style="position:relative;height:64px;width:960px"><div class="bartrack" style="left:0;right:0;top:0"></div>
   <div class="barfill" data-w="${r.w}" data-t0="${r.t}" style="background:${r.c};box-shadow:${r.g||'none'}"></div>
   <div class="barv" data-t0="${r.t}" style="position:absolute;left:24px;top:0;bottom:0;display:flex;align-items:center;font-family:Mont;font-weight:800;font-size:32px;color:${r.tc};opacity:0">${r.v}</div></div>`;});
  h+='</div>';
  return el(s3,h,`left:60px;top:${top}px`,t0,'up',.4);
}
barGroup(890,'PRISIÓN',[
  {l:'Revisión injustificada',v:'hasta 1 año',w:.5,t:38.0,c:'linear-gradient(90deg,#8f8f8f,#B9B9B9)',tc:'#0B1526'},
  {l:'Con agravantes',v:'1 a 2 años',w:1,t:38.4,c:'linear-gradient(90deg,#B8924A,#D6B270)',g:'0 0 24px rgba(214,178,112,.55)',tc:'#0B1526'}],37.85);
barGroup(1225,'MULTA · SALARIOS MÍNIMOS',[
  {l:'Revisión injustificada',v:'1 a 2',w:2/6,t:40.2,c:'linear-gradient(90deg,#8f8f8f,#B9B9B9)',tc:'#0B1526'},
  {l:'Con agravantes',v:'3 a 6 salarios',w:1,t:40.6,c:'linear-gradient(90deg,#B8924A,#D6B270)',g:'0 0 24px rgba(214,178,112,.55)',tc:'#0B1526'}],40.0);

// ===== SCENE 4 — ACLARACIÓN (42.2 – 49.75)
const s4=scene('s4',42.2,49.75);
el(s4,`<div style="display:flex;align-items:center;justify-content:center;gap:22px"><div style="width:96px;height:96px">${svg('eye')}</div><div class="title gold" style="font-size:120px;line-height:1">OJO</div></div>`,'left:0;right:0;top:340px',42.38,'slam',.22);
el(s4,`<div class="title" style="font-family:Playfair;font-weight:700;font-size:56px;line-height:1.18">Esto <span class="gold">NO</span> significa que<br>nunca te puedan revisar</div>`,'left:0;right:0;top:500px;text-align:center',43.0,'up',.5);
function panel(left,ok,t0){
  const c= ok?'#D6B270':'#C4524A';
  return el(s4,`<div style="width:465px;height:390px;border:2.5px solid ${c};border-radius:8px;background:rgba(11,21,38,.88);padding:28px 26px;text-align:center;box-shadow:0 18px 50px rgba(0,0,0,.5)">
    <div style="width:110px;height:110px;margin:0 auto;border-radius:50%;border:3px solid ${c};display:flex;align-items:center;justify-content:center"><div style="width:76px;height:76px">${svg(ok?'check':'cross',`style="stroke:${c};stroke-width:6"`)}</div></div>
    <div class="cinzel" style="font-size:36px;line-height:1.1;color:${c};margin-top:20px">${ok?'REVISIÓN<br>LEGAL':'REVISIÓN<br>INJUSTIFICADA'}</div>
    <div style="font-family:Mont;font-weight:600;font-size:29px;line-height:1.25;color:#F0E8D6;margin-top:16px">${ok?'La ley la autoriza<br>o hay causa probable':'Sin base legal<br>ni causa probable'}</div></div>`,`left:${left}px;top:680px`,t0,ok?'left':'right',.5);
}
const pOK=panel(60,true,45.9); panel(555,false,46.75);
const mapEl = el(s4,`<div style="position:relative;width:620px;height:${Math.round(620*MAP.h/MAP.w)}px;margin:0 auto">
   <svg viewBox="-10 -10 ${MAP.w+20} ${MAP.h+20}" style="width:100%;height:100%;overflow:visible"><path id="mapPath" d="${MAP.d}" fill="rgba(214,178,112,0)" stroke="#D6B270" stroke-width="3.2" stroke-linejoin="round" style="filter:drop-shadow(0 0 10px rgba(214,178,112,.8))"/></svg></div>
   <div class="cinzel gold" id="mapTxt" style="font-size:44px;text-align:center;margin-top:6px;opacity:0;letter-spacing:.12em">APLICA EN TODO EL PAÍS</div>`,'left:0;right:0;top:1120px',48.2,'fade',.3);

// ===== SCENE 5 — QUÉ HACER (49.75 – 59.5)
const s5=scene('s5',49.75,59.5);
el(s5,`<div class="title" style="font-size:100px">¿QUÉ HACER?</div>`,'left:0;right:0;top:340px;text-align:center',49.8,'blur',.5);
[['calm','Mantén la calma',49.98],['wheel','No te resistas',51.08],['ask','Pregunta el motivo',52.12]].forEach((a,i)=>{
  el(s5,`<div style="display:flex;align-items:center;gap:26px;width:960px;height:120px;padding:0 28px;background:rgba(11,21,38,.82);border-left:5px solid #D6B270;border-radius:4px">
     <div class="title gold" style="font-size:66px;width:50px;text-align:center">${i+1}</div>
     <div style="width:76px;height:76px;flex:none">${svg(a[0])}</div>
     <div style="font-family:Mont;font-weight:800;font-size:50px;color:#F0E8D6">${a[1]}</div></div>`,`left:60px;top:${500+i*150}px`,a[2],'left',.45);
});
el(s5,`<div class="card" style="width:960px;padding:30px 40px 28px">
   <div style="display:flex;align-items:center;gap:24px">
    <div style="width:88px;height:88px;flex:none">${svg('phone')}</div>
    <div><div class="cinzel gold" style="font-size:62px;line-height:1">ARTÍCULO 275</div>
    <div id="rec" style="font-family:Mont;font-weight:800;font-size:24px;color:#C4524A;letter-spacing:.25em;margin-top:6px">● REC</div></div></div>
   <div style="height:2px;background:linear-gradient(90deg,#D6B270,rgba(214,178,112,0));margin:20px 0 16px"></div>
   <div class="quote" style="font-size:46px;line-height:1.15">“Derecho a grabar el arresto o registro”</div>
   <div class="src" style="margin-top:14px">Fuente: Ley núm. 74-25, Código Penal de la República Dominicana</div></div>`,'left:60px;top:1000px',53.55,'up',.55);
el(s5,`<div style="display:inline-flex;align-items:center;gap:16px;padding:16px 34px;border:2px solid #D6B270;border-radius:50px;background:rgba(11,21,38,.85)"><div style="width:44px;height:44px">${svg('noentry')}</div><div style="font-family:Mont;font-weight:700;font-size:36px;color:#F0E8D6">Sin interferir con el agente</div></div>`,'left:0;right:0;top:1440px;text-align:center',57.84,'up',.4);

// ===== SCENE 6 — ENCUESTA (59.5 – 63.5)
const s6=scene('s6',59.5,64);
el(s6,`<div class="card" style="width:960px;height:860px"></div>`,'left:60px;top:500px',59.55,'up',.45);
el(s6,`<div style="display:flex;align-items:center;justify-content:center;gap:16px"><div style="width:52px;height:52px">${svg('scale')}</div><div class="cinzel gold" style="font-size:38px;letter-spacing:.3em">ENCUESTA</div></div>`,'left:0;right:0;top:550px',59.6,'fade',.4);
el(s6,`<div class="title" style="font-family:Playfair;font-weight:700;font-size:60px;line-height:1.15">¿Te han revisado el vehículo<br>sin explicación?</div>`,'left:80px;right:80px;top:650px;text-align:center',59.7,'up',.45);
el(s6,`<div class="optrow" style="top:0"><div class="optfill" id="opt1" style="width:0"></div><div class="optlbl">SÍ, me ha pasado</div><div class="optpct" id="pct1">…</div></div>`,'left:60px;right:60px;top:900px;height:110px',60.45,'left',.4);
el(s6,`<div class="optrow" style="top:0"><div class="optfill" id="opt2" style="width:0"></div><div class="optlbl">NO, nunca</div><div class="optpct" id="pct2">…</div></div>`,'left:60px;right:60px;top:1040px;height:110px',60.75,'left',.4);
el(s6,`<div style="display:flex;align-items:center;justify-content:center;gap:18px"><div style="width:62px;height:62px">${svg('comment')}</div><div style="font-family:Mont;font-weight:800;font-size:44px;color:#D6B270">Cuéntalo en los comentarios</div></div>`,'left:0;right:0;top:1220px',62.06,'pop',.45);

// ---------- SUBTITLES ----------
const SUBS = window.SUBS; const subline=$('#subline'); let curChunk=-1;
function renderSubs(t){
  let idx=-1;
  for(let i=0;i<SUBS.length;i++){const c=SUBS[i];const s=c[0].s-.06;const nx=i+1<SUBS.length?SUBS[i+1][0].s-.06:1e9;const end=Math.min(nx,c[c.length-1].e+.7);if(t>=s&&t<end){idx=i;break;}}
  if(t>63.15) idx=-1;
  if(idx!==curChunk){curChunk=idx;subline.innerHTML=idx<0?'':SUBS[idx].map(w=>`<span>${w.w}</span>`).join(' ');}
  if(idx<0){subline.style.opacity=0;return;}
  const c=SUBS[idx];const sp=subline.children;
  const u=eOut(prog(t,c[0].s-.06,.14));subline.style.opacity=u;subline.style.transform=`translateY(${(1-u)*14}px)`;
  for(let k=0;k<c.length;k++){const w=c[k];const nx=k+1<c.length?c[k+1].s:w.e+.25;const on=t>=w.s-.02&&t<Math.max(nx,w.e);
    sp[k].className=on?'on':'';sp[k].style.transform=on?'scale(1.04)':'none';}
}

// ---------- GRAIN ----------
const grainEl=$('#grain');const grains=[];
for(let g=0;g<4;g++){const c=document.createElement('canvas');c.width=c.height=256;const x=c.getContext('2d');const im=x.createImageData(256,256);
  let seed=1234+g*977;const rnd=()=>{seed=(seed*16807)%2147483647;return seed/2147483647;};
  for(let i=0;i<im.data.length;i+=4){const v=Math.floor(rnd()*255);im.data[i]=im.data[i+1]=im.data[i+2]=v;im.data[i+3]=255;}
  x.putImageData(im,0,0);grains.push(c.toDataURL());}

// ---------- TRANSITIONS / FX ----------
const FLASHES=[3.6,7.55,25.3,32.5,42.2,49.75,53.55,59.5];
const SHAKES=[[6.74,14],[21.26,7],[23.56,7],[42.38,6]];
function hash(n){const s=Math.sin(n*127.1)*43758.5453;return s-Math.floor(s);}

window.renderFrame = function(t){
  const frame=Math.round(t*30);
  // backgrounds
  BGS.forEach(b=>{
    const a=Math.min(prog(t,b.t0,FADE), 1-prog(t,b.t1-FADE,FADE));
    b.el.style.opacity=a>0?eInOut(clamp(a)):0;
    if(a<=0) return;
    const u=clamp((t-b.t0)/(b.t1-b.t0));const ue=eInOut(u)*.3+u*.7;
    b.img.style.objectPosition=`${lerp(b.x0,b.x1,ue)}% ${lerp(b.y0,b.y1,ue)}%`;
    b.img.style.transform=`scale(${lerp(b.s0,b.s1,ue)})`;
    b.img.style.filter=`brightness(${b.br}) saturate(.78) contrast(1.08)${b.blur?` blur(${b.blur}px)`:''}`;
  });
  // police light flicker in hook
  const pl=$('#police'); const pa=1-prog(t,3.2,.6);
  if(pa>0){const r=.5+.5*Math.sin(t*Math.PI*2*1.4),bl=1-r;
    pl.style.background=`radial-gradient(ellipse 60% 40% at 10% 30%,rgba(255,40,60,${.32*r*pa}),transparent 70%),radial-gradient(ellipse 60% 40% at 90% 30%,rgba(40,90,255,${.36*bl*pa}),transparent 70%)`;}
  else pl.style.background='none';
  // scenes
  for(const k in SC){const s=SC[k];const a=Math.min(prog(t,s.t0,.3),1-prog(t,s.t1-.25,.25));s.el.style.opacity=clamp(a);s.el.style.display=a>0?'block':'none';}
  // element anims
  ANIMS.forEach(A=>{
    let p=prog(t,A.t0,A.d);let o=1,tr='',f='';
    if(t<A.t0){A.e.style.opacity=0;return;}
    const pe=eOut(p);
    switch(A.type){
      case 'up': o=pe;tr=`translateY(${(1-pe)*50}px)`;break;
      case 'fade': o=pe;break;
      case 'blur': o=pe;f=`blur(${(1-pe)*14}px)`;tr=`scale(${1+(1-pe)*.08})`;break;
      case 'pop': o=clamp(p*2.5);tr=`scale(${.55+.45*eBack(p)})`;break;
      case 'slam': o=clamp(p*3);tr=`scale(${1+(1-pe)*1.4})`;break;
      case 'stamp': o=clamp(p*3);tr=`scale(${1+(1-pe)*1.8})`;break;
      case 'left': o=pe;tr=`translateX(${(1-pe)*-90}px)`;break;
      case 'right': o=pe;tr=`translateX(${(1-pe)*90}px)`;break;
      case 'wipe': o=1;A.e.style.clipPath=`inset(0 ${(1-pe)*50}% 0 ${(1-pe)*50}%)`;break;
    }
    if(A.out!==null){const q=eOut(prog(t,A.out,A.od));o*=1-q;tr+=` translateY(${-q*40}px)`;}
    A.e.style.opacity=o;A.e.style.transform=tr;A.e.style.filter=f;
  });
  // timeline
  $('#tlLine').style.width=(820*eInOut(prog(t,11.9,.9)))+'px';
  $('#tlN1').style.opacity=1; $('#tlN2').style.opacity=eOut(prog(t,12.46,.4));
  $('#tlN2').style.transform=`translateY(${(1-eOut(prog(t,12.46,.4)))*20}px)`;
  // counter 15 días
  $('#cnt15').textContent=Math.round(15*eOut(prog(t,26.74,.55)));
  $('#arrow').style.opacity=eOut(prog(t,27.55,.3)); $('#arrow').style.transform=`translateX(${(1-eOut(prog(t,27.55,.3)))*-40}px)`;
  const oy=prog(t,27.88,.3); $('#oneyear').style.opacity=clamp(oy*3); $('#oneyear').style.transform=`scale(${1+(1-eOut(oy))*.8})`;
  const mn=prog(t,29.72,.35); $('#multaN').style.opacity=clamp(mn*3); $('#multaN').style.transform=`scale(${.6+.4*eBack(mn)})`;
  $('#multaT').style.opacity=eOut(prog(t,30.42,.4));
  // bars
  document.querySelectorAll('.barfill').forEach(b=>{const p=eInOut(prog(t,+b.dataset.t0,.9));b.style.width=(p*100*b.dataset.w)+'%';});
  document.querySelectorAll('.barv').forEach(b=>{b.style.opacity=eOut(prog(t,+b.dataset.t0+.55,.3));});
  // panel highlight
  const hl=Math.max(0,Math.sin(Math.PI*prog(t,49.0,.7)));pOK.style.filter=hl?`drop-shadow(0 0 ${hl*30}px rgba(214,178,112,.9))`:'';
  // map draw
  const mp=$('#mapPath'); if(!mp._len){mp._len=mp.getTotalLength();mp.style.strokeDasharray=mp._len;}
  const md=eInOut(prog(t,48.25,1.1)); mp.style.strokeDashoffset=mp._len*(1-md); mp.setAttribute('fill',`rgba(214,178,112,${.28*eOut(prog(t,48.9,.6))})`);
  $('#mapTxt').style.opacity=eOut(prog(t,48.6,.4));
  // REC blink
  $('#rec').style.opacity=(Math.floor(t*2.2)%2)?.25:1;
  // poll
  const f1=eInOut(prog(t,61.0,1.4)),f2=eInOut(prog(t,61.25,1.3));
  const wob1=t>62.4?Math.sin((t-62.4)*5)*1.2:0, wob2=t>62.55?Math.sin((t-62.55)*5+1)*1.0:0;
  $('#opt1').style.width=(f1*44+wob1)+'%'; $('#opt2').style.width=(f2*27+wob2)+'%';
  const dots=['·','··','···'][Math.floor(t*3)%3]; $('#pct1').textContent=t>60.9?'?':'…'; $('#pct2').textContent=t>61.1?'?':'…';
  $('#pct1').style.opacity=$('#pct2').style.opacity=.55+.45*Math.abs(Math.sin(t*3));
  // subtitles
  renderSubs(t);
  // grain
  grainEl.style.backgroundImage=`url(${grains[frame%4]})`;
  grainEl.style.backgroundPosition=`${Math.floor(hash(frame)*256)}px ${Math.floor(hash(frame+7)*256)}px`;
  // flash
  let fl=0;FLASHES.forEach(T=>{fl+=Math.exp(-Math.pow((t-T)/.09,2))*.28;});$('#flash').style.opacity=fl;
  // shake
  let sx=0,sy=0;SHAKES.forEach(([T,amp])=>{const d=t-T;if(d>=0&&d<.4){const k=amp*Math.exp(-d*9);sx+=(hash(frame*3.1)-.5)*2*k;sy+=(hash(frame*5.7)-.5)*2*k;}});
  content.style.transform=`translate(${sx}px,${sy}px)`;
};
window.READY = Promise.all([document.fonts.ready, ...[...document.images].map(i=>i.decode().catch(()=>{}))]);
})();
