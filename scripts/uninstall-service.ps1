# MacroPad Studio — Script de desinstalación del servicio
$ErrorActionPreference = "SilentlyContinue"

$RegistryPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$ValueName = "MacroPadStudioService"

Write-Host "============================================================" -ForegroundColor Yellow
Write-Host " Deteniendo y desinstalando MacroPad Service de Windows" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow

# Detener proceso si está corriendo
$Procs = Get-Process -Name "macropad-service" -ErrorAction SilentlyContinue
if ($Procs) {
    Write-Host "[+] Deteniendo procesos activos de macropad-service..." -ForegroundColor Yellow
    $Procs | Stop-Process -Force
    Write-Host "[✓] Procesos detenidos." -ForegroundColor Green
}

# Remover de HKCU Run
Remove-ItemProperty -Path $RegistryPath -Name $ValueName -ErrorAction SilentlyContinue | Out-Null

Write-Host "[✓] Entrada de inicio automático eliminada." -ForegroundColor Green
