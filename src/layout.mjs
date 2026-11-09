import {
  SITE_URL, BUSINESS, NAV, LOGO_IMAGE, SHOW_REVIEW_MARKS, waLink, DEFAULT_WA_TEXT,
} from './config.mjs';
import { SERVICES } from './services.mjs';
import { icon, whatsappIcon } from './icons.mjs';

const YEAR = 2026;

export const esc = (s = '') =>
  String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

// Convierte las marcas [VERIFICAR] en una etiqueta visible (o las elimina).
export const rv = (text = '') =>
  SHOW_REVIEW_MARKS
    ? text.replace(/\s*\[VERIFICAR\]/g, ' <span class="verify" title="Requisito pendiente de confirmar por el abogado">[VERIFICAR]</span>')
    : text.replace(/\s*\[VERIFICAR\]/g, '');

export const stripMarks = (text = '') => text.replace(/\s*\[VERIFICAR\]/g, '');

export const divider = (cls = '') =>
  `<div class="divider ${cls}" aria-hidden="true"><span></span><i></i><span></span></div>`;

// Monograma "S" dentro de un rombo dorado (logo provisional / favicon).
export const monogram = (cls = '') =>
  `<svg class="monogram ${cls}" viewBox="0 0 64 64" aria-hidden="true" focusable="false"><rect x="12" y="12" width="40" height="40" transform="rotate(45 32 32)" fill="none" stroke="currentColor" stroke-width="1.4"/><rect x="16.5" y="16.5" width="31" height="31" transform="rotate(45 32 32)" fill="none" stroke="currentColor" stroke-width=".6" opacity=".7"/><text x="32" y="43" text-anchor="middle" font-family="'Cormorant Garamond', Georgia, serif" font-size="33" font-weight="600" fill="currentColor">S</text></svg>`;

const logo = (variant = 'header') =>
  LOGO_IMAGE
    ? `<img src="${LOGO_IMAGE}" alt="${BUSINESS.name} — ${BUSINESS.slogan}" class="logo-img" width="180" height="60">`
    : `${monogram()}<span class="logo-text"><span class="logo-name">Sandoval Legal</span><span class="logo-slogan">${BUSINESS.slogan}</span></span>`;

export function head({ title, description, path = '/', type = 'website', jsonLd = [], noindex = false }) {
  const url = SITE_URL + path;
  const fullTitle = title.includes(BUSINESS.name) ? title : `${title} | ${BUSINESS.name}`;
  return `<!doctype html>
<html lang="es-DO">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>${esc(fullTitle)}</title>
<meta name="description" content="${esc(description)}">
<link rel="canonical" href="${url}">
${noindex ? '<meta name="robots" content="noindex, follow">' : '<meta name="robots" content="index, follow">'}
<meta name="theme-color" content="#0B1F3A">
<meta name="geo.region" content="DO-18">
<meta name="geo.placename" content="Puerto Plata">
<meta property="og:type" content="${type}">
<meta property="og:locale" content="es_DO">
<meta property="og:site_name" content="${BUSINESS.name}">
<meta property="og:title" content="${esc(fullTitle)}">
<meta property="og:description" content="${esc(description)}">
<meta property="og:url" content="${url}">
<meta property="og:image" content="${SITE_URL}/assets/og-image.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="${BUSINESS.name} — ${BUSINESS.slogan}">
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="${esc(fullTitle)}">
<meta name="twitter:description" content="${esc(description)}">
<meta name="twitter:image" content="${SITE_URL}/assets/og-image.jpg">
<link rel="icon" href="/favicon.ico" sizes="32x32">
<link rel="icon" href="/assets/favicon-192.png" type="image/png" sizes="192x192">
<link rel="apple-touch-icon" href="/assets/apple-touch-icon.png">
<link rel="manifest" href="/site.webmanifest">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,500;0,600;0,700;1,500&family=Montserrat:wght@400;500;600&display=swap">
<link rel="stylesheet" href="/css/styles.css">
<script>document.documentElement.classList.add('js')</script>
${jsonLd.map((o) => `<script type="application/ld+json">${JSON.stringify(o)}</script>`).join('\n')}
</head>
<body>
<a class="skip-link" href="#contenido">Saltar al contenido</a>`;
}

export function header(current = '') {
  const links = NAV.map(
    (n) => `<li><a href="${n.href}"${current === n.label ? ' aria-current="page"' : ''}>${n.label}</a></li>`,
  ).join('');
  return `<header class="site-header" data-header>
  <div class="container header-inner">
    <a class="logo" href="/" aria-label="${BUSINESS.name}, ir al inicio">${logo()}</a>
    <nav class="main-nav" aria-label="Menú principal">
      <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="menu" data-nav-toggle>
        <span class="sr-only">Abrir menú</span><span class="bars" aria-hidden="true"><span></span><span></span><span></span></span>
      </button>
      <div class="nav-panel" id="menu" data-nav-panel>
        <ul class="nav-list">${links}</ul>
        <a class="btn btn-gold btn-sm" href="${waLink(DEFAULT_WA_TEXT)}" target="_blank" rel="noopener">Consulta gratis</a>
      </div>
    </nav>
  </div>
</header>
<main id="contenido">`;
}

export function footer() {
  const serviceLinks = SERVICES.map((s) => `<li><a href="/servicios/${s.slug}/">${s.name}</a></li>`).join('');
  return `</main>
<footer class="site-footer">
  <div class="container">
    <div class="footer-top">
      <div class="footer-brand">
        <a class="logo logo-footer" href="/" aria-label="${BUSINESS.name}, ir al inicio">${logo('footer')}</a>
        ${divider('divider-left')}
        <p class="footer-phrase">${BUSINESS.closingPhrase}</p>
        <a class="social" href="${BUSINESS.instagramUrl}" target="_blank" rel="noopener">${icon('instagram')}<span>${BUSINESS.instagramHandle}</span></a>
      </div>
      <div class="footer-col">
        <h2 class="footer-title">Servicios</h2>
        <ul class="footer-links footer-links-2col">${serviceLinks}</ul>
      </div>
      <div class="footer-col">
        <h2 class="footer-title">Contacto</h2>
        <ul class="footer-links footer-contact">
          <li>${icon('chat')}<a href="${waLink(DEFAULT_WA_TEXT)}" target="_blank" rel="noopener">WhatsApp ${BUSINESS.phoneDisplay}</a></li>
          <li>${icon('phone')}<a href="tel:${BUSINESS.phoneE164}">${BUSINESS.phoneDisplay}</a></li>
          ${BUSINESS.email ? `<li>${icon('mail')}<a href="mailto:${BUSINESS.email}">${BUSINESS.email}</a></li>` : ''}
          <li>${icon('clock')}<span>${BUSINESS.hoursText}</span></li>
          <li>${icon('pin')}<span>${BUSINESS.locationLine}</span></li>
        </ul>
      </div>
    </div>
    <div class="footer-bottom">
      <p class="disclaimer">La información de este sitio es general y no constituye asesoría legal.</p>
      <p>© ${BUSINESS.name} ${YEAR} · <a href="/aviso-legal/">Aviso legal y privacidad</a></p>
    </div>
  </div>
</footer>
<a class="wa-float" href="${waLink(DEFAULT_WA_TEXT)}" target="_blank" rel="noopener" aria-label="Consulta gratis por WhatsApp">${whatsappIcon()}<span>Consulta gratis</span></a>
<script src="/js/main.js" defer></script>
</body>
</html>`;
}

// Datos estructurados del despacho (schema.org), reutilizados en todas las páginas.
export const orgJsonLd = () => ({
  '@context': 'https://schema.org',
  '@type': ['LegalService', 'Attorney'],
  '@id': `${SITE_URL}/#despacho`,
  name: BUSINESS.name,
  slogan: BUSINESS.slogan,
  description:
    'Oficina de abogados en Puerto Plata, República Dominicana. Consultas online en todo el país y trámites en Puerto Plata. Primera consulta gratis.',
  url: `${SITE_URL}/`,
  logo: `${SITE_URL}/assets/logo-512.png`,
  image: `${SITE_URL}/assets/og-image.jpg`,
  telephone: BUSINESS.phoneE164,
  ...(BUSINESS.email ? { email: BUSINESS.email } : {}),
  areaServed: [
    { '@type': 'City', name: 'Puerto Plata' },
    { '@type': 'Country', name: 'República Dominicana' },
  ],
  openingHoursSpecification: [
    {
      '@type': 'OpeningHoursSpecification',
      dayOfWeek: ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday'],
      opens: BUSINESS.opens,
      closes: BUSINESS.closes,
    },
  ],
  sameAs: [BUSINESS.instagramUrl],
  knowsLanguage: 'es',
  founder: {
    '@type': 'Person',
    name: 'Eddy Marino Sandoval Rojas',
    honorificPrefix: 'Lic.',
    jobTitle: 'Abogado',
    alumniOf: { '@type': 'CollegeOrUniversity', name: 'Universidad Tecnológica de Santiago (UTESA)' },
  },
  hasOfferCatalog: {
    '@type': 'OfferCatalog',
    name: 'Servicios legales',
    itemListElement: SERVICES.map((s) => ({
      '@type': 'Offer',
      itemOffered: { '@type': 'Service', name: s.name, url: `${SITE_URL}/servicios/${s.slug}/` },
    })),
  },
});
