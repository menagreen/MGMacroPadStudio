# MacroPad Studio — Script de instalación del servicio en segundo plano
$ErrorActionPreference = "Stop"

$RepoDir = Split-Path -Parent $PSScriptRoot
$ExePath = Join-Path $RepoDir "macropad-service\target\release\macropad-service.exe"

if (-not (Test-Path $ExePath)) {
    Write-Error "No se encontró el ejecutable: $ExePath. Compila primero con 'cargo build --release'."
    exit 1
}

$TaskName = "MacroPadStudioService"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Instalando MacroPad Service como Tarea de Inicio en Windows" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Eliminar tarea previa si ya existe
try {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null
} catch {}

$Action = New-ScheduledTaskAction -Execute $ExePath -WorkingDirectory (Split-Path -Parent $ExePath)
$Trigger = New-ScheduledTaskTrigger -AtLogOn
$Settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit 0 -Priority 4

Register-ScheduledTask -TaskName $TaskName -Action $Action -Trigger $Trigger -Settings $Settings -Description "MacroPad Studio SDCX Background Service" | Out-Null

Write-Host "[✓] Tarea programada '$TaskName' registrada exitosamente." -ForegroundColor Green
Write-Host "    Se ejecutará automáticamente al iniciar sesión en Windows." -ForegroundColor Green

# Iniciar la tarea ahora mismo
Write-Host "[+] Iniciando servicio ahora mismo..." -ForegroundColor Yellow
Start-ScheduledTask -TaskName $TaskName

Start-Sleep -Seconds 1
$Running = Get-Process -Name "macropad-service" -ErrorAction SilentlyContinue
if ($Running) {
    Write-Host "[✓] Servicio activo y ejecutándose en segundo plano (PID: $($Running.Id))." -ForegroundColor Green
} else {
    Write-Host "[!] El proceso no reporta estar activo aún. Puedes ejecutarlo manualmente con: $ExePath" -ForegroundColor Yellow
}
