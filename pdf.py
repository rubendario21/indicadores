import io

from xhtml2pdf import pisa


def html_a_pdf(html):
    buf = io.BytesIO()
    resultado = pisa.CreatePDF(html, dest=buf, encoding="utf-8")
    if resultado.err:
        raise RuntimeError("No se pudo generar el PDF")
    return buf.getvalue()