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


def _solo_fecha(indice: pd.Index) -> pd.DatetimeIndex:
    """Lleva fechas con o sin zona horaria a fechas simples (sin hora)."""
    indice = pd.DatetimeIndex(indice)
    if indice.tz is not None:
        indice = indice.tz_localize(None)
    return indice.normalize()


def objetivos_publicados(historial: pd.DataFrame, splits: pd.Series) -> pd.DataFrame:
    """Precios objetivo publicados, en la escala de los precios actuales.

    Descarta los registros sin objetivo (cambios de recomendación sin precio)
    y deja uno por banco por trimestre, el último: así un banco que confirma
    su objetivo varias veces no pesa más que otro. Los objetivos no están
    corregidos por splits y los precios sí, por eso un objetivo publicado
    antes de un split se divide por su proporción.
    """
    splits = pd.Series(splits.values, index=_solo_fecha(splits.index))
    tabla = pd.DataFrame({
        "fecha": _solo_fecha(historial.index),
        "banco": historial["Firm"].values,
        "objetivo": historial["currentPriceTarget"].values,
    })
    tabla = tabla[tabla["objetivo"] > 0].sort_values("fecha")
    tabla["trimestre"] = tabla["fecha"].dt.to_period("Q")
    tabla = tabla.groupby(["banco", "trimestre"]).tail(1)
    for fecha_split, proporcion in splits.items():
        tabla.loc[tabla["fecha"] < fecha_split, "objetivo"] /= proporcion
    return tabla.drop(columns="trimestre").reset_index(drop=True)


def precision_objetivos(
    precios: pd.Series, objetivos: pd.DataFrame, hoy, anios: int, meses: int = 12
) -> pd.DataFrame:
    """Compara cada precio objetivo publicado con lo que pasó `meses` después.

    `precios` son los cierres diarios y `objetivos` sale de
    `objetivos_publicados`. Se evalúan los objetivos publicados en los
    últimos `anios` años que ya cumplieron `meses` de antigüedad.

    Un objetivo por encima del precio del día espera una suba: se cumple si el
    precio final está en el objetivo o por encima. Uno por debajo espera una
    baja: se cumple si el precio final está en el objetivo o por debajo.
    """
    precios = pd.Series(precios.values, index=_solo_fecha(precios.index)).dropna()
    limite = min(pd.Timestamp(hoy), precios.index.max())
    desde = max(pd.Timestamp(hoy) - pd.DateOffset(years=anios), precios.index.min())

    filas = []
    for _, fila in objetivos.iterrows():
        fecha, objetivo = fila["fecha"], fila["objetivo"]
        fin = fecha + pd.DateOffset(months=meses)
        if fin > limite or fecha < desde:
            continue
        inicial = precios[precios.index >= fecha].iloc[0]
        tramo = precios[(precios.index > fecha) & (precios.index <= fin)]
        final = tramo.iloc[-1]
        alcista = objetivo >= inicial
        filas.append({
            "fecha": fecha,
            "banco": fila["banco"],
            "objetivo": objetivo,
            "precio_inicial": inicial,
            "precio_final": final,
            "suba_prometida": objetivo / inicial - 1,
            "suba_real": final / inicial - 1,
            "cumplido": final >= objetivo if alcista else final <= objetivo,
            "tocado": tramo.max() >= objetivo if alcista else tramo.min() <= objetivo,
        })
    return pd.DataFrame(filas)


def resumen_precision(detalle: pd.DataFrame) -> dict:
    """Porcentaje de objetivos cumplidos y tocados.

    No se resumen las subas de cada objetivo en un promedio o mediana: las
    ventanas de 12 meses se superponen y mezclan años muy distintos. La
    comparación de subas se hace con `consenso_contra_realidad`.
    """
    if detalle.empty:
        return {"evaluados": 0}
    return {
        "evaluados": len(detalle),
        "cumplidos": detalle["cumplido"].mean(),
        "tocados": detalle["tocado"].mean(),
    }


def precision_por_banco(detalles: list, minimo: int = 3) -> pd.DataFrame:
    """Lo mismo que `resumen_precision`, por banco, sumando todas las acciones.

    Solo incluye los bancos con al menos `minimo` objetivos evaluados.
    """
    todos = pd.concat([d for d in detalles if not d.empty], ignore_index=True) if detalles else pd.DataFrame()
    if todos.empty:
        return pd.DataFrame()
    tabla = todos.groupby("banco").agg(
        evaluados=("cumplido", "size"),
        cumplidos=("cumplido", "mean"),
        tocados=("tocado", "mean"),
    )
    return tabla[tabla["evaluados"] >= minimo].sort_values("evaluados", ascending=False)


def consenso(objetivos: pd.DataFrame, fecha, vigencia: int = 12):
    """Consenso de los analistas a una fecha: promedio del último objetivo de
    cada banco publicado en los `vigencia` meses anteriores (un objetivo más
    viejo se considera vencido). Devuelve None si no hay ninguno vigente."""
    fecha = pd.Timestamp(fecha)
    vigentes = objetivos[(objetivos["fecha"] <= fecha)
                         & (objetivos["fecha"] > fecha - pd.DateOffset(months=vigencia))]
    if vigentes.empty:
        return None
    return vigentes.groupby("banco").tail(1)["objetivo"].mean()


def tendencia_objetivos(objetivos: pd.DataFrame, hoy, meses: int = 3):
    """Variación del consenso de los analistas en los últimos `meses`."""
    actual = consenso(objetivos, hoy)
    anterior = consenso(objetivos, pd.Timestamp(hoy) - pd.DateOffset(months=meses))
    if actual is None or anterior is None:
        return None
    return actual / anterior - 1


def consenso_contra_realidad(objetivos: pd.DataFrame, precios: pd.Series, hoy, anios: int = 3) -> dict:
    """Para hace 12, 24, ... meses: cuánto prometía subir el consenso de ese
    día y cuánto subió de verdad la acción en los 12 meses siguientes.

    Es una sola predicción por fecha, sin superponer ventanas: las subas
    reales de cada año, compuestas, dan la suba total del período. Devuelve
    {meses atrás: {"prometida", "real"}} y, en "anualizada", la suba real
    anualizada de todo el período (promedio geométrico de las subas de cada
    año). None donde falta el dato.
    """
    precios = pd.Series(precios.values, index=_solo_fecha(precios.index)).dropna()
    hoy = pd.Timestamp(hoy)
    resultado = {}
    for anio in range(anios, 0, -1):
        fecha = hoy - pd.DateOffset(months=12 * anio)
        fin = fecha + pd.DateOffset(months=12)
        valor = consenso(objetivos, fecha)
        desde = precios[precios.index <= fecha]
        hasta = precios[precios.index <= fin]
        if desde.empty or hasta.empty:
            resultado[12 * anio] = {"prometida": None, "real": None}
            continue
        # La suba real solo depende de los precios: se calcula aunque falte el consenso.
        resultado[12 * anio] = {
            "prometida": valor / desde.iloc[-1] - 1 if valor is not None else None,
            "real": hasta.iloc[-1] / desde.iloc[-1] - 1,
        }
    reales = [r["real"] for r in resultado.values()]
    if all(r is not None for r in reales):
        compuesta = 1.0
        for r in reales:
            compuesta *= 1 + r
        resultado["anualizada"] = compuesta ** (1 / anios) - 1
    else:
        resultado["anualizada"] = None
    return resultado


def objetivo_implicito(tenencias: list, precio_etf: float) -> dict:
    """Precio objetivo implícito de un ETF a partir de sus principales tenencias.

    `tenencias` es una lista de {peso, precio, objetivo}, con el objetivo
    promedio de los analistas de cada tenencia. La suba esperada del
    ETF es el promedio de la suba esperada de cada tenencia, ponderado por su
    peso, contando solo las que tienen precio objetivo. `cobertura` es la
    parte del ETF que representan esas tenencias.
    """
    con_dato = [t for t in tenencias if t.get("precio") and t.get("objetivo")]
    cobertura = sum(t["peso"] for t in con_dato)
    if cobertura == 0:
        return {"cobertura": 0}
    suba = sum(t["peso"] * (t["objetivo"] / t["precio"] - 1) for t in con_dato) / cobertura
    return {"cobertura": cobertura, "suba": suba, "objetivo": precio_etf * (1 + suba)}
