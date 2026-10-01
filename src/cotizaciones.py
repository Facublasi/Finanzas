"""Descarga cotizaciones de cierre usando yfinance."""

import sys

import yfinance as yf


def cierres(ticker: str, periodo: str = "5d"):
    """Devuelve los precios de cierre de `ticker` para el `periodo` indicado."""
    return yf.Ticker(ticker).history(period=periodo)[["Close"]]


if __name__ == "__main__":
    ticker = sys.argv[1] if len(sys.argv) > 1 else "GGAL"
    periodo = sys.argv[2] if len(sys.argv) > 2 else "5d"
    print(cierres(ticker, periodo))
