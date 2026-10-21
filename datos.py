from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL

from config import SQL

CARPETA_SQL = Path(__file__).parent / "consultas"
MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun","Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]


def crear_engine(**opciones):
    url = URL.create(
        "mssql+pyodbc",
        username=SQL["user"],
        password=SQL["password"],
        host=SQL["server"],
        port=SQL["port"],
        database=SQL["database"],
        query={"driver": SQL["driver"], "TrustServerCertificate": SQL["trust_cert"]},
    )
    return create_engine(url, **opciones)


def _leer(engine, ind, anio):
    sql = (CARPETA_SQL / ind.archivo_sql).read_text(encoding="utf-8")
    params = {"anio": anio} if ":anio" in sql else None
    with engine.connect() as cn:
        return pd.read_sql(text(sql), cn, params=params)


def _agregar_porcentaje(df, ind):
    if not ind.porcentaje:
        return df
    etiqueta, num, den = ind.porcentaje
    faltan = [c for c in (num, den) if c not in df.columns]
    if faltan:
        raise ValueError(f"{ind.nombre}: faltan las columnas {faltan} para el porcentaje")
    df[etiqueta] = df[num] / df[den].where(df[den] != 0)
    return df


def ejecutar(engine, ind, anio):
    df = _leer(engine, ind, anio)

    faltan = [c for c in ["Mes", *ind.columnas] if c not in df.columns]
    if faltan:
        raise ValueError(f"{ind.archivo_sql}: faltan las columnas {faltan}")

    df["Mes"] = df["Mes"].astype(int)
    df = df.set_index("Mes")[ind.columnas]
    if df.index.duplicated().any():
        raise ValueError(f"{ind.archivo_sql}: debe retornar una sola fila por mes")

    df = df.reindex(range(1, 13)).astype(float)
    df.index = MESES
    return _agregar_porcentaje(df, ind)


def ejecutar_detalle(engine, ind, anio):
    df = _leer(engine, ind, anio)
    return _agregar_porcentaje(df, ind)

def ejecutar_foto(engine, ind, anio):
    df = _leer(engine, ind, anio)

    faltan = [c for c in ind.columnas if c not in df.columns]
    if faltan:
        raise ValueError(f"{ind.archivo_sql}: faltan las columnas {faltan}")
    if len(df) != 1:
        raise ValueError(f"{ind.archivo_sql}: debe retornar una sola fila")

    df = df[ind.columnas].astype(float)
    return _agregar_porcentaje(df, ind)

def _leer(engine, ind, anio):
    if ind.fuente == "zoho":
        from zoho_indicadores import ejecutar_zoho
        return ejecutar_zoho(ind.consulta_zoho, anio)
    sql = (CARPETA_SQL / ind.archivo_sql).read_text(encoding="utf-8")
    params = {"anio": anio} if ":anio" in sql else None
    with engine.connect() as cn:
        return pd.read_sql(text(sql), cn, params=params)
