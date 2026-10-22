"""Presentación de los resultados: en pantalla y como reporte (HTML y PDF)
con la estética de Tu Asesoría Financiera."""

import base64
import html
import io
from datetime import date
from pathlib import Path
from string import Template

import matplotlib

matplotlib.use("Agg")  # Genera las imágenes sin abrir ventanas.
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import font_manager

from metricas import retornos_log

ASSETS = Path(__file__).parent / "assets"
FUENTES = ASSETS / "fonts"

# Colores de la marca.
NAVY = "#2C4255"
NAVY_PROFUNDO = "#1E2F3C"
DORADO = "#C0A870"
DORADO_TEXTO = "#9C7E3E"
CREMA = "#F7F3EA"
TINTA = "#33373B"
GRIS = "#6E7479"
LINEA = "#E4DDCB"
# Colores para los gráficos, en orden (los 6 de la marca, más el dorado oscuro
# y el gris para carteras de 7 u 8 activos).
PALETA = ["#2C4255", "#C0A870", "#5E7C8E", "#DCC58A", "#9DB6C2", "#A99B82", "#9C7E3E", "#6E7479"]

NOMBRES_FRECUENCIA = {"1d": "Diaria", "1wk": "Semanal", "1mo": "Mensual"}
RETORNOS_FRECUENCIA = {"1d": "diarios", "1wk": "semanales", "1mo": "mensuales"}


# ---------------------------------------------------------------------------
# Pantalla
# ---------------------------------------------------------------------------

def mostrar_detalle(ticker: str, datos, r: dict, tasa_libre_riesgo: float, ticker_tasa: str):
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
        f" (promedio de {ticker_tasa}; log: {r['tasa_libre_riesgo_log']:.2%})"
    )
    print(f"  Sharpe ratio:               {r['sharpe']:8.2f}")


def mostrar_comparativa(resumenes: dict, cartera: dict, tasa_libre_riesgo: float, ticker_tasa: str):
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
    print(f"\nTasa libre de riesgo (promedio de {ticker_tasa}): {tasa_libre_riesgo:.2%}")


def mostrar_cartera(c: dict):
    """Matrices de covarianzas y correlaciones, y métricas de la cartera."""
    if len(c["covarianzas"]) > 1:
        print("\nMatriz de covarianzas (por período)")
        print(c["covarianzas"].to_string(float_format="{:.6f}".format))
        print("\nMatriz de correlaciones")
        print(c["correlaciones"].to_string(float_format="{:.4f}".format))
    print(f"\nCartera ({c['observaciones']} retornos)")
    print("  Retorno esperado, E(Rp) = Σ w_i · E(R_i)")
    print(f"    Por período:  {c['retorno_periodo']:8.4%}")
    print(f"    Anual:        {c['retorno_anual']:8.2%}")
    print("  Volatilidad, σp = √(wᵀ · Σ · w)")
    print(f"    Por período:  {c['volatilidad_periodo']:8.4%}")
    print(f"    Anual:        {c['volatilidad_anual']:8.2%}")
    print(f"  Sharpe ratio:   {c['sharpe']:8.2f}")


def _pct(valor, decimales: int = 1) -> str:
    """Porcentaje con signo, o un guion si no hay dato."""
    return "—" if valor is None or pd.isna(valor) else f"{valor:+.{decimales}%}"


def _tabla_analistas(analistas: dict) -> pd.DataFrame:
    """Una fila por activo: objetivo actual, tendencia y precisión de los
    objetivos pasados. Los ETF se marcan en el nombre con la parte que cubren
    sus principales tenencias."""
    filas = {}
    for ticker, r in analistas["activos"].items():
        if r["tipo"] == "ETF":
            cobertura = r.get("cobertura", 0)
            nombre = f"{ticker} (ETF, {cobertura:.0%})" if cobertura else f"{ticker} (ETF)"
            filas[nombre] = {"Precio": r["precio"], "Objetivo": r.get("objetivo"),
                             "Suba esperada a 12 meses": r.get("suba")}
        elif r["tipo"] == "Acción":
            filas[ticker] = {
                "Precio": r.get("precio"),
                "Objetivo": r.get("objetivo"),
                "Rango": f"{r['minimo']:.2f} a {r['maximo']:.2f}" if r.get("minimo") and r.get("maximo") else None,
                "Suba esperada a 12 meses": r.get("suba"),
                "Tendencia 3m": r.get("tendencia"),
                "Evaluados": r.get("evaluados"),
                "Cumplidos": r.get("cumplidos"),
                "Tocados": r.get("tocados"),
            }
        else:
            filas[ticker] = {}
    columnas = ["Precio", "Objetivo", "Rango", "Suba esperada a 12 meses", "Tendencia 3m",
                "Evaluados", "Cumplidos", "Tocados"]
    return pd.DataFrame.from_dict(filas, orient="index").reindex(columns=columnas)


def _tabla_consenso(analistas: dict) -> pd.DataFrame:
    """Una fila por acción: para hace 36, 24 y 12 meses, lo que prometía el
    consenso y lo que subió la acción en los 12 meses siguientes, y la suba
    real anualizada de todo el período."""
    filas = {}
    for ticker, r in analistas["activos"].items():
        historia = r.get("historia")
        if r["tipo"] != "Acción" or not historia:
            continue
        fila = {}
        for meses, valores in historia.items():
            if meses == "anualizada":
                continue
            fila[(f"Hace {meses} meses", "Prometía")] = valores["prometida"]
            fila[(f"Hace {meses} meses", "Subió")] = valores["real"]
        fila[(f"{analistas['anios'] * 12} meses", "Anualizada")] = historia["anualizada"]
        filas[ticker] = fila
    if not filas:
        return pd.DataFrame()
    tabla = pd.DataFrame.from_dict(filas, orient="index")
    tabla.columns = pd.MultiIndex.from_tuples(tabla.columns)
    return tabla


_NOTA_ANALISTAS = (
    "Objetivo: promedio actual de los analistas, el mismo que muestra Yahoo Finance; Rango: objetivo mínimo y "
    "máximo. En los ETF, el objetivo es implícito a partir de sus 10 principales tenencias (entre paréntesis, "
    "la parte del ETF que cubren). Tendencia 3m: cuánto cambió el consenso en los últimos 3 meses. "
    "Evaluados: objetivos publicados entre hace {meses} y hace 12 meses (uno por banco por trimestre), "
    "comparados con el precio de cierre 12 meses después. Cumplidos: el precio final alcanzó el objetivo. "
    "Tocados: lo alcanzó en algún momento de esos 12 meses."
)
_NOTA_CONSENSO = (
    "Prometía: cuánto esperaba subir en 12 meses el consenso de ese día (promedio del último objetivo de cada "
    "banco). Subió: cuánto subió de verdad la acción en esos 12 meses. Los años no se superponen: compuestos, "
    "dan la suba total del período. Anualizada: promedio geométrico de las subas de cada año."
)


def mostrar_analistas(analistas: dict):
    """Objetivo actual de cada activo, consenso contra realidad y precisión por banco."""
    tabla = _tabla_analistas(analistas)
    numero = lambda v: "—" if v is None or pd.isna(v) else f"{v:.2f}"
    entero = lambda v: "—" if v is None or pd.isna(v) else f"{int(v)}"
    simple = lambda v: "—" if v is None or pd.isna(v) else f"{v:.0%}"
    print("\nProyecciones de analistas")
    print(tabla.to_string(na_rep="—", formatters={
        "Precio": numero, "Objetivo": numero, "Suba esperada a 12 meses": _pct, "Tendencia 3m": _pct,
        "Evaluados": entero, "Cumplidos": simple, "Tocados": simple,
    }))
    print("\n  " + _NOTA_ANALISTAS.format(meses=analistas["anios"] * 12))
    for ticker, r in analistas["activos"].items():
        if (r["tipo"] == "Sin datos" or (r["tipo"] == "Acción" and r.get("evaluados") is None)
                or (r["tipo"] == "ETF" and not r.get("cobertura"))):
            print(f"  Aviso: Yahoo no devolvió los datos de analistas de {ticker}. Probá de nuevo en unos minutos.")
    consenso = _tabla_consenso(analistas)
    if not consenso.empty:
        print("\nConsenso contra realidad, a 12 meses")
        print(consenso.to_string(na_rep="—", float_format=lambda v: _pct(v)))
        print("\n  " + _NOTA_CONSENSO)
    bancos = analistas["bancos"]
    if not bancos.empty:
        print("\nPrecisión por banco (al menos 3 objetivos evaluados)")
        print(bancos.rename_axis(None).to_string(
            header=["Evaluados", "Cumplidos", "Tocados"],
            formatters={"cumplidos": simple, "tocados": simple},
        ))


_NOTA_ESTRUCTURA = (
    "Giros: un máximo (o mínimo) es relevante si es el más alto (o más bajo) de los 5 días hábiles anteriores y "
    "posteriores, con precios diarios del último año. Cada máximo se compara con el anterior (HH más alto, LH más "
    "bajo, EH igual con 1% de tolerancia) y cada mínimo también (HL, LL, EL). Alcista: último máximo HH y último "
    "mínimo HL. Bajista: LH y LL. Rango: alguno es EH o EL. Transición: señales mezcladas. Los giros se confirman "
    "5 días después."
)


def _tabla_estructura(estructura: dict) -> pd.DataFrame:
    """Una fila por activo: tendencia, último máximo y mínimo, y secuencia."""
    def giro(g):
        return f"{g['etiqueta']} {g['precio']:.2f} ({g['fecha']:%d-%m-%Y})" if g else None
    filas = {}
    for ticker, r in estructura.items():
        if r is None:
            filas[ticker] = {"Tendencia": "Sin datos"}
            continue
        filas[ticker] = {
            "Tendencia": r["tendencia"],
            "Precio actual": r["precio"],
            "Último máximo": giro(r["ultimo_maximo"]),
            "Último mínimo": giro(r["ultimo_minimo"]),
            "Secuencia": " → ".join(r["secuencia"]) or None,
        }
    columnas = ["Tendencia", "Precio actual", "Último máximo", "Último mínimo", "Secuencia"]
    return pd.DataFrame.from_dict(filas, orient="index").reindex(columns=columnas)


def mostrar_estructura(estructura: dict):
    """Tendencia de cada activo según su estructura de máximos y mínimos."""
    print("\nEstructura de mercado (diaria)")
    print(_tabla_estructura(estructura).to_string(
        na_rep="—", formatters={"Precio actual": lambda v: "—" if pd.isna(v) else f"{v:.2f}"}))
    print("\n  " + _NOTA_ESTRUCTURA)
    for ticker, r in estructura.items():
        if r is None:
            print(f"  Aviso: Yahoo no devolvió los precios diarios de {ticker}. Probá de nuevo en unos minutos.")


# ---------------------------------------------------------------------------
# Gráficos (imágenes PNG con la paleta y la tipografía de la marca)
# ---------------------------------------------------------------------------

def _preparar_matplotlib():
    for archivo in ("Lato-Regular.ttf", "Lato-Bold.ttf"):
        font_manager.fontManager.addfont(str(FUENTES / archivo))
    plt.rcParams.update({
        "font.family": "Lato",
        "font.size": 11,
        "text.color": TINTA,
        "axes.edgecolor": LINEA,
        "axes.labelcolor": GRIS,
        "xtick.color": GRIS,
        "ytick.color": GRIS,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.grid": True,
        "grid.color": LINEA,
        "grid.linewidth": 0.6,
        "axes.axisbelow": True,
    })


def _a_png(fig) -> str:
    """Convierte el gráfico en una imagen incrustable en el HTML."""
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", dpi=200, transparent=True, bbox_inches="tight", pad_inches=0.05)
    plt.close(fig)
    return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode()


def _porcentaje_eje(eje):
    eje.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0%}"))


def grafico_pesos(cartera: dict) -> str:
    """Anillo con el peso de cada activo."""
    fig, ax = plt.subplots(figsize=(3.6, 3.6))
    colores = [PALETA[i % len(PALETA)] for i in range(len(cartera))]
    ax.pie(
        list(cartera.values()), colors=colores, startangle=90, counterclock=False,
        wedgeprops=dict(width=0.38, edgecolor="#FFFFFF", linewidth=2.5),
    )
    ax.set(aspect="equal")
    return _a_png(fig)


def grafico_riesgo_retorno(resumenes: dict, c: dict) -> str:
    """Volatilidad anual (x) contra retorno anual (y) de cada activo y de la cartera."""
    fig, ax = plt.subplots(figsize=(6.4, 3.9))
    for i, (ticker, r) in enumerate(resumenes.items()):
        ax.scatter(r["volatilidad_anual"], r["retorno_log_anual"], s=110,
                   color=PALETA[i % len(PALETA)], edgecolor="white", linewidth=1.5, zorder=3)
        ax.annotate(ticker, (r["volatilidad_anual"], r["retorno_log_anual"]),
                    xytext=(8, 6), textcoords="offset points", fontweight="bold", color=NAVY)
    ax.scatter(c["volatilidad_anual"], c["retorno_anual"], s=170, marker="D",
               color=DORADO, edgecolor=NAVY, linewidth=1.5, zorder=4)
    ax.annotate("Cartera", (c["volatilidad_anual"], c["retorno_anual"]),
                xytext=(9, -14), textcoords="offset points", fontweight="bold", color=DORADO_TEXTO)
    ax.axhline(0, color=GRIS, linewidth=0.8)
    ax.set_xlim(left=0)
    _porcentaje_eje(ax.xaxis)
    _porcentaje_eje(ax.yaxis)
    ax.set_xlabel("Volatilidad anual")
    ax.set_ylabel("Retorno logarítmico anual")
    return _a_png(fig)


def grafico_sharpe(resumenes: dict, c: dict) -> str:
    """Barras horizontales con el Sharpe de cada activo y de la cartera."""
    valores = {t: r["sharpe"] for t, r in resumenes.items()}
    valores = dict(sorted(valores.items(), key=lambda par: par[1]))
    nombres = list(valores) + ["Cartera"]
    numeros = list(valores.values()) + [c["sharpe"]]
    colores = [NAVY] * len(valores) + [DORADO]
    fig, ax = plt.subplots(figsize=(6.4, 3.9))
    barras = ax.barh(nombres, numeros, color=colores, height=0.6, zorder=3)
    ax.bar_label(barras, labels=[f"{v:.2f}" for v in numeros], padding=5, color=NAVY, fontweight="bold")
    ax.axvline(0, color=GRIS, linewidth=0.8)
    ax.grid(axis="y", visible=False)
    margen = max(abs(v) for v in numeros) * 0.3 or 0.1
    ax.set_xlim(min(0, min(numeros)) - margen, max(0, max(numeros)) + margen)
    ax.set_xlabel("Sharpe ratio")
    return _a_png(fig)


def grafico_precios(precios: dict) -> str:
    """Evolución de cada activo, con todos los precios llevados a 100 al inicio."""
    fig, ax = plt.subplots(figsize=(13, 5.2))
    for i, (ticker, serie) in enumerate(precios.items()):
        base_100 = serie / serie.iloc[0] * 100
        ax.plot(base_100.index, base_100.values, color=PALETA[i % len(PALETA)], linewidth=2.2, label=ticker)
    ax.axhline(100, color=GRIS, linewidth=0.8, linestyle="--")
    ax.grid(axis="x", visible=False)
    ax.set_ylabel("Base 100 al inicio")
    ax.legend(frameon=False, ncol=min(len(precios), 8), loc="upper left")
    ax.margins(x=0.01)
    return _a_png(fig)


def grafico_correlaciones(correlaciones: pd.DataFrame) -> str:
    """Mapa de calor de las correlaciones, con el valor en cada celda.

    La matriz es simétrica y la diagonal siempre vale 1, por eso se muestra solo
    el triángulo de abajo, sin la diagonal. Usa una escala de colores propia
    (rojo para -1, amarillo para 0 y verde para 1) y no la paleta de la marca.
    """
    # Filas desde el segundo activo y columnas hasta el anteúltimo: así entra
    # justo el triángulo de abajo.
    tabla = correlaciones.iloc[1:, :-1]
    n = len(tabla)
    valores = tabla.values.copy()
    for i in range(n):
        for j in range(i + 1, n):
            valores[i, j] = float("nan")  # Mitad repetida: queda en blanco.
    fig, ax = plt.subplots(figsize=(6.4, 5.4))
    mapa = matplotlib.colormaps["RdYlGn"].copy()
    mapa.set_bad(alpha=0)
    imagen = ax.imshow(valores, cmap=mapa, vmin=-1, vmax=1)
    barra = fig.colorbar(imagen, ax=ax, fraction=0.046, pad=0.04, ticks=[-1, -0.5, 0, 0.5, 1])
    barra.outline.set_visible(False)
    ax.grid(False)
    ax.set_xticks(range(n), tabla.columns, fontweight="bold", color=NAVY)
    ax.set_yticks(range(n), tabla.index, fontweight="bold", color=NAVY)
    ax.tick_params(length=0)
    for spine in ax.spines.values():
        spine.set_visible(False)
    for i in range(n):
        for j in range(i + 1):
            valor = valores[i, j]
            ax.text(j, i, f"{valor:.4f}", ha="center", va="center", fontsize=11 if n <= 4 else 9,
                    color="white" if abs(valor) > 0.75 else TINTA)
    return _a_png(fig)


# ---------------------------------------------------------------------------
# Reporte HTML / PDF
# ---------------------------------------------------------------------------

def _archivo_base64(ruta: Path, tipo: str) -> str:
    return f"data:{tipo};base64," + base64.b64encode(ruta.read_bytes()).decode()


def _fuentes_css() -> str:
    fuentes = [
        ("Cinzel", "Cinzel.ttf", "400 900", "normal"),
        ("EB Garamond", "EBGaramond.ttf", "400 700", "normal"),
        ("EB Garamond", "EBGaramond-Italic.ttf", "400 700", "italic"),
        ("Lato", "Lato-Regular.ttf", 400, "normal"),
        ("Lato", "Lato-Bold.ttf", 700, "normal"),
    ]
    return "\n".join(
        f"@font-face{{font-family:'{familia}';src:url({_archivo_base64(FUENTES / archivo, 'font/ttf')});"
        f"font-weight:{peso};font-style:{estilo}}}"
        for familia, archivo, peso, estilo in fuentes
    )


def _diapositiva(numero: int, total: int, kicker: str, titulo: str, contenido: str) -> str:
    return f"""
<section class="slide">
  <header>
    <img class="logo" src="$logo_horizontal" alt="Tu Asesoría Financiera">
    <div class="htitle"><div class="kicker">{kicker}</div><h1>{titulo}</h1></div>
  </header>
  <div class="rule"><span class="dot"></span><span class="ln"></span><span class="dot"></span></div>
  <div class="body">{contenido}</div>
  <footer><span class="brand">Tu Asesoría Financiera</span><span class="num">{numero} / {total}</span></footer>
</section>"""


def _kpi(valor: str, etiqueta: str, detalle: str = "", alt: bool = False) -> str:
    clase = "kpi alt" if alt else "kpi"
    detalle = f'<div class="d">{detalle}</div>' if detalle else ""
    return f'<div class="{clase}"><div class="v">{valor}</div><div class="l">{etiqueta}</div>{detalle}</div>'


def _signo(valor: float) -> str:
    return ' class="r neg"' if valor < 0 else ' class="r"'


def _analistas_html(analistas: dict) -> str:
    """Tabla de proyecciones por activo, consenso contra realidad y, si hay,
    la precisión por banco."""
    def celda(valor, formato):
        if valor is None or pd.isna(valor):
            return '<td class="r">—</td>'
        clase = ' class="r neg"' if formato is _pct and valor < 0 else ' class="r"'
        return f"<td{clase}>{formato(valor)}</td>"
    formatos = {
        "Precio": lambda v: f"{v:.2f}", "Objetivo": lambda v: f"{v:.2f}", "Rango": str,
        "Suba esperada a 12 meses": _pct, "Tendencia 3m": _pct, "Evaluados": lambda v: f"{int(v)}",
        "Cumplidos": lambda v: f"{v:.0%}", "Tocados": lambda v: f"{v:.0%}",
    }

    tabla = _tabla_analistas(analistas)
    cabecera = "".join(f'<th class="r">{c}</th>' for c in tabla.columns)
    filas = "".join(
        f'<tr><td class="tk">{html.escape(t)}</td>'
        + "".join(celda(f[c], formatos[c]) for c in tabla.columns) + "</tr>"
        for t, f in tabla.iterrows()
    )
    contenido = f"""
<table class="compacta">
  <thead><tr><th>Activo</th>{cabecera}</tr></thead>
  <tbody>{filas}</tbody>
</table>"""

    consenso = _tabla_consenso(analistas)
    if not consenso.empty:
        grupos = list(dict.fromkeys(consenso.columns.get_level_values(0)))
        arriba = "".join(
            f'<th class="r" colspan="{(consenso.columns.get_level_values(0) == g).sum()}">{html.escape(g)}</th>'
            for g in grupos
        )
        abajo = "".join(f'<th class="r">{html.escape(c)}</th>' for _, c in consenso.columns)
        filas = "".join(
            f'<tr><td class="tk">{html.escape(t)}</td>' + "".join(celda(v, _pct) for v in f.values) + "</tr>"
            for t, f in consenso.iterrows()
        )
        contenido += f"""
<div class="sec"><span class="bar"></span><h2>Consenso contra realidad, a 12 meses</h2></div>
<table class="compacta">
  <thead><tr><th rowspan="2">Acción</th>{arriba}</tr><tr>{abajo}</tr></thead>
  <tbody>{filas}</tbody>
</table>"""

    bancos = analistas["bancos"].head(4)
    if not bancos.empty:
        filas = "".join(
            f'<tr><td class="tk">{html.escape(banco)}</td>' + celda(f["evaluados"], formatos["Evaluados"])
            + celda(f["cumplidos"], formatos["Cumplidos"]) + celda(f["tocados"], formatos["Tocados"]) + "</tr>"
            for banco, f in bancos.iterrows()
        )
        contenido += f"""
<div class="sec"><span class="bar"></span><h2>Precisión por banco</h2></div>
<table class="compacta">
  <thead><tr><th>Banco</th><th class="r">Evaluados</th><th class="r">Cumplidos</th><th class="r">Tocados</th></tr></thead>
  <tbody>{filas}</tbody>
</table>"""
    nota = _NOTA_ANALISTAS.format(meses=analistas["anios"] * 12) + " " + _NOTA_CONSENSO
    contenido += f'''
<div class="note">{html.escape(nota)}</div>'''
    return contenido


def armar_html(cartera, inicio, fin, intervalo, tasa_libre_riesgo, ticker_tasa,
               resumenes, c, precios, analistas=None) -> str:
    """Arma la presentación completa como un único archivo HTML."""
    _preparar_matplotlib()
    tickers = [html.escape(t) for t in cartera]
    periodo = f"{inicio:%d-%m-%Y} al {fin:%d-%m-%Y}"
    frecuencia = NOMBRES_FRECUENCIA[intervalo]
    varios = len(cartera) > 1
    total = (7 if varios else 5) + (1 if analistas else 0)

    # 1. Portada
    portada = f"""
<section class="slide cover">
  <img class="logo-v" src="$logo_vertical" alt="Tu Asesoría Financiera">
  <div class="rule"><span class="dot"></span><span class="ln"></span><span class="lbl">Análisis de cartera</span><span class="ln"></span><span class="dot"></span></div>
  <h1>Rendimiento y riesgo</h1>
  <div class="sub">{", ".join(tickers)}</div>
  <div class="meta">Período {periodo} &nbsp;·&nbsp; Frecuencia {frecuencia.lower()} &nbsp;·&nbsp; Emitido el {date.today():%d-%m-%Y}</div>
</section>"""

    # 2. La cartera: pesos y métricas principales
    leyenda = "".join(
        f'<div class="it"><span class="sw" style="background:{PALETA[i % len(PALETA)]}"></span>'
        f'{html.escape(t)}<b>{peso:.2%}</b></div>'
        for i, (t, peso) in enumerate(cartera.items())
    )
    kpis = (
        _kpi(f"{c['retorno_anual']:.2%}", "Retorno esperado anual", f"{c['retorno_periodo']:.4%} por período")
        + _kpi(f"{c['volatilidad_anual']:.2%}", "Volatilidad anual", f"{c['volatilidad_periodo']:.4%} por período")
        + _kpi(f"{c['sharpe']:.2f}", "Sharpe ratio")
        + _kpi(f"{tasa_libre_riesgo:.2%}", "Tasa libre de riesgo", f"Promedio de {html.escape(ticker_tasa)}", alt=True)
    )
    cartera_html = f"""
<div class="split">
  <div class="card">
    <div class="ct">Composición</div>
    <div class="donut-wrap"><img src="{grafico_pesos(cartera)}" alt=""><div class="legend">{leyenda}</div></div>
  </div>
  <div>
    <div class="kpis">{kpis}</div>
    <div class="pres">
      <span class="first">Fórmulas de la cartera.</span> Retorno esperado E(R<sub>p</sub>) = Σ w<sub>i</sub> · E(R<sub>i</sub>);
      volatilidad σ<sub>p</sub> = √(wᵀ · Σ · w); Sharpe = (E(R<sub>p</sub>) anual − ln(1 + r<sub>f</sub>)) / σ<sub>p</sub> anual.
      Calculado con {c['observaciones']} retornos {RETORNOS_FRECUENCIA[intervalo]} entre el {periodo}. Los pesos se consideran fijos durante todo el período.
    </div>
  </div>
</div>"""

    # 3. Métricas por activo
    orden = sorted(resumenes, key=lambda t: resumenes[t]["sharpe"], reverse=True)
    filas = "".join(
        f"<tr><td class=\"tk\">{html.escape(t)}</td>"
        f"<td class=\"r\">{cartera[t]:.2%}</td>"
        f"<td class=\"r\">{resumenes[t]['observaciones']}</td>"
        f"<td{_signo(resumenes[t]['retorno_log_total'])}>{resumenes[t]['retorno_log_total']:.2%}</td>"
        f"<td{_signo(resumenes[t]['retorno_log_anual'])}>{resumenes[t]['retorno_log_anual']:.2%}</td>"
        f"<td class=\"r\">{resumenes[t]['volatilidad_anual']:.2%}</td>"
        f"<td{_signo(resumenes[t]['sharpe'])}>{resumenes[t]['sharpe']:.2f}</td></tr>"
        for t in orden
    )
    activos_html = f"""
<table>
  <thead><tr><th>Activo</th><th class="r">Peso</th><th class="r">Retornos</th><th class="r">Ret. log total</th>
  <th class="r">Ret. log anual</th><th class="r">Volatilidad anual</th><th class="r">Sharpe</th></tr></thead>
  <tbody>{filas}</tbody>
  <tfoot><tr><td>Cartera</td><td class="r">{sum(cartera.values()):.2%}</td><td class="r">{c['observaciones']}</td><td class="r">—</td>
  <td class="r">{c['retorno_anual']:.2%}</td><td class="r">{c['volatilidad_anual']:.2%}</td><td class="r"><span class="g">{c['sharpe']:.2f}</span></td></tr></tfoot>
</table>
<div class="note">Ordenado de mayor a menor Sharpe. Tasa libre de riesgo: {tasa_libre_riesgo:.2%} (promedio de {html.escape(ticker_tasa)}).
Para la cartera no se calcula un retorno total.</div>"""

    # 4. Evolución de los precios
    precios_html = f"""
<img class="chart" src="{grafico_precios(precios)}" alt="">
<div class="note">Cada precio se divide por el del inicio del período y se multiplica por 100: un valor de 150 indica una suba de 50% desde el inicio.</div>"""

    # 5 y 6 (solo con más de un activo): riesgo contra retorno, Sharpe y
    # correlaciones.
    if varios:
        riesgo_html = f"""
<div class="grid2">
  <div class="card"><div class="ct">Riesgo vs. retorno (anual)</div><img class="chart" src="{grafico_riesgo_retorno(resumenes, c)}" alt=""></div>
  <div class="card"><div class="ct">Sharpe ratio</div><img class="chart" src="{grafico_sharpe(resumenes, c)}" alt=""></div>
</div>"""

        correl_html = f"""
<div class="card solo"><img class="chart" src="{grafico_correlaciones(c['correlaciones'])}" alt=""></div>"""

    # Última: metodología y contacto
    nota_mensual = " Cada precio es el cierre del último día hábil del mes." if intervalo == "1mo" else ""
    nota_analistas = (
        '\n  <p><span class="first">Analistas.</span> Precios objetivo publicados en Yahoo Finance. Los objetivos '
        "anteriores a un split se corrigen por su proporción. En los ETF, el objetivo implícito es el promedio "
        "de la suba esperada de sus principales tenencias, ponderado por su peso.</p>"
        if analistas else ""
    )
    metodo_html = f"""
<div class="pres method">
  <p><span class="first">Datos.</span> Precios de cierre ajustados por dividendos y splits, descargados de Yahoo Finance (yfinance).{nota_mensual}</p>
  <p><span class="first">Retornos.</span> Retorno logarítmico de cada período: ln(P<sub>t</sub> / P<sub>t−1</sub>). El retorno total es la suma, igual a ln(P<sub>fin</sub> / P<sub>inicio</sub>).</p>
  <p><span class="first">Volatilidad.</span> Desvío estándar muestral de los retornos logarítmicos.</p>
  <p><span class="first">Covarianzas y correlaciones.</span> La volatilidad de la cartera usa la matriz de covarianzas muestral: σ<sub>p</sub> = √(wᵀ · Σ · w). La correlación es la covarianza dividida por los desvíos de los dos activos, y va de −1 a 1.</p>
  <p><span class="first">Anualización.</span> Retorno medio × períodos por año y volatilidad × √(períodos por año), con 252 días hábiles, 52 semanas o 12 meses según la frecuencia.</p>
  <p><span class="first">Tasa libre de riesgo.</span> Promedio de {html.escape(ticker_tasa)} (Letra del Tesoro de EE.UU. a 13 semanas) entre la fecha de inicio y la de fin.</p>
  <p><span class="first">Sharpe ratio.</span> (Retorno anualizado − ln(1 + r<sub>f</sub>)) / volatilidad anualizada.</p>{nota_analistas}
</div>
<div class="contact-block">
  <div><div class="brand">Tu Asesoría Financiera</div>
  <div class="contact">Facundo Astoviza · Alejandro Grizutti · Facundo Blasi<br>sgrgarantias@gmail.com &nbsp;|&nbsp; 9 de Julio, Prov. de Bs As</div></div>
  <div class="handle">@tuasesoriafinanciera</div>
</div>"""

    diapositivas = [
        ("La cartera", "Composición y métricas", cartera_html),
        ("Por activo", "Métricas individuales", activos_html),
        ("Evolución", "Precios base 100", precios_html),
    ]
    if varios:
        diapositivas.append(("Comparación", "Riesgo, retorno y Sharpe", riesgo_html))
        diapositivas.append(("Diversificación", "Matriz de correlaciones", correl_html))
    if analistas:
        diapositivas.append(("Analistas", "Proyecciones y precisión", _analistas_html(analistas)))
    diapositivas.append(("Metodología", "Cómo se calcula", metodo_html))

    cuerpo = portada + "".join(
        _diapositiva(i, total, kicker, titulo, contenido)
        for i, (kicker, titulo, contenido) in enumerate(diapositivas, start=2)
    )
    plantilla = Template((ASSETS / "plantilla.html").read_text(encoding="utf-8"))
    pagina = plantilla.substitute(fuentes=_fuentes_css(), titulo=f"Análisis de cartera: {', '.join(tickers)}",
                                  diapositivas=cuerpo)
    # Las diapositivas usan $logo_...; se reemplazan al final.
    return Template(pagina).safe_substitute(
        logo_horizontal=_archivo_base64(ASSETS / "logo_horizontal.png", "image/png"),
        logo_vertical=_archivo_base64(ASSETS / "logo_vertical.png", "image/png"),
    )


def guardar_pdf(ruta_html: Path, ruta_pdf: Path) -> bool:
    """Convierte el HTML en PDF con Chromium (Playwright). Devuelve False si
    Playwright no está instalado o no puede abrir el navegador."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    try:
        with sync_playwright() as p:
            navegador = p.chromium.launch()
            pagina = navegador.new_page()
            pagina.goto(ruta_html.resolve().as_uri(), wait_until="networkidle")
            pagina.pdf(path=str(ruta_pdf), print_background=True, prefer_css_page_size=True)
            navegador.close()
    except Exception:
        return False
    return True


def generar_reporte(carpeta: Path, cartera, inicio, fin, intervalo, tasa_libre_riesgo, ticker_tasa,
                    resumenes, c, precios, analistas=None):
    """Guarda la presentación como reporte.html y reporte.pdf en `carpeta`."""
    carpeta.mkdir(parents=True, exist_ok=True)
    ruta_html = carpeta / "reporte.html"
    ruta_pdf = carpeta / "reporte.pdf"
    ruta_html.write_text(
        armar_html(cartera, inicio, fin, intervalo, tasa_libre_riesgo, ticker_tasa, resumenes, c, precios,
                   analistas),
        encoding="utf-8",
    )
    print(f"\nPresentación guardada en {ruta_html}")
    if guardar_pdf(ruta_html, ruta_pdf):
        print(f"PDF guardado en {ruta_pdf}")
    else:
        print("No se pudo generar el PDF (falta Playwright). Abrí el HTML en el navegador"
              " y usá Imprimir > Guardar como PDF.")
