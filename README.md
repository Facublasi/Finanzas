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
Ticker (tiene que cotizar en USD) [GGAL]: AAPL
Fecha de inicio (AAAA-MM-DD) [2026-09-01]: 2026-01-01
Fecha de fin (AAAA-MM-DD) [2026-10-01]: 2026-06-30
Frecuencia:
  1) Diaria
  2) Semanal
  3) Mensual
Elegí una opción [1]: 2

Tasa libre de riesgo: promedio de ^IRX (Letra del Tesoro de EE.UU. a 13 semanas) entre 2026-01-01 y 2026-06-30: 3.6%
Tasa libre de riesgo anual en % [3.6]:
```

Muestra apertura, máximo, mínimo, cierre y volumen. Las fechas de inicio y fin están incluidas.

Solo se analizan activos que cotizan en **USD** (por ejemplo `AAPL` o `GGAL`, el ADR en NYSE). Si el ticker cotiza en otra moneda (como `GGAL.BA`, en pesos), el programa avisa y termina.

Para **acciones argentinas** se usa el **ADR** que cotiza en EE.UU. Si se ingresa el ticker de BYMA, el programa indica cuál es el ADR:

| BYMA | ADR |
|---|---|
| GGAL.BA | GGAL |
| YPFD.BA | YPF |
| PAMP.BA | PAM |
| BMA.BA | BMA |
| BBAR.BA | BBAR |
| SUPV.BA | SUPV |
| CEPU.BA | CEPU |
| EDN.BA | EDN |
| TGSU2.BA | TGS |
| TECO2.BA | TEO |
| LOMA.BA | LOMA |
| CRES.BA | CRESY |
| IRSA.BA | IRS |

## Retornos y volatilidad

Además de los precios, el programa calcula con los precios de cierre (`src/metricas.py`):

- **Retorno logarítmico** de cada período: `ln(P_t / P_t-1)` (columna `Ret. log`).
- **Retorno logarítmico total**: suma de los retornos del período, igual a `ln(P_fin / P_inicio)`.
- **Volatilidad**: desvío estándar muestral de los retornos logarítmicos.
- **Volatilidad anualizada**: volatilidad × √(períodos por año), con 252 días hábiles, 52 semanas o 12 meses según la frecuencia elegida.
- **Retorno logarítmico anualizado**: retorno medio por período × períodos por año. Funciona igual para plazos menores o mayores a un año.
- **Sharpe ratio**: `(retorno anualizado − ln(1 + rf)) / volatilidad anualizada`. La tasa libre de riesgo `rf` se ingresa como tasa efectiva anual y se pasa a logarítmica para restarla en la misma escala que el retorno. Siempre es la tasa de EE.UU.: el valor por defecto es el promedio de `^IRX` (rendimiento de la Letra del Tesoro a 13 semanas) entre la fecha de inicio y la de fin. Se acepta con Enter o se escribe otra.

Los precios que devuelve yfinance están ajustados por dividendos y splits.
