# MacroPad Studio by MenaGreen — Ejecutar daemon de Rust en consola interactiva
$RepoDir = Split-Path -Parent $PSScriptRoot
$ExePath = Join-Path $RepoDir "target\release\macropad-studio.exe"

if (-not (Test-Path $ExePath)) {
    Write-Host "Compilando versión release..." -ForegroundColor Cyan
    Push-Location $RepoDir
    cargo build --release
    Pop-Location
}

Write-Host "Iniciando MacroPad Studio Service en consola..." -ForegroundColor Green
& $ExePath --service
