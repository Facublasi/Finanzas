# Finanzas

Trabajo práctico de análisis financiero con [yfinance](https://github.com/ranaroussi/yfinance).

## Instalación

```bash
pip install -r requirements.txt
```

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
```

## Cálculos

Con los precios de cierre (`src/metricas.py`):

- **Retorno logarítmico** de cada período: `ln(P_t / P_t-1)`.
- **Retorno logarítmico total**: suma de los retornos, igual a `ln(P_fin / P_inicio)`.
- **Volatilidad**: desvío estándar muestral de los retornos logarítmicos.
- **Anualización**: retorno medio × períodos por año y volatilidad × √(períodos por año), con 252 días hábiles, 52 semanas o 12 meses según la frecuencia. Funciona igual para plazos menores o mayores a un año.
- **Tasa libre de riesgo**: promedio de `^IRX` (rendimiento anual de la Letra del Tesoro de EE.UU. a 13 semanas) entre la fecha de inicio y la de fin. Se calcula sola, no se pregunta.
- **Sharpe ratio**: `(retorno anualizado − ln(1 + rf)) / volatilidad anualizada`. La tasa se pasa a logarítmica para restarla en la misma escala que el retorno.

Los precios que devuelve yfinance están ajustados por dividendos y splits. Con frecuencia mensual, cada precio es el cierre del último día hábil del mes.
