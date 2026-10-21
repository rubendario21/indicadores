import json
from datetime import date

from zoho import oportunidades
from zoho_campaigns import _get, lista_campanas, reportes_campanas

campanas = lista_campanas()
print(f"Campañas enviadas encontradas: {len(campanas)}")
if campanas:
    print("\nPrimera campaña de la lista:")
    print(json.dumps(campanas[0], indent=2, ensure_ascii=False)[:1500])
    rep = _get("campaignreports", {"campaignkey": campanas[0].get("campaign_key")})
    print("\nReporte de esa campaña:")
    print(json.dumps(rep, indent=2, ensure_ascii=False)[:2500])

df = reportes_campanas(date.today().year)
print(f"\nCampañas del año con reporte: {len(df)}")
print(df.head(10).to_string())

print("\nFuentes de las oportunidades en el CRM (Lead_Source):")
print(oportunidades()["Lead_Source"].value_counts(dropna=False).to_string())
print("\nOportunidades con campaña de origen:", oportunidades()["Campaign_Source"].notna().sum())

import pandas as pd
from zoho_campaigns import _fecha_campana

print("\nCampañas enviadas por año:")
print(pd.Series([_fecha_campana(c).year for c in campanas]).value_counts().sort_index().to_string())