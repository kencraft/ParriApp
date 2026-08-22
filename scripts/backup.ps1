#requires -Version 5.1
<#
    Parri - Backup del SQLite de produccion
    Copia instance\parri.db a backups\parri-YYYYMMDD-HHMMSS.db manteniendo
    las ultimas $Keep copias.

    Uso:
        .\scripts\backup.ps1                  # default Keep = 30
        .\scripts\backup.ps1 -Keep 60

    Programador (Tarea Programada de Windows):
        Programa diaria este script. Ejemplo desde cmd / PowerShell:
        Register-ScheduledTask -TaskName "Parri Backup Diario" `
            -Trigger (New-ScheduledTaskTrigger -Daily -At "02:00") `
            -Action (New-ScheduledTaskAction -Execute "PowerShell.exe" `
                -Argument "-NoProfile -ExecutionPolicy Bypass -File C:\Parri\scripts\backup.ps1")
#>

param(
    [int]$Keep = 30
)

$ErrorActionPreference = 'Stop'

$RepoRoot = Split-Path -Parent $PSScriptRoot
$InstancePath = Join-Path $RepoRoot 'instance\parri.db'
$BackupDir = Join-Path $RepoRoot 'backups'

if (-not (Test-Path -LiteralPath $InstancePath)) {
    Write-Error "No se encontro $InstancePath. Saliendo."
    exit 1
}

if (-not (Test-Path -LiteralPath $BackupDir)) {
    New-Item -ItemType Directory -Path $BackupDir | Out-Null
}

$Timestamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$Dest = Join-Path $BackupDir ("parri-{0}.db" -f $Timestamp)

Copy-Item -LiteralPath $InstancePath -Destination $Dest -Force
Write-Host "Backup OK: $Dest"

$SqlCheck = $null
Get-ChildItem -LiteralPath $BackupDir -Filter 'parri-*.db' | Sort-Object LastWriteTime -Descending | ForEach-Object {
    if ($SqlCheck -ge $Keep) {
        Remove-Item -LiteralPath $_.FullName -Force
        Write-Host "Eliminado backup viejo: $($_.Name)"
    }
    $SqlCheck++
}

Write-Host ""
Write-Host "Backups actuales en $BackupDir :"
Get-ChildItem -LiteralPath $BackupDir -Filter 'parri-*.db' | Sort-Object LastWriteTime -Descending |
    Select-Object Name, @{Name='MB';Expression={[math]::Round($_.Length/1MB,2)}}, LastWriteTime |
    Format-Table -AutoSize
