"""Descarga cotizaciones usando yfinance, pidiendo los datos por teclado."""

from datetime import date, datetime, timedelta

import pandas as pd
import yfinance as yf

from metricas import resumen, retornos_log

# Tasa libre de riesgo: rendimiento anual (en %) de la Letra del Tesoro de
# EE.UU. a 13 semanas.
TICKER_TASA = "^IRX"

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
    """Pide una fecha en formato DD-MM-AAAA (o DD/MM/AAAA) hasta que sea válida."""
    while True:
        valor = pedir_texto(mensaje, defecto.strftime("%d-%m-%Y")).replace("/", "-")
        try:
            return datetime.strptime(valor, "%d-%m-%Y").date()
        except ValueError:
            print("  Fecha inválida. Usá el formato DD-MM-AAAA, por ejemplo 31-01-2025.")


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


def descargar(ticker: str, inicio: date, fin: date, intervalo: str):
    """Devuelve los precios de `ticker` entre `inicio` y `fin` (ambos incluidos)
    y la moneda en la que cotiza (por ejemplo "USD" o "ARS")."""
    activo = yf.Ticker(ticker)
    # yfinance no incluye la fecha de fin, por eso se le suma un día.
    datos = activo.history(start=inicio, end=fin + timedelta(days=1), interval=intervalo)
    moneda = activo.history_metadata.get("currency") if not datos.empty else None
    return datos, moneda


def tasa_promedio(inicio: date, fin: date):
    """Promedio del rendimiento de ^IRX entre `inicio` y `fin`, en decimal
    (0.0366 = 3,66%). Devuelve None si no hay datos para ese rango."""
    datos, _ = descargar(TICKER_TASA, inicio, fin, "1d")
    if datos.empty:
        return None
    return float(datos["Close"].mean()) / 100


def pedir_cartera() -> dict:
    """Pide los tickers con su peso en % (ej. "JPM 40, BA 60") hasta que los
    datos sean válidos y los pesos sumen 100%. Devuelve {ticker: peso decimal}."""
    while True:
        valor = pedir_texto("Tickers y peso en % (ej: JPM 40, BA 60)", "AAPL 100")
        cartera = {}
        error = None
        for parte in valor.upper().replace("%", "").split(","):
            elementos = parte.split()
            if len(elementos) != 2:
                error = f"'{parte.strip()}' tiene que ser un ticker y su peso, por ejemplo JPM 40."
                break
            ticker, peso = elementos
            try:
                peso = float(peso)
            except ValueError:
                error = f"El peso de {ticker} no es un número."
                break
            if peso <= 0:
                error = f"El peso de {ticker} tiene que ser mayor a 0."
                break
            if ticker in cartera:
                error = f"{ticker} está repetido."
                break
            cartera[ticker] = peso
        if error is None:
            total = sum(cartera.values())
            if abs(total - 100) < 1e-9:
                return {ticker: peso / 100 for ticker, peso in cartera.items()}
            error = f"Los pesos suman {total:g}%, tienen que sumar 100%."
        print(f"  {error}")


def descargar_validos(tickers: list, inicio: date, fin: date, intervalo: str) -> dict:
    """Descarga cada ticker y descarta los que no sirven para el análisis."""
    validos = {}
    for ticker in tickers:
        datos, moneda = descargar(ticker, inicio, fin, intervalo)
        if datos.empty:
            print(f"  {ticker}: no se encontraron datos en ese rango, se omite.")
        elif moneda != "USD":
            # La tasa libre de riesgo es en dólares: el activo también tiene que serlo.
            print(f"  {ticker}: cotiza en {moneda}, no en USD, se omite.")
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
        f" (promedio de {TICKER_TASA}; log: {r['tasa_libre_riesgo_log']:.2%})"
    )
    print(f"  Sharpe ratio:               {r['sharpe']:8.2f}")


def mostrar_comparativa(resumenes: dict, cartera: dict, tasa_libre_riesgo: float):
    """Tabla con una fila por activo, ordenada de mayor a menor Sharpe."""
    tabla = pd.DataFrame(
        {
            "Peso": cartera,
            "Retornos": {t: r["observaciones"] for t, r in resumenes.items()},
            "Ret. log total": {t: r["retorno_log_total"] for t, r in resumenes.items()},
            "Ret. log anual": {t: r["retorno_log_anual"] for t, r in resumenes.items()},
            "Volatilidad anual": {t: r["volatilidad_anual"] for t, r in resumenes.items()},
            "Sharpe": {t: r["sharpe"] for t, r in resumenes.items()},
        }
    ).sort_values("Sharpe", ascending=False)
    porcentaje = "{:.2%}".format
    print(tabla.to_string(formatters={
        "Peso": porcentaje,
        "Ret. log total": porcentaje,
        "Ret. log anual": porcentaje,
        "Volatilidad anual": porcentaje,
        "Sharpe": "{:.2f}".format,
    }))
    print(f"\nTasa libre de riesgo (promedio de {TICKER_TASA}): {tasa_libre_riesgo:.2%}")


def main():
    hoy = date.today()
    cartera = pedir_cartera()
    while True:
        inicio = pedir_fecha("Fecha de inicio (DD-MM-AAAA)", hoy - timedelta(days=30))
        fin = pedir_fecha("Fecha de fin (DD-MM-AAAA)", hoy)
        if inicio <= fin:
            break
        print("  La fecha de inicio tiene que ser anterior o igual a la de fin.")
    intervalo = pedir_frecuencia()

    print()
    validos = descargar_validos(list(cartera), inicio, fin, intervalo)
    if len(validos) < len(cartera):
        # Sin todos los activos, los pesos de la cartera ya no suman 100%.
        print("\nNo se pudieron descargar todos los activos de la cartera.")
        return
    tasa_libre_riesgo = tasa_promedio(inicio, fin)
    if tasa_libre_riesgo is None:
        print(f"\nNo hay datos de {TICKER_TASA} entre {inicio:%d-%m-%Y} y {fin:%d-%m-%Y}.")
        return

    resumenes = {
        ticker: resumen(datos["Close"], intervalo, tasa_libre_riesgo)
        for ticker, datos in validos.items()
    }
    print(f"\n{', '.join(validos)} | {inicio:%d-%m-%Y} a {fin:%d-%m-%Y} | intervalo {intervalo}\n")
    if len(validos) == 1:
        ticker = next(iter(validos))
        mostrar_detalle(ticker, validos[ticker], resumenes[ticker], tasa_libre_riesgo)
    else:
        mostrar_comparativa(resumenes, cartera, tasa_libre_riesgo)


if __name__ == "__main__":
    main()
