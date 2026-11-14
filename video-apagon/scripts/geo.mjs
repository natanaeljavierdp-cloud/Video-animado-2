import fs from 'fs'; import * as topo from 'topojson-client';
const us=JSON.parse(fs.readFileSync('node_modules/us-atlas/states-albers-10m.json'));
const usF=topo.feature(us,us.objects.nation);
const st=topo.mesh(us,us.objects.states,(a,b)=>a!==b);
const w=JSON.parse(fs.readFileSync('node_modules/world-atlas/countries-10m.json'));
const cs=topo.feature(w,w.objects.countries).features;
const dr=cs.find(f=>f.properties.name.startsWith('Dominican'));
const ht=cs.find(f=>f.properties.name==='Haiti');
function polys(g){return g.type==='Polygon'?[g.coordinates]:g.type==='MultiPolygon'?g.coordinates:[]}
function proj(c){const k=Math.cos(19*Math.PI/180);return [c[0]*k,-c[1]]}
const usPolys=polys(usF.geometry?usF.geometry:usF.features[0].geometry).map(p=>p.map(r=>r.map(([x,y])=>[+x.toFixed(1),+y.toFixed(1)])));
const stLines=st.coordinates.map(l=>l.map(([x,y])=>[+x.toFixed(1),+y.toFixed(1)]));
const P=f=>polys(f.geometry).map(p=>p.map(r=>r.map(c=>proj(c).map(v=>+v.toFixed(4)))));
fs.writeFileSync('data/geo.json',JSON.stringify({us:usPolys,usStates:stLines,dr:P(dr),haiti:P(ht)}));
console.log(dr.properties.name, ht.properties.name, fs.statSync('data/geo.json').size);
