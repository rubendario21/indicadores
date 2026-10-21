import functools
import pandas as pd
import requests

from config import CAMPO_MOTIVO_PERDIDA,ETAPAS_GANADA,ETAPAS_PERDIDA,ZOHO

CAMPOS_DEALS = ["Deal_Name", "Stage", "Amount","Probability", "Closing_Date", "Created_Time",
                "Modified_Time","Last_Activity_Time", "Owner", "Account_Name", "Lead_Source", "Campaign_Source",
                CAMPO_MOTIVO_PERDIDA]

@functools.lru_cache(maxsize=1)
def _token():
    r = requests.post(
        f"{ZOHO['accounts_url']}/oauth/v2/token",
        params={
            "refresh_token": ZOHO["refresh_token"],
            "client_id": ZOHO["client_id"],
            "client_secret": ZOHO["client_secret"],
            "grant_type": "refresh_token",
        },
        timeout=30,
    )
    
    datos = r.json()
    if "access_token" not in datos:
        raise RuntimeError(f"Zoho no entrego el token: {datos}")
    return datos['access_token'], datos.get("api_domain", "https://www.zohoapis.com")

def obtener_registros(modulo, campos):
    token, dominio = _token()
    url = f"{dominio}/crm/{ZOHO['api_version']}/{modulo}"
    headers = {"Authorization": f"Zoho-oauthtoken {token}"}
    base = {"fields": ",".join(campos), "per_page": 200}
    params = dict(base, page=1)
    registros = []
    
    while True:
        r = requests.get(url, headers=headers, params=params, timeout=60)
        if r.status_code == 204:
            break
        if r.status_code != 200:
            raise RuntimeError(f"Error Zoho {modulo} ({r.status_code}): {r.text[:300]}")
        
        cuerpo = r.json()
        registros.extend(cuerpo.get("data", []))
        info = cuerpo.get("info",[])
        if not info.get("more_page_token"):
            break
        if info.get("next_page_token"):
            params = dict(base, page_token=info["next_page_token"])
        else:
            params = dict(base, page=info.get("page", 1) + 1)
    return registros

def _nombre(valor):
    return valor.get("name") if isinstance(valor, dict) else valor

@functools.lru_cache(maxsize=1)
def oportunidades():
    """Todas las oportunidades, descargadas una sola vez por ejecucion."""
    df = pd.DataFrame(obtener_registros("Deals",CAMPOS_DEALS))
    for campo in CAMPOS_DEALS:
        if campo not in df.columns:
            df[campo] = None
    
    df["Owner"] = df["Owner"].map(_nombre)
    df["Account_Id"] = df["Account_Name"].map(lambda v: v.get("id") if isinstance(v, dict) else None)
    df["Account_Name"] = df["Account_Name"].map(_nombre)
    df["Account_Name"] = df["Account_Name"].map(_nombre)
    df["Campaign_Source"] = df["Campaign_Source"].map(_nombre)
    df["Amount"] = pd.to_numeric(df["Amount"], errors="coerce").fillna(0)
    df["Probability"] = pd.to_numeric(df["Probability"], errors="coerce")
    df["Closing_Date"] = pd.to_datetime(df["Closing_Date"], errors="coerce")
    for campo in ("Created_Time", "Modified_Time", "Last_Activity_Time"):
        df[campo] = (pd.to_datetime(df[campo], errors="coerce", utc=True)
                    .dt.tz_convert("America/Bogota")
                    .dt.tz_localize(None))
    df["Estado"] = "Abierta"
    df.loc[df["Stage"].isin(ETAPAS_GANADA), "Estado"] = "Ganada"
    df.loc[df["Stage"].isin(ETAPAS_PERDIDA), "Estado"] = "Perdida"
    df["FechaCierre"] = df["Closing_Date"]
    cerradas_sin_fecha = df["Estado"].isin(["Ganada", "Perdida"]) & df["Closing_Date"].isna()
    df.loc[cerradas_sin_fecha, "FechaCierre"] = df.loc[cerradas_sin_fecha, "Modified_Time"].dt.normalize()
    df["UltimaGestion"] = df["Last_Activity_Time"].fillna(df["Modified_Time"])
    return df

CAMPOS_ACCOUNTS = ["Account_Name", "Created_Time", "Owner", "Industry","Grupo","Categoria", "Account_Type"]

def _lista_valores(valor):
    """Convierte el valor de un campo de selección múltiple en una lista limpia."""
    if isinstance(valor, list):
        return [str(x).strip() for x in valor if str(x).strip()]
    if isinstance(valor, str) and valor.strip():
        return [x.strip() for x in valor.split(";") if x.strip()]
    return []

@functools.lru_cache(maxsize=1)
def cuentas():
    """Todas las cuentas, descargadas una sola vez por ejecución."""
    df = pd.DataFrame(obtener_registros("Accounts", CAMPOS_ACCOUNTS))
    for campo in CAMPOS_ACCOUNTS + ["id"]:
        if campo not in df.columns:
            df[campo] = None

    df["Owner"] = df["Owner"].map(_nombre)
    df["Created_Time"] = (pd.to_datetime(df["Created_Time"], errors="coerce", utc=True)
                            .dt.tz_convert("America/Bogota")
                            .dt.tz_localize(None))
    df["Categoria"] = df["Categoria"].map(_lista_valores)
    return df