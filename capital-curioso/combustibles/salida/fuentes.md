# Fuentes y verificación — El costo de congelar los combustibles

Fecha de verificación: 15 de noviembre de 2026.

## Datos usados en la pieza

| Dato en pantalla / narración | Valor | Fuente |
|---|---|---|
| Congelamiento de los principales combustibles | hasta el 7 de enero de 2027 | Presidencia de la República; Noticias SIN (13/11/2026) |
| Condición | subsidio semanal no mayor a RD$1,500 millones | Presidencia de la República; Noticias SIN |
| Subsidio de la semana del 14 al 20 de noviembre de 2026 | RD$796.4 millones | MICM; Noticias SIN; Diario Libre |
| Proporción asignado / tope | 53.1 % | **Cálculo propio**: 796.4 ÷ 1,500 = 0.5309. En pantalla se rotula como "cálculo de Capital Curioso". |

El gráfico de barras de la escena 3 es proporcional: la barra del tope mide 570 px y la de la semana mide 570 × 796.4 / 1,500 = 302.6 px.

El esquema de la escena 4 (precio al consumidor / subsidio) **no contiene montos**: se rotula "Esquema ilustrativo: no representa montos reales".

## Enlaces

- Presidencia (fuente primaria): https://prensadelpresidente.gob.do/noticias/presidente-abinader-anuncia-congelamiento-de-precios-de-combustibles-hasta-el-7-de-enero-de-2027-siempre-que-el-subsidio-no-supere-los-rd1500-millones-semanales/
- Noticias SIN: https://noticiassin.com/pais/nacional/2026/11/13/gobierno-congela-precios-de-combustibles-hasta-2027-2169560/
- MICM: https://micm.gob.do/gobierno-congela-precios-de-los-principales-combustibles/
- Diario Libre: https://www.diariolibre.com/economia/energia/2026/11/13/gobierno-congela-el-precio-de-los-combustibles/3720093

## Cómo se verificó (y sus límites)

- Desde el entorno de producción **no fue posible abrir directamente** prensadelpresidente.gob.do ni noticiassin.com (la red del entorno no permite esos dominios).
- Se verificó mediante búsqueda web el 15/11/2026. Los resultados (MICM, Diario Libre, Noticias SIN, El Día, El Dinero, Acento, De Último Minuto) coinciden en: congelamiento hasta el 7 de enero de 2027, condición de RD$1,500 millones semanales y RD$796.4 millones para la semana del 14 al 20 de noviembre. Algunos medios redondean a "RD$796 millones"; la cifra exacta reportada es RD$796.4 millones.
- **No se encontró ningún cambio** de estos datos posterior al anuncio.
- Recomendación: antes de publicar, abrir manualmente el enlace de la Presidencia y el comunicado del MICM para una confirmación final, y revisar si el MICM publicó la cifra de la semana siguiente (21-27 de noviembre) si la pieza sale después del 20 de noviembre.

## Precisión editorial aplicada

- No se afirma que los precios vayan a subir. La narración y el gráfico de la escena 5 dicen explícitamente: superar el tope hace que el congelamiento deje de estar garantizado, y **eso no significa que los precios aumenten automáticamente**.
- No se usan declaraciones textuales, rostros ni voces de funcionarios o periodistas.
- No se usan billetes ni documentos simulados.

## Recursos visuales y sonoros

| Recurso | Origen | Rótulo en pantalla |
|---|---|---|
| 01_signo_interrogacion.jpg, 02_camion_cisterna.jpg, 03_grafico_subida.jpg, 04_mapa_rd.jpg, 05_bomba_gasolina.jpg | Proporcionadas por Capital Curioso (`imagenes_combustibles.zip`) | "IMAGEN ILUSTRATIVA" en todas las escenas donde aparecen y en la portada |
| Logotipo y animación de cierre | `capital_curioso_cierre.mp4`, proporcionado por Capital Curioso | — |
| Narración | `content_5.mp3`, proporcionado por Capital Curioso | — |
| Música | Original, sintetizada por código (`src/audio.py`). Sin muestras de terceros | — |
| Efectos de sonido | Originales, sintetizados por código | — |
| Tipografía | Poppins (SIL Open Font License 1.1), paquete npm `@expo-google-fonts/poppins` | — |

> Pendiente de su parte: confirmar la licencia/origen de las cinco imágenes del zip. Por su aspecto parecen generadas por IA o de banco de imágenes; por eso se rotularon como ilustrativas.
