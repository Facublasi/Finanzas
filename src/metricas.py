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


def resumen(precios: pd.Series, intervalo: str) -> dict:
    """Retorno logarítmico total y volatilidad (por período y anualizada)."""
    retornos = retornos_log(precios)
    periodos = PERIODOS_POR_ANIO[intervalo]
    # Desvío estándar muestral (ddof=1) de los retornos logarítmicos.
    volatilidad = retornos.std(ddof=1)
    return {
        "observaciones": len(retornos),
        # Los retornos logarítmicos se suman: el total es ln(P_fin / P_inicio).
        "retorno_log_total": retornos.sum(),
        "retorno_log_medio": retornos.mean(),
        "volatilidad_periodo": volatilidad,
        # Regla de la raíz del tiempo para llevar la volatilidad a un año.
        "volatilidad_anual": volatilidad * np.sqrt(periodos),
    }
