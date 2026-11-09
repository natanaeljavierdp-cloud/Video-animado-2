import {
  SITE_URL, BUSINESS, LAWYER, SHOW_TESTIMONIALS, TESTIMONIALS, waLink, DEFAULT_WA_TEXT,
} from './config.mjs';
import { SERVICES, NOTARY_NOTE } from './services.mjs';
import { icon, whatsappIcon } from './icons.mjs';
import { head, header, footer, divider, monogram, rv, stripMarks, esc, orgJsonLd } from './layout.mjs';

const sectionHead = (eyebrow, title, intro = '', cls = '') => `
  <div class="section-head reveal ${cls}">
    <p class="eyebrow">${eyebrow}</p>
    <h2>${title}</h2>
    ${divider()}
    ${intro ? `<p class="lead">${intro}</p>` : ''}
  </div>`;

const FAQ = [
  [
    '¿La primera consulta es realmente gratis?',
    'Sí. La primera consulta no tiene costo ni compromiso. En ella escuchamos su caso, le explicamos sus opciones y los pasos a seguir. Si decide continuar, le informamos los honorarios antes de iniciar cualquier trámite.',
  ],
  [
    '¿Pueden atenderme si no vivo en Puerto Plata?',
    'Sí. Atendemos consultas por WhatsApp y videollamada a clientes de todo el país y a dominicanos en el exterior. Muchos trámites pueden avanzarse a distancia; cuando se requiere una gestión presencial en Puerto Plata, la coordinamos con usted.',
  ],
  [
    '¿Qué documentos debo tener a mano?',
    'Para la consulta, basta con su cédula (o pasaporte) y cualquier documento relacionado con su caso: actas, títulos, contratos, matrículas, etc. Cada servicio tiene su propia lista; puede verla en la página de cada servicio y la confirmamos con usted en la consulta.',
  ],
  [
    '¿Cuánto tarda un trámite?',
    'Depende del tipo de trámite y, sobre todo, de los tiempos de cada institución (DGII, Registro de Títulos, tribunales, ONAPI, entre otras). No prometemos plazos exactos, pero le damos un estimado realista y le mantenemos informado en cada etapa.',
  ],
  [
    '¿Cómo agendo mi consulta?',
    `Escríbanos por WhatsApp al ${BUSINESS.phoneDisplay} o complete el formulario de contacto. Le respondemos para acordar el día y la hora, por WhatsApp o videollamada, de lunes a viernes de 8:00 a. m. a 6:00 p. m.`,
  ],
  [
    '¿El abogado legaliza firmas o hace actos notariales?',
    'No. El Lic. Sandoval es abogado, no notario. Cuando un documento requiere legalización de firmas o un acto notarial, nuestro despacho prepara el documento y coordina la legalización con un notario público.',
  ],
];

// ------------------------------------------------------------------ INICIO
export function homePage() {
  const faqLd = {
    '@context': 'https://schema.org',
    '@type': 'FAQPage',
    mainEntity: FAQ.map(([q, a]) => ({ '@type': 'Question', name: q, acceptedAnswer: { '@type': 'Answer', text: a } })),
  };
  const websiteLd = {
    '@context': 'https://schema.org',
    '@type': 'WebSite',
    '@id': `${SITE_URL}/#web`,
    url: `${SITE_URL}/`,
    name: BUSINESS.name,
    inLanguage: 'es-DO',
    publisher: { '@id': `${SITE_URL}/#despacho` },
  };

  const trust = [
    ['gift', 'Consulta gratis'],
    ['globe', 'Atención online en todo el país'],
    ['chat', 'Respuesta rápida por WhatsApp'],
    ['clock', 'Lunes a viernes de 8:00 a. m. a 6:00 p. m.'],
  ];

  const cards = SERVICES.map(
    (s, i) => `
      <li class="service-card reveal" style="--d:${(i % 5) * 60}ms">
        <a href="/servicios/${s.slug}/">
          <span class="icon-circle">${icon(s.icon)}</span>
          <h3>${s.name}</h3>
          <p>${s.short}</p>
          <span class="more">Ver detalles ${icon('arrow')}</span>
        </a>
      </li>`,
  ).join('');

  const steps = [
    ['chat', 'Consulta gratis', 'Por WhatsApp o videollamada, escuchamos su caso y le explicamos sus opciones.'],
    ['search', 'Revisión de documentos', 'Analizamos sus documentos y le indicamos qué hace falta.'],
    ['gear', 'Gestión del trámite', 'Preparamos los documentos y gestionamos el proceso ante cada institución.'],
    ['check', 'Entrega', 'Le entregamos su documentación y le explicamos los siguientes pasos.'],
  ]
    .map(
      ([ic, t, d], i) => `
      <li class="step reveal" style="--d:${i * 90}ms">
        <span class="step-num">0${i + 1}</span>
        <span class="icon-circle">${icon(ic)}</span>
        <h3>${t}</h3>
        <p>${d}</p>
      </li>`,
    )
    .join('');

  const photo = LAWYER.photo
    ? `<picture>
        <source srcset="${LAWYER.photo.webp}" type="image/webp">
        <img src="${LAWYER.photo.fallback || LAWYER.photo.webp}" alt="${LAWYER.name}" width="${LAWYER.photo.width}" height="${LAWYER.photo.height}" loading="lazy" decoding="async">
      </picture>`
    : `<div class="portrait-placeholder" role="img" aria-label="Monograma de Sandoval Legal">
        ${monogram()}
        <span class="portrait-caption">Sandoval Legal</span>
      </div>`;

  const testimonials =
    SHOW_TESTIMONIALS && TESTIMONIALS.length
      ? `
  <section class="section section-cream" id="testimonios" aria-labelledby="t-title">
    <div class="container">
      ${sectionHead('Testimonios', '<span id="t-title">Lo que dicen nuestros clientes</span>')}
      <ul class="testimonials">${TESTIMONIALS.map(
        (t) => `<li class="testimonial reveal"><blockquote>“${esc(t.quote)}”</blockquote><p class="t-name">${esc(t.name)}</p>${t.detail ? `<p class="t-detail">${esc(t.detail)}</p>` : ''}</li>`,
      ).join('')}</ul>
    </div>
  </section>`
      : '<!-- Testimonios: componente listo pero oculto (ver SHOW_TESTIMONIALS en src/config.mjs) -->';

  const options = SERVICES.map((s) => `<option value="${s.name}">${s.name}</option>`).join('');

  return (
    head({
      title: 'Abogado en Puerto Plata | Sandoval Legal — Solución Jurídica',
      description:
        'Abogado en Puerto Plata, República Dominicana. Contratos, divorcios, herederos, traspasos, compañías y más. Primera consulta gratis, en persona o en línea desde todo el país.',
      path: '/',
      jsonLd: [orgJsonLd(), websiteLd, faqLd],
    }) +
    header('Inicio') +
    `
  <section class="hero" id="inicio">
    <div class="hero-bg" aria-hidden="true"></div>
    <div class="container hero-inner">
      <p class="eyebrow eyebrow-light reveal">Sandoval Legal · ${BUSINESS.slogan}</p>
      <h1 class="reveal" style="--d:80ms">Soluciones legales claras y confiables en Puerto&nbsp;Plata</h1>
      ${divider('divider-left reveal')}
      <p class="hero-sub reveal" style="--d:160ms">Primera consulta gratis, en persona o en línea desde cualquier lugar del país.</p>
      <div class="hero-actions reveal" style="--d:240ms">
        <a class="btn btn-gold" href="${waLink(DEFAULT_WA_TEXT)}" target="_blank" rel="noopener">${whatsappIcon()} Agenda tu consulta gratis</a>
        <a class="btn btn-outline-light" href="#servicios">Ver servicios</a>
      </div>
    </div>
  </section>

  <section class="trust" aria-label="Por qué elegirnos">
    <div class="container">
      <ul class="trust-list">
        ${trust.map(([ic, t]) => `<li>${icon(ic)}<span>${t}</span></li>`).join('')}
      </ul>
    </div>
  </section>

  <section class="section section-cream" id="servicios" aria-labelledby="servicios-title">
    <div class="container">
      ${sectionHead('Servicios', '<span id="servicios-title">¿En qué podemos ayudarle?</span>', 'Trámites y asesoría legal para personas, familias y negocios, con atención directa del abogado.')}
      <ul class="services-grid">${cards}</ul>
    </div>
  </section>

  <section class="section" id="nosotros" aria-labelledby="nosotros-title">
    <div class="container about">
      <div class="about-media reveal">${photo}</div>
      <div class="about-text reveal" style="--d:120ms">
        <p class="eyebrow">Nosotros</p>
        <h2 id="nosotros-title">${LAWYER.name}</h2>
        ${divider('divider-left')}
        <p class="lead">Abogado egresado de la ${LAWYER.university}, con ${LAWYER.yearsExperience} años de experiencia.</p>
        <p>Ejerce de forma independiente, por eso cada cliente recibe atención directa y personal: usted habla con el abogado que lleva su caso, desde la primera consulta hasta la entrega.</p>
        <p>Nuestro compromiso es explicarle cada paso con palabras claras, decirle qué documentos necesita y mantenerle informado, sin promesas que no dependan de nosotros.</p>
        <ul class="about-points">
          <li>${icon('user')}<span>Atención directa del abogado</span></li>
          <li>${icon('shield')}<span>Trato confidencial y respetuoso</span></li>
          <li>${icon('scale')}<span>Explicaciones claras, sin tecnicismos</span></li>
        </ul>
      </div>
    </div>
  </section>

  <section class="section section-cream" id="como-trabajamos" aria-labelledby="pasos-title">
    <div class="container">
      ${sectionHead('Cómo trabajamos', '<span id="pasos-title">Un proceso sencillo, de principio a fin</span>')}
      <ol class="steps">${steps}</ol>
    </div>
  </section>

  <section class="section online" id="consultas-online" aria-labelledby="online-title">
    <div class="container online-inner reveal">
      <div class="online-icons" aria-hidden="true">
        <span class="icon-circle icon-circle-lg">${icon('chat')}</span>
        <span class="icon-circle icon-circle-lg">${icon('video')}</span>
      </div>
      <div>
        <p class="eyebrow eyebrow-light">Consultas online</p>
        <h2 id="online-title">Le atendemos donde usted esté</h2>
        ${divider('divider-left')}
        <p>Atendemos por <strong>WhatsApp</strong> y <strong>videollamada</strong> a clientes de todo el país y a dominicanos en el exterior. Usted nos envía sus documentos de forma segura, conversamos en el horario que le convenga y avanzamos su trámite sin que tenga que trasladarse a Puerto Plata, salvo cuando una gestión requiera su presencia.</p>
        <a class="btn btn-gold" href="${waLink('Hola, quiero una consulta gratis por videollamada.')}" target="_blank" rel="noopener">${whatsappIcon()} Agendar consulta online</a>
      </div>
    </div>
  </section>

  ${testimonials}

  <section class="section" id="preguntas" aria-labelledby="faq-title">
    <div class="container container-narrow">
      ${sectionHead('Preguntas frecuentes', '<span id="faq-title">Resolvemos sus dudas</span>')}
      <div class="faq">
        ${FAQ.map(
          ([q, a], i) => `<details class="faq-item reveal"${i === 0 ? ' open' : ''}><summary><span>${q}</span><i aria-hidden="true"></i></summary><div class="faq-body"><p>${a}</p></div></details>`,
        ).join('')}
      </div>
    </div>
  </section>

  <section class="section section-cream" id="contacto" aria-labelledby="contacto-title">
    <div class="container">
      ${sectionHead('Contacto', '<span id="contacto-title">Agende su consulta gratis</span>', 'Escríbanos por WhatsApp o déjenos sus datos y le contactamos.')}
      <div class="contact">
        <form class="contact-form reveal" name="contacto" method="POST" action="/gracias/" data-netlify="true" netlify-honeypot="bot-field">
          <input type="hidden" name="form-name" value="contacto">
          <p class="hidden-field"><label>No llene este campo: <input name="bot-field" tabindex="-1" autocomplete="off"></label></p>
          <div class="field">
            <label for="f-nombre">Nombre</label>
            <input id="f-nombre" name="nombre" type="text" autocomplete="name" required>
          </div>
          <div class="field">
            <label for="f-telefono">Teléfono / WhatsApp</label>
            <input id="f-telefono" name="telefono" type="tel" autocomplete="tel" inputmode="tel" placeholder="+1 (809) 000-0000" required>
          </div>
          <div class="field">
            <label for="f-servicio">Servicio de interés</label>
            <select id="f-servicio" name="servicio" required>
              <option value="" disabled selected>Seleccione un servicio</option>
              ${options}
              <option value="Otro">Otro / no estoy seguro</option>
            </select>
          </div>
          <div class="field">
            <label for="f-mensaje">Mensaje</label>
            <textarea id="f-mensaje" name="mensaje" rows="5" placeholder="Cuéntenos brevemente su caso"></textarea>
          </div>
          <p class="form-note">Al enviar acepta nuestro <a href="/aviso-legal/">aviso de privacidad</a>. No comparta información sensible por este medio.</p>
          <button class="btn btn-navy" type="submit">Enviar mensaje</button>
        </form>
        <aside class="contact-info reveal" style="--d:120ms" aria-label="Datos de contacto">
          <a class="contact-wa" href="${waLink(DEFAULT_WA_TEXT)}" target="_blank" rel="noopener">${whatsappIcon()}<span><strong>Escríbanos por WhatsApp</strong><small>Respuesta rápida</small></span></a>
          <ul>
            <li><span class="icon-circle icon-circle-sm">${icon('phone')}</span><span><small>Teléfono</small><a href="tel:${BUSINESS.phoneE164}">${BUSINESS.phoneDisplay}</a></span></li>
            <li><span class="icon-circle icon-circle-sm">${icon('instagram')}</span><span><small>Instagram</small><a href="${BUSINESS.instagramUrl}" target="_blank" rel="noopener">${BUSINESS.instagramHandle}</a></span></li>
            ${BUSINESS.email ? `<li><span class="icon-circle icon-circle-sm">${icon('mail')}</span><span><small>Correo</small><a href="mailto:${BUSINESS.email}">${BUSINESS.email}</a></span></li>` : ''}
            <li><span class="icon-circle icon-circle-sm">${icon('clock')}</span><span><small>Horario</small>${BUSINESS.hoursText}</span></li>
            <li><span class="icon-circle icon-circle-sm">${icon('pin')}</span><span><small>Ubicación</small>${BUSINESS.locationLine}</span></li>
          </ul>
        </aside>
      </div>
    </div>
  </section>
` +
    footer()
  );
}

// ------------------------------------------------------------- SERVICIO
export function servicePage(s) {
  const path = `/servicios/${s.slug}/`;
  const waText = `Hola, quiero una consulta gratis sobre ${s.name.toLowerCase()}.`;
  const others = SERVICES.filter((o) => o.slug !== s.slug);

  const ld = [
    orgJsonLd(),
    {
      '@context': 'https://schema.org',
      '@type': 'Service',
      name: s.name,
      serviceType: s.name,
      description: s.metaDescription,
      url: SITE_URL + path,
      provider: { '@id': `${SITE_URL}/#despacho` },
      areaServed: [
        { '@type': 'City', name: 'Puerto Plata' },
        { '@type': 'Country', name: 'República Dominicana' },
      ],
    },
    {
      '@context': 'https://schema.org',
      '@type': 'BreadcrumbList',
      itemListElement: [
        { '@type': 'ListItem', position: 1, name: 'Inicio', item: `${SITE_URL}/` },
        { '@type': 'ListItem', position: 2, name: 'Servicios', item: `${SITE_URL}/#servicios` },
        { '@type': 'ListItem', position: 3, name: s.name, item: SITE_URL + path },
      ],
    },
  ];

  return (
    head({ title: `${s.name} en Puerto Plata`, description: s.metaDescription, path, jsonLd: ld }) +
    header('Servicios') +
    `
  <section class="page-hero">
    <div class="hero-bg" aria-hidden="true"></div>
    <div class="container">
      <nav class="breadcrumb" aria-label="Ruta de navegación">
        <ol><li><a href="/">Inicio</a></li><li><a href="/#servicios">Servicios</a></li><li aria-current="page">${s.name}</li></ol>
      </nav>
      <span class="icon-circle icon-circle-lg reveal">${icon(s.icon)}</span>
      <h1 class="reveal" style="--d:80ms">${s.name}</h1>
      ${divider('reveal')}
      <p class="hero-sub reveal" style="--d:160ms">${s.short}</p>
    </div>
  </section>

  <div class="section">
    <div class="container service-layout">
      <article class="service-body">
        <section class="reveal" aria-labelledby="desc">
          <h2 id="desc" class="h-sm">Descripción</h2>
          <p class="lead">${rv(s.intro)}</p>
        </section>

        <section class="reveal" aria-labelledby="cuando">
          <h2 id="cuando" class="h-sm">¿Cuándo lo necesitas?</h2>
          <ul class="check-list">${s.when.map((w) => `<li>${icon('check')}<span>${rv(w)}</span></li>`).join('')}</ul>
        </section>

        <section class="reveal" aria-labelledby="docs">
          <h2 id="docs" class="h-sm">Documentos que suelen pedirse</h2>
          <ul class="doc-list">${s.documents.map((d) => `<li>${icon('doc')}<span>${rv(d)}</span></li>`).join('')}</ul>
          <p class="small-note">La lista puede variar según cada caso y según los requisitos vigentes de cada institución. La confirmamos con usted en la consulta gratis.</p>
        </section>

        ${
          s.notary
            ? `<aside class="notice reveal" aria-label="Nota sobre la legalización">${icon('shield')}<p><strong>Sobre la legalización:</strong> ${NOTARY_NOTE}</p></aside>`
            : ''
        }
        ${s.extraNote ? `<aside class="notice reveal" aria-label="Nota">${icon('shield')}<p>${rv(s.extraNote)}</p></aside>` : ''}

        <section class="reveal" aria-labelledby="proceso">
          <h2 id="proceso" class="h-sm">Proceso paso a paso</h2>
          <ol class="process">${s.steps
            .map(([t, d], i) => `<li><span class="process-num">${i + 1}</span><div><h3>${t}</h3><p>${rv(d)}</p></div></li>`)
            .join('')}</ol>
          <p class="small-note">Los tiempos dependen de cada institución y de la documentación disponible; no garantizamos plazos ni resultados específicos.</p>
        </section>
      </article>

      <aside class="service-aside">
        <div class="cta-card reveal">
          <p class="eyebrow eyebrow-light">Primera consulta gratis</p>
          <h2>¿Necesita ayuda con ${s.name.toLowerCase()}?</h2>
          ${divider()}
          <p>Escríbanos y le explicamos su caso sin costo ni compromiso.</p>
          <a class="btn btn-gold btn-block" href="${waLink(waText)}" target="_blank" rel="noopener">${whatsappIcon()} Consultar por WhatsApp</a>
          <p class="cta-meta">${BUSINESS.hoursShort}<br>Atención online en todo el país</p>
        </div>
      </aside>
    </div>
  </div>

  <section class="section section-cream" aria-labelledby="otros">
    <div class="container">
      ${sectionHead('Otros servicios', '<span id="otros">También podemos ayudarle con</span>')}
      <ul class="other-services">${others
        .map((o) => `<li><a href="/servicios/${o.slug}/"><span class="icon-circle icon-circle-sm">${icon(o.icon)}</span><span>${o.name}</span></a></li>`)
        .join('')}</ul>
    </div>
  </section>
` +
    footer()
  );
}

// ---------------------------------------------------- AVISO LEGAL Y PRIVACIDAD
export function legalPage() {
  return (
    head({
      title: 'Aviso legal y privacidad',
      description: 'Aviso legal y política de privacidad del sitio web de Sandoval Legal, Puerto Plata, República Dominicana.',
      path: '/aviso-legal/',
      jsonLd: [orgJsonLd()],
    }) +
    header() +
    `
  <section class="page-hero page-hero-sm">
    <div class="hero-bg" aria-hidden="true"></div>
    <div class="container"><h1>Aviso legal y privacidad</h1>${divider()}</div>
  </section>
  <div class="section">
    <div class="container container-narrow prose">
      <h2>1. Titular del sitio</h2>
      <p>Este sitio web pertenece a <strong>${BUSINESS.name}</strong>, despacho del ${LAWYER.name}, abogado con ejercicio en Puerto Plata, República Dominicana. Contacto: WhatsApp y teléfono ${BUSINESS.phoneDisplay}${BUSINESS.email ? `, correo ${BUSINESS.email}` : ''}; Instagram ${BUSINESS.instagramHandle}.</p>

      <h2>2. Información general, no asesoría legal</h2>
      <p>La información publicada en este sitio es general y orientativa. <strong>No constituye asesoría legal</strong> ni crea una relación abogado-cliente. Cada caso debe analizarse de forma individual. Los requisitos y procedimientos pueden cambiar según las disposiciones vigentes de cada institución.</p>

      <h2>3. Sin garantía de resultados</h2>
      <p>${BUSINESS.name} no garantiza resultados ni plazos específicos, ya que estos dependen de terceros, como tribunales e instituciones públicas, y de la documentación disponible en cada caso.</p>

      <h2>4. Servicios notariales</h2>
      <p>El Lic. Sandoval es abogado y no ejerce como notario público. Cuando un documento requiere legalización de firmas o un acto notarial, el despacho prepara el documento y coordina la legalización con un notario público.</p>

      <h2>5. Datos personales</h2>
      <p>Los datos que usted nos envía a través del formulario de contacto (nombre, teléfono, servicio de interés y mensaje) o por WhatsApp se utilizan únicamente para responder su consulta y, si lo decide, prestarle nuestros servicios. No los vendemos ni los compartimos con terceros, salvo cuando sea necesario para realizar el trámite que usted nos encargue (por ejemplo, ante una institución pública o un notario) o cuando la ley lo exija.</p>
      <p>Tratamos su información con confidencialidad, conforme al secreto profesional y a la Ley núm. 172-13 sobre protección de datos personales de la República Dominicana. Puede solicitar en cualquier momento el acceso, la corrección o la eliminación de sus datos escribiéndonos por WhatsApp.</p>

      <h2>6. Formulario y proveedores</h2>
      <p>El sitio está alojado en Netlify, que procesa los envíos del formulario de contacto. Le recomendamos no incluir en el formulario información sensible; podemos solicitarla luego por un medio adecuado.</p>

      <h2>7. Cookies</h2>
      <p>Este sitio no utiliza cookies de publicidad ni de seguimiento propias. Las fuentes tipográficas se cargan desde Google Fonts, que puede registrar datos técnicos de la conexión.</p>

      <h2>8. Enlaces externos</h2>
      <p>Los enlaces a WhatsApp, Instagram u otros sitios se rigen por las políticas de privacidad de esos servicios.</p>

      <h2>9. Propiedad intelectual</h2>
      <p>El nombre, el logo y los contenidos de este sitio pertenecen a ${BUSINESS.name}. No se permite su reproducción sin autorización.</p>

      <p class="small-note">Última actualización: noviembre de 2026.</p>
    </div>
  </div>
` +
    footer()
  );
}

// ----------------------------------------------------------- GRACIAS / 404
export function thanksPage() {
  return (
    head({
      title: 'Mensaje enviado',
      description: 'Gracias por escribir a Sandoval Legal. Le responderemos a la brevedad.',
      path: '/gracias/',
      noindex: true,
    }) +
    header() +
    `
  <section class="page-hero page-hero-full">
    <div class="hero-bg" aria-hidden="true"></div>
    <div class="container">
      <span class="icon-circle icon-circle-lg">${icon('check')}</span>
      <h1>¡Gracias por escribirnos!</h1>
      ${divider()}
      <p class="hero-sub">Recibimos su mensaje y le contactaremos en horario laborable (${BUSINESS.hoursShort}). Si su consulta es urgente, escríbanos por WhatsApp.</p>
      <div class="hero-actions hero-actions-center">
        <a class="btn btn-gold" href="${waLink(DEFAULT_WA_TEXT)}" target="_blank" rel="noopener">${whatsappIcon()} Escribir por WhatsApp</a>
        <a class="btn btn-outline-light" href="/">Volver al inicio</a>
      </div>
    </div>
  </section>
` +
    footer()
  );
}

export function notFoundPage() {
  return (
    head({ title: 'Página no encontrada', description: 'La página que busca no existe.', path: '/404.html', noindex: true }) +
    header() +
    `
  <section class="page-hero page-hero-full">
    <div class="hero-bg" aria-hidden="true"></div>
    <div class="container">
      <p class="eyebrow eyebrow-light">Error 404</p>
      <h1>Página no encontrada</h1>
      ${divider()}
      <p class="hero-sub">Es posible que el enlace haya cambiado. Puede volver al inicio o ver nuestros servicios.</p>
      <div class="hero-actions hero-actions-center">
        <a class="btn btn-gold" href="/">Ir al inicio</a>
        <a class="btn btn-outline-light" href="/#servicios">Ver servicios</a>
      </div>
    </div>
  </section>
` +
    footer()
  );
}

export { FAQ, stripMarks };
