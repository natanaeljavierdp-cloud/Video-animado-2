const topo=require(process.argv[2]+'/world-atlas-2.0.2/countries-50m.json');
const tc=require(process.argv[2]+'/topojson-client-3.1.0');
const f=tc.feature(topo,topo.objects.countries).features.find(x=>x.id==='724');
const polys=(f.geometry.type==='Polygon'?[f.geometry.coordinates]:f.geometry.coordinates).map(p=>p[0]).filter(r=>r[0][1]>34);
console.log(JSON.stringify(polys.map(r=>r.map(([x,y])=>[+x.toFixed(3),+y.toFixed(3)]))));
