// Genera assets/us-states.json (rutas SVG de los estados, proyección Albers 975x610)
import fs from 'node:fs'; import {createRequire} from 'node:module';
const req=createRequire(process.argv[2]+'/');
const topo=req('us-atlas/states-albers-10m.json'); const {feature}=req('topojson-client');
const fc=feature(topo,topo.objects.states);
const ring=r=>'M'+r.map(p=>p[0].toFixed(1)+','+p[1].toFixed(1)).join('L')+'Z';
const out=fc.features.map(f=>{const polys=f.geometry.type==='Polygon'?[f.geometry.coordinates]:f.geometry.coordinates;
 let sx=0,n=0,sy=0; polys.forEach(p=>p[0].forEach(c=>{sx+=c[0];sy+=c[1];n++}));
 return {name:f.properties.name,d:polys.map(p=>p.map(ring).join('')).join(''),cx:sx/n,cy:sy/n}});
fs.writeFileSync('assets/us-states.json',JSON.stringify(out)); console.log(out.length,'estados');
