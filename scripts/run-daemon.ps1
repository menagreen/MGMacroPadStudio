# MacroPad Studio — Ejecutar daemon de Rust en consola interactiva
$RepoDir = Split-Path -Parent $PSScriptRoot
$ExePath = Join-Path $RepoDir "macropad-service\target\release\macropad-service.exe"

if (-not (Test-Path $ExePath)) {
    Write-Host "Compilando versión release..." -ForegroundColor Cyan
    Push-Location (Join-Path $RepoDir "macropad-service")
    cargo build --release
    Pop-Location
}

Write-Host "Iniciando MacroPad Service en consola..." -ForegroundColor Green
& $ExePath
