"""Indicadores técnicos calculados a partir de los precios diarios."""

import pandas as pd

# Días a cada lado para que un máximo (o mínimo) cuente como giro: tiene que
# ser el más alto (o más bajo) de los DIAS_PIVOTE días anteriores y posteriores.
DIAS_PIVOTE = 5
# Diferencia máxima para considerar iguales dos máximos (EH) o dos mínimos (EL).
TOLERANCIA_IGUALES = 0.01


def pivotes(maximos: pd.Series, minimos: pd.Series, dias: int = DIAS_PIVOTE) -> pd.DataFrame:
    """Máximos y mínimos relevantes (giros) del precio, en orden de fecha.

    Un día es un máximo relevante si su precio máximo es el más alto de la
    ventana que va de `dias` días antes a `dias` días después (y el primero,
    si se repite). Lo mismo para los mínimos. Los últimos `dias` días no se
    pueden confirmar todavía.
    """
    filas = []
    for i in range(dias, len(maximos) - dias):
        ventana_max = maximos.iloc[i - dias:i + dias + 1]
        ventana_min = minimos.iloc[i - dias:i + dias + 1]
        # argmax/argmin devuelven la primera posición del extremo: si el máximo
        # se repite en la ventana, solo cuenta el primer día.
        if ventana_max.values.argmax() == dias:
            filas.append({"fecha": maximos.index[i], "tipo": "máximo", "precio": maximos.iloc[i]})
        if ventana_min.values.argmin() == dias:
            filas.append({"fecha": minimos.index[i], "tipo": "mínimo", "precio": minimos.iloc[i]})
    return pd.DataFrame(filas, columns=["fecha", "tipo", "precio"])


def clasificar(giros: pd.DataFrame, tolerancia: float = TOLERANCIA_IGUALES) -> pd.DataFrame:
    """Compara cada máximo con el máximo anterior y cada mínimo con el mínimo
    anterior: HH/LH/EH para los máximos y HL/LL/EL para los mínimos. El primero
    de cada tipo no tiene con qué compararse y queda sin etiqueta."""
    giros = giros.copy()
    giros["etiqueta"] = None
    for tipo, (sube, baja, igual) in {"máximo": ("HH", "LH", "EH"), "mínimo": ("HL", "LL", "EL")}.items():
        indices = giros.index[giros["tipo"] == tipo]
        for anterior, actual in zip(indices[:-1], indices[1:]):
            cambio = giros.at[actual, "precio"] / giros.at[anterior, "precio"] - 1
            if abs(cambio) <= tolerancia:
                giros.at[actual, "etiqueta"] = igual
            else:
                giros.at[actual, "etiqueta"] = sube if cambio > 0 else baja
    return giros


def tendencia(giros: pd.DataFrame) -> str:
    """Tendencia según la etiqueta del último máximo y del último mínimo.

    Alcista: HH y HL. Bajista: LH y LL. Rango: alguno es igual al anterior
    (EH o EL). Transición: señales mezcladas (HH con LL, o LH con HL).
    """
    ultimo_max = giros[(giros["tipo"] == "máximo") & giros["etiqueta"].notna()].tail(1)
    ultimo_min = giros[(giros["tipo"] == "mínimo") & giros["etiqueta"].notna()].tail(1)
    if ultimo_max.empty or ultimo_min.empty:
        return "Sin datos suficientes"
    par = (ultimo_max["etiqueta"].iloc[0], ultimo_min["etiqueta"].iloc[0])
    if par == ("HH", "HL"):
        return "Alcista"
    if par == ("LH", "LL"):
        return "Bajista"
    if "EH" in par or "EL" in par:
        return "Rango"
    return "Transición"


def estructura_mercado(precios: pd.DataFrame) -> dict:
    """Estructura de mercado a partir de precios diarios (columnas High y Low).

    Devuelve la tendencia, el último máximo y el último mínimo clasificados, y
    la secuencia de las últimas etiquetas.
    """
    giros = clasificar(pivotes(precios["High"], precios["Low"]))
    con_etiqueta = giros[giros["etiqueta"].notna()]
    ultimo = lambda tipo: con_etiqueta[con_etiqueta["tipo"] == tipo].tail(1).to_dict("records")
    return {
        "tendencia": tendencia(giros),
        "ultimo_maximo": (ultimo("máximo") or [None])[0],
        "ultimo_minimo": (ultimo("mínimo") or [None])[0],
        "secuencia": list(con_etiqueta["etiqueta"].tail(6)),
        "giros": giros,
    }
