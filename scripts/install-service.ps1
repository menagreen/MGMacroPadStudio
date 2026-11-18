# MacroPad Studio — Script de instalación del servicio en segundo plano
$ErrorActionPreference = "Stop"

$RepoDir = Split-Path -Parent $PSScriptRoot
$ExePath = Join-Path $RepoDir "macropad-service\target\release\macropad-service.exe"

if (-not (Test-Path $ExePath)) {
    Write-Error "No se encontró el ejecutable: $ExePath. Compila primero con 'cargo build --release'."
    exit 1
}

$RegistryPath = "HKCU:\Software\Microsoft\Windows\CurrentVersion\Run"
$ValueName = "MacroPadStudioService"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host " Configurando MacroPad Service para inicio con Windows" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Registrar en HKCU Run (Inicio de sesión del usuario sin requerir elevación de administrador)
Set-ItemProperty -Path $RegistryPath -Name $ValueName -Value "`"$ExePath`""

Write-Host "[✓] Registro de inicio automático configurado exitosamente." -ForegroundColor Green
Write-Host "    Clave: $RegistryPath\$ValueName" -ForegroundColor DarkGray
Write-Host "    Se ejecutará de forma silenciosa e invisible en segundo plano al iniciar sesión." -ForegroundColor Green

# Detener instancias previas e iniciar el servicio ahora
Get-Process | Where-Object { $_.ProcessName -like "*macropad*" } | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Milliseconds 300

$proc = Start-Process -FilePath $ExePath -WorkingDirectory (Split-Path -Parent $ExePath) -PassThru

Start-Sleep -Milliseconds 500
if ($proc -and -not $proc.HasExited) {
    Write-Host "[✓] Servicio activo y ejecutándose en segundo plano (PID: $($proc.Id))." -ForegroundColor Green
} else {
    Write-Host "[!] El proceso se inició pero no reporta PID activo." -ForegroundColor Yellow
}
