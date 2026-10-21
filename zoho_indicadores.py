import pandas as pd

from config import CAMPO_MOTIVO_PERDIDA, ORIGENES_CAMPANA
from zoho import cuentas, oportunidades
from zoho_campaigns import reportes_campanas,suscriptores

def tasa_cierre(anio):
    df = oportunidades()
    df = df[df["Estado"].isin(["Ganada","Perdida"]) & (df["FechaCierre"].dt.year == anio)]
    df = df.assign(Mes=df["FechaCierre"].dt.month)
    t = df.groupby("Mes").agg(
        Ganadas=("Estado", lambda s: (s == "Ganada").sum()),
        Perdidas=("Estado", lambda s: (s == "Perdida").sum()),
    )
    
    t["Cerradas"] = t["Ganadas"] + t["Perdidas"]
    return t.reset_index()

def ciclo_venta(anio):
    df = oportunidades()
    df = df[(df["Estado"] == "Ganada") & (df["FechaCierre"].dt.year == anio)].copy()
    df["Dias"] = (df["FechaCierre"] - df["Created_Time"].dt.normalize()).dt.days
    df = df[df["Dias"] >= 0]
    df["Mes"] = df["FechaCierre"].dt.month
    t = df.groupby("Mes").agg(**{
        "Dias promedio": ("Dias","mean"),
        "Dias maximo": ("Dias", "max"),
        "Ganadas": ("Dias", "count"),
    }).reset_index()
    t["Dias promedio"] = t["Dias promedio"].round(0)
    return t

def motivos_perdida(anio):
    df = oportunidades()
    df = df[(df["Estado"] == "Perdida") & (df["FechaCierre"].dt.year == anio)].copy()
    df["Motivo"] = (df[CAMPO_MOTIVO_PERDIDA].fillna("").astype(str).str.strip()
                    .replace("", "(Sin motivo)"))
    t = df.groupby("Motivo").agg(**{
        "Oportunidades": ("Motivo", "count"),
        "Valor (COP)": ("Amount", "sum"),
    }).reset_index()
    return t.sort_values("Valor (COP)", ascending=False)


def oportunidades_vencidas(anio):
    df = oportunidades()
    hoy = pd.Timestamp.today().normalize()
    abiertas = df[(df["Estado"] == "Abierta") & (df["FechaCierre"].dt.year == anio)]
    vencidas = abiertas[abiertas["FechaCierre"] < hoy]
    return pd.DataFrame([{"Abiertas": len(abiertas), "Vencidas": len(vencidas)}])


def oportunidades_vencidas_detalle(anio):
    df = oportunidades()
    hoy = pd.Timestamp.today().normalize()
    v = df[(df["Estado"] == "Abierta") & (df["FechaCierre"] < hoy) & (df["FechaCierre"].dt.year == anio)].copy()
    v["Días vencida"] = (hoy - v["FechaCierre"]).dt.days
    v = v.rename(columns={
        "Deal_Name": "Oportunidad", "Account_Name": "Cuenta", "Owner": "Comercial",
        "Stage": "Etapa", "Amount": "Valor (COP)", "FechaCierre": "Fecha de cierre",
    })
    columnas = ["Oportunidad", "Cuenta", "Comercial", "Etapa",
                "Valor (COP)", "Fecha de cierre", "Días vencida"]
    return v[columnas].sort_values("Días vencida", ascending=False)

def campanas_email(anio):
    df = reportes_campanas(anio)
    df = df.assign(Mes=df["Fecha envío"].dt.month)
    return df.groupby("Mes").agg(
        Campañas=("Campaña", "count"),
        Enviados=("Enviados", "sum"),
        Entregados=("Entregados", "sum"),
        Aperturas=("Aperturas", "sum"),
        Clics=("Clics", "sum"),
        Rebotes=("Rebotes", "sum"),
        Desuscritos=("Desuscritos", "sum"),
    ).reset_index()


def oportunidades_campanas(anio):
    df = oportunidades()
    de_campana = df["Campaign_Source"].notna() | df["Lead_Source"].isin(ORIGENES_CAMPANA)

    creadas = df[df["Created_Time"].dt.year == anio]
    c = (creadas.assign(Mes=creadas["Created_Time"].dt.month, Campana=de_campana)
                .groupby("Mes")
                .agg(**{"Creadas": ("Campana", "count"),
                        "De campañas": ("Campana", "sum")}))

    ganadas = df[de_campana & (df["Estado"] == "Ganada") & (df["FechaCierre"].dt.year == anio)]
    g = (ganadas.assign(Mes=ganadas["FechaCierre"].dt.month)
                .groupby("Mes")
                .agg(**{"Ganadas de campañas": ("Amount", "count"),
                        "Valor ganado de campañas": ("Amount", "sum")}))

    return c.join(g, how="outer").fillna(0).reset_index()

def valor_ganado(anio):
    df = oportunidades()
    ganadas = df[(df["Estado"] == "Ganada") & (df["FechaCierre"].dt.year == anio)]
    g = (ganadas.assign(Mes=ganadas["FechaCierre"].dt.month)
            .groupby("Mes")
            .agg(**{"Valor ganado": ("Amount", "sum"),
                    "Ganadas": ("Amount", "count")}))
    return g.reset_index()

def ticket_promedio(anio):
    df = valor_ganado(anio)
    df["Ticket promedio"] = df["Valor ganado"] / df["Ganadas"].where(df["Ganadas"] != 0)
    return df

def oportunidades_creadas(anio):
    df = oportunidades()
    creadas = df[df["Created_Time"].dt.year == anio]
    c = (creadas.assign(Mes=creadas["Created_Time"].dt.month)
        .groupby("Mes")
        .agg(**{"Valor creado": ("Amount", "sum"),
                "Creadas": ("Amount","count")}))
    return c.reset_index()

def pipeline_por_etapa(anio):
    df = oportunidades()
    abiertas = df[(df["Estado"] == "Abierta") & (df["Closing_Date"].dt.year == anio)]
    return (abiertas.groupby("Stage")
                    .agg(**{"Oportunidades": ("Amount", "count"),
                            "Valor": ("Amount", "sum"),
                            "_orden": ("Probability", "mean")})
                    .sort_values("_orden")
                    .drop(columns="_orden")
                    .reset_index()
                    .rename(columns={"Stage": "Etapa"}))

def pipeline_ponderado(anio):
    df = oportunidades()
    abiertas = df[(df["Estado"] == "Abierta") & (df["Closing_Date"].dt.year == anio)]
    ponderado = (abiertas["Amount"] * abiertas["Probability"].fillna(0) / 100).sum()
    return pd.DataFrame([{
        "Valor pipeline": abiertas["Amount"].sum(),
        "Valor ponderado": ponderado,
    }])

def oportunidades_sin_gestion(anio):
    df = oportunidades()
    hoy = pd.Timestamp.today().normalize()
    abiertas = df[(df["Estado"] == "Abierta") & (df["Closing_Date"].dt.year == anio)]
    dias = (hoy - abiertas["UltimaGestion"].dt.normalize()).dt.days
    return pd.DataFrame([{
        "Abiertas": len(abiertas),
        "Sin gestión": (dias > 30).sum(),
    }])
    
def _resumen_por(df, columna, anio):
    """Creadas, ganadas, perdidas, valor ganado y abiertas, agrupado por la columna indicada."""
    creadas = df[df["Created_Time"].dt.year == anio].groupby(columna).size().rename("Creadas")

    cerradas = df[df["Estado"].isin(["Ganada", "Perdida"]) & (df["FechaCierre"].dt.year == anio)]
    resultado = cerradas.groupby(columna).agg(
        Ganadas=("Estado", lambda s: (s == "Ganada").sum()),
        Perdidas=("Estado", lambda s: (s == "Perdida").sum()),
    )
    valor = (cerradas[cerradas["Estado"] == "Ganada"]
            .groupby(columna)["Amount"].sum().rename("Valor ganado (COP)"))
    abiertas = df[df["Estado"] == "Abierta"].groupby(columna).size().rename("Abiertas hoy")

    t = pd.concat([creadas, resultado, valor, abiertas], axis=1).fillna(0)
    t["Cerradas"] = t["Ganadas"] + t["Perdidas"]
    t.index.name = columna
    columnas = ["Creadas", "Ganadas", "Perdidas", "Cerradas", "Valor ganado (COP)", "Abiertas hoy"]
    return t[columnas].reset_index().sort_values("Valor ganado (COP)", ascending=False)


def desempeno_comercial(anio):
    df = oportunidades().assign(Comercial=lambda d: d["Owner"].fillna("(Sin responsable)"))
    return _resumen_por(df, "Comercial", anio)


def conversion_por_origen(anio):
    df = oportunidades().assign(Origen=lambda d: d["Lead_Source"].fillna("(Sin origen)"))
    return _resumen_por(df, "Origen", anio)

def cuentas_nuevas(anio):
    c = cuentas()
    nuevas = c[c["Created_Time"].dt.year == anio]
    con_oportunidad = set(oportunidades()["Account_Id"].dropna())
    return (nuevas.assign(Mes=nuevas["Created_Time"].dt.month,
                        ConOportunidad=nuevas["id"].isin(con_oportunidad))
            .groupby("Mes")
            .agg(**{"Creadas": ("id","count"),
                    "Con oportunidad": ("ConOportunidad","sum")})
            .reset_index())

def clientes_nuevos_recurrentes(anio):
    df = oportunidades()
    g = df[df["Estado"] == "Ganada"].dropna(subset=["FechaCierre"]).copy()

    # Cliente = cuenta de la oportunidad; si no tiene cuenta, se toma como cliente único
    g["Cliente"] = g["Account_Id"].fillna(g["Account_Name"]).fillna(g["id"])
    primera_ganada = g.groupby("Cliente")["FechaCierre"].transform("min")
    g["Nuevo"] = g["FechaCierre"] == primera_ganada

    g = g[g["FechaCierre"].dt.year == anio]
    g = g.assign(Mes=g["FechaCierre"].dt.month,
                ValorNuevo=g["Amount"].where(g["Nuevo"], 0),
                ValorRecurrente=g["Amount"].where(~g["Nuevo"], 0))
    return g.groupby("Mes").agg(**{
        "Ganadas": ("Nuevo", "count"),
        "De clientes nuevos": ("Nuevo", "sum"),
        "De recurrentes": ("Nuevo", lambda s: (~s).sum()),
        "Valor ganado": ("Amount", "sum"),
        "Valor clientes nuevos": ("ValorNuevo", "sum"),
        "Valor recurrentes": ("ValorRecurrente", "sum"),
    }).reset_index()
    
    
def _ganado_por_cuenta(anio):
    df = oportunidades()
    g = df[(df["Estado"] == "Ganada") & (df["FechaCierre"].dt.year == anio)].copy()
    g["Cuenta"] = g["Account_Name"].fillna("(Sin cuenta)")
    g["Clave"] = g["Account_Id"].fillna(g["Cuenta"])
    return (g.groupby("Clave")
            .agg(**{"Cuenta": ("Cuenta", "first"),
                    "Ganadas": ("Amount", "count"),
                    "Valor ganado": ("Amount", "sum")})
            .sort_values("Valor ganado", ascending=False)
            .reset_index(drop=True))


def concentracion_ventas(anio):
    t = _ganado_por_cuenta(anio)
    return pd.DataFrame([{
        "Valor ganado del año": t["Valor ganado"].sum(),
        "Top 5 cuentas": t["Valor ganado"].head(5).sum(),
        "Cuentas con ventas": len(t),
    }])


def principales_cuentas(anio):
    return _ganado_por_cuenta(anio).head(10)

def _fecha_referencia(anio):
    hoy = pd.Timestamp.today().normalize()
    return hoy if anio >= hoy.year else pd.Timestamp(anio, 12, 31)


def _clientes_historicos(anio):
    """Una fila por cuenta que ganó hasta la fecha de referencia, con su última oportunidad creada."""
    ref = _fecha_referencia(anio)
    df = oportunidades()
    df = df[df["Account_Id"].notna() & (df["Created_Time"] <= ref + pd.Timedelta(days=1))]
    ganadas = df[(df["Estado"] == "Ganada") & (df["FechaCierre"] <= ref)]
    resumen = ganadas.groupby("Account_Id").agg(**{
        "Cuenta": ("Account_Name", "first"),
        "Ganadas históricas": ("Amount", "count"),
        "Valor ganado histórico (COP)": ("Amount", "sum"),
        "Última ganada": ("FechaCierre", "max"),
    })
    ultima = df.groupby("Account_Id")["Created_Time"].max().rename("Última oportunidad")
    return resumen.join(ultima)


def cuentas_inactivas(anio):
    ref = _fecha_referencia(anio)
    t = _clientes_historicos(anio)
    t = t[t["Última oportunidad"] < ref - pd.DateOffset(months=6)].copy()

    t["Meses sin oportunidades"] = ((ref - t["Última oportunidad"]).dt.days / 30.4).round(0)
    t["Última oportunidad"] = t["Última oportunidad"].dt.normalize()
    t["Responsable"] = t.index.map(cuentas().set_index("id")["Owner"])

    columnas = ["Cuenta", "Responsable", "Ganadas históricas", "Valor ganado histórico (COP)",
                "Última ganada", "Última oportunidad", "Meses sin oportunidades"]
    return (t[columnas].sort_values("Valor ganado histórico (COP)", ascending=False)
                    .reset_index(drop=True))


def cuentas_inactivas_resumen(anio):
    ref = _fecha_referencia(anio)
    t = _clientes_historicos(anio)
    return pd.DataFrame([{
        "Clientes con compras": len(t),
        "Inactivos": (t["Última oportunidad"] < ref - pd.DateOffset(months=6)).sum(),
    }])
    
def _por_campo_de_cuenta(campo, etiqueta, anio):
    valores = cuentas().set_index("id")[campo]
    df = oportunidades()
    df = df.assign(**{etiqueta: df["Account_Id"].map(valores).fillna(f"(Sin {etiqueta.lower()})")})
    return _resumen_por(df, etiqueta, anio)


def ventas_por_sector(anio):
    return _por_campo_de_cuenta("Grupo", "Sector", anio)


def ventas_por_tipo_cuenta(anio):
    categorias = cuentas().set_index("id")["Categoria"]
    df = oportunidades()
    df = df.assign(**{"Tipo de cuenta": df["Account_Id"].map(categorias)})
    df["Tipo de cuenta"] = df["Tipo de cuenta"].map(
        lambda v: v if isinstance(v, list) and v else ["(sin categoria)"])
    df = df.explode("Tipo de cuenta")
    return _resumen_por(df, "Tipo de cuenta", anio)

def campanas_enviadas(anio):
    df = campanas_email(anio).set_index("Mes")
    hoy = pd.Timestamp.today()
    ultimo_mes = hoy.month if anio == hoy.year else 12
    return (df.reindex(range(1, ultimo_mes + 1), fill_value=0)
            .rename_axis("Mes")
            .reset_index())
    
def crecimiento_base(anio):
    s = suscriptores()
    # Cada persona cuenta una sola vez, en la fecha en que entró por primera vez a cualquier lista
    primera = s.groupby("Email")["Agregado"].min()
    nuevos = primera[primera.dt.year == anio]
    t_nuevos = nuevos.groupby(nuevos.dt.month).size().rename("Nuevos")

    desuscritos = campanas_email(anio).set_index("Mes")["Desuscritos"]

    t = pd.concat([t_nuevos, desuscritos], axis=1).fillna(0)
    t["Crecimiento neto"] = t["Nuevos"] - t["Desuscritos"]
    t.index.name = "Mes"
    return t.reset_index()


def tamano_base(anio):
    ref = _fecha_referencia(anio)
    s = suscriptores()
    s = s[s["Agregado"] <= ref]
    return pd.DataFrame([{
        "Contactos activos": s["Email"].nunique(),
        "Listas con contactos": s["Lista"].nunique(),
    }])

    
CONSULTAS = {
    "tasa_cierre": tasa_cierre,
    "ciclo_venta": ciclo_venta,
    "motivos_perdida": motivos_perdida,
    "oportunidades_vencidas": oportunidades_vencidas,
    "oportunidades_vencidas_detalle": oportunidades_vencidas_detalle,
    "campanas_email": campanas_email,
    "oportunidades_campanas": oportunidades_campanas,
    "valor_ganado": valor_ganado,
    "ticket_promedio": ticket_promedio,
    "oportunidades_creadas": oportunidades_creadas,
    "pipeline_por_etapa": pipeline_por_etapa,
    "pipeline_ponderado": pipeline_ponderado,
    "oportunidades_sin_gestion": oportunidades_sin_gestion,
    "desempeno_comercial": desempeno_comercial,
    "conversion_por_origen": conversion_por_origen,
    "cuentas_nuevas": cuentas_nuevas,
    "clientes_nuevos_recurrentes": clientes_nuevos_recurrentes,
    "concentracion_ventas": concentracion_ventas,
    "principales_cuentas": principales_cuentas,
    "cuentas_inactivas_resumen": cuentas_inactivas_resumen,
    "cuentas_inactivas": cuentas_inactivas,
    "ventas_por_sector": ventas_por_sector,
    "ventas_por_tipo_cuenta": ventas_por_tipo_cuenta,
    "campanas_enviadas": campanas_enviadas,
    "crecimiento_base": crecimiento_base,
    "tamano_base": tamano_base,
}

def ejecutar_zoho(nombre, anio):
    if nombre not in CONSULTAS:
        raise ValueError(f"Consulta Zoho '{nombre}' no existe en zoho_indicadores.py")
    return CONSULTAS[nombre](anio)