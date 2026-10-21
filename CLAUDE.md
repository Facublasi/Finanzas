# Contexto del proyecto

Trabajo práctico de finanzas (análisis de activos y carteras con yfinance). El código se construye de a poco durante varias semanas; cada cambio se prueba, se commitea y se sube a `main`.

## Estructura

- `src/cotizaciones.py`: programa principal (se corre con `python src/cotizaciones.py`). Pide los datos, descarga precios y muestra resultados.
- `src/metricas.py`: solo las fórmulas (retornos, volatilidad, Sharpe, cartera).
- `src/presentacion.py`: todo lo que se muestra. Las tablas de la pantalla y la presentación con la estética de Tu Asesoría Financiera (`reportes/reporte.html` y `reportes/reporte.pdf`).
- `src/assets/`: logo, tipografías (Cinzel, EB Garamond, Lato) y `plantilla.html` (estilos de la presentación).
- `README.md`: describe el uso y los cálculos; mantenerlo actualizado con cada cambio.

Es un único programa en tres archivos: datos (`cotizaciones.py`), cálculos (`metricas.py`) y presentación (`presentacion.py`). Mantener esa separación.

## Qué hace hoy

1. Pide tickers con su peso en % (ej: `JPM 40, BA 30, AAL 20, XOM 10`); los pesos tienen que sumar 100%.
2. Pide fecha de inicio y de fin en **DD-MM-AAAA** (también acepta DD/MM/AAAA) y la frecuencia (diaria, semanal, mensual).
3. Descarga precios ajustados (Adj Close) de cada activo. Si alguno no tiene datos, no cotiza en USD o tiene menos de 3 precios, avisa y termina.
4. Tasa libre de riesgo: promedio de `^IRX` entre las fechas. **No se pregunta.**
5. Por activo: retorno logarítmico, retorno anualizado, volatilidad anualizada y Sharpe.
6. Cartera: retorno esperado `Σ w·E(R)`, volatilidad `√(wᵀΣw)`, Sharpe, matrices de covarianzas y correlaciones.
7. Opcional: proyecciones de analistas de Yahoo (promedio y rango del precio objetivo actual, igual que Yahoo Finance; tendencia del consenso en 3 meses; precisión de los objetivos publicados entre hace 36 y 12 meses, uno por banco por trimestre (cumplidos y tocados, por activo y por banco); consenso de hace 36, 24 y 12 meses contra la suba real de los 12 meses siguientes, sin ventanas superpuestas, y suba real anualizada; objetivo implícito de los ETF por sus 10 principales tenencias). Los objetivos anteriores a un split se dividen por su proporción.
8. Guarda una presentación tipo diapositivas (16:9) en HTML y PDF con la marca Tu Asesoría Financiera: paleta azul marino, dorado y crema; logo y datos de contacto. El PDF se genera con Playwright (Chromium); si no está, queda solo el HTML.

## Decisiones tomadas (no cambiar sin que el usuario lo pida)

- Solo activos en USD. La tasa libre de riesgo siempre es la de EE.UU. (`^IRX`).
- Sin foco en activos argentinos: no agregar tablas de ADRs ni lógica específica de BYMA.
- Fechas en formato DD-MM-AAAA.
- Retornos logarítmicos, desvío muestral (ddof=1), métricas anualizadas (252 / 52 / 12). Sharpe = (retorno anual − ln(1 + rf)) / volatilidad anual.
- Pesos de la cartera fijos durante el período.

## Pendiente de definir con el profesor

El profesor usa **retornos aritméticos**, **desvío poblacional** y **Sharpe sin anualizar** (por período). Sus precios de control tampoco coincidieron con los de yfinance (incluso para BA y AAL, que no pagan dividendos); falta saber de dónde saca los datos. No cambiar estos criterios hasta que el usuario lo confirme.

## Forma de trabajo

- Hacer solo lo que se pide; no agregar funcionalidades por cuenta propia. Si algo parece útil, proponerlo y esperar.
- No inventar valores ni supuestos (por ejemplo, tasas): si no hay un dato, decirlo.
- Antes de subir, probar con casos reales y verificar los cálculos a mano o por otro camino.
- Explicar en español, claro y paso a paso, sin vueltas.
