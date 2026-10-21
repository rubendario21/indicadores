"""Dashboard web de indicadores en tiempo real.

Desarrollo:   .venv\\Scripts\\uvicorn dashboard:app --reload --port 8000
Producción:   ver README.md (uvicorn detrás de nginx)
"""
import hashlib
import hmac
import logging
import os
import re
import threading
from contextlib import asynccontextmanager
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

import zoho
import zoho_campaigns
from datos import crear_engine, ejecutar, ejecutar_detalle, ejecutar_foto
from indicadores import INDICADORES
from reporte import armar_excel, nombre_hoja
from reporte_pdf import EMPRESA, _estado, _resultado

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

CARPETA_WEB = Path(__file__).parent / "web"
NOMBRES_FUENTE = {"sql": "SAP", "zoho": "Zoho CRM"}
CACHE_SEG = int(os.getenv("DASHBOARD_CACHE_MIN", "5")) * 60
MIN_FORZAR_SEG = 60          # evita que el botón "Actualizar" martille SAP y Zoho
TOKEN_ZOHO_SEG = 50 * 60     # el token de Zoho dura 1 hora
MAX_FILAS_TABLA = 1000
ESTADOS = {"cumple": "cumple", "nocumple": "nocumple", "neutro": "neutro"}

_engine = None
_cache = {}                  # anio -> {"en": epoch, "datos": dict, "dfs": {id: (ind, df)}}
_bloqueo = threading.Lock()
_en_fondo = set()
_token_zoho_en = 0.0


# ---------------------------------------------------------------- usuarios

def hash_clave(clave, sal=None):
    sal = sal or os.urandom(16).hex()
    h = hashlib.pbkdf2_hmac("sha256", clave.encode(), bytes.fromhex(sal), 200_000).hex()
    return f"{sal}${h}"


def _usuarios():
    """DASHBOARD_USUARIOS=usuario:sal$hash,otro:sal$hash (se generan con crear_usuario.py)"""
    usuarios = {}
    for item in os.getenv("DASHBOARD_USUARIOS", "").split(","):
        if ":" in item:
            u, h = item.strip().split(":", 1)
            usuarios[u.lower()] = h
    return usuarios


def _clave_valida(usuario, clave):
    guardado = _usuarios().get(usuario.lower())
    if not guardado or "$" not in guardado:
        return False
    sal = guardado.split("$", 1)[0]
    return hmac.compare_digest(hash_clave(clave, sal), guardado)


# ---------------------------------------------------------------- cálculo

def _sistema(ind):
    return ind.sistema or NOMBRES_FUENTE.get(ind.fuente, ind.fuente.upper())


def _id(ind):
    return re.sub(r"[^a-z0-9]+", "-", f"{ind.proceso}-{ind.nombre}".lower()).strip("-")


def _num(v):
    return None if v is None or pd.isna(v) else float(v)


def _celda(v):
    if v is None or (not isinstance(v, str) and pd.isna(v)):
        return None
    if isinstance(v, (int, float)):
        return float(v)
    if isinstance(v, (pd.Timestamp, datetime, date)):
        return v.strftime("%d/%m/%Y")
    return str(v)


def _calcular_uno(ind, anio):
    if ind.tipo in ("detalle", "tabla"):
        return ejecutar_detalle(_engine, ind, anio)
    if ind.tipo == "foto":
        return ejecutar_foto(_engine, ind, anio)
    return ejecutar(_engine, ind, anio)


def _serializar(ind, df, error):
    valor, meta, fmt = _resultado(ind, df)
    estado, clase = _estado(ind, valor, meta, error)
    d = {
        "id": _id(ind), "nombre": ind.nombre, "proceso": ind.proceso, "sistema": _sistema(ind),
        "descripcion": ind.descripcion, "tipo": ind.tipo, "formato": ind.formato,
        "resultado": {"valor": _num(valor), "formato": fmt},
        "meta": None if meta is None else {"valor": meta, "formato": fmt, "sentido": ind.meta_sentido},
        "meta_serie": ind.meta, "meta_sentido": ind.meta_sentido, "acumulado": ind.acumulado,
        "estado": "error" if error is not None else ESTADOS[clase], "estado_texto": estado,
        "error": None if error is None else str(error)[:400],
        "excel": ind.excel or ind.tipo == "detalle",
        "tipo_grafico": ind.tipo_grafico or "barras",
    }
    if df is None:
        return d
    pct = None
    if ind.porcentaje:
        etiqueta, num, den = ind.porcentaje
        pct = {"etiqueta": etiqueta, "meta": ind.meta_porcentaje}

    if ind.tipo == "mensual":
        d["meses"] = list(df.index)
        d["series"] = [{"nombre": c, "valores": [_num(v) for v in df[c]]} for c in ind.columnas]
        if pct:
            pct["valores"] = [_num(v) for v in df[pct["etiqueta"]]]
    elif ind.tipo == "foto":
        fila = df.iloc[0]
        d["valores"] = [{"nombre": c, "valor": _num(fila[c])} for c in ind.columnas]
        if pct:
            pct["valor"] = _num(fila[pct["etiqueta"]])
    else:
        numericas = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        d["columnas"] = [{"nombre": str(c), "numerica": c in numericas} for c in df.columns]
        d["filas"] = [[_celda(v) for v in fila] for fila in df.head(MAX_FILAS_TABLA).itertuples(index=False)]
        d["total_filas"] = len(df)
    d["porcentaje"] = pct
    return d


def _refrescar_zoho():
    """Los datos de Zoho viven en lru_cache; en un servidor hay que vaciarlos en cada cálculo."""
    global _token_zoho_en
    for f in (zoho.oportunidades, zoho.cuentas, zoho_campaigns.reportes_campanas,
            zoho_campaigns.suscriptores):
        f.cache_clear()
    if time.time() - _token_zoho_en > TOKEN_ZOHO_SEG:
        zoho._token.cache_clear()
        _token_zoho_en = time.time()


def _calcular(anio):
    inicio = time.time()
    _refrescar_zoho()
    resultados = {}

    def correr(lista):
        for ind in lista:
            try:
                resultados[_id(ind)] = (ind, _calcular_uno(ind, anio), None)
            except Exception as e:
                logging.exception("Error en %s", ind.nombre)
                resultados[_id(ind)] = (ind, None, e)

    # SQL en paralelo; Zoho en un solo hilo para no descargar dos veces lo mismo
    sql = [i for i in INDICADORES if i.fuente != "zoho"]
    con_zoho = [i for i in INDICADORES if i.fuente == "zoho"]
    with ThreadPoolExecutor(max_workers=6) as pool:
        tareas = [pool.submit(correr, [i]) for i in sql]
        tareas.append(pool.submit(correr, con_zoho))
        for t in tareas:
            t.result()

    procesos = {}
    for ind in INDICADORES:
        _, df, error = resultados[_id(ind)]
        procesos.setdefault(ind.proceso, []).append(_serializar(ind, df, error))

    segundos = round(time.time() - inicio, 1)
    logging.info("Indicadores %s calculados en %s s", anio, segundos)
    return {
        "datos": {
            "empresa": EMPRESA, "anio": anio,
            "actualizado": datetime.now().isoformat(timespec="seconds"),
            "segundos": segundos, "cache_min": CACHE_SEG // 60,
            "procesos": [{"nombre": p, "indicadores": l} for p, l in procesos.items()],
        },
        "dfs": {k: (ind, df) for k, (ind, df, error) in resultados.items() if df is not None},
        "en": time.time(),
    }


def _recalcular(anio, edad_max):
    """Calcula salvo que otro hilo lo haya hecho mientras se esperaba el bloqueo."""
    with _bloqueo:
        actual = _cache.get(anio)
        if actual and time.time() - actual["en"] < edad_max:
            return actual
        _cache[anio] = _calcular(anio)
        return _cache[anio]


def _recalcular_en_fondo(anio):
    def tarea():
        try:
            _recalcular(anio, CACHE_SEG)
        except Exception:
            logging.exception("Error recalculando %s en segundo plano", anio)
        finally:
            _en_fondo.discard(anio)

    if anio not in _en_fondo:
        _en_fondo.add(anio)
        threading.Thread(target=tarea, daemon=True).start()


def _obtener(anio, forzar=False):
    """Vencida la caché se entrega el dato anterior y se recalcula en segundo plano;
    'Actualizar' (forzar) sí espera la consulta nueva."""
    actual = _cache.get(anio)
    if not actual:
        return _recalcular(anio, CACHE_SEG)
    edad = time.time() - actual["en"]
    if forzar and edad > MIN_FORZAR_SEG:
        return _recalcular(anio, MIN_FORZAR_SEG)
    if edad >= CACHE_SEG:
        _recalcular_en_fondo(anio)
    return actual


# ---------------------------------------------------------------- web

@asynccontextmanager
async def _ciclo(app):
    global _engine
    _engine = crear_engine(pool_pre_ping=True, pool_size=6, max_overflow=2, pool_recycle=1800)
    if not _usuarios():
        logging.warning("No hay usuarios en DASHBOARD_USUARIOS: nadie podrá entrar. Usa crear_usuario.py")
    yield
    _engine.dispose()


app = FastAPI(title="Indicadores de gestión", docs_url=None, redoc_url=None, openapi_url=None,
            lifespan=_ciclo)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("DASHBOARD_SECRET") or os.urandom(32).hex(),
    session_cookie="indicadores",
    max_age=12 * 3600,
    https_only=os.getenv("DASHBOARD_HTTPS", "0") == "1",
    same_site="lax",
)
app.mount("/static", StaticFiles(directory=CARPETA_WEB / "static"), name="static")


def _usuario(request):
    return request.session.get("usuario")


def _exigir_usuario(request):
    if not _usuario(request):
        raise HTTPException(status_code=401, detail="Sesión vencida")


def _anio(anio):
    hoy = date.today().year
    anio = anio or hoy
    if not hoy - 3 <= anio <= hoy:
        raise HTTPException(status_code=400, detail="Año fuera de rango")
    return anio


@app.get("/")
def inicio(request: Request):
    if not _usuario(request):
        return RedirectResponse("/login", status_code=303)
    return FileResponse(CARPETA_WEB / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/login")
def pagina_login(request: Request):
    if _usuario(request):
        return RedirectResponse("/", status_code=303)
    return FileResponse(CARPETA_WEB / "login.html")


@app.post("/login")
def login(request: Request, usuario: str = Form(...), clave: str = Form(...)):
    if not _clave_valida(usuario.strip(), clave):
        time.sleep(1)
        return RedirectResponse("/login?error=1", status_code=303)
    request.session.clear()
    request.session["usuario"] = usuario.strip().lower()
    logging.info("Ingreso: %s", usuario.strip().lower())
    return RedirectResponse("/", status_code=303)


@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login", status_code=303)


@app.get("/api/indicadores")
def api_indicadores(request: Request, anio: int | None = None, forzar: bool = False):
    _exigir_usuario(request)
    datos = dict(_obtener(_anio(anio), forzar)["datos"], usuario=_usuario(request))
    return JSONResponse(datos, headers={"Cache-Control": "no-store"})


@app.get("/api/excel")
def api_excel(request: Request, proceso: str, anio: int | None = None):
    _exigir_usuario(request)
    anio = _anio(anio)
    hojas = [(ind, df) for ind, df in _obtener(anio)["dfs"].values()
            if ind.proceso == proceso and ind.tipo in ("mensual", "detalle")]
    if not hojas:
        raise HTTPException(status_code=404, detail="Sin datos para ese proceso")
    vistos, unicas = set(), []
    for ind, df in hojas:              # Excel no admite hojas con el mismo nombre
        if nombre_hoja(ind) not in vistos:
            vistos.add(nombre_hoja(ind))
            unicas.append((ind, df))
    nombre = re.sub(r"[^\w]+", "_", f"{proceso}_{anio}_{date.today():%Y-%m-%d}")
    return Response(
        armar_excel(unicas),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{nombre}.xlsx"'},
    )


@app.get("/salud")
def salud():
    return {"ok": True}
