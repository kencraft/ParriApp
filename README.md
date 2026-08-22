# Parri — Sistema de Gestión Parrilla

Sistema web para la administración de mesas, mostrador, pedidos y cobros de un restaurante. Desarrollado con Flask + SQLite, tickets térmicos de 80 mm, jornadas laborales y dashboard con resumen del turno.

## Stack

- **Backend**: Python 3.11 / Flask
- **Base de datos**: SQLite (archivo `instance/parri.db`, modo WAL)
- **Frontend**: Bootstrap 5 + Bootstrap Icons (vendoreados, sin CDN)
- **Producción**: Docker + Gunicorn

## Estructura

```
app.py                  # App principal, rutas index/resumen, filtros
models.py               # Modelos SQLAlchemy (Mesa, Pedido, Mozo, etc.)
routes/                 # Blueprints: pedidos, jornadas, configuracion, categorias...
templates/              # Jinja2 (base, index, pedidos, resumen)
static/                 # CSS y fuentes vendoreadas
scripts/                # Utilidades (backup.ps1, importar_csv.py)
Dockerfile              # Imagen de producción
docker-compose.yml      # Orquestación (puerto 80, volumen instance/)
requirements.txt        # Dependencias base
requirements-prod.txt   # Gunicorn
.env.example            # Plantilla de variables de entorno
```

## Desarrollo local

```powershell
python -m venv venv
.\venv\Scripts\pip install -r requirements.txt
.\venv\Scripts\python app.py
```

La app corre en `http://127.0.0.1:5000` (accesible desde la LAN en `http://<ip>:5000`).

> **Importante**: no correr el servidor de desarrollo y Docker a la vez; ambos usan el mismo archivo `instance/parri.db`.

---

## Puesta en producción (Docker)

### Requisitos previos en la PC servidor (Windows dedicada)

1. **Docker Desktop** instalado. En Settings activar *"Start Docker Desktop when you sign in"*.
2. **Git** instalado (recomendado para actualizaciones).

### Paso a paso

**1. Clonar el proyecto**

```powershell
git clone https://github.com/kencraft/ParriApp.git C:\Parri
cd C:\Parri
```

(o copiar la carpeta completa por red/pendrive)

**2. Configurar variables de entorno**

```powershell
copy .env.example .env
notepad .env
```

Completar `SECRET_KEY` con un valor único:

```powershell
[guid]::NewGuid()
```

**3. Copiar la base de datos existente (opcional)**

Para conservar los datos actuales, copiar `instance\parri.db` desde la máquina original a `C:\Parri\instance\parri.db`. Si no existe, el contenedor crea una base vacía.

> Si Windows niega permisos de escritura sobre `instance\`, otorgar control total a `Everyone` sobre esa carpeta (el contenedor corre con usuario sin privilegios).

**4. Levantar el contenedor**

```powershell
docker compose up -d --build
```

Verificar:

```powershell
curl.exe http://localhost/
```

Debe responder HTTP 200. El contenedor publica el **puerto 80** del host.

**5. Abrir el firewall (una sola vez, PowerShell como administrador)**

```powershell
netsh advfirewall firewall add rule name="Parri HTTP 80" dir=in action=allow protocol=TCP localport=80
```

**6. IP fija para el servidor**

En el router del local, crear una **reserva DHCP** para la MAC de la PC servidor (ej.: `192.168.123.50`). Los terminales/tablets apuntan a:

```
http://192.168.123.50/
```

**7. Auto-inicio**

Con *"Start Docker Desktop when you sign in"* activado y `restart: unless-stopped` en el compose, el sistema levanta solo al encender la PC.

### Comandos de operación

| Acción | Comando |
|---|---|
| Ver estado | `docker compose ps` |
| Ver logs | `docker compose logs -f` |
| Reiniciar | `docker compose restart` |
| Detener | `docker compose down` |
| Actualizar versión | `git pull` → `docker compose up -d --build` |

Los datos sobreviven a rebuilds y actualizaciones porque `instance/` es un volumen montado.

### Notas

- **Impresoras**: los tickets se imprimen desde el navegador de cada terminal (`window.print()`); cada POS configura su impresora localmente. El servidor no maneja impresión.
- **Zona horaria**: el contenedor corre con `TZ=America/Argentina/Buenos_Aires`.
- **Backups**: ver sección siguiente — son manuales u opcionales.

---

## Backups (manual / opcional)

El script `scripts\backup.ps1` copia `instance\parri.db` a `backups\parri-YYYYMMDD-HHMMSS.db` conservando las últimas 30 copias (configurable).

**Ejecución manual** cuando se desee respaldar:

```powershell
.\scripts\backup.ps1          # conserva las últimas 30 copias
.\scripts\backup.ps1 -Keep 60 # retención personalizada
```

Si se prefiere automatizarlo (opcional), se puede programar una tarea diaria:

```powershell
Register-ScheduledTask -TaskName "Parri Backup Diario" `
    -Trigger (New-ScheduledTaskTrigger -Daily -At "02:00") `
    -Action (New-ScheduledTaskAction -Execute "PowerShell.exe" `
        -Argument "-NoProfile -ExecutionPolicy Bypass -File C:\Parri\scripts\backup.ps1")
```
