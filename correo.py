import base64

import msal
import requests
from pathlib import Path
from config import GRAPH, MAIL_FROM, MAIL_TO

XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
TIPOS = {".pdf": "application/pdf", ".xlsx": XLSX}


def _token():
    app = msal.ConfidentialClientApplication(
        GRAPH["client_id"],
        authority=f"https://login.microsoftonline.com/{GRAPH['tenant_id']}",
        client_credential=GRAPH["client_secret"],
    )
    r = app.acquire_token_for_client(scopes=["https://graph.microsoft.com/.default"])
    if "access_token" not in r:
        raise RuntimeError(f"No se obtuvo token: {r.get('error_description')}")
    return r["access_token"]


def _adjunto(nombre, contenido, tipo, cid=None):
    a = {
        "@odata.type": "#microsoft.graph.fileAttachment",
        "name": nombre,
        "contentType": tipo,
        "contentBytes": base64.b64encode(contenido).decode(),
    }
    if cid:
        a.update({"contentId": cid, "isInline": True})
    return a


TIPOS = {".pdf": "application/pdf", ".xlsx": XLSX}


def enviar(asunto, html, imagenes, adjuntos=None):
    attachments = [_adjunto(f"{cid}.png", img, "image/png", cid) for cid, img in imagenes.items()]
    for nombre, contenido in (adjuntos or {}).items():
        tipo = TIPOS.get(Path(nombre).suffix.lower(), "application/octet-stream")
        attachments.append(_adjunto(nombre, contenido, tipo))

    mensaje = {
        "message": {
            "subject": asunto,
            "body": {"contentType": "HTML", "content": html},
            "toRecipients": [{"emailAddress": {"address": c}} for c in MAIL_TO],
            "attachments": attachments,
        },
        "saveToSentItems": True,
    }
    r = requests.post(
        f"https://graph.microsoft.com/v1.0/users/{MAIL_FROM}/sendMail",
        headers={"Authorization": f"Bearer {_token()}"},
        json=mensaje,
        timeout=60,
    )
    if r.status_code != 202:
        raise RuntimeError(f"Error enviando correo ({r.status_code}): {r.text}")