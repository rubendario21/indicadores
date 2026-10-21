from config import CAMPO_MOTIVO_PERDIDA,ETAPAS_GANADA,ETAPAS_PERDIDA
from zoho import oportunidades

df = oportunidades()

print(f"Oportunidades descargadas: {len(df)}\n")

print("Etapas en zoho CRM:")
print(df["Stage"].value_counts(dropna=False).to_string(), "\n")

print(f"Configuradas como ganada: {ETAPAS_GANADA}")
print(f"Configuradas como perdida: {ETAPAS_PERDIDA}")
print(df["Estado"].value_counts().to_string(),"\n")

perdidas = df[df["Estado"] == "Perdida"]
abiertas = df[df["Estado"] == "Abierta"]

print(f"Perdidas sin motivo: {perdidas[CAMPO_MOTIVO_PERDIDA].isna().sum()} {len(perdidas)}")
print(f"Abiertas sin fecha de cierre: {abiertas['Closing_Date'].isna().sum()} de {len(abiertas)}")
