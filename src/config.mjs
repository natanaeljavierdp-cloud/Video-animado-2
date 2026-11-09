// =============================================================
//  CONFIGURACIÓN GENERAL DEL SITIO — Sandoval Legal
//  Edita este archivo para cambiar datos del negocio.
// =============================================================

// 👉 URL pública del sitio. Cámbiala aquí (y solo aquí) cuando
//    compres el dominio propio, por ejemplo:
//    'https://sandovallegal.com.do'
//    También puedes definirla en Netlify con la variable de entorno SITE_URL.
export const SITE_URL = (process.env.SITE_URL || 'https://sandoval-legal.netlify.app').replace(/\/$/, '');

export const BUSINESS = {
  name: 'Sandoval Legal',
  slogan: 'Solución Jurídica',
  closingPhrase: 'Comprometidos con tus derechos, en cada paso del camino.',
  city: 'Puerto Plata',
  region: 'Puerto Plata',
  country: 'República Dominicana',
  countryCode: 'DO',
  locationLine: 'Puerto Plata, República Dominicana · Atención online',

  phoneDisplay: '+1 (829) 683-5975',
  phoneE164: '+18296835975',
  whatsappNumber: '18296835975',

  instagramHandle: '@sandoval_legal',
  instagramUrl: 'https://instagram.com/sandoval_legal',

  // [PENDIENTE] Correo electrónico del despacho. Cuando exista, escríbelo aquí
  // (por ejemplo 'contacto@sandovallegal.com.do') y aparecerá en Contacto y en el footer.
  email: '',

  hoursText: 'Lunes a viernes, 8:00 a. m. – 6:00 p. m.',
  hoursShort: 'Lun. a vie. 8:00 a. m. – 6:00 p. m.',
  opens: '08:00',
  closes: '18:00',
};

// Logo en imagen: si subes el logo oficial (por ejemplo public/assets/logo-blanco.webp,
// versión blanca/dorada sobre fondo transparente o azul), escribe aquí su ruta y
// reemplazará al logo tipográfico del menú y del footer. Ej.: '/assets/logo-blanco.webp'
export const LOGO_IMAGE = null;

export const LAWYER = {
  name: 'Lic. Eddy Marino Sandoval Rojas',
  shortName: 'Eddy Marino Sandoval Rojas',
  university: 'Universidad Tecnológica de Santiago (UTESA)',
  universityShort: 'UTESA',
  yearsExperience: 3,
  // Foto del abogado: cuando la tengas, guarda la imagen en public/assets/
  // (ideal: abogado.webp de 800×1000 px y abogado.jpg como respaldo) y escribe:
  // photo: { webp: '/assets/abogado.webp', fallback: '/assets/abogado.jpg', width: 800, height: 1000 }
  photo: null,
};

// Mostrar u ocultar las marcas [VERIFICAR] en las páginas.
// Déjalo en true mientras el abogado revisa los textos; cámbialo a false antes de lanzar.
export const SHOW_REVIEW_MARKS = true;

// Testimonios: el componente está listo pero oculto. Cuando haya testimonios
// reales (con permiso del cliente), agrégalos aquí y cambia SHOW_TESTIMONIALS a true.
export const SHOW_TESTIMONIALS = false;
export const TESTIMONIALS = [
  // { quote: 'Texto del testimonio…', name: 'Nombre del cliente', detail: 'Divorcio · Santiago' },
];

export const NAV = [
  { label: 'Inicio', href: '/#inicio' },
  { label: 'Servicios', href: '/#servicios' },
  { label: 'Nosotros', href: '/#nosotros' },
  { label: 'Preguntas', href: '/#preguntas' },
  { label: 'Contacto', href: '/#contacto' },
];

export const waLink = (text) =>
  `https://wa.me/${BUSINESS.whatsappNumber}${text ? `?text=${encodeURIComponent(text)}` : ''}`;

export const DEFAULT_WA_TEXT = 'Hola, quiero una consulta gratis.';
