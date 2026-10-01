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
```

Muestra apertura, máximo, mínimo, cierre y volumen. Las fechas de inicio y fin están incluidas.
