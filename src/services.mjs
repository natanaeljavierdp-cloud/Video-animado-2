// =============================================================
//  SERVICIOS — contenido de las 10 páginas de servicio.
//  Cada requisito lleva la marca [VERIFICAR] para que el abogado
//  lo confirme. Se ocultan todas cambiando SHOW_REVIEW_MARKS en config.mjs.
//
//  IMPORTANTE: el Lic. Sandoval es abogado, NO notario. Cuando un documento
//  requiere legalización de firmas o acto notarial, el despacho lo prepara y
//  COORDINA la legalización con un notario público.
// =============================================================

const NOTARY_NOTE =
  'Nuestro despacho redacta el documento y coordina la legalización de firmas con un notario público de su confianza o de la zona. El abogado no actúa como notario.';

export const SERVICES = [
  {
    slug: 'contratos-de-alquiler',
    name: 'Contratos de alquiler',
    icon: 'key',
    short: 'Contratos claros para propietarios e inquilinos, de vivienda o local comercial.',
    metaDescription:
      'Redacción y revisión de contratos de alquiler en Puerto Plata y todo el país. Primera consulta gratis por WhatsApp con Sandoval Legal.',
    intro:
      'Un buen contrato de alquiler evita malentendidos sobre el pago, el depósito, las reparaciones y la entrega del inmueble. Redactamos o revisamos su contrato de vivienda o de local comercial para que sus derechos y obligaciones queden por escrito, en un lenguaje claro.',
    when: [
      'Va a alquilar una casa, apartamento o local y quiere un contrato a su medida.',
      'Le entregaron un contrato y quiere que un abogado lo revise antes de firmar.',
      'Necesita renovar, modificar o terminar un contrato de alquiler vigente.',
      'Quiere dejar claras las condiciones del depósito, los aumentos y las reparaciones.',
    ],
    documents: [
      'Cédula de identidad y electoral (o pasaporte) del propietario y del inquilino. [VERIFICAR]',
      'Documento que acredite la propiedad o la facultad de alquilar el inmueble (por ejemplo, certificado de título o poder del propietario). [VERIFICAR]',
      'Dirección y descripción del inmueble que se alquila.',
      'Monto del alquiler, depósito, duración y forma de pago acordados.',
      'Datos y cédula del fiador o garante, si lo hay. [VERIFICAR]',
      'Información sobre el depósito de alquiler en el Banco Agrícola, cuando corresponda según la Ley 4314. [VERIFICAR]',
      'Registro del contrato ante la DGII, cuando aplique. [VERIFICAR]',
    ],
    steps: [
      ['Consulta gratis', 'Conversamos por WhatsApp o videollamada sobre el inmueble y lo que las partes acordaron.'],
      ['Redacción o revisión', 'Preparamos el contrato o le señalamos los puntos a corregir del borrador que ya tiene.'],
      ['Ajustes con las partes', 'Incorporamos los cambios que propietario e inquilino acuerden.'],
      ['Firma y legalización', 'Coordinamos la legalización de las firmas con un notario público.'],
      ['Entrega y registro', 'Le entregamos su contrato y le orientamos sobre el depósito y el registro cuando correspondan.'],
    ],
    notary: true,
  },
  {
    slug: 'actos-de-venta',
    name: 'Actos de venta',
    icon: 'handshake',
    short: 'Compraventa de inmuebles, vehículos y otros bienes con respaldo legal.',
    metaDescription:
      'Redacción de actos de venta de inmuebles, vehículos y otros bienes en Puerto Plata y todo el país. Consulta gratis con Sandoval Legal.',
    intro:
      'El acto de venta es el documento que deja constancia de una compraventa. Lo redactamos con los datos correctos del bien y de las partes, y le orientamos sobre las verificaciones previas y los pasos posteriores ante las instituciones correspondientes.',
    when: [
      'Va a comprar o vender una casa, un solar, un apartamento o un vehículo.',
      'Quiere verificar la situación legal del bien antes de pagar.',
      'Necesita formalizar una venta que se hizo de palabra.',
      'Requiere el acto de venta para un traspaso o una transferencia posterior.',
    ],
    documents: [
      'Cédula de identidad y electoral (o pasaporte) del vendedor y del comprador. [VERIFICAR]',
      'Acta de matrimonio y consentimiento del cónyuge, si el vendedor está casado. [VERIFICAR]',
      'Certificado de título del inmueble o matrícula del vehículo, según el caso. [VERIFICAR]',
      'Certificación de estado jurídico del inmueble emitida por el Registro de Títulos. [VERIFICAR]',
      'Constancia de impuestos al día ante la DGII (por ejemplo, IPI cuando aplique). [VERIFICAR]',
      'Precio, forma de pago y condiciones acordadas entre las partes.',
    ],
    steps: [
      ['Consulta gratis', 'Revisamos qué se vende, entre quiénes y en qué condiciones.'],
      ['Verificaciones previas', 'Le indicamos qué certificaciones conviene solicitar antes de firmar.'],
      ['Redacción del acto', 'Preparamos el acto de venta con los datos del bien y de las partes.'],
      ['Firma y legalización', 'Coordinamos la legalización de las firmas con un notario público.'],
      ['Pasos posteriores', 'Le orientamos sobre el pago de impuestos y el registro ante DGII o Registro de Títulos.'],
    ],
    notary: true,
  },
  {
    slug: 'divorcios',
    name: 'Divorcios',
    icon: 'rings',
    short: 'Acompañamiento en divorcios por mutuo consentimiento y otras causas.',
    metaDescription:
      'Abogado de divorcios en Puerto Plata. Divorcio por mutuo consentimiento y otras causas, con consulta gratis y atención online en todo el país.',
    intro:
      'Un divorcio es un proceso delicado. Le explicamos con claridad las opciones que existen en República Dominicana —como el divorcio por mutuo consentimiento o por causa determinada— y le acompañamos en cada etapa, cuidando los acuerdos sobre bienes, hijos y pensión.',
    when: [
      'Usted y su pareja decidieron divorciarse de común acuerdo.',
      'Desea divorciarse y su pareja no está de acuerdo.',
      'Necesita definir la guarda, visitas y manutención de los hijos menores.',
      'Vive en el exterior y necesita tramitar su divorcio en República Dominicana. [VERIFICAR]',
    ],
    documents: [
      'Extracto o copia íntegra reciente del acta de matrimonio. [VERIFICAR]',
      'Cédula de identidad y electoral (o pasaporte) de ambos cónyuges. [VERIFICAR]',
      'Actas de nacimiento de los hijos menores, si los hay. [VERIFICAR]',
      'Información sobre los bienes en común (inmuebles, vehículos, cuentas). [VERIFICAR]',
      'Acuerdos sobre guarda, visitas y pensión alimentaria, en el divorcio por mutuo consentimiento. [VERIFICAR]',
      'Poder especial, si uno de los cónyuges no puede estar presente. [VERIFICAR]',
    ],
    steps: [
      ['Consulta gratis', 'Escuchamos su caso y le explicamos el tipo de divorcio que corresponde.'],
      ['Preparación', 'Reunimos los documentos y redactamos los acuerdos o la demanda, según el caso.'],
      ['Proceso ante el tribunal', 'Depositamos el expediente y le representamos en las audiencias.'],
      ['Sentencia', 'Le informamos el resultado y los pasos que siguen.'],
      ['Pronunciamiento', 'Gestionamos el pronunciamiento del divorcio ante la Oficialía del Estado Civil. [VERIFICAR]'],
    ],
    notary: false,
    extraNote:
      'Cuando el proceso requiera un acto auténtico (por ejemplo, el acto de estipulaciones y convenciones), coordinamos su instrumentación con un notario público. [VERIFICAR]',
  },
  {
    slug: 'determinacion-de-herederos',
    name: 'Determinación de herederos',
    icon: 'family',
    short: 'Identificación legal de los herederos para disponer de los bienes de una sucesión.',
    metaDescription:
      'Determinación de herederos y sucesiones en Puerto Plata y todo el país. Le orientamos paso a paso. Primera consulta gratis con Sandoval Legal.',
    intro:
      'Cuando una persona fallece, sus herederos necesitan acreditar legalmente esa condición para vender, transferir o administrar los bienes. Le orientamos en la determinación de herederos y en los trámites relacionados con la sucesión.',
    when: [
      'Falleció un familiar y dejó una casa, un solar, un vehículo o cuentas bancarias.',
      'Quiere transferir a nombre de los herederos un inmueble del fallecido.',
      'Un banco o institución le solicita la determinación de herederos.',
      'Varios herederos necesitan ponerse de acuerdo sobre los bienes.',
    ],
    documents: [
      'Acta de defunción de la persona fallecida. [VERIFICAR]',
      'Actas de nacimiento de los herederos y, si aplica, acta de matrimonio del fallecido. [VERIFICAR]',
      'Cédulas de identidad y electoral de los herederos. [VERIFICAR]',
      'Documentos de los bienes: certificados de título, matrículas, estados de cuenta. [VERIFICAR]',
      'Acto de notoriedad, que se instrumenta con un notario público. [VERIFICAR]',
      'Declaración y pago del impuesto sucesoral ante la DGII, cuando corresponda. [VERIFICAR]',
    ],
    steps: [
      ['Consulta gratis', 'Conocemos quién falleció, quiénes son los herederos y qué bienes existen.'],
      ['Reunión de documentos', 'Le indicamos qué actas y certificaciones solicitar.'],
      ['Acto de notoriedad', 'Preparamos la información y coordinamos el acto con un notario público.'],
      ['Gestión del trámite', 'Presentamos las solicitudes ante el tribunal o la institución que corresponda.'],
      ['Entrega', 'Le entregamos la documentación y le orientamos sobre la transferencia de los bienes.'],
    ],
    notary: true,
  },
  {
    slug: 'declaraciones-juradas',
    name: 'Declaraciones juradas',
    icon: 'docPen',
    short: 'Declaraciones de soltería, convivencia, residencia y otras, bien redactadas.',
    metaDescription:
      'Redacción de declaraciones juradas en Puerto Plata y todo el país: soltería, unión libre, residencia y más. Consulta gratis con Sandoval Legal.',
    intro:
      'Muchas instituciones —consulados, bancos, escuelas y oficinas públicas— solicitan una declaración jurada. Redactamos la suya con el contenido y el formato adecuados para el trámite que necesita realizar.',
    when: [
      'Un consulado o embajada le pide una declaración de soltería o de convivencia.',
      'Necesita declarar residencia, dependencia económica o ingresos.',
      'Perdió un documento y le solicitan una declaración para reponerlo.',
      'Una institución le pidió una declaración jurada con testigos.',
    ],
    documents: [
      'Cédula de identidad y electoral (o pasaporte) del declarante. [VERIFICAR]',
      'Cédulas de los testigos, cuando la declaración los requiera. [VERIFICAR]',
      'Documentos de soporte relacionados con lo que se declara. [VERIFICAR]',
      'Requisitos o modelo exigido por la institución que la solicita, si lo tiene.',
    ],
    steps: [
      ['Consulta gratis', 'Nos dice para qué institución es la declaración y qué debe constar.'],
      ['Redacción', 'Preparamos el texto de la declaración según el uso que tendrá.'],
      ['Revisión', 'Usted revisa el documento y confirmamos los datos.'],
      ['Legalización', 'Coordinamos la legalización de la firma con un notario público.'],
      ['Entrega', 'Le entregamos la declaración lista para presentar.'],
    ],
    notary: true,
  },
  {
    slug: 'traspaso-de-vehiculos',
    name: 'Traspaso de vehículos',
    icon: 'car',
    short: 'Traspaso de vehículos ante la DGII, sin vueltas innecesarias.',
    metaDescription:
      'Traspaso de vehículos en Puerto Plata ante la DGII. Preparamos el acto de venta y le guiamos en el proceso. Primera consulta gratis.',
    intro:
      'Al comprar o vender un vehículo, el traspaso pone la matrícula a nombre del nuevo propietario y evita responsabilidades futuras para el vendedor. Preparamos los documentos y le guiamos en el trámite ante la DGII.',
    when: [
      'Compró un vehículo y necesita ponerlo a su nombre.',
      'Vendió un vehículo y quiere asegurarse de que ya no figure a su nombre.',
      'Recibió un vehículo por herencia o donación.',
      'La matrícula tiene un problema o un dato incorrecto que debe corregirse. [VERIFICAR]',
    ],
    documents: [
      'Matrícula original del vehículo. [VERIFICAR]',
      'Acto de venta con las firmas legalizadas por notario público. [VERIFICAR]',
      'Certificación de la Procuraduría General de la República sobre la firma del notario, cuando se requiera. [VERIFICAR]',
      'Cédulas de identidad y electoral del vendedor y del comprador. [VERIFICAR]',
      'Certificación de no oposición o de investigación del vehículo, si la DGII la solicita. [VERIFICAR]',
      'Pago del impuesto de traspaso ante la DGII. [VERIFICAR]',
    ],
    steps: [
      ['Consulta gratis', 'Revisamos los datos del vehículo y de las partes.'],
      ['Acto de venta', 'Redactamos el acto y coordinamos la legalización de firmas con un notario público.'],
      ['Certificaciones', 'Le orientamos sobre las certificaciones que pide la DGII.'],
      ['Gestión ante la DGII', 'Acompañamos el depósito del expediente y el pago de impuestos.'],
      ['Entrega', 'Usted recibe la nueva matrícula a su nombre.'],
    ],
    notary: true,
  },
  {
    slug: 'transferencia-de-inmuebles',
    name: 'Transferencia de inmuebles',
    icon: 'building',
    short: 'Transferencia de casas, solares y apartamentos ante el Registro de Títulos.',
    metaDescription:
      'Transferencia de inmuebles en Puerto Plata: DGII y Registro de Títulos. Acompañamiento legal y primera consulta gratis con Sandoval Legal.',
    intro:
      'Comprar un inmueble no termina con el pago: hay que transferirlo para que el nuevo certificado de título quede a nombre del comprador. Le acompañamos desde la verificación del inmueble hasta el depósito en el Registro de Títulos.',
    when: [
      'Compró una casa, un apartamento o un solar y necesita el título a su nombre.',
      'Recibió un inmueble por herencia o donación.',
      'Quiere comprobar que el inmueble no tiene cargas ni gravámenes antes de comprar.',
      'Tiene un acto de venta antiguo que nunca se registró.',
    ],
    documents: [
      'Certificado de título original del inmueble. [VERIFICAR]',
      'Acto de venta (o donación) con firmas legalizadas por notario público. [VERIFICAR]',
      'Certificación de estado jurídico del inmueble del Registro de Títulos. [VERIFICAR]',
      'Cédulas de identidad y electoral de las partes y, si aplica, de los cónyuges. [VERIFICAR]',
      'Recibo de pago del impuesto de transferencia ante la DGII. [VERIFICAR]',
      'Constancia de IPI al día, cuando aplique. [VERIFICAR]',
    ],
    steps: [
      ['Consulta gratis', 'Conocemos el inmueble y la operación que realizó o va a realizar.'],
      ['Verificación', 'Revisamos el estado jurídico del inmueble antes de avanzar.'],
      ['Documentación', 'Preparamos los actos y coordinamos la legalización de firmas con un notario público.'],
      ['Impuestos y depósito', 'Gestionamos el pago ante la DGII y el depósito en el Registro de Títulos.'],
      ['Entrega', 'Le entregamos el nuevo certificado de título cuando sea emitido.'],
    ],
    notary: true,
  },
  {
    slug: 'registro-de-nombres-comerciales',
    name: 'Registro de nombres comerciales',
    icon: 'tag',
    short: 'Proteja el nombre de su negocio con su registro ante ONAPI.',
    metaDescription:
      'Registro de nombres comerciales ante ONAPI desde Puerto Plata para todo el país. Búsqueda de disponibilidad y solicitud. Consulta gratis.',
    intro:
      'El nombre de su negocio es parte de su identidad. Registrarlo ante la Oficina Nacional de la Propiedad Industrial (ONAPI) le ayuda a protegerlo y es un paso previo habitual para constituir una compañía.',
    when: [
      'Va a abrir un negocio y quiere asegurar su nombre.',
      'Necesita el nombre comercial para constituir una compañía.',
      'Quiere saber si el nombre que eligió está disponible.',
      'Su registro de nombre comercial está por vencer y desea renovarlo. [VERIFICAR]',
    ],
    documents: [
      'Cédula de identidad y electoral (o pasaporte) del solicitante. [VERIFICAR]',
      'Nombre comercial propuesto y algunas alternativas.',
      'Descripción de la actividad del negocio. [VERIFICAR]',
      'Dirección o domicilio del negocio. [VERIFICAR]',
      'Pago de las tasas de ONAPI. [VERIFICAR]',
    ],
    steps: [
      ['Consulta gratis', 'Conversamos sobre su negocio y el nombre que desea.'],
      ['Búsqueda', 'Verificamos la disponibilidad del nombre ante ONAPI.'],
      ['Solicitud', 'Preparamos y presentamos la solicitud de registro.'],
      ['Seguimiento', 'Damos seguimiento al expediente hasta su respuesta.'],
      ['Entrega', 'Le entregamos el certificado de registro cuando sea emitido.'],
    ],
    notary: false,
  },
  {
    slug: 'constitucion-de-companias',
    name: 'Constitución de compañías',
    icon: 'briefcase',
    short: 'Formalice su empresa: SRL, EIRL y otras figuras, de principio a fin.',
    metaDescription:
      'Constitución de compañías (SRL, EIRL, SAS) en Puerto Plata y todo el país: ONAPI, Cámara de Comercio y DGII. Primera consulta gratis.',
    intro:
      'Formalizar su negocio le da respaldo frente a clientes, bancos e instituciones. Le ayudamos a elegir la figura adecuada —como una SRL o una EIRL— y gestionamos los pasos ante ONAPI, la Cámara de Comercio y Producción de Puerto Plata y la DGII.',
    when: [
      'Tiene un negocio informal y quiere formalizarlo.',
      'Va a iniciar un emprendimiento con uno o varios socios.',
      'Necesita una empresa para facturar con comprobantes fiscales.',
      'Quiere saber qué tipo de sociedad le conviene.',
    ],
    documents: [
      'Cédulas de identidad y electoral (o pasaportes) de los socios. [VERIFICAR]',
      'Certificado de registro del nombre comercial en ONAPI. [VERIFICAR]',
      'Domicilio social de la empresa. [VERIFICAR]',
      'Capital social y distribución de cuotas o acciones entre los socios. [VERIFICAR]',
      'Datos de quien será gerente o administrador. [VERIFICAR]',
      'Estatutos, acta de asamblea constitutiva y nómina de socios (los preparamos nosotros). [VERIFICAR]',
    ],
    steps: [
      ['Consulta gratis', 'Definimos la figura societaria y la estructura de la empresa.'],
      ['Nombre comercial', 'Registramos o verificamos el nombre ante ONAPI.'],
      ['Documentos societarios', 'Redactamos estatutos, actas y nómina de socios.'],
      ['Registro mercantil', 'Gestionamos el registro ante la Cámara de Comercio y Producción de Puerto Plata.'],
      ['RNC', 'Le orientamos para la inscripción de la empresa en la DGII.'],
    ],
    notary: false,
  },
  {
    slug: 'permiso-de-salida-de-menores',
    name: 'Permiso de salida del país a menores',
    icon: 'plane',
    short: 'Autorizaciones para que niños, niñas y adolescentes viajen al exterior.',
    metaDescription:
      'Permiso de salida del país para menores en Puerto Plata: autorización de los padres y trámite ante CONANI. Primera consulta gratis.',
    intro:
      'Cuando un menor de edad viaja al exterior sin uno o ambos padres, normalmente se requiere una autorización. Preparamos los documentos y le orientamos en el trámite ante la autoridad correspondiente para que el viaje se haga sin contratiempos.',
    when: [
      'Su hijo o hija viajará con solo uno de los padres.',
      'El menor viajará con un familiar, un tercero o en un grupo escolar.',
      'Uno de los padres vive en el exterior y debe autorizar el viaje.',
      'Necesita un permiso de salida por un periodo prolongado. [VERIFICAR]',
    ],
    documents: [
      'Acta de nacimiento del menor (copia íntegra o extracto reciente). [VERIFICAR]',
      'Pasaporte vigente del menor. [VERIFICAR]',
      'Cédulas de identidad y electoral (o pasaportes) de los padres. [VERIFICAR]',
      'Autorización del padre o la madre que no viaja, con firma legalizada por notario público. [VERIFICAR]',
      'Datos del viaje y de la persona que acompañará al menor. [VERIFICAR]',
      'Requisitos adicionales de CONANI o de la Dirección General de Migración, según el caso. [VERIFICAR]',
    ],
    steps: [
      ['Consulta gratis', 'Revisamos con quién viaja el menor, a dónde y por cuánto tiempo.'],
      ['Autorización', 'Redactamos la autorización de los padres.'],
      ['Legalización', 'Coordinamos la legalización de firmas con un notario público.'],
      ['Gestión ante CONANI', 'Le orientamos y acompañamos en la solicitud del permiso. [VERIFICAR]'],
      ['Entrega', 'Usted recibe el permiso para presentarlo al viajar.'],
    ],
    notary: true,
  },
];

export { NOTARY_NOTE };
