import os
from dotenv import load_dotenv

load_dotenv()

SQL = {
    "server": os.getenv("SQL_SERVER"),
    "port": int(os.getenv("SQL_PORT","1433")),
    "database": os.getenv("SQL_DATABASE"),
    "user": os.getenv("SQL_USER"),
    "password": os.getenv("SQL_PASSWORD"),
    "driver": os.getenv("SQL_DRIVER"),
    "trust_cert": os.getenv("SQL_TRUST_CERT")
}

GRAPH = {
    "tenant_id": os.getenv("GRAPH_TENANT_ID"),
    "client_id": os.getenv("GRAPH_CLIENT_ID"),
    "client_secret": os.getenv("GRAPH_CLIENT_SECRET"),
}

MAIL_FROM = os.getenv("MAIL_FROM")
MAIL_TO = [c.strip() for c in os.getenv("MAIL_TO","").split(",") if c.strip()]


ZOHO = {
    "client_id": os.getenv("ZOHO_CLIENT_ID"),
    "client_secret": os.getenv("ZOHO_CLIENT_SECRET"),
    "refresh_token": os.getenv("ZOHO_REFRESH_TOKEN"),
    "accounts_url": os.getenv("ZOHO_ACCOUNTS_URL", "https://accounts.zoho.com"),
    "api_version": os.getenv("ZOHO_CRM_VERSION", "v7"),
    "campaigns_url": os.getenv("ZOHO_CAMPAIGNS_URL", "https://campaigns.zoho.com"),
}

def _lista(nombre, defecto):
    return [x.strip() for x in os.getenv(nombre, defecto).split(",") if x.strip()]

ETAPAS_GANADA = _lista("ZOHO_ETAPAS_GANADA", "Cerrado Ganado")
ETAPAS_PERDIDA = _lista("ZOHO_ETAPAS_PERDIDA", "Cerrado Perdido")
CAMPO_MOTIVO_PERDIDA = os.getenv("ZOHO_CAMPO_MOTIVO", "Reason_For_Loss__s")
ORIGENES_CAMPANA = _lista("ZOHO_ORIGENES_CAMPANA", "Campaña,Email marketing")