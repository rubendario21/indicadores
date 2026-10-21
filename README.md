# Indicadores de gestión

Calcula los indicadores de gestión desde **SAP (SQL Server)** y **Zoho CRM / Campaigns** y los muestra de dos formas:

- **Dashboard web en tiempo real** (`dashboard.py`): tablero tipo Power BI con resumen general, una vista por proceso, gráficos interactivos, tablas mensuales y descarga a Excel.
- **Reporte por correo** (`main.py`): genera los PDF y Excel por proceso y los envía con Microsoft Graph. Sigue funcionando igual que antes.

Las dos usan la misma definición de indicadores (`indicadores.py` + `consultas/*.sql`).

---

## Contenido

1. [Estructura del proyecto](#1-estructura-del-proyecto)
2. [Variables del .env](#2-variables-del-env)
3. [Trabajar en localhost (Windows)](#3-trabajar-en-localhost-windows)
4. [Publicar en el servidor Ubuntu con nginx](#4-publicar-en-el-servidor-ubuntu-con-nginx)
5. [Actualizar el servidor con cambios nuevos](#5-actualizar-el-servidor-con-cambios-nuevos)
6. [Tareas frecuentes](#6-tareas-frecuentes)
7. [Solución de problemas](#7-solución-de-problemas)

---

## 1. Estructura del proyecto

```
indicadores/
├── dashboard.py            # Servidor web (FastAPI): login, API y caché
├── crear_usuario.py        # Genera usuarios para el dashboard
├── main.py                 # Reporte PDF/Excel por correo
├── indicadores.py          # Definición de todos los indicadores (metas, columnas, proceso)
├── consultas/              # Un .sql por indicador de SAP
├── datos.py                # Conexión a SQL Server y ejecución de consultas
├── zoho.py, zoho_campaigns.py, zoho_indicadores.py   # Indicadores de Zoho
├── reporte.py, reporte_pdf.py, graficos.py, correo.py, pdf.py   # Reporte por correo
├── web/
│   ├── index.html          # Dashboard
│   ├── login.html          # Pantalla de ingreso
│   └── static/             # estilos.css, app.js y vendor/echarts
├── deploy/
│   ├── nginx-dashboard.conf            # Sitio de nginx
│   └── indicadores-dashboard.service   # Servicio systemd
├── requirements.txt
└── .env                    # Credenciales (NO se sube a ningún repositorio)
```

---

## 2. Variables del .env

Las de SQL, Graph y Zoho ya existían. Las del dashboard son nuevas.

| Variable | Ejemplo | Para qué |
|---|---|---|
| `SQL_SERVER`, `SQL_PORT`, `SQL_DATABASE`, `SQL_USER`, `SQL_PASSWORD` | | Conexión a la base de SAP |
| `SQL_DRIVER` | `ODBC Driver 18 for SQL Server` | Driver ODBC instalado en la máquina |
| `SQL_TRUST_CERT` | `yes` | Confiar en el certificado del SQL Server |
| `GRAPH_*`, `MAIL_FROM`, `MAIL_TO` | | Envío del correo (solo `main.py`) |
| `ZOHO_*` | | Acceso a Zoho CRM y Campaigns |
| `DASHBOARD_USUARIOS` | `ruben:3bd8...$9f1a...,ana:...` | Usuarios del dashboard. Se generan con `crear_usuario.py` |
| `DASHBOARD_SECRET` | texto aleatorio de 64 caracteres | Firma la cookie de sesión. **Distinto en local y en el servidor** |
| `DASHBOARD_CACHE_MIN` | `5` | Cada cuántos minutos se vuelve a consultar SAP y Zoho |
| `DASHBOARD_HTTPS` | `0` en local, `1` en el servidor | Con `1` la cookie de sesión solo viaja por HTTPS |

Para generar un `DASHBOARD_SECRET` nuevo:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

---

## 3. Trabajar en localhost (Windows)

### 3.1 Requisitos

- Python 3.10 o superior.
- **Microsoft ODBC Driver 17 o 18 for SQL Server** (el mismo que ya usa `main.py`).
- Acceso de red al SQL Server de SAP desde el equipo.

### 3.2 Instalar dependencias

En PowerShell, dentro de la carpeta del proyecto:

```powershell
cd C:\wamp64\www\Python\indicadores

# Solo la primera vez, si no existe la carpeta .venv
python -m venv .venv

.venv\Scripts\python -m pip install -r requirements.txt
```

### 3.3 Crear tu usuario

```powershell
.venv\Scripts\python crear_usuario.py ruben
```

Pide la contraseña dos veces (mínimo 8 caracteres) e imprime una línea como:

```
ruben:3bd8e9d0...$a91c4f...
```

Cópiala en el `.env`:

```ini
DASHBOARD_USUARIOS=ruben:3bd8e9d0...$a91c4f...
```

Para varios usuarios, sepáralos con coma:

```ini
DASHBOARD_USUARIOS=ruben:xxxx$yyyy,gerencia:xxxx$yyyy,comercial:xxxx$yyyy
```

### 3.4 Arrancar el dashboard

```powershell
.venv\Scripts\uvicorn dashboard:app --reload --port 8000
```

Abre **http://localhost:8000** e ingresa con tu usuario.

- La **primera carga tarda unos 10 a 20 segundos** porque consulta SAP y Zoho. Después responde al instante desde la caché.
- `--reload` reinicia el servidor solo cuando guardas cambios en el código.
- Para detenerlo: `Ctrl + C`.

### 3.5 Probar que todo está bien

```powershell
curl http://localhost:8000/salud
# {"ok":true}
```

En la consola donde corre uvicorn verás líneas como:

```
INFO Ingreso: ruben
INFO Indicadores 2026 calculados en 6.7 s
```

Si un indicador falla, el dashboard lo muestra con el estado **Con error** y el mensaje del error, y la consola muestra el detalle completo.

### 3.6 El reporte por correo sigue igual

```powershell
.venv\Scripts\python main.py --prueba   # genera los archivos en salida\ sin enviar nada
.venv\Scripts\python main.py            # genera y envía el correo
```

---

## 4. Publicar en el servidor Ubuntu con nginx

Resultado final: **https://dashboard.peoplecore.com.co** → nginx (HTTPS) → uvicorn en `127.0.0.1:8000` → SAP y Zoho.

Probado para Ubuntu 22.04 y 24.04. Todos los comandos se ejecutan en el servidor, salvo el paso 4.4, que se hace desde tu equipo Windows.

### 4.1 Antes de empezar

1. **DNS**: en el administrador del dominio `peoplecore.com.co`, crea un registro:

   | Tipo | Nombre | Valor |
   |---|---|---|
   | A | `dashboard` | IP pública del servidor Ubuntu |

   Verifica desde tu equipo (puede tardar unos minutos en propagarse):

   ```powershell
   nslookup dashboard.peoplecore.com.co
   ```

2. **Firewall del SQL Server**: pide que permitan la **IP pública del servidor Ubuntu** hacia el SQL Server de SAP (puerto `SQL_PORT`, normalmente 1433). Sin esto el dashboard no podrá consultar SAP.

### 4.2 Instalar paquetes del sistema

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip nginx certbot python3-certbot-nginx curl gnupg
```

### 4.3 Instalar el driver ODBC 18 de SQL Server

```bash
curl -fsSL https://packages.microsoft.com/keys/microsoft.asc \
  | sudo gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg

curl -fsSL https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list \
  | sudo tee /etc/apt/sources.list.d/mssql-release.list

sudo apt update
sudo ACCEPT_EULA=Y apt install -y msodbcsql18 unixodbc-dev
```

Verifica que quedó instalado:

```bash
odbcinst -q -d
# [ODBC Driver 18 for SQL Server]
```

### 4.4 Copiar el proyecto al servidor (desde Windows)

En PowerShell, en tu equipo, empaqueta el proyecto **sin** la `.venv`, la carpeta `salida` ni los `__pycache__`:

```powershell
cd C:\wamp64\www\Python\indicadores
tar --exclude=.venv --exclude=__pycache__ --exclude=salida -czf $env:TEMP\indicadores.tar.gz .
scp $env:TEMP\indicadores.tar.gz usuario@IP_DEL_SERVIDOR:/tmp/
```

> El paquete incluye tu `.env` con credenciales. Bórralo de `/tmp` cuando termines (paso 4.5).

### 4.5 Ubicar el código en el servidor

```bash
# Usuario de sistema sin acceso por SSH, solo para correr el dashboard
sudo useradd --system --home /opt/indicadores --shell /usr/sbin/nologin indicadores

sudo mkdir -p /opt/indicadores
sudo tar -xzf /tmp/indicadores.tar.gz -C /opt/indicadores
rm /tmp/indicadores.tar.gz
```

### 4.6 Entorno de Python

```bash
cd /opt/indicadores
sudo python3 -m venv .venv
sudo .venv/bin/pip install --upgrade pip
sudo .venv/bin/pip install -r requirements.txt
```

### 4.7 Ajustar el .env del servidor

```bash
sudo nano /opt/indicadores/.env
```

Cambia estas líneas:

```ini
SQL_DRIVER=ODBC Driver 18 for SQL Server
SQL_TRUST_CERT=yes
DASHBOARD_HTTPS=1
DASHBOARD_SECRET=<genera uno nuevo, distinto al de tu equipo>
DASHBOARD_USUARIOS=<los usuarios de producción>
```

Genera el secreto en el servidor:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Puedes crear usuarios directamente en el servidor:

```bash
cd /opt/indicadores && sudo .venv/bin/python crear_usuario.py gerencia
```

### 4.8 Permisos

```bash
sudo chown -R indicadores:indicadores /opt/indicadores
sudo chmod 600 /opt/indicadores/.env        # solo el usuario del servicio lee las credenciales
sudo chmod 755 /opt/indicadores /opt/indicadores/web /opt/indicadores/web/static
```

### 4.9 Probar la conexión a SQL Server y Zoho

```bash
cd /opt/indicadores
sudo -u indicadores .venv/bin/python -c "
from sqlalchemy import text
from datos import crear_engine
with crear_engine().connect() as c:
    print('SQL Server OK:', c.execute(text('SELECT 1')).scalar())
from zoho import _token
_token(); print('Zoho OK')
"
```

Si falla SQL Server, revisa el punto 4.1.2 (firewall) y la sección [Solución de problemas](#7-solución-de-problemas).

### 4.10 Servicio systemd (arranca solo y se reinicia si falla)

```bash
sudo cp /opt/indicadores/deploy/indicadores-dashboard.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now indicadores-dashboard

sudo systemctl status indicadores-dashboard     # debe decir "active (running)"
curl http://127.0.0.1:8000/salud                # {"ok":true}
```

> El servicio usa **un solo worker** a propósito: la caché de indicadores vive en la memoria del proceso. Las peticiones simultáneas se atienden con hilos, así que no hace falta más.

### 4.11 nginx

```bash
sudo cp /opt/indicadores/deploy/nginx-dashboard.conf /etc/nginx/sites-available/dashboard.peoplecore.com.co
sudo ln -s /etc/nginx/sites-available/dashboard.peoplecore.com.co /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

La configuración ya incluye:

- proxy hacia uvicorn (`127.0.0.1:8000`) con un timeout de 120 s para la primera consulta;
- archivos estáticos servidos directamente por nginx;
- límite de 10 intentos de login por minuto por IP;
- cabeceras de seguridad básicas.

En este punto **http://dashboard.peoplecore.com.co** ya debe abrir la pantalla de ingreso.

### 4.12 HTTPS con Let's Encrypt

```bash
sudo certbot --nginx -d dashboard.peoplecore.com.co
```

- Acepta redirigir HTTP a HTTPS cuando lo pregunte.
- La renovación es automática. Para comprobarla: `sudo certbot renew --dry-run`.

> **Obligatorio**: el dashboard muestra márgenes y ventas. No lo dejes publicado sin HTTPS. Con `DASHBOARD_HTTPS=1`, la sesión no funciona por HTTP plano.

### 4.13 Firewall del servidor

```bash
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw enable
sudo ufw status
```

El puerto 8000 **no** se abre: uvicorn solo escucha en `127.0.0.1` y únicamente nginx lo ve.

Listo: entra a **https://dashboard.peoplecore.com.co**.

---

## 5. Actualizar el servidor con cambios nuevos

Desde Windows, empaqueta solo el código, **sin el `.env`**, para no pisar la configuración del servidor:

```powershell
cd C:\wamp64\www\Python\indicadores
tar --exclude=.venv --exclude=__pycache__ --exclude=salida --exclude=.env -czf $env:TEMP\indicadores.tar.gz .
scp $env:TEMP\indicadores.tar.gz usuario@IP_DEL_SERVIDOR:/tmp/
```

En el servidor:

```bash
sudo tar -xzf /tmp/indicadores.tar.gz -C /opt/indicadores && rm /tmp/indicadores.tar.gz
sudo chown -R indicadores:indicadores /opt/indicadores
sudo /opt/indicadores/.venv/bin/pip install -r /opt/indicadores/requirements.txt   # solo si cambió requirements.txt
sudo systemctl restart indicadores-dashboard
```

---

## 6. Tareas frecuentes

### Agregar un indicador

No hay que tocar nada del dashboard:

1. Crea el `.sql` en `consultas/`, o la función en `zoho_indicadores.py`.
2. Agrega su `Indicador(...)` en `indicadores.py`.
3. Reinicia: en local se recarga solo con `--reload`; en el servidor, `sudo systemctl restart indicadores-dashboard`.

### Agregar o quitar un usuario

1. `python crear_usuario.py nombre` y agrega la línea a `DASHBOARD_USUARIOS`, o borra la del usuario que quieres quitar.
2. Reinicia el servicio. Al quitar a alguien, también conviene cambiar `DASHBOARD_SECRET` para cerrar las sesiones abiertas.

### Cambiar cada cuánto se consulta SAP y Zoho

`DASHBOARD_CACHE_MIN` en el `.env` (por defecto 5 minutos) y reinicia el servicio. Funciona así:

- Vencida la caché, la página entrega el último dato al instante y consulta de nuevo en segundo plano. La pantalla se actualiza sola en menos de un minuto.
- El botón **Actualizar** fuerza la consulta en el momento. Se puede usar como máximo una vez por minuto, para no sobrecargar SAP.

### Ver los logs

```bash
sudo journalctl -u indicadores-dashboard -f                 # dashboard
sudo tail -f /var/log/nginx/access.log /var/log/nginx/error.log
```

### Reiniciar, detener o ver el estado

```bash
sudo systemctl restart indicadores-dashboard
sudo systemctl stop indicadores-dashboard
sudo systemctl status indicadores-dashboard
```

---

## 7. Solución de problemas

| Síntoma | Causa probable | Qué hacer |
|---|---|---|
| `502 Bad Gateway` | El servicio no está corriendo | `sudo systemctl status indicadores-dashboard` y `journalctl -u indicadores-dashboard -n 50` |
| `504 Gateway Timeout` en la primera carga | SAP o Zoho tardaron más de 120 s | Revisa la conectividad; sube `proxy_read_timeout` en el sitio de nginx |
| `Can't open lib 'ODBC Driver 18 for SQL Server'` | Driver no instalado o nombre distinto en `.env` | `odbcinst -q -d` y copia el nombre exacto en `SQL_DRIVER` |
| `Login timeout expired` / `TCP Provider` | El firewall del SQL Server bloquea la IP del servidor | Pedir que permitan la IP pública del Ubuntu (punto 4.1.2) |
| `SSL Provider: certificate verify failed` | Certificado del SQL Server no confiable | `SQL_TRUST_CERT=yes` en el `.env` |
| Ingreso correcto pero vuelve al login | `DASHBOARD_HTTPS=1` y se entró por `http://` | Entrar siempre por `https://`, o en local usar `DASHBOARD_HTTPS=0` |
| "Usuario o contraseña incorrectos" | Usuario mal copiado en `.env` o servicio sin reiniciar | Revisa `DASHBOARD_USUARIOS` y reinicia el servicio |
| Un indicador sale "Con error" | Falla de su consulta SQL o de Zoho | El mensaje aparece en la tarjeta; el detalle completo, en los logs |
| `Zoho no entregó el token` | Refresh token vencido o revocado | Generar un nuevo `ZOHO_REFRESH_TOKEN` en la consola de Zoho |
| Los gráficos no aparecen | Falta `web/static/vendor/echarts-5.5.1.min.js` | Verifica que el archivo se copió al servidor |
#   i n d i c a d o r e s  
 