# Finanzas

Trabajo práctico de análisis financiero con [yfinance](https://github.com/ranaroussi/yfinance).

## Instalación

```bash
pip install -r requirements.txt
playwright install chromium
```

El segundo comando descarga el navegador que se usa para generar el PDF. Si no se instala, el programa igual funciona y guarda la presentación en HTML.

## Uso

```bash
python src/cotizaciones.py
```

El programa pide los datos por teclado. Si apretás Enter sin escribir nada, usa el valor entre corchetes.

```
Tickers y peso en % (ej: JPM 40, BA 60) [AAPL 100]: JPM 40, BA 30, AAL 20, XOM 10
Fecha de inicio (DD-MM-AAAA) [02-09-2026]: 01-04-2021
Fecha de fin (DD-MM-AAAA) [02-10-2026]: 01-03-2026
Frecuencia:
  1) Diaria
  2) Semanal
  3) Mensual
Elegí una opción [1]: 3
¿Analizar proyecciones de analistas? (s/n) [n]: s
```

- Cada activo se escribe con su peso en la cartera, en %, separados por coma. Los pesos tienen que ser mayores a 0 y sumar 100%; si no, el programa avisa y vuelve a preguntar. Para decimales se usa punto (ej: `AAPL 33.33`).
- Las fechas se escriben DD-MM-AAAA (también se acepta DD/MM/AAAA). Las fechas de inicio y fin están incluidas.
- Los activos tienen que cotizar en USD, porque la tasa libre de riesgo es en dólares. Si algún activo no tiene datos, no cotiza en USD o tiene menos de 3 precios, el programa avisa y termina, porque sin él los pesos ya no suman 100%.
- **Un ticker**: muestra la tabla de precios (apertura, máximo, mínimo, cierre, volumen y retorno logarítmico) y el resumen de métricas.
- **Varios tickers**: muestra una tabla comparativa ordenada de mayor a menor Sharpe:

```
      Peso  Retornos Ret. log total Ret. log anual Volatilidad anual Sharpe
XOM 10.00%        59        127.81%         25.99%            25.56%   0.89
JPM 40.00%        59         76.97%         15.65%            23.41%   0.53
BA  30.00%        59        -16.32%         -3.32%            35.64%  -0.19
AAL 20.00%        59        -70.43%        -14.32%            41.89%  -0.42

Tasa libre de riesgo (promedio de ^IRX): 3.38%

Matriz de covarianzas (por período)
         JPM       BA      AAL      XOM
JPM 0.004566 0.002909 0.003838 0.001274
BA  0.002909 0.010587 0.003777 0.000300
AAL 0.003838 0.003777 0.014620 0.000315
XOM 0.001274 0.000300 0.000315 0.005444

Matriz de correlaciones
       JPM     BA    AAL    XOM
JPM 1.0000 0.4184 0.4697 0.2556
BA  0.4184 1.0000 0.3036 0.0395
AAL 0.4697 0.3036 1.0000 0.0353
XOM 0.2556 0.0395 0.0353 1.0000

Cartera (59 retornos)
  Retorno esperado, E(Rp) = Σ w_i · E(R_i)
    Por período:   0.4167%
    Anual:           5.00%
  Volatilidad, σp = √(wᵀ · Σ · w)
    Por período:   6.4967%
    Anual:          22.51%
  Sharpe ratio:       0.07
```

## Proyecciones de analistas

Si respondés `s` a la última pregunta, el programa descarga de Yahoo Finance los precios objetivo de los analistas y muestra una tabla con:

- **Objetivo y Rango**: promedio actual de los precios objetivo (el "1y Target Est" que muestra Yahoo Finance) y el mínimo y máximo. **Suba esperada**: cuánto tendría que subir la acción desde el precio de hoy para llegar al promedio.
- **Tendencia 3m**: cuánto cambió el consenso en los últimos 3 meses. El consenso a una fecha es el promedio del último objetivo de cada banco publicado en los 12 meses anteriores. Por eso puede no coincidir exactamente con el promedio de Yahoo.
- **Precisión de los objetivos pasados** (solo acciones): toma los objetivos publicados entre hace 36 y hace 12 meses y los compara con el precio de cierre 12 meses después. Si un banco publicó varias veces en el mismo trimestre, se usa solo el último, para que los bancos que confirman su objetivo seguido no pesen más.
  - **Evaluados**: cantidad de objetivos comparados.
  - **Cumplidos**: porcentaje en el que el precio final alcanzó el objetivo (o bajó hasta él, si el objetivo esperaba una baja).
  - **Tocados**: porcentaje en el que el precio lo alcanzó en algún momento de esos 12 meses.
  - **Suba prometida**: mediana de cuánto prometía subir cada objetivo desde el precio del día en que se publicó. **Suba real**: mediana de cuánto subió de verdad en los 12 meses siguientes.
  - **Error típico**: mediana de suba real − suba prometida de cada objetivo. Positivo: la acción subió más de lo prometido; negativo, menos. Se usan medianas para que unas pocas subas extremas no distorsionen el resultado.
- **Precisión por banco**: lo mismo, por banco, sumando todas las acciones (solo bancos con al menos 3 objetivos evaluados).

Los precios objetivo publicados antes de un split se corrigen por su proporción, para compararlos con los precios en la misma escala.

Los ETF no tienen analistas propios. Para ellos se calcula un **objetivo implícito**: el promedio de la suba esperada de sus 10 principales tenencias, ponderado por su peso. La tabla indica qué porcentaje del ETF cubren esas tenencias. La precisión pasada no se puede medir para los ETF, porque no hay registro de su composición anterior.

Yahoo limita las consultas cuando son muchas seguidas: el programa reintenta y, si no lo logra, avisa qué activo quedó sin datos.

## Presentación

Además de mostrar los resultados en pantalla, el programa guarda una presentación con la estética de Tu Asesoría Financiera en la carpeta `reportes/`:

- `reportes/reporte.html`: se abre con cualquier navegador.
- `reportes/reporte.pdf`: el mismo contenido en PDF, una diapositiva por página.

Cada vez que se corre el programa, los dos archivos se reemplazan. Las diapositivas son:

1. **Portada**: activos, período, frecuencia y fecha de emisión.
2. **La cartera**: gráfico de pesos, retorno esperado, volatilidad, Sharpe y tasa libre de riesgo.
3. **Métricas por activo**: la misma tabla comparativa de la pantalla, con la fila de la cartera.
4. **Evolución de precios**: gráfico de cada activo con los precios llevados a 100 al inicio del período.
5. **Riesgo, retorno y Sharpe**: gráfico de volatilidad contra retorno y barras con el Sharpe de cada activo y de la cartera.
6. **Correlaciones**: mapa de calor con la mitad de abajo de la matriz (es simétrica y la diagonal siempre vale 1). Usa su propia escala de colores: rojo para −1, amarillo para 0 y verde para 1. La matriz de covarianzas se muestra solo en pantalla.
7. **Analistas** (solo si se pidió): la tabla de proyecciones por activo y los 5 bancos con más objetivos evaluados.
8. **Metodología**: cómo se calcula cada métrica, y los datos de contacto.

Con un solo activo no se incluyen las diapositivas 5 y 6. Los valores son los mismos que se muestran en pantalla, con el mismo redondeo.

## Cálculos

Con los precios de cierre (`src/metricas.py`):

- **Retorno logarítmico** de cada período: `ln(P_t / P_t-1)`.
- **Retorno logarítmico total**: suma de los retornos, igual a `ln(P_fin / P_inicio)`.
- **Volatilidad**: desvío estándar muestral de los retornos logarítmicos.
- **Anualización**: retorno medio × períodos por año y volatilidad × √(períodos por año), con 252 días hábiles, 52 semanas o 12 meses según la frecuencia. Funciona igual para plazos menores o mayores a un año.
- **Tasa libre de riesgo**: promedio de `^IRX` (rendimiento anual de la Letra del Tesoro de EE.UU. a 13 semanas) entre la fecha de inicio y la de fin. Se calcula sola, no se pregunta.
- **Retorno esperado de la cartera**: `E(Rp) = Σ w_i · E(R_i)`, el promedio ponderado por los pesos de los retornos esperados (retorno logarítmico medio) de cada activo. Se muestra por período y anualizado.
- **Volatilidad de la cartera**: `σp = √(wᵀ · Σ · w)`, donde `Σ` es la matriz de covarianzas muestral de los retornos logarítmicos de los activos (alineados por fecha). Se anualiza con √(períodos por año). Los pesos se consideran fijos durante todo el período.
- **Sharpe de la cartera**: `(E(Rp) anual − ln(1 + rf)) / σp anual`, con el mismo criterio que el Sharpe de cada activo.
- **Sharpe ratio**: `(retorno anualizado − ln(1 + rf)) / volatilidad anualizada`. La tasa se pasa a logarítmica para restarla en la misma escala que el retorno.

Los precios que devuelve yfinance están ajustados por dividendos y splits. Con frecuencia mensual, cada precio es el cierre del último día hábil del mes.
