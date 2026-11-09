// Genera el sitio estático en /dist. Sin dependencias: solo Node 18+.
import { mkdir, writeFile, rm, cp } from 'node:fs/promises';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { SITE_URL, BUSINESS } from '../src/config.mjs';
import { SERVICES } from '../src/services.mjs';
import { homePage, servicePage, legalPage, thanksPage, notFoundPage } from '../src/pages.mjs';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const dist = join(root, 'dist');

const out = async (rel, content) => {
  const file = join(dist, rel);
  await mkdir(dirname(file), { recursive: true });
  await writeFile(file, content);
};

await rm(dist, { recursive: true, force: true });
await cp(join(root, 'public'), dist, { recursive: true });

await out('index.html', homePage());
for (const s of SERVICES) await out(`servicios/${s.slug}/index.html`, servicePage(s));
await out('aviso-legal/index.html', legalPage());
await out('gracias/index.html', thanksPage());
await out('404.html', notFoundPage());

const today = new Date().toISOString().slice(0, 10);
const urls = [
  ['/', '1.0'],
  ...SERVICES.map((s) => [`/servicios/${s.slug}/`, '0.8']),
  ['/aviso-legal/', '0.3'],
];
await out(
  'sitemap.xml',
  `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.map(([p, pr]) => `  <url><loc>${SITE_URL}${p}</loc><lastmod>${today}</lastmod><priority>${pr}</priority></url>`).join('\n')}
</urlset>
`,
);
await out('robots.txt', `User-agent: *\nAllow: /\nDisallow: /gracias/\n\nSitemap: ${SITE_URL}/sitemap.xml\n`);
await out(
  'site.webmanifest',
  JSON.stringify(
    {
      name: BUSINESS.name,
      short_name: 'Sandoval Legal',
      lang: 'es-DO',
      start_url: '/',
      display: 'standalone',
      background_color: '#0B1F3A',
      theme_color: '#0B1F3A',
      icons: [
        { src: '/assets/favicon-192.png', sizes: '192x192', type: 'image/png' },
        { src: '/assets/logo-512.png', sizes: '512x512', type: 'image/png' },
      ],
    },
    null,
    2,
  ),
);

console.log(`✔ Sitio generado en dist/ (${urls.length + 2} páginas) para ${SITE_URL}`);
