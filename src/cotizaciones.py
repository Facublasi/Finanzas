"""Descarga cotizaciones usando yfinance, pidiendo los datos por teclado."""

import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
import yfinance as yf

from metricas import (
    objetivo_implicito, precision_objetivos, precision_por_banco, resumen, resumen_cartera,
    resumen_precision,
)
from presentacion import (
    generar_reporte, mostrar_analistas, mostrar_cartera, mostrar_comparativa, mostrar_detalle,
)

# Tasa libre de riesgo: rendimiento anual (en %) de la Letra del Tesoro de
# EE.UU. a 13 semanas.
TICKER_TASA = "^IRX"

# Años de precios que se descargan para medir la precisión de los analistas.
# Cada objetivo se evalúa 12 meses después de publicado, así que con 3 años se
# evalúan los publicados entre hace 36 y hace 12 meses.
ANIOS_ANALISTAS = 3

# Carpeta donde se guarda la presentación (HTML y PDF).
CARPETA_REPORTES = Path(__file__).parent.parent / "reportes"

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


def _con_reintentos(funcion, intentos: int = 3, pausa: int = 15):
    """Yahoo corta las consultas cuando son muchas seguidas y a veces responde
    vacío: se reintenta con una pausa antes de darse por vencido."""
    for intento in range(intentos):
        try:
            resultado = funcion()
            if resultado is not None and len(resultado) > 0:
                return resultado
        except Exception:
            pass
        if intento < intentos - 1:
            time.sleep(pausa)
    return None


def descargar_analistas(ticker: str, hoy: date):
    """Datos de analistas de `ticker`.

    Para una acción: precio objetivo actual, historial de objetivos publicados
    y precios diarios para medir su precisión. Para un ETF: sus principales
    tenencias con el precio actual y el objetivo de cada una. Devuelve None si
    Yahoo no responde.
    """
    activo = yf.Ticker(ticker)
    inicio = hoy - timedelta(days=365 * ANIOS_ANALISTAS + 7)
    precios = _con_reintentos(
        lambda: activo.history(start=inicio, end=hoy + timedelta(days=1), auto_adjust=False)
    )
    if precios is None:
        return None

    if activo.history_metadata.get("instrumentType") == "ETF":
        posiciones = _con_reintentos(lambda: activo.funds_data.top_holdings)
        tenencias = []
        for simbolo, fila in (posiciones.iterrows() if posiciones is not None else []):
            objetivos = _con_reintentos(lambda: yf.Ticker(simbolo.replace(".", "-")).analyst_price_targets)
            objetivos = objetivos or {}
            tenencias.append({
                "ticker": simbolo,
                "peso": float(fila["Holding Percent"]),
                "precio": objetivos.get("current"),
                "objetivo": objetivos.get("mean"),
            })
        return {"tipo": "ETF", "precio": float(precios["Close"].iloc[-1]), "tenencias": tenencias}

    historial = _con_reintentos(lambda: activo.upgrades_downgrades)
    return {
        "tipo": "Acción",
        "precios": precios["Close"],
        "splits": precios.loc[precios["Stock Splits"] > 0, "Stock Splits"],
        "objetivo_actual": _con_reintentos(lambda: activo.analyst_price_targets) or {},
        "historial": historial if historial is not None else None,
    }


def analizar_analistas(tickers: list, hoy: date) -> dict:
    """Descarga los datos de analistas de cada activo y calcula su precisión
    (acciones) o su objetivo implícito (ETFs)."""
    resultados = {}
    for ticker in tickers:
        print(f"  Analistas de {ticker}...")
        datos = descargar_analistas(ticker, hoy)
        if datos is None:
            resultados[ticker] = {"tipo": "Sin datos"}
        elif datos["tipo"] == "ETF":
            resultados[ticker] = {"tipo": "ETF", "precio": datos["precio"],
                                  **objetivo_implicito(datos["tenencias"], datos["precio"])}
        else:
            actual = datos["objetivo_actual"]
            if datos["historial"] is None:
                # Yahoo no devolvió el historial: no es lo mismo que 0 objetivos.
                detalle, precision = pd.DataFrame(), {"evaluados": None}
            else:
                detalle = precision_objetivos(datos["precios"], datos["splits"], datos["historial"], hoy)
                precision = resumen_precision(detalle)
            resultados[ticker] = {
                "tipo": "Acción",
                "precio": actual.get("current"),
                "objetivo": actual.get("mean"),
                "suba": actual["mean"] / actual["current"] - 1 if actual.get("mean") and actual.get("current") else None,
                "detalle": detalle,
                **precision,
            }
    bancos = precision_por_banco([r["detalle"] for r in resultados.values() if "detalle" in r])
    return {"activos": resultados, "bancos": bancos, "anios": ANIOS_ANALISTAS}


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
    con_analistas = pedir_texto("¿Analizar proyecciones de analistas? (s/n)", "n").lower().startswith("s")

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
        mostrar_detalle(ticker, validos[ticker], resumenes[ticker], tasa_libre_riesgo, TICKER_TASA)
    else:
        mostrar_comparativa(resumenes, cartera, tasa_libre_riesgo, TICKER_TASA)

    precios = {ticker: datos["Close"] for ticker, datos in validos.items()}
    datos_cartera = resumen_cartera(precios, cartera, intervalo, tasa_libre_riesgo)
    mostrar_cartera(datos_cartera)

    analistas = None
    if con_analistas:
        print("\nDescargando datos de analistas (puede tardar unos segundos)...")
        analistas = analizar_analistas(list(cartera), hoy)
        mostrar_analistas(analistas)

    generar_reporte(CARPETA_REPORTES, cartera, inicio, fin, intervalo, tasa_libre_riesgo, TICKER_TASA,
                    resumenes, datos_cartera, precios, analistas)


if __name__ == "__main__":
    main()
