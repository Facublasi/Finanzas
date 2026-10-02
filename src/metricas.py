"""Cálculo de retornos logarítmicos y volatilidad a partir de precios."""

import numpy as np
import pandas as pd

# Cantidad de períodos en un año, según la frecuencia de los datos.
PERIODOS_POR_ANIO = {
    "1d": 252,  # días hábiles
    "1wk": 52,
    "1mo": 12,
}


def retornos_log(precios: pd.Series) -> pd.Series:
    """Retorno logarítmico de cada período: ln(P_t / P_t-1).

    El primer período no tiene precio anterior, por eso se descarta.
    """
    return np.log(precios / precios.shift(1)).dropna()


def resumen(precios: pd.Series, intervalo: str, tasa_libre_riesgo: float) -> dict:
    """Retorno, volatilidad y Sharpe ratio, todo en términos anuales.

    `tasa_libre_riesgo` es la tasa efectiva anual en decimal (0.04 = 4%).
    """
    retornos = retornos_log(precios)
    periodos = PERIODOS_POR_ANIO[intervalo]
    retorno_medio = retornos.mean()
    # Desvío estándar muestral (ddof=1) de los retornos logarítmicos.
    volatilidad = retornos.std(ddof=1)

    # Anualización: retorno medio por período × períodos en un año. Sirve igual
    # si el plazo es menor o mayor a un año, porque parte del promedio por
    # período y no del total acumulado.
    retorno_anual = retorno_medio * periodos
    volatilidad_anual = volatilidad * np.sqrt(periodos)
    # La tasa libre de riesgo se pasa a logarítmica para restar en la misma
    # escala que el retorno: ln(1 + rf).
    tasa_log = np.log(1 + tasa_libre_riesgo)

    return {
        "observaciones": len(retornos),
        # Los retornos logarítmicos se suman: el total es ln(P_fin / P_inicio).
        "retorno_log_total": retornos.sum(),
        "retorno_log_medio": retorno_medio,
        "retorno_log_anual": retorno_anual,
        "volatilidad_periodo": volatilidad,
        # Regla de la raíz del tiempo para llevar la volatilidad a un año.
        "volatilidad_anual": volatilidad_anual,
        "tasa_libre_riesgo_log": tasa_log,
        "sharpe": (retorno_anual - tasa_log) / volatilidad_anual,
    }


def retorno_esperado_cartera(resumenes: dict, cartera: dict) -> dict:
    """Retorno esperado de la cartera: promedio ponderado de los retornos
    esperados de cada activo, E(Rp) = Σ w_i · E(R_i).

    `resumenes` es {ticker: resumen(...)} y `cartera` es {ticker: peso decimal}.
    """
    return {
        "por_periodo": sum(cartera[t] * r["retorno_log_medio"] for t, r in resumenes.items()),
        "anual": sum(cartera[t] * r["retorno_log_anual"] for t, r in resumenes.items()),
    }
