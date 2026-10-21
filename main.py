import logging
import os
import re
import sys
from datetime import date
from pathlib import Path

from correo import enviar
from datos import crear_engine, ejecutar, ejecutar_detalle, ejecutar_foto
from graficos import generar_grafico
from indicadores import INDICADORES
from pdf import html_a_pdf
from reporte import armar_correo, armar_excel, nombre_hoja
from reporte_pdf import armar_pdf_html

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

NOMBRES_FUENTE = {"sql": "SAP", "zoho": "Zoho CRM"}


def _nombre_archivo(texto):
    limpio = re.sub(r'[\\/:*?"<>|]', "", texto).strip()
    return limpio.replace(" ", "_") or "General"


def _sistema(ind):
    return ind.sistema or NOMBRES_FUENTE.get(ind.fuente, ind.fuente.upper())


def main():
    os.chdir(Path(__file__).parent)
    hoy = date.today()
    anio = hoy.year
    engine = crear_engine()
    grupos, resumen = {}, []

    for ind in INDICADORES:
        sistema = _sistema(ind)
        g = grupos.setdefault((ind.proceso, sistema), {"pdf": [], "excel": []})
        base = f"{_nombre_archivo(ind.proceso)}_{_nombre_archivo(sistema)}_{anio}_{hoy:%Y-%m-%d}"
        pdf_nombre, xlsx_nombre = f"{base}.pdf", f"{base}.xlsx"

        try:
            img = None
            if ind.tipo == "detalle":
                df = ejecutar_detalle(engine, ind, anio)
                donde = f"{xlsx_nombre} · hoja «{nombre_hoja(ind)}»"
            else:
                if ind.tipo == "foto":
                    df = ejecutar_foto(engine, ind, anio)
                elif ind.tipo == "tabla":
                    df = ejecutar_detalle(engine, ind, anio)
                else:
                    df = ejecutar(engine, ind, anio)
                    if ind.grafico:
                        img = generar_grafico(df, ind)
                donde = pdf_nombre
                if ind.excel:
                    donde += f" y {xlsx_nombre} · hoja «{nombre_hoja(ind)}»"

            if ind.excel or ind.tipo == "detalle":
                g["excel"].append((ind, df))
            g["pdf"].append((ind, df, None, img))
            resumen.append((ind.proceso, ind.nombre, donde, True))
            logging.info("OK: %s (%s)", ind.nombre, sistema)
        except Exception as e:
            logging.exception("Error en %s", ind.nombre)
            g["pdf"].append((ind, None, e, None))
            resumen.append((ind.proceso, ind.nombre, f"No se pudo calcular (ver {pdf_nombre})", False))

    engine.dispose()

    # Un PDF por proceso y fuente, y un Excel solo si ese grupo tiene hojas
    adjuntos = {}
    for (proceso, sistema), contenido in grupos.items():
        base = f"{_nombre_archivo(proceso)}_{_nombre_archivo(sistema)}_{anio}_{hoy:%Y-%m-%d}"
        adjuntos[f"{base}.pdf"] = html_a_pdf(
            armar_pdf_html(anio, contenido["pdf"], f"{proceso} · {sistema}"))
        if contenido["excel"]:
            adjuntos[f"{base}.xlsx"] = armar_excel(contenido["excel"])
        logging.info("Archivos generados: %s", base)

    cuerpo = armar_correo(anio, resumen, list(adjuntos))

    if "--prueba" in sys.argv:
        salida = Path("salida")
        salida.mkdir(exist_ok=True)
        (salida / "vista_previa_correo.html").write_text(cuerpo, encoding="utf-8")
        for nombre, contenido in adjuntos.items():
            (salida / nombre).write_bytes(contenido)
        logging.info("Modo prueba: archivos guardados en la carpeta 'salida'; no se envió nada")
        return

    enviar(f"Indicadores de gestión {anio} – corte {hoy:%d/%m/%Y}", cuerpo, {}, adjuntos)
    logging.info("Correo enviado con %d adjuntos", len(adjuntos))


if __name__ == "__main__":
    main()