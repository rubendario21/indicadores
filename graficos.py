import io

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.ticker import FuncFormatter

COLORES = ["#0F4C81", "#1D9E75", "#BA7517", "#7F77DD", "#D85A30"]


def _co(texto):
    """1,234.5 -> 1.234,5 (formato colombiano)"""
    return texto.replace(",", "X").replace(".", ",").replace("X", ".")

def _compacto(v):
    a = abs(v)
    if a >= 1_000_000_000_000:
        return _co(f"{v / 1_000_000_000_000:,.1f}") + " B"
    if a >= 1_000_000_000:
        return _co(f"{v / 1_000_000_000:,.1f}") + " MM"
    if a >= 1_000_000:
        return _co(f"{round(v / 1_000_000):,}") + " M"
    if a >= 1_000:
        return _co(f"{round(v / 1_000):,}") + " mil"
    return _co(f"{round(v):,}")

def formatear(v, formato):
    if v is None or pd.isna(v):
        return "–"
    if formato == "millones":
        return _compacto(v)
    if formato == "moneda":
        return "$ " + _co(f"{round(v):,}")
    if formato == "porcentaje":
        if v != 0 and abs(v) < 0.01:
            return _co(f"{v * 100:,.1f}") + "%"
        return _co(f"{round(v * 100):,}") + "%"
    return _co(f"{round(v):,}")

def _formato_eje(v, formato):
    if formato == "porcentaje":
        return f"{v * 100:.0f}%"
    if formato in ("moneda", "millones") and abs(v) >= 1_000_000:
        return "$ " + _co(f"{v / 1_000_000:,.0f}") + " M"
    if formato in ("moneda", "millones"):
        return "$ " + _co(f"{v:,.0f}")
    return _co(f"{v:,.0f}")


def generar_grafico(df, ind):
    fig, ax = plt.subplots(figsize=(9, 3.6), dpi=110)
    x = list(range(len(df.index)))
    cols = ind.columnas

    if ind.tipo_grafico == "lineas":
        for i, c in enumerate(cols):
            ax.plot(x, df[c].values, marker="o", linewidth=2,
                    color=COLORES[i % len(COLORES)], label=c)
    else:
        ancho = 0.8 / len(cols)
        for i, c in enumerate(cols):
            pos = [p - 0.4 + ancho / 2 + i * ancho for p in x]
            ax.bar(pos, df[c].values, width=ancho,
                color=COLORES[i % len(COLORES)], label=c)

    if ind.meta is not None:
        ax.axhline(ind.meta, color="#C0392B", linestyle="--", linewidth=1.5, label="Meta")

    ax.set_xticks(x)
    ax.set_xticklabels(df.index)
    ax.yaxis.set_major_formatter(FuncFormatter(lambda v, _: _formato_eje(v, ind.formato)))
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(axis="y", alpha=0.3)
    if len(cols) > 1 or ind.meta is not None:
        ax.legend(frameon=False, fontsize=8, loc="upper left", ncol=4)

    fig.tight_layout()
    buf = io.BytesIO()
    fig.savefig(buf, format="png")
    plt.close(fig)
    return buf.getvalue()