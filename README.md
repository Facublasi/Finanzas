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
Ticker (acciones de BYMA llevan sufijo .BA) [GGAL]: YPFD.BA
Fecha de inicio (AAAA-MM-DD) [2026-09-01]: 2026-01-01
Fecha de fin (AAAA-MM-DD) [2026-10-01]: 2026-06-30
Frecuencia:
  1) Diaria
  2) Semanal
  3) Mensual
Elegí una opción [1]: 2
Tasa libre de riesgo anual en % (en la moneda del activo) [5]: 4.5
```

Muestra apertura, máximo, mínimo, cierre y volumen. Las fechas de inicio y fin están incluidas.

## Retornos y volatilidad

Además de los precios, el programa calcula con los precios de cierre (`src/metricas.py`):

- **Retorno logarítmico** de cada período: `ln(P_t / P_t-1)` (columna `Ret. log`).
- **Retorno logarítmico total**: suma de los retornos del período, igual a `ln(P_fin / P_inicio)`.
- **Volatilidad**: desvío estándar muestral de los retornos logarítmicos.
- **Volatilidad anualizada**: volatilidad × √(períodos por año), con 252 días hábiles, 52 semanas o 12 meses según la frecuencia elegida.
- **Retorno logarítmico anualizado**: retorno medio por período × períodos por año. Funciona igual para plazos menores o mayores a un año.
- **Sharpe ratio**: `(retorno anualizado − ln(1 + rf)) / volatilidad anualizada`. La tasa libre de riesgo `rf` se ingresa como tasa efectiva anual y se pasa a logarítmica para restarla en la misma escala que el retorno. Tiene que estar en la misma moneda que el activo (USD para AAPL o GGAL, pesos para tickers `.BA`).

Los precios que devuelve yfinance están ajustados por dividendos y splits.
