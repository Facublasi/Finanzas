"""Descarga cotizaciones usando yfinance, pidiendo los datos por teclado."""

from datetime import date, datetime, timedelta

import pandas as pd
import yfinance as yf

from metricas import resumen, retornos_log

# Todos los activos se analizan en dólares.
MONEDA = "USD"
# Tasa libre de riesgo: rendimiento anual (en %) de la Letra del Tesoro de
# EE.UU. a 13 semanas.
TICKER_TASA = "^IRX"

# Acciones argentinas: ticker en BYMA (pesos) -> ADR en EE.UU. (dólares).
ADRS = {
    "GGAL.BA": "GGAL",
    "YPFD.BA": "YPF",
    "PAMP.BA": "PAM",
    "BMA.BA": "BMA",
    "BBAR.BA": "BBAR",
    "SUPV.BA": "SUPV",
    "CEPU.BA": "CEPU",
    "EDN.BA": "EDN",
    "TGSU2.BA": "TGS",
    "TECO2.BA": "TEO",
    "LOMA.BA": "LOMA",
    "CRES.BA": "CRESY",
    "IRSA.BA": "IRS",
}

FRECUENCIAS = {
    "1": ("1d", "Diaria"),
    "2": ("1wk", "Semanal"),
    "3": ("1mo", "Mensual"),
}


def pedir_texto(mensaje: str, defecto: str) -> str:
    """Pide un texto; si se deja vacío, usa el valor por defecto."""
    valor = input(f"{mensaje} [{defecto}]: ").strip()
    return valor or defecto


def pedir_fecha(mensaje: str, defecto: date) -> date:
    """Pide una fecha en formato AAAA-MM-DD hasta que sea válida."""
    while True:
        valor = pedir_texto(mensaje, defecto.isoformat())
        try:
            return datetime.strptime(valor, "%Y-%m-%d").date()
        except ValueError:
            print("  Fecha inválida. Usá el formato AAAA-MM-DD, por ejemplo 2025-01-31.")


def pedir_frecuencia() -> str:
    """Muestra el menú de frecuencias y devuelve el intervalo de yfinance."""
    print("Frecuencia:")
    for opcion, (_, nombre) in FRECUENCIAS.items():
        print(f"  {opcion}) {nombre}")
    while True:
        opcion = pedir_texto("Elegí una opción", "1")
        if opcion in FRECUENCIAS:
            return FRECUENCIAS[opcion][0]
        print("  Opción inválida. Elegí 1, 2 o 3.")


def pedir_tasa(mensaje: str, defecto: float) -> float:
    """Pide una tasa en porcentaje (ej. 4.5) y la devuelve en decimal (0.045)."""
    while True:
        valor = pedir_texto(mensaje, f"{defecto:g}").replace(",", ".")
        try:
            tasa = float(valor)
        except ValueError:
            print("  Tasa inválida. Ingresá un número, por ejemplo 4.5 para 4,5%.")
            continue
        if tasa <= -100:
            print("  La tasa tiene que ser mayor a -100%.")
            continue
        return tasa / 100


def descargar(ticker: str, inicio: date, fin: date, intervalo: str):
    """Devuelve los precios de `ticker` entre `inicio` y `fin` (ambos incluidos)
    y la moneda en la que cotiza (por ejemplo "USD" o "ARS")."""
    activo = yf.Ticker(ticker)
    # yfinance no incluye la fecha de fin, por eso se le suma un día.
    datos = activo.history(start=inicio, end=fin + timedelta(days=1), interval=intervalo)
    moneda = activo.history_metadata.get("currency") if not datos.empty else None
    return datos, moneda


def tasa_promedio(inicio: date, fin: date):
    """Promedio del rendimiento de ^IRX entre `inicio` y `fin`, en %.

    Devuelve None si no hay datos para ese rango.
    """
    datos, _ = descargar(TICKER_TASA, inicio, fin, "1d")
    if datos.empty:
        return None
    return round(float(datos["Close"].mean()), 2)


def pedir_tickers() -> list:
    """Pide uno o varios tickers separados por coma o espacio."""
    while True:
        valor = pedir_texto("Tickers separados por coma (tienen que cotizar en USD)", "GGAL")
        tickers = list(dict.fromkeys(valor.upper().replace(",", " ").split()))
        locales = [t for t in tickers if t in ADRS]
        if not locales:
            return tickers
        for t in locales:
            print(f"  {t} cotiza en pesos. Para acciones argentinas usá el ADR: {ADRS[t]}")


def descargar_validos(tickers: list, inicio: date, fin: date, intervalo: str) -> dict:
    """Descarga cada ticker y descarta los que no sirven para el análisis."""
    validos = {}
    for ticker in tickers:
        datos, moneda = descargar(ticker, inicio, fin, intervalo)
        if datos.empty:
            print(f"  {ticker}: no se encontraron datos en ese rango, se omite.")
        elif moneda != MONEDA:
            print(f"  {ticker}: cotiza en {moneda}, se omite (solo se analizan activos"
                  f" en {MONEDA}; para acciones argentinas, usá el ADR).")
        elif len(datos) < 3:
            print(f"  {ticker}: hacen falta al menos 3 precios para calcular la"
                  " volatilidad, se omite.")
        else:
            validos[ticker] = datos
    return validos


def mostrar_detalle(ticker: str, datos, r: dict, tasa_libre_riesgo: float):
    """Tabla de precios y resumen de métricas de un único activo."""
    datos["Ret. log"] = retornos_log(datos["Close"])
    print(datos[["Open", "High", "Low", "Close", "Volume", "Ret. log"]])
    print(f"\nResumen de {ticker} ({r['observaciones']} retornos)")
    print(f"  Retorno logarítmico total:  {r['retorno_log_total']:8.2%}")
    print(f"  Retorno logarítmico medio:  {r['retorno_log_medio']:8.4%} por período")
    print(f"  Retorno logarítmico anual:  {r['retorno_log_anual']:8.2%}")
    print(f"  Volatilidad:                {r['volatilidad_periodo']:8.4%} por período")
    print(f"  Volatilidad anualizada:     {r['volatilidad_anual']:8.2%}")
    print(
        f"  Tasa libre de riesgo:       {tasa_libre_riesgo:8.2%}"
        f" (log: {r['tasa_libre_riesgo_log']:.2%})"
    )
    print(f"  Sharpe ratio:               {r['sharpe']:8.2f}")


def mostrar_comparativa(resumenes: dict, tasa_libre_riesgo: float):
    """Tabla con una fila por activo, ordenada de mayor a menor Sharpe."""
    tabla = pd.DataFrame(
        {
            "Retornos": {t: r["observaciones"] for t, r in resumenes.items()},
            "Ret. log total": {t: r["retorno_log_total"] for t, r in resumenes.items()},
            "Ret. log anual": {t: r["retorno_log_anual"] for t, r in resumenes.items()},
            "Volatilidad anual": {t: r["volatilidad_anual"] for t, r in resumenes.items()},
            "Sharpe": {t: r["sharpe"] for t, r in resumenes.items()},
        }
    ).sort_values("Sharpe", ascending=False)
    porcentaje = "{:.2%}".format
    print(tabla.to_string(formatters={
        "Ret. log total": porcentaje,
        "Ret. log anual": porcentaje,
        "Volatilidad anual": porcentaje,
        "Sharpe": "{:.2f}".format,
    }))
    print(f"\nTasa libre de riesgo: {tasa_libre_riesgo:.2%}")


def main():
    hoy = date.today()
    tickers = pedir_tickers()
    while True:
        inicio = pedir_fecha("Fecha de inicio (AAAA-MM-DD)", hoy - timedelta(days=30))
        fin = pedir_fecha("Fecha de fin (AAAA-MM-DD)", hoy)
        if inicio <= fin:
            break
        print("  La fecha de inicio tiene que ser anterior o igual a la de fin.")
    intervalo = pedir_frecuencia()

    print()
    validos = descargar_validos(tickers, inicio, fin, intervalo)
    if not validos:
        print("\nNo quedó ningún activo para analizar.")
        return
    tasa = tasa_promedio(inicio, fin)
    if tasa is None:
        print(f"\nNo hay datos de {TICKER_TASA} entre {inicio} y {fin}.")
        return
    print(f"\nTasa libre de riesgo: promedio de {TICKER_TASA} (Letra del Tesoro de"
          f" EE.UU. a 13 semanas) entre {inicio} y {fin}: {tasa:.2f}%")
    tasa_libre_riesgo = pedir_tasa("Tasa libre de riesgo anual en %", tasa)

    resumenes = {
        ticker: resumen(datos["Close"], intervalo, tasa_libre_riesgo)
        for ticker, datos in validos.items()
    }
    print(f"\n{', '.join(validos)} | {inicio} a {fin} | intervalo {intervalo}\n")
    if len(validos) == 1:
        ticker = next(iter(validos))
        mostrar_detalle(ticker, validos[ticker], resumenes[ticker], tasa_libre_riesgo)
    else:
        mostrar_comparativa(resumenes, tasa_libre_riesgo)


if __name__ == "__main__":
    main()
