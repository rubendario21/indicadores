"""Genera la entrada de un usuario para DASHBOARD_USUARIOS en el .env

Uso: python crear_usuario.py nombre_usuario
"""
import getpass
import sys

from dashboard import hash_clave

if len(sys.argv) != 2:
    sys.exit("Uso: python crear_usuario.py nombre_usuario")

usuario = sys.argv[1].strip().lower()
clave = getpass.getpass(f"Contraseña para {usuario}: ")
if len(clave) < 8:
    sys.exit("La contraseña debe tener al menos 8 caracteres")
if clave != getpass.getpass("Repítela: "):
    sys.exit("Las contraseñas no coinciden")

print("\nAgrega esto a DASHBOARD_USUARIOS en el .env (separa varios usuarios con coma):\n")
print(f"{usuario}:{hash_clave(clave)}")
