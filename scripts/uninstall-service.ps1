# MacroPad Studio by MenaGreen — Desinstalador de inicio automático en Windows
$ErrorActionPreference = "SilentlyContinue"

$RegistryPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$ValueName = "MacroPadStudioService"

Write-Host "============================================================" -ForegroundColor Yellow
Write-Host " Deteniendo y desinstalando MacroPad Studio Service" -ForegroundColor Yellow
Write-Host "============================================================" -ForegroundColor Yellow

# Detener procesos activos
$Procs = Get-Process | Where-Object { $_.ProcessName -like "*macropad*" }
if ($Procs) {
    Write-Host "[+] Deteniendo procesos activos de macropad-studio..." -ForegroundColor Yellow
    $Procs | Stop-Process -Force
    Write-Host "[✓] Procesos detenidos." -ForegroundColor Green
}

# Remover de HKCU Run
Remove-ItemProperty -Path $RegistryPath -Name $ValueName -ErrorAction SilentlyContinue | Out-Null

Write-Host "[✓] Entrada de inicio automático eliminada." -ForegroundColor Green
