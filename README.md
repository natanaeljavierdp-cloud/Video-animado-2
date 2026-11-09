# Sandoval Legal — Sitio web

Sitio web de **Sandoval Legal · Solución Jurídica**, oficina de abogados en Puerto Plata, República Dominicana.

Sitio estático (HTML + CSS + JS) generado con un pequeño script de Node **sin dependencias**: no hay nada que instalar ni base de datos. Listo para publicarse gratis en Netlify.

## Estructura

```
src/config.mjs     ← DATOS DEL NEGOCIO y URL del sitio (SITE_URL). Empieza aquí.
src/services.mjs   ← Textos de los 10 servicios (con marcas [VERIFICAR])
src/pages.mjs      ← Inicio, plantilla de servicio, aviso legal, gracias y 404
src/layout.mjs     ← <head> con SEO/Open Graph, menú, footer, schema.org
src/icons.mjs      ← Íconos de línea fina
public/            ← CSS, JS, favicon, imagen Open Graph y logos (se copia tal cual)
scripts/build.mjs  ← Genera dist/ (páginas, sitemap.xml, robots.txt, manifest)
scripts/serve.mjs  ← Servidor local
netlify.toml       ← Configuración de Netlify
```

Páginas generadas: inicio, 10 páginas de servicio (`/servicios/<servicio>/`), `/aviso-legal/`, `/gracias/` (después de enviar el formulario) y `404.html`.

## Verlo en local

Requiere [Node.js](https://nodejs.org) 18 o superior.

```bash
npm run dev
```

Abre <http://localhost:4321>. Después de editar un archivo de `src/` o `public/`, detén el servidor (Ctrl+C) y vuelve a ejecutar `npm run dev`.
En local el formulario solo redirige a la página de gracias; el envío real funciona una vez publicado en Netlify.

## Publicar en Netlify (gratis)

1. Crea una cuenta en <https://app.netlify.com> (puedes entrar con GitHub).
2. **Add new site → Import an existing project → GitHub** y elige este repositorio y la rama que quieras publicar.
3. Netlify lee `netlify.toml` automáticamente: comando `npm run build`, carpeta `dist`. Pulsa **Deploy**.
4. En **Site configuration → Change site name** escribe `sandoval-legal` para obtener `https://sandoval-legal.netlify.app`.
   Si ese nombre ya está tomado, elige otro y actualiza `SITE_URL` en `src/config.mjs` (o crea la variable de entorno `SITE_URL` en Netlify).
5. **Formulario:** en **Forms** activa *Form detection* y vuelve a desplegar. Los mensajes del formulario “contacto” aparecerán ahí.
   En **Forms → Form notifications** agrega un aviso por correo para recibir cada mensaje.
6. Cada vez que hagas push a la rama, Netlify publica la nueva versión sola.

## Conectar un dominio propio más adelante

1. Compra el dominio (recomendado `sandovallegal.com.do` en [NIC.do](https://nic.do) o `sandovallegal.com` en cualquier registrador).
2. En Netlify: **Domain management → Add a domain** y escribe el dominio.
3. Sigue las instrucciones: usa los *nameservers* de Netlify (lo más sencillo) o crea los registros DNS que te indique (A / CNAME).
4. Netlify activa HTTPS gratis (Let’s Encrypt) en unos minutos u horas.
5. Cambia **una sola línea** en `src/config.mjs`:
   ```js
   export const SITE_URL = (process.env.SITE_URL || 'https://sandovallegal.com.do')...
   ```
   Haz commit y push: el sitemap, las etiquetas canónicas, Open Graph y schema.org se actualizan solos.
6. Registra el sitio en [Google Search Console](https://search.google.com/search-console) y envía `/sitemap.xml`. Crea también un **Perfil de Empresa en Google** (sin dirección, como empresa de servicio en Puerto Plata) para el SEO local.

## Cambios frecuentes

| Quiero… | Dónde |
|---|---|
| Cambiar teléfono, horario, Instagram o agregar el correo | `src/config.mjs` → `BUSINESS` |
| Poner la foto del abogado | Guarda `public/assets/abogado.webp` (800×1000) y completa `LAWYER.photo` en `src/config.mjs` |
| Usar el logo oficial en imagen | Guarda `public/assets/logo-blanco.webp` y pon `LOGO_IMAGE = '/assets/logo-blanco.webp'` |
| Mostrar testimonios | Agrégalos en `TESTIMONIALS` y cambia `SHOW_TESTIMONIALS = true` |
| Ocultar las marcas [VERIFICAR] | `SHOW_REVIEW_MARKS = false` en `src/config.mjs` |
| Editar los textos de un servicio | `src/services.mjs` |

Para convertir fotos a WebP puedes usar <https://squoosh.app> (gratis, en el navegador). Las imágenes nuevas deben llevar `loading="lazy"`, como la foto del abogado.

---

## Lista de [PENDIENTE]

- [ ] **Correo electrónico** del despacho → `BUSINESS.email` en `src/config.mjs` (si queda vacío, no se muestra en ninguna parte).
- [ ] **Logos oficiales** (`logo-blanco.jpg` y `flyer-servicios.jpg`): no venían con el proyecto. Se usa un logo tipográfico provisional con la “S” en un rombo dorado (menú, footer, favicon e imagen para redes). Al tenerlos, convierte el logo a WebP, guárdalo en `public/assets/` y activa `LOGO_IMAGE`. Si quieres, también se pueden regenerar el favicon y `og-image.jpg` a partir del logo real.
- [ ] **Foto del abogado** (opcional) → `LAWYER.photo`.
- [ ] **Dominio propio** → cambiar `SITE_URL`.
- [ ] **Testimonios reales** (con permiso de los clientes) → `TESTIMONIALS`.
- [ ] Activar **notificaciones por correo** del formulario en Netlify.
- [ ] Cambiar `SHOW_REVIEW_MARKS` a `false` cuando el abogado haya revisado todo.

## Lista de [VERIFICAR] (60 puntos para que el abogado confirme)

Se ven en las páginas como una etiqueta roja **[VERIFICAR]** mientras `SHOW_REVIEW_MARKS = true`.

**Contratos de alquiler** — `/servicios/contratos-de-alquiler/`
- [ ] Cédula de identidad y electoral (o pasaporte) del propietario y del inquilino.
- [ ] Documento que acredite la propiedad o la facultad de alquilar el inmueble (por ejemplo, certificado de título o poder del propietario).
- [ ] Datos y cédula del fiador o garante, si lo hay.
- [ ] Información sobre el depósito de alquiler en el Banco Agrícola, cuando corresponda según la Ley 4314.
- [ ] Registro del contrato ante la DGII, cuando aplique.

**Actos de venta** — `/servicios/actos-de-venta/`
- [ ] Cédula de identidad y electoral (o pasaporte) del vendedor y del comprador.
- [ ] Acta de matrimonio y consentimiento del cónyuge, si el vendedor está casado.
- [ ] Certificado de título del inmueble o matrícula del vehículo, según el caso.
- [ ] Certificación de estado jurídico del inmueble emitida por el Registro de Títulos.
- [ ] Constancia de impuestos al día ante la DGII (por ejemplo, IPI cuando aplique).

**Divorcios** — `/servicios/divorcios/`
- [ ] Vive en el exterior y necesita tramitar su divorcio en República Dominicana.
- [ ] Extracto o copia íntegra reciente del acta de matrimonio.
- [ ] Cédula de identidad y electoral (o pasaporte) de ambos cónyuges.
- [ ] Actas de nacimiento de los hijos menores, si los hay.
- [ ] Información sobre los bienes en común (inmuebles, vehículos, cuentas).
- [ ] Acuerdos sobre guarda, visitas y pensión alimentaria, en el divorcio por mutuo consentimiento.
- [ ] Poder especial, si uno de los cónyuges no puede estar presente.
- [ ] Gestionamos el pronunciamiento del divorcio ante la Oficialía del Estado Civil.
- [ ] Cuando el proceso requiera un acto auténtico (por ejemplo, el acto de estipulaciones y convenciones), coordinamos su instrumentación con un notario público.

**Determinación de herederos** — `/servicios/determinacion-de-herederos/`
- [ ] Acta de defunción de la persona fallecida.
- [ ] Actas de nacimiento de los herederos y, si aplica, acta de matrimonio del fallecido.
- [ ] Cédulas de identidad y electoral de los herederos.
- [ ] Documentos de los bienes: certificados de título, matrículas, estados de cuenta.
- [ ] Acto de notoriedad, que se instrumenta con un notario público.
- [ ] Declaración y pago del impuesto sucesoral ante la DGII, cuando corresponda.

**Declaraciones juradas** — `/servicios/declaraciones-juradas/`
- [ ] Cédula de identidad y electoral (o pasaporte) del declarante.
- [ ] Cédulas de los testigos, cuando la declaración los requiera.
- [ ] Documentos de soporte relacionados con lo que se declara.

**Traspaso de vehículos** — `/servicios/traspaso-de-vehiculos/`
- [ ] La matrícula tiene un problema o un dato incorrecto que debe corregirse.
- [ ] Matrícula original del vehículo.
- [ ] Acto de venta con las firmas legalizadas por notario público.
- [ ] Certificación de la Procuraduría General de la República sobre la firma del notario, cuando se requiera.
- [ ] Cédulas de identidad y electoral del vendedor y del comprador.
- [ ] Certificación de no oposición o de investigación del vehículo, si la DGII la solicita.
- [ ] Pago del impuesto de traspaso ante la DGII.

**Transferencia de inmuebles** — `/servicios/transferencia-de-inmuebles/`
- [ ] Certificado de título original del inmueble.
- [ ] Acto de venta (o donación) con firmas legalizadas por notario público.
- [ ] Certificación de estado jurídico del inmueble del Registro de Títulos.
- [ ] Cédulas de identidad y electoral de las partes y, si aplica, de los cónyuges.
- [ ] Recibo de pago del impuesto de transferencia ante la DGII.
- [ ] Constancia de IPI al día, cuando aplique.

**Registro de nombres comerciales** — `/servicios/registro-de-nombres-comerciales/`
- [ ] Su registro de nombre comercial está por vencer y desea renovarlo.
- [ ] Cédula de identidad y electoral (o pasaporte) del solicitante.
- [ ] Descripción de la actividad del negocio.
- [ ] Dirección o domicilio del negocio.
- [ ] Pago de las tasas de ONAPI.

**Constitución de compañías** — `/servicios/constitucion-de-companias/`
- [ ] Cédulas de identidad y electoral (o pasaportes) de los socios.
- [ ] Certificado de registro del nombre comercial en ONAPI.
- [ ] Domicilio social de la empresa.
- [ ] Capital social y distribución de cuotas o acciones entre los socios.
- [ ] Datos de quien será gerente o administrador.
- [ ] Estatutos, acta de asamblea constitutiva y nómina de socios (los preparamos nosotros).

**Permiso de salida del país a menores** — `/servicios/permiso-de-salida-de-menores/`
- [ ] Necesita un permiso de salida por un periodo prolongado.
- [ ] Acta de nacimiento del menor (copia íntegra o extracto reciente).
- [ ] Pasaporte vigente del menor.
- [ ] Cédulas de identidad y electoral (o pasaportes) de los padres.
- [ ] Autorización del padre o la madre que no viaja, con firma legalizada por notario público.
- [ ] Datos del viaje y de la persona que acompañará al menor.
- [ ] Requisitos adicionales de CONANI o de la Dirección General de Migración, según el caso.
- [ ] Le orientamos y acompañamos en la solicitud del permiso.

**Otros textos para revisar (sin marca):**
- [ ] Aviso legal y privacidad (`/aviso-legal/`): mención a la Ley núm. 172-13 de protección de datos.
- [ ] Preguntas frecuentes de la página de inicio.
- [ ] La nota fija de los servicios con legalización: *“Nuestro despacho redacta el documento y coordina la legalización de firmas con un notario público… El abogado no actúa como notario.”*
