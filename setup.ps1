Write-Host "=== Parri - Setup ===" -ForegroundColor Cyan
Write-Host ""

# Crear entorno virtual
if (-not (Test-Path "venv")) {
    Write-Host "Creando entorno virtual..." -ForegroundColor Yellow
    python -m venv venv
} else {
    Write-Host "Entorno virtual ya existe" -ForegroundColor Green
}

# Activar e instalar dependencias
Write-Host "Instalando dependencias..." -ForegroundColor Yellow
& .\venv\Scripts\python -m pip install --upgrade pip -q
& .\venv\Scripts\python -m pip install -r requirements.txt -q

Write-Host ""
Write-Host "=== Setup completo ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Para iniciar el servidor ejecute:" -ForegroundColor White
Write-Host "  .\venv\Scripts\python app.py" -ForegroundColor Green
Write-Host ""
Write-Host "Luego abra http://127.0.0.1:5000 en su navegador" -ForegroundColor White
