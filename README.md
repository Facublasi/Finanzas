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
