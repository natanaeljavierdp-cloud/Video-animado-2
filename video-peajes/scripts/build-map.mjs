// Proyecta el contorno de la isla (RD + Haití) y las autopistas a coordenadas SVG.
import fs from "node:fs";
import { geoMercator, geoPath } from "d3-geo";
import { feature } from "topojson-client";
const topo = JSON.parse(fs.readFileSync("node_modules/world-atlas/countries-10m.json", "utf8"));
const countries = feature(topo, topo.objects.countries).features;
const dr = countries.find((f) => f.properties.name === "Dominican Rep.");
const ht = countries.find((f) => f.properties.name === "Haiti");
const W = 1000, H = 760;
const proj = geoMercator().fitExtent([[40, 40], [W - 40, H - 40]], dr);
const path = geoPath(proj);
const P = (pts) => pts.map(([lon, lat]) => proj([lon, lat]).map((v) => +v.toFixed(1)));
const highways = {
  lasAmericas: P([[-69.885,18.474],[-69.84,18.466],[-69.79,18.452],[-69.74,18.446],[-69.70,18.447],[-69.65,18.451],[-69.60,18.455],[-69.50,18.459],[-69.40,18.456],[-69.31,18.462]]),
  duarte: P([[-69.955,18.49],[-70.02,18.52],[-70.10,18.58],[-70.17,18.67],[-70.27,18.79],[-70.41,18.94],[-70.47,19.08],[-70.53,19.22],[-70.62,19.35],[-70.69,19.45]]),
  seisNoviembre: P([[-69.97,18.455],[-70.01,18.43],[-70.06,18.42],[-70.11,18.42]]),
};
const out = {
  W, H,
  dr: path(dr), haiti: path(ht),
  highways,
  santoDomingo: P([[-69.93, 18.486]])[0],
  peajeLasAmericas: P([[-69.712, 18.447]])[0],
  santiago: P([[-70.69, 19.45]])[0],
};
fs.writeFileSync("src/data/map.json", JSON.stringify(out));
console.log("ok", out.santoDomingo, out.peajeLasAmericas, out.dr.length);
