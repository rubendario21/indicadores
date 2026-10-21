import base64
import html
from datetime import date

import pandas as pd

from graficos import formatear
from reporte import _cumple_meta, _fila_total, nombre_hoja

EMPRESA = "Escenarios Deportivos SAS"

CSS = """
@font-face {
    font-family: Arial;
    src: url("fuentes/arial.ttf");
}
@font-face {
    font-family: Arial;
    src: url("fuentes/arialbd.ttf");
    font-weight: bold;
}
}
@page {
    size: a4 landscape;
    margin: 1cm 1.1cm 1.3cm 1.1cm;
    @frame pie {
        -pdf-frame-content: pie;
        bottom: 0.4cm;
        margin-left: 1.1cm;
        margin-right: 1.1cm;
        height: 0.6cm;
    }
}
body { font-family: Arial; font-size: 8.5pt; color: #1F2A37; }

table.portada td { background-color: #0F4C81; color: #FFFFFF; padding: 9px 12px; }
.portada-titulo { font-size: 16pt; font-weight: bold; }
.portada-sub { font-size: 8.5pt; color: #C9D8EA; }

h2.seccion { font-size: 11pt; color: #0F4C81; margin-top: 10px; margin-bottom: 4px; }

table.resumen th { background-color: #0F4C81; color: #FFFFFF; font-size: 8pt;
                padding: 4px 5px; text-align: left; }
table.resumen td { font-size: 8.5pt; padding: 3px 5px; border-bottom: 0.5pt solid #E5E7EB; }
table.resumen td.proc { font-weight: bold; color: #0F4C81; }
td.cumple { color: #1B7F4B; font-weight: bold; }
td.nocumple { color: #C0392B; font-weight: bold; }
td.neutro { color: #6B7280; }

table.proceso { margin-top: 10px; -pdf-keep-with-next: true; }
table.proceso td { background-color: #E8EEF6; color: #0F4C81; font-size: 11pt;
                font-weight: bold; padding: 4px 8px; border-left: 4pt solid #0F4C81; }

.ind-titulo { font-size: 10pt; font-weight: bold; color: #1F2A37; margin-top: 8px;
            -pdf-keep-with-next: true; }
.ind-desc { font-size: 8pt; color: #6B7280; margin-bottom: 3px; -pdf-keep-with-next: true; }

table.datos th { background-color: #0F4C81; color: #FFFFFF; font-size: 7.5pt;
                padding: 3px 2px; text-align: center; }
table.datos th.serie { text-align: left; padding-left: 4px; }
table.datos td { font-size: 8pt; padding: 3px 2px; text-align: right;
                border-bottom: 0.5pt solid #E5E7EB; }
table.datos td.serie { text-align: left; font-weight: bold; padding-left: 4px; }
table.datos tr.par td { background-color: #F7F9FC; }
table.datos tr.pct td { font-weight: bold; border-top: 0.75pt solid #9CA3AF; }
table.datos td.tot { background-color: #EEF2F7; font-weight: bold; }
table.datos td.ok { color: #1B7F4B; }
table.datos td.mal { color: #C0392B; }
table.datos td.tot-ok { background-color: #EEF2F7; font-weight: bold; color: #1B7F4B; }
table.datos td.tot-mal { background-color: #EEF2F7; font-weight: bold; color: #C0392B; }

table.aviso-excel td { background-color: #EAF3EC; color: #1B7F4B; padding: 6px 8px;
                    font-size: 8.5pt; border-left: 3pt solid #1B7F4B; }
table.aviso-error td { background-color: #FDECEA; color: #C0392B; padding: 6px 8px;
                    font-size: 8.5pt; border-left: 3pt solid #C0392B; }
.nota { font-size: 7.5pt; color: #6B7280; margin-top: 3px; }
#pie td { font-size: 7pt; color: #9CA3AF; }
"""


def _valor_texto(v, formato):
    texto = formatear(v, formato)
    if formato == "millones" and texto != "–":
        return f"$ {texto}"
    return texto


def _meta_texto(meta, sentido, formato):
    if meta is None:
        return "Sin meta"
    palabra = "mínimo" if sentido == ">=" else "máximo"
    return f"{palabra} {_valor_texto(meta, formato)}"


def _meta_de(ind):
    if ind.meta_porcentaje is not None:
        return ind.meta_porcentaje, "porcentaje"
    return ind.meta, ind.formato


def _resultado(ind, df):
    """Valor del año, meta y formato para la tabla de resumen."""
    if df is None:
        return None, None, ind.formato
    if ind.porcentaje:
        _, num, den = ind.porcentaje
        total_den = df[den].sum()
        valor = df[num].sum() / total_den if total_den else None
        return valor, ind.meta_porcentaje, "porcentaje"
    if ind.tipo == "mensual" and ind.columnas:
        serie = df[ind.columnas[0]].dropna()
        return (serie.mean() if len(serie) else None), ind.meta, ind.formato
    if ind.tipo == "foto" and ind.columnas:
        return df[ind.columnas[0]].iloc[0], ind.meta, ind.formato
    return None, ind.meta, ind.formato


def _estado(ind, valor, meta, error):
    if error is not None:
        return "Error", "nocumple"
    if valor is None or meta is None:
        return ("Ver Excel" if ind.tipo == "detalle" else "Sin meta"), "neutro"
    if _cumple_meta(valor, meta, ind.meta_sentido):
        return "Cumple", "cumple"
    return "No cumple", "nocumple"


def _agrupar(items):
    grupos = {}
    for item in items:
        grupos.setdefault(item[0].proceso, []).append(item)
    return grupos


def _resumen(items):
    filas = ""
    for proceso, lista in _agrupar(items).items():
        # Los listados de detalle sin porcentaje no tienen resultado: no van en el resumen
        lista = [it for it in lista if not (it[0].tipo in ("detalle", "tabla") and not it[0].porcentaje)]
        for n, (ind, df, error, _) in enumerate(lista):
            valor, meta, fmt = _resultado(ind, df)
            estado, clase = _estado(ind, valor, meta, error)
            donde = "Excel" if ind.tipo == "detalle" else "PDF"
            filas += (f'<tr><td class="proc">{html.escape(proceso) if n == 0 else ""}</td>'
                    f'<td>{html.escape(ind.nombre)}</td>'
                    f'<td>{_meta_texto(meta, ind.meta_sentido, fmt)}</td>'
                    f'<td>{_valor_texto(valor, fmt)}</td>'
                    f'<td class="{clase}">{estado}</td>'
                    f'<td>{donde}</td></tr>')
    return ('<table class="resumen" repeat="1">'
            '<tr><th width="15%">Proceso</th><th width="37%">Indicador</th>'
            '<th width="14%">Meta</th><th width="14%">Resultado del año</th>'
            '<th width="11%">Estado</th><th width="9%">Detalle</th></tr>'
            f'{filas}</table>')


def _tabla(ind, df):
    titulo_total = {"suma": "Total", "promedio": "Prom."}.get(ind.acumulado)

    enc = '<tr><th class="serie" width="15%">Serie</th>'
    enc += "".join(f"<th>{m}</th>" for m in df.index)
    if titulo_total:
        enc += f"<th>{titulo_total}</th>"
    enc += "</tr>"

    filas = ""
    for n, col in enumerate(ind.columnas):
        celdas = ""
        for v in df[col]:
            clase = ""
            if n == 0 and ind.meta is not None and v == v:          # v == v descarta NaN
                clase = "ok" if _cumple_meta(v, ind.meta, ind.meta_sentido) else "mal"
            celdas += f'<td class="{clase}">{formatear(v, ind.formato)}</td>'
        if titulo_total:
            serie = df[col].dropna()
            total = None
            if len(serie):
                total = serie.sum() if ind.acumulado == "suma" else serie.mean()
            celdas += f'<td class="tot">{formatear(total, ind.formato)}</td>'
        clase_fila = "par" if n % 2 else ""
        filas += (f'<tr class="{clase_fila}"><td class="serie">{html.escape(col)}</td>'
                f'{celdas}</tr>')

    if ind.porcentaje:
        etiqueta, num, den = ind.porcentaje
        celdas = ""
        for v in df[etiqueta]:
            clase = ""
            if ind.meta_porcentaje is not None and v == v:
                clase = "ok" if _cumple_meta(v, ind.meta_porcentaje, ind.meta_sentido) else "mal"
            celdas += f'<td class="{clase}">{formatear(v, "porcentaje")}</td>'
        if titulo_total:
            total_den = df[den].sum()
            total = df[num].sum() / total_den if total_den else None
            clase = "tot"
            if total is not None and ind.meta_porcentaje is not None:
                cumple = _cumple_meta(total, ind.meta_porcentaje, ind.meta_sentido)
                clase = "tot-ok" if cumple else "tot-mal"
            celdas += f'<td class="{clase}">{formatear(total, "porcentaje")}</td>'
        filas += (f'<tr class="pct"><td class="serie">{html.escape(etiqueta)}</td>'
                f'{celdas}</tr>')

    return f'<table class="datos" repeat="1">{enc}{filas}</table>'


def _tabla_foto(ind, df):
    fila = df.iloc[0]
    filas = ""
    for n, col in enumerate(ind.columnas):
        v = fila[col]
        clase = ""
        if n == 0 and ind.meta is not None and v == v:
            clase = "ok" if _cumple_meta(v, ind.meta, ind.meta_sentido) else "mal"
        clase_fila = "par" if n % 2 else ""
        filas += (f'<tr class="{clase_fila}"><td class="serie">{html.escape(col)}</td>'
                f'<td class="{clase}">{formatear(v, ind.formato)}</td></tr>')

    if ind.porcentaje:
        etiqueta = ind.porcentaje[0]
        v = fila[etiqueta]
        clase = ""
        if ind.meta_porcentaje is not None and v == v:
            clase = "ok" if _cumple_meta(v, ind.meta_porcentaje, ind.meta_sentido) else "mal"
        filas += (f'<tr class="pct"><td class="serie">{html.escape(etiqueta)}</td>'
                f'<td class="{clase}">{formatear(v, "porcentaje")}</td></tr>')

    return (f'<table class="datos" width="40%">'
            f'<tr><th class="serie" width="60%">Concepto</th>'
            f'<th>Al {date.today():%d/%m/%Y}</th></tr>{filas}</table>')

def _tabla_libre(ind, df):
    con_total = ind.acumulado == "suma"
    datos = _fila_total(df, ind) if con_total else df
    numericas = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]

    enc = "".join(f'<th>{html.escape(str(c))}</th>' if c in numericas
                else f'<th class="serie">{html.escape(str(c))}</th>' for c in df.columns)
    filas = ""
    for i, (_, fila) in enumerate(datos.iterrows()):
        es_total = con_total and i == len(datos) - 1
        clase = "pct" if es_total else ("par" if i % 2 else "")
        celdas = ""
        for c in df.columns:
            if c in numericas:
                celdas += f"<td>{formatear(fila[c], ind.formato)}</td>"
            else:
                celdas += f'<td class="serie">{html.escape(str(fila[c]))}</td>'
        filas += f'<tr class="{clase}">{celdas}</tr>'

    return f'<table class="datos" width="55%" repeat="1"><tr>{enc}</tr>{filas}</table>'
def _bloque(ind, df, error, img):
    detalles = []
    if ind.descripcion:
        detalles.append(html.escape(ind.descripcion))
    meta, fmt = _meta_de(ind)
    if meta is not None:
        detalles.append("Meta: " + _meta_texto(meta, ind.meta_sentido, fmt))
    if ind.formato == "millones":
        detalles.append("Cifras en pesos: M = millones · MM = miles de millones")

    partes = [f'<div class="ind-titulo">{html.escape(ind.nombre)}</div>',
            f'<div class="ind-desc">{" · ".join(detalles)}</div>']

    if error is not None:
        partes.append(f'<table class="aviso-error"><tr><td>No se pudo calcular: '
                    f'{html.escape(str(error)[:300])}</td></tr></table>')
    elif ind.tipo == "detalle":
        partes.append(f'<table class="aviso-excel"><tr><td>Este indicador se visualiza en el '
                    f'Excel adjunto, hoja <b>«{html.escape(nombre_hoja(ind))}»</b>, por '
                    f'tratarse de un detalle amplio ({len(df)} filas).</td></tr></table>')
    else:
        if img:
            partes.append(f'<img src="data:image/png;base64,{base64.b64encode(img).decode()}" '
                        f'width="700">')
        if ind.tipo == "foto":
            partes.append(_tabla_foto(ind, df))
        elif ind.tipo == "tabla":
            partes.append(_tabla_libre(ind, df))
        else:
            partes.append(_tabla(ind, df))
        if ind.excel:
            partes.append(f'<div class="nota">También disponible en el Excel adjunto, hoja '
                        f'«{html.escape(nombre_hoja(ind))}».</div>')
    return "".join(partes)


def armar_pdf_html(anio, items, proceso=None):
    """items: lista de (indicador, df, error, imagen)."""
    titulo = f"Indicadores de gestión {anio}" + (f" . {proceso}" if proceso else "")
    hoy = date.today()
    detalle = ""
    for proceso, lista in _agrupar(items).items():
        detalle += f'<table class="proceso"><tr><td>{html.escape(proceso)}</td></tr></table>'
        detalle += "".join(_bloque(*item) for item in lista)

    return f"""<html><head><meta charset="utf-8"><style>{CSS}</style></head><body>
<div id="pie"><table><tr>
<td>{titulo} · {EMPRESA}</td>
<td align="right">Página <pdf:pagenumber> de <pdf:pagecount></td>
</tr></table></div>

<table class="portada"><tr><td>
<div class="portada-titulo">{titulo}</div>
<div class="portada-sub">{EMPRESA} · Corte al {hoy:%d/%m/%Y} · Información mes a mes del año en curso</div>
</td></tr></table>

<h2 class="seccion">Resumen de cumplimiento</h2>
{_resumen(items)}
<div class="nota">Resultado del año: en los indicadores con porcentaje es el acumulado del año
(total del numerador / total del denominador); en los demás, el promedio mensual.
Los listados de detalle sin meta se consultan directamente en el Excel.</div>

<pdf:nextpage />
<h2 class="seccion">Detalle por proceso</h2>
{detalle}
</body></html>"""