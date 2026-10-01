"""Descarga cotizaciones usando yfinance, pidiendo los datos por teclado."""

from datetime import date, datetime, timedelta

import yfinance as yf

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


def descargar(ticker: str, inicio: date, fin: date, intervalo: str):
    """Devuelve precios de `ticker` entre `inicio` y `fin` (ambos incluidos)."""
    # yfinance no incluye la fecha de fin, por eso se le suma un día.
    return yf.Ticker(ticker).history(
        start=inicio, end=fin + timedelta(days=1), interval=intervalo
    )


def main():
    hoy = date.today()
    ticker = pedir_texto("Ticker (acciones de BYMA llevan sufijo .BA)", "GGAL").upper()
    while True:
        inicio = pedir_fecha("Fecha de inicio (AAAA-MM-DD)", hoy - timedelta(days=30))
        fin = pedir_fecha("Fecha de fin (AAAA-MM-DD)", hoy)
        if inicio <= fin:
            break
        print("  La fecha de inicio tiene que ser anterior o igual a la de fin.")
    intervalo = pedir_frecuencia()

    datos = descargar(ticker, inicio, fin, intervalo)
    if datos.empty:
        print(f"\nNo se encontraron datos para {ticker} en ese rango.")
        return
    print(f"\n{ticker} | {inicio} a {fin} | intervalo {intervalo}\n")
    print(datos[["Open", "High", "Low", "Close", "Volume"]])


if __name__ == "__main__":
    main()
