import functools

import pandas as pd
import requests

from config import ZOHO
from zoho import _token

COLUMNAS = ["Campaña", "Fecha envío", "Enviados", "Entregados",
            "Aperturas", "Clics", "Rebotes", "Desuscritos"]


def _get(ruta, params):
    token, _ = _token()
    r = requests.get(
        f"{ZOHO['campaigns_url']}/api/v1.1/{ruta}",
        headers={"Authorization": f"Zoho-oauthtoken {token}"},
        params={"resfmt": "JSON", **params},
        timeout=60,
    )
    if r.status_code != 200:
        raise RuntimeError(f"Error Zoho Campaigns {ruta} ({r.status_code}): {r.text[:300]}")
    datos = r.json()
    if str(datos.get("status", "")).lower() == "error":
        raise RuntimeError(f"Zoho Campaigns {ruta}: {datos}")
    return datos


def _buscar(obj, clave):
    """Busca una clave en cualquier nivel de la respuesta JSON."""
    if isinstance(obj, dict):
        if clave in obj:
            return obj[clave]
        valores = obj.values()
    elif isinstance(obj, list):
        valores = obj
    else:
        return None
    for v in valores:
        encontrado = _buscar(v, clave)
        if encontrado is not None:
            return encontrado
    return None


def _numero(valor):
    try:
        return float(str(valor).replace(",", "").replace("%", ""))
    except (TypeError, ValueError):
        return 0.0
    
def _fecha_campana(c):
    """Fecha de envío en hora de Colombia, a partir de la lista de campañas."""
    try:
        return (pd.to_datetime(int(c.get("sent_time_gmt")), unit="ms", utc=True)
                .tz_convert("America/Bogota").tz_localize(None))
    except (TypeError, ValueError):
        return pd.to_datetime(c.get("sent_date_string"), format="%d %b %Y, %I:%M %p", errors="coerce")


def lista_campanas():
    campanas, inicio, bloque = [], 1, 50
    while True:
        datos = _get("recentcampaigns", {"fromindex": inicio, "range": bloque, "status": "sent"})
        lote = next((v for v in datos.values() if isinstance(v, list)), [])
        campanas.extend(lote)
        if len(lote) < bloque:
            break
        inicio += bloque
    return campanas


@functools.lru_cache(maxsize=4)
def reportes_campanas(anio):
    filas = []
    for c in lista_campanas():
        clave = c.get("campaign_key")
        fecha = _fecha_campana(c)
        if not clave or pd.isna(fecha) or fecha.year != anio:
            continue

        rep = _get("campaignreports", {"campaignkey": clave})
        filas.append({
            "Campaña": c.get("campaign_name"),
            "Fecha envío": fecha,
            "Enviados": _numero(_buscar(rep, "emails_sent_count")),
            "Entregados": _numero(_buscar(rep, "delivered_count")),
            "Aperturas": _numero(_buscar(rep, "opens_count")),
            "Clics": _numero(_buscar(rep, "unique_clicks_count")),
            "Rebotes": _numero(_buscar(rep, "bounces_count")),
            "Desuscritos": _numero(_buscar(rep, "unsub_count")),
        })

    df = pd.DataFrame(filas, columns=COLUMNAS)
    df["Fecha envío"] = pd.to_datetime(df["Fecha envío"])
    return df


def _get_o_vacio(ruta, params):
    """Igual que _get, pero si la lista no tiene contactos devuelve vacío en lugar de error."""
    try:
        return _get(ruta, params)
    except RuntimeError as e:
        if "2502" in str(e):
            return {}
        raise


def listas_correo():
    listas, inicio, bloque = [], 1, 50
    while True:
        datos = _get("getmailinglists", {"sort": "asc", "fromindex": inicio, "range": bloque})
        lote = datos.get("list_of_details") or []
        listas.extend(lote)
        if len(lote) < bloque:
            break
        inicio += bloque
    return listas


@functools.lru_cache(maxsize=1)
def suscriptores():
    """Contactos activos de todas las listas, con la fecha en que entraron a cada lista."""
    filas = []
    for lista in listas_correo():
        inicio, bloque = 1, 200
        while True:
            datos = _get_o_vacio("getlistsubscribers", {
                "listkey": lista["listkey"], "sort": "asc",
                "fromindex": inicio, "range": bloque, "status": "active",
            })
            lote = datos.get("list_of_details") or []
            for s in lote:
                filas.append({
                    "Lista": lista.get("listname"),
                    "Email": str(s.get("contact_email", "")).strip().lower(),
                    "Agregado": s.get("added_time"),
                })
            if len(lote) < bloque:
                break
            inicio += bloque

    df = pd.DataFrame(filas, columns=["Lista", "Email", "Agregado"])
    df["Agregado"] = pd.to_datetime(df["Agregado"], format="%d/%m/%Y", errors="coerce")
    return df