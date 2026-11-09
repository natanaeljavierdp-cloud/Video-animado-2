// Íconos de línea fina (SVG en línea, heredan el color con currentColor).
const P = {
  // Servicios
  key: '<circle cx="8" cy="15" r="4"/><path d="M11 12l9-9M16 7l3 3M14 9l2 2"/>',
  handshake:
    '<path d="M3 11l4-4 4 2 3-2 4 1 3 3"/><path d="M3 11l5 5c.8.8 2 .8 2.8 0l.4-.4M21 11l-5.5 5.5c-.8.8-2 .8-2.8 0L9 13"/><path d="M11.5 15l1.5 1.5M13.5 13l1.8 1.8"/>',
  rings: '<circle cx="9" cy="14" r="5"/><circle cx="15" cy="14" r="5"/><path d="M9 6l1.5-3h3L15 6"/>',
  family:
    '<circle cx="12" cy="4.5" r="2"/><circle cx="5" cy="13" r="2"/><circle cx="12" cy="13" r="2"/><circle cx="19" cy="13" r="2"/><path d="M12 6.5V9M5 11V9h14v2M12 9v2M3 21v-1.5a2 2 0 0 1 2-2h0a2 2 0 0 1 2 2V21M10 21v-1.5a2 2 0 0 1 2-2h0a2 2 0 0 1 2 2V21M17 21v-1.5a2 2 0 0 1 2-2h0a2 2 0 0 1 2 2V21"/>',
  docPen:
    '<path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z"/><path d="M14 3v5h5M8 12h6M8 15h4"/><path d="M13 19l1-3 4-4 2 2-4 4z"/>',
  car: '<path d="M5 16V12l2-5h10l2 5v4"/><path d="M3 16h18v2a1 1 0 0 1-1 1h-1M5 19H4a1 1 0 0 1-1-1v-2"/><circle cx="7.5" cy="16" r="1.5"/><circle cx="16.5" cy="16" r="1.5"/><path d="M5 12h14"/>',
  building:
    '<path d="M3 21h18M5 21V8l7-5 7 5v13"/><path d="M9 21v-5h6v5M9 11h.01M15 11h.01M12 11h.01"/>',
  tag: '<path d="M3 12V4a1 1 0 0 1 1-1h8l9 9-9 9z"/><circle cx="8" cy="8" r="1.5"/><path d="M11 13.5l2.5 2.5M13 11.5l2.5 2.5"/>',
  briefcase:
    '<rect x="3" y="7" width="18" height="13" rx="1"/><path d="M9 7V5a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2M3 12h18M11 12v2h2v-2"/>',
  plane:
    '<path d="M10.5 13.5L3 11l1.5-1.5 8 1 4-4c1-1 3-1.5 3.5-1s0 2.5-1 3.5l-4 4 1 8L14.5 23 12 15.5"/><circle cx="5" cy="19" r="1.6"/><path d="M5 20.6V23"/>',
  // Interfaz
  gift: '<rect x="3" y="8" width="18" height="4" rx="1"/><path d="M5 12v9h14v-9M12 8v13M12 8c-1.5-3-5-3.5-5-1.5S10 8 12 8zM12 8c1.5-3 5-3.5 5-1.5S14 8 12 8z"/>',
  globe:
    '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.5 2.5 3.8 5.5 3.8 9s-1.3 6.5-3.8 9c-2.5-2.5-3.8-5.5-3.8-9S9.5 5.5 12 3z"/>',
  chat: '<path d="M4 20l1.3-3.9A8 8 0 1 1 8 19z"/><path d="M8.5 9.5c0 3 3 6 6 6l1.2-1.4-2-1-1 .8c-.9-.4-2.2-1.7-2.6-2.6l.8-1-1-2z"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  video: '<rect x="3" y="6" width="13" height="12" rx="1.5"/><path d="M16 10l5-3v10l-5-3"/>',
  search: '<circle cx="11" cy="11" r="6"/><path d="M20 20l-4.5-4.5M8.5 11h5M11 8.5v5"/>',
  gear: '<path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z"/><path d="M14 3v5h5"/><path d="M8.5 15l2 2 4-4.5"/>',
  check: '<circle cx="12" cy="12" r="9"/><path d="M8 12.5l2.7 2.5L16 9.5"/>',
  shield: '<path d="M12 3l7 3v6c0 4.5-3 7.5-7 9-4-1.5-7-4.5-7-9V6z"/><path d="M9 12l2 2 4-4"/>',
  user: '<circle cx="12" cy="8" r="4"/><path d="M4 21c0-4 3.6-6.5 8-6.5s8 2.5 8 6.5"/>',
  phone:
    '<path d="M5 4h4l2 5-2.5 1.5a11 11 0 0 0 5 5L15 13l5 2v4a1 1 0 0 1-1 1A16 16 0 0 1 4 5a1 1 0 0 1 1-1z"/>',
  instagram:
    '<rect x="3" y="3" width="18" height="18" rx="5"/><circle cx="12" cy="12" r="4"/><circle cx="17.5" cy="6.5" r=".6" fill="currentColor"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="1.5"/><path d="M3.5 6l8.5 7 8.5-7"/>',
  pin: '<path d="M12 21s-7-6.2-7-11.5A7 7 0 0 1 19 9.5C19 14.8 12 21 12 21z"/><circle cx="12" cy="9.5" r="2.5"/>',
  arrow: '<path d="M5 12h14M13 6l6 6-6 6"/>',
  doc: '<path d="M14 3H6a1 1 0 0 0-1 1v16a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1V8z"/><path d="M14 3v5h5M8 13h8M8 17h5"/>',
  scale:
    '<path d="M12 3v18M7 21h10M5 7h14M12 5a1 1 0 1 0 0-2 1 1 0 0 0 0 2z"/><path d="M5 7l-3 7a3 3 0 0 0 6 0zM19 7l-3 7a3 3 0 0 0 6 0z"/>',
};

export const icon = (name, cls = '') =>
  `<svg class="icon ${cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">${P[name] || P.doc}</svg>`;

// Ícono oficial de WhatsApp (relleno), para el botón flotante y los CTA.
export const whatsappIcon = (cls = '') =>
  `<svg class="icon-wa ${cls}" viewBox="0 0 32 32" aria-hidden="true" focusable="false"><path fill="currentColor" d="M16.04 3C8.86 3 3.03 8.82 3.03 16c0 2.3.6 4.53 1.74 6.5L3 29l6.68-1.75A12.95 12.95 0 0 0 16.04 29C23.2 29 29 23.18 29 16S23.2 3 16.04 3zm0 23.62c-1.98 0-3.92-.53-5.61-1.54l-.4-.24-3.96 1.04 1.06-3.86-.26-.4A10.6 10.6 0 0 1 5.4 16c0-5.87 4.77-10.63 10.64-10.63 5.86 0 10.62 4.76 10.62 10.63 0 5.86-4.76 10.62-10.62 10.62zm5.83-7.95c-.32-.16-1.89-.93-2.18-1.04-.3-.1-.5-.16-.72.16-.21.32-.82 1.04-1.01 1.25-.19.21-.37.24-.69.08-.32-.16-1.35-.5-2.57-1.59-.95-.85-1.59-1.9-1.78-2.21-.19-.32-.02-.49.14-.65.14-.14.32-.37.48-.56.16-.18.21-.32.32-.53.1-.21.05-.4-.03-.56-.08-.16-.72-1.73-.98-2.37-.26-.62-.52-.54-.72-.55h-.61c-.21 0-.56.08-.85.4-.29.32-1.12 1.09-1.12 2.66 0 1.57 1.14 3.08 1.3 3.3.16.2 2.24 3.42 5.43 4.8.76.33 1.35.52 1.81.67.76.24 1.45.2 2 .12.61-.09 1.89-.77 2.15-1.52.27-.74.27-1.38.19-1.52-.08-.13-.29-.21-.61-.37z"/></svg>`;
