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


def resumen_cartera(
    precios: dict, cartera: dict, intervalo: str, tasa_libre_riesgo: float
) -> dict:
    """Retorno esperado, volatilidad y Sharpe de la cartera.

    `precios` es {ticker: serie de precios de cierre} y `cartera` es
    {ticker: peso decimal}. Los pesos se mantienen fijos en todo el período.
    """
    # Retornos de todos los activos en una tabla, alineados por fecha (solo
    # fechas en las que hay precio de todos).
    retornos = pd.DataFrame({t: retornos_log(p) for t, p in precios.items()}).dropna()
    pesos = np.array([cartera[t] for t in retornos.columns])
    periodos = PERIODOS_POR_ANIO[intervalo]

    # Retorno esperado: E(Rp) = Σ w_i · E(R_i).
    retorno_periodo = float(pesos @ retornos.mean())
    # Matriz de covarianzas muestral (ddof=1, igual que la volatilidad de cada activo).
    covarianzas = retornos.cov(ddof=1)
    # Volatilidad: σp = √(wᵀ · Σ · w).
    volatilidad_periodo = float(np.sqrt(pesos @ covarianzas.values @ pesos))

    retorno_anual = retorno_periodo * periodos
    volatilidad_anual = volatilidad_periodo * np.sqrt(periodos)
    tasa_log = np.log(1 + tasa_libre_riesgo)
    return {
        "observaciones": len(retornos),
        "retorno_periodo": retorno_periodo,
        "retorno_anual": retorno_anual,
        "volatilidad_periodo": volatilidad_periodo,
        "volatilidad_anual": volatilidad_anual,
        "sharpe": (retorno_anual - tasa_log) / volatilidad_anual,
        "covarianzas": covarianzas,
        "correlaciones": retornos.corr(),
    }
