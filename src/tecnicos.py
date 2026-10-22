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


# ---------------------------------------------------------------------------
# Quiebre de estructura
# ---------------------------------------------------------------------------

def quiebre(estructura: dict, precio: float):
    """Avisa si el precio actual ya rompió el último máximo o mínimo
    confirmado, antes de que se confirme un giro nuevo."""
    maximo, minimo = estructura["ultimo_maximo"], estructura["ultimo_minimo"]
    if minimo and precio < minimo["precio"]:
        return f"Bajista: perforó el mínimo de {minimo['precio']:.2f}"
    if maximo and precio > maximo["precio"]:
        return f"Alcista: superó el máximo de {maximo['precio']:.2f}"
    return None


# ---------------------------------------------------------------------------
# Medias móviles
# ---------------------------------------------------------------------------

PERIODOS_MEDIAS = (9, 21, 50, 200)


def medias_moviles(cierres: pd.Series, periodos=PERIODOS_MEDIAS) -> dict:
    """Medias móviles simples de hoy, posición del precio respecto de cada una,
    si están alineadas y el último cruce entre la de 50 y la de 200."""
    medias = {p: cierres.rolling(p).mean() for p in periodos}
    precio = cierres.iloc[-1]
    hoy = {p: medias[p].iloc[-1] for p in periodos}
    if any(pd.isna(v) for v in hoy.values()):
        return {"precio": precio, "medias": hoy, "alineacion": "Sin datos suficientes", "cruce": None,
                "cruce_desde": None}

    # Alineadas: de la más corta a la más larga, cada una por encima (alcista)
    # o por debajo (bajista) de la siguiente.
    valores = [hoy[p] for p in sorted(periodos)]
    if all(a > b for a, b in zip(valores, valores[1:])):
        alineacion = "Alcista"
    elif all(a < b for a, b in zip(valores, valores[1:])):
        alineacion = "Bajista"
    else:
        alineacion = "Mezclada"

    cruce, cruce_desde = None, None
    if 50 in medias and 200 in medias:
        diferencia = (medias[50] - medias[200]).dropna()
        # Desde cuándo se pueden buscar cruces: el primer día con las dos medias.
        cruce_desde = diferencia.index[0]
        signo = diferencia > 0
        cambios = signo[signo != signo.shift()].index[1:]
        if len(cambios):
            fecha = cambios[-1]
            cruce = {"fecha": fecha, "tipo": "Dorado" if signo[fecha] else "De la muerte"}
    return {"precio": precio, "medias": hoy, "alineacion": alineacion, "cruce": cruce,
            "cruce_desde": cruce_desde}


# ---------------------------------------------------------------------------
# DMI y ADX (Wilder)
# ---------------------------------------------------------------------------

DIAS_DMI = 14
# Días hábiles hacia atrás para ver si el ADX sube o baja.
DIAS_PENDIENTE_ADX = 5


def _wilder(serie: pd.Series, dias: int) -> pd.Series:
    """Suavizado de Wilder (el ta.rma de TradingView): arranca con el promedio
    simple de los primeros `dias` valores y después cada valor nuevo pesa 1/dias."""
    serie = serie.dropna()
    resultado = pd.Series(float("nan"), index=serie.index)
    if len(serie) < dias:
        return resultado
    anterior = serie.iloc[:dias].mean()
    resultado.iloc[dias - 1] = anterior
    for i in range(dias, len(serie)):
        anterior = (anterior * (dias - 1) + serie.iloc[i]) / dias
        resultado.iloc[i] = anterior
    return resultado


def dmi(maximos: pd.Series, minimos: pd.Series, cierres: pd.Series, dias: int = DIAS_DMI):
    """+DI, −DI y ADX diarios, con el método de Wilder (igual que TradingView)."""
    suba = maximos.diff()
    baja = -minimos.diff()
    dm_mas = suba.where((suba > baja) & (suba > 0), 0.0)
    dm_menos = baja.where((baja > suba) & (baja > 0), 0.0)
    dm_mas[suba.isna()] = float("nan")
    dm_menos[suba.isna()] = float("nan")
    cierre_anterior = cierres.shift()
    rango = pd.concat([maximos - minimos, (maximos - cierre_anterior).abs(),
                       (minimos - cierre_anterior).abs()], axis=1).max(axis=1)
    rango[cierre_anterior.isna()] = float("nan")

    rango_suavizado = _wilder(rango, dias)
    di_mas = 100 * _wilder(dm_mas, dias) / rango_suavizado
    di_menos = 100 * _wilder(dm_menos, dias) / rango_suavizado
    suma = (di_mas + di_menos).replace(0, 1)
    adx = _wilder(100 * (di_mas - di_menos).abs() / suma, dias)
    return di_mas, di_menos, adx


def lectura_adx(adx: float) -> str:
    """Potencia de la tendencia según el valor del ADX."""
    if adx < 20:
        return "Sin tendencia"
    if adx < 25:
        return "Débil"
    if adx < 40:
        return "Fuerte"
    return "Muy fuerte"


def resumen_dmi(maximos: pd.Series, minimos: pd.Series, cierres: pd.Series) -> dict:
    """ADX, +DI y −DI de hoy; dirección según qué DI domina, fecha del último
    cruce de los DI y si el ADX sube o baja respecto de hace una semana."""
    di_mas, di_menos, adx = dmi(maximos, minimos, cierres)
    if adx.dropna().empty:
        return {"adx": None}
    # Solo los días con los dos DI calculados: comparar con un valor vacío
    # daría False y podría inventar un cruce.
    validos = di_mas.notna() & di_menos.notna()
    domina = (di_mas > di_menos)[validos]
    cambios = domina[domina != domina.shift()].index[1:]
    pendiente = adx.iloc[-1] - adx.iloc[-1 - DIAS_PENDIENTE_ADX]
    return {
        "adx": adx.iloc[-1],
        "di_mas": di_mas.iloc[-1],
        "di_menos": di_menos.iloc[-1],
        "lectura": lectura_adx(adx.iloc[-1]),
        "direccion": "Alcista" if domina.iloc[-1] else "Bajista",
        "desde": cambios[-1] if len(cambios) else None,
        "adx_subiendo": pendiente > 0,
    }
