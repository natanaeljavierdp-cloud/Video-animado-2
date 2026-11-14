// Empaqueta transcripción, mapas e íconos en render/data.js (para cargar sin servidor)
import fs from 'fs';
const words = JSON.parse(fs.readFileSync('data/words.json'));
const geo = JSON.parse(fs.readFileSync('data/geo.json'));
const names = ['lightbulb','lightbulb-off','wifi','wifi-off','landmark','radio','tv','check','glass-water','cylinder',
 'flashlight','pill','file-text','banknote','backpack','users','message-circle','triangle-alert','radio-tower','zap-off','share-2','eye'];
const icons = {};
for (const n of names) {
  const p = `node_modules/lucide-static/icons/${n}.svg`;
  if (!fs.existsSync(p)) { console.warn('missing icon', n); continue; }
  icons[n] = fs.readFileSync(p, 'utf8').replace(/<!--.*?-->/s, '').trim();
}
fs.writeFileSync('render/data.js', `window.WORDS=${JSON.stringify(words)};\nwindow.GEO=${JSON.stringify(geo)};\nwindow.ICONS=${JSON.stringify(icons)};\n`);
console.log('ok', Object.keys(icons).length, 'icons');
