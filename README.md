# Finanzas

Trabajo práctico de análisis financiero con [yfinance](https://github.com/ranaroussi/yfinance).

## Instalación

```bash
pip install -r requirements.txt
```

## Uso

```bash
# Cierres de GGAL (ADR, NYSE) de los últimos 5 días
python src/cotizaciones.py

# Otro ticker y período (acciones de BYMA llevan sufijo .BA)
python src/cotizaciones.py GGAL.BA 1mo
```
