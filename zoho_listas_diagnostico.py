import json

from zoho_campaigns import _get

listas = _get("getmailinglists", {"sort": "asc", "fromindex": 1, "range": 20})
print("Listas de correo:")
print(json.dumps(listas, indent=2, ensure_ascii=False)[:2500])

lista = next((v for v in listas.values() if isinstance(v, list)), [])
if lista:
    clave = lista[0].get("listkey")
    for estado in ("active", "unsub"):
        subs = _get("getlistsubscribers", {
            "listkey": clave, "sort": "desc", "fromindex": 1, "range": 3, "status": estado,
        })
        print(f"\nSuscriptores de la primera lista (estado: {estado}):")
        print(json.dumps(subs, indent=2, ensure_ascii=False)[:2000])