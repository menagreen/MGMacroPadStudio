# MacroPad Studio — Script de desinstalación del servicio
$ErrorActionPreference = "SilentlyContinue"

$TaskName = "MacroPadStudioService"

Write-Host "============================================================" -ForegroundColor Yellow
Write-Host " Deteniendo y desinstalando MacroPad Service" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow

# Detener proceso si está corriendo
$Procs = Get-Process -Name "macropad-service" -ErrorAction SilentlyContinue
if ($Procs) {
    Write-Host "[+] Deteniendo procesos activos de macropad-service..." -ForegroundColor Yellow
    $Procs | Stop-Process -Force
    Write-Host "[✓] Procesos detenidos." -ForegroundColor Green
}

# Detener tarea programada
Stop-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue | Out-Null
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue | Out-Null

Write-Host "[✓] Servicio '$TaskName' eliminado del inicio de Windows." -ForegroundColor Green
