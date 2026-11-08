# ============================================================
#  Gera o app de bandeja para Windows (dist\HolyricsBot\HolyricsBot.exe)
#
#  O executável final já leva Python, dependências, ffmpeg e ffprobe.
#  Este script NÃO baixa ffmpeg: ele usa o ffmpeg.exe que você já tem
#  (na pasta bin\ ou no PATH).
#
#  Uso:
#    1. Abra o PowerShell nesta pasta
#    2. Set-ExecutionPolicy -Scope Process Bypass -Force
#    3. .\build-windows.ps1
# ============================================================
param(
    [switch]$SemInstalar
)

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

Write-Host "==> Verificando o Python" -ForegroundColor Cyan
try {
    python --version | Out-Host
} catch {
    throw "Python 3 nao encontrado. Instale o Python 3.11+ e marque 'Add python.exe to PATH'."
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "==> Criando .venv"
    python -m venv .venv
}
$py = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"

if (-not $SemInstalar) {
    Write-Host "==> Instalando dependencias (uma vez)"
    & $py -m pip install --upgrade pip
    & $py -m pip install -r requirements.txt pyinstaller
}
if (-not (Test-Path ".venv\Scripts\pyinstaller.exe")) {
    throw "PyInstaller nao encontrado. Rode sem -SemInstalar."
}

# --- ffmpeg/ffprobe: usa o que ja existe, sem baixar nada -------------
Write-Host "==> Conferindo ffmpeg/ffprobe" -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path bin | Out-Null
foreach ($nome in @("ffmpeg.exe", "ffprobe.exe")) {
    if (Test-Path "bin\$nome") { continue }
    $base = $nome -replace "\.exe$", ""
    $cmd = Get-Command $base -ErrorAction SilentlyContinue
    if (-not $cmd) {
        throw "Coloque $nome em .\bin (o build nao baixa nada)."
    }
    $real = $cmd.Source
    # O Chocolatey instala um "shim" em chocolatey\bin; copiamos o binario real.
    if ($real -like "*chocolatey\bin*" -and $env:ChocolateyInstall) {
        $alt = Get-ChildItem "$env:ChocolateyInstall\lib\ffmpeg" -Recurse -Filter $nome `
            -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($alt) { $real = $alt.FullName }
    }
    Copy-Item $real "bin\$nome"
    Write-Host "    copiado $nome de $real"
}

# --- build -------------------------------------------------------------
Write-Host "==> Gerando o executavel (pode levar alguns minutos)" -ForegroundColor Cyan
& $py -m PyInstaller --noconfirm --clean HolyricsBot.spec
if ($LASTEXITCODE -ne 0) {
    throw "Falha no PyInstaller."
}

if (Test-Path "config.example.json") {
    Copy-Item "config.example.json" "dist\HolyricsBot\config.example.json" -Force
}

Write-Host ""
Write-Host "Pronto! Abra: dist\HolyricsBot\HolyricsBot.exe" -ForegroundColor Green
Write-Host "O app fica na bandeja; clique no icone para configurar." -ForegroundColor Green
