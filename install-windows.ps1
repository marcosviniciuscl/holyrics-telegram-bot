# ============================================================
#  Instala o Bot do Telegram x Holyrics como TAREFA do Windows
#  (inicia junto com o usuário e reinicia sozinho se cair)
#
#  Como usar:
#    1. Abra o PowerShell na pasta do bot
#    2. Set-ExecutionPolicy -Scope Process Bypass -Force
#    3. .\install-windows.ps1
#
#  Para remover: .\install-windows.ps1 -Desinstalar
# ============================================================
param(
    [string]$NomeTarefa = "BotHolyrics",
    [switch]$Desinstalar
)

$ErrorActionPreference = "Stop"
$raiz = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $raiz

if ($Desinstalar) {
    Unregister-ScheduledTask -TaskName $NomeTarefa -Confirm:$false
    Write-Host "Tarefa '$NomeTarefa' removida." -ForegroundColor Yellow
    return
}

# --- 1. Python disponível? -----------------------------------
$pythonExe = $null
foreach ($tentativa in @("py -3", "python", "python3")) {
    try {
        $partes = $tentativa.Split(" ")
        & $partes[0] $partes[1..($partes.Length - 1)] --version 2>$null | Out-Null
        $pythonExe = $tentativa
        break
    } catch { }
}
if (-not $pythonExe) {
    Write-Host "Python 3 nao encontrado. Instale em https://python.org (marque 'Add python.exe to PATH')." -ForegroundColor Red
    exit 1
}
Write-Host "==> Usando: $pythonExe"

# --- 2. Ambiente virtual + dependencias ----------------------
Write-Host "==> Criando .venv e instalando dependencias (pode levar 1-2 min)"
$partes = $pythonExe.Split(" ")
& $partes[0] $partes[1..($partes.Length - 1)] -m venv .venv
& ".\.venv\Scripts\python.exe" -m pip install --upgrade pip --quiet
& ".\.venv\Scripts\python.exe" -m pip install -r requirements.txt --quiet

# --- 3. config.json -----------------------------------------
if (-not (Test-Path ".\config.json")) {
    Copy-Item ".\config.example.json" ".\config.json"
    Write-Host "==> config.json criado. EDITE o token e as pastas antes de usar!" -ForegroundColor Yellow
}

# --- 3b. ffmpeg (MP3 e juntar video+audio) -------------------
Write-Host "==> Verificando o ffmpeg"
if (Get-Command ffmpeg -ErrorAction SilentlyContinue) {
    Write-Host "    ffmpeg ja esta no sistema: $((Get-Command ffmpeg).Source)"
} else {
    Write-Host "    ffmpeg nao encontrado - baixando a versao portatil para $raiz\bin (pode demorar, ~100 MB)"
    & ".\.venv\Scripts\python.exe" "baixar_ffmpeg.py" --destino "$raiz\bin"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "    AVISO: nao consegui baixar o ffmpeg agora. Rode depois:" -ForegroundColor Yellow
        Write-Host "           .\.venv\Scripts\python.exe baixar_ffmpeg.py" -ForegroundColor Yellow
    }
}

# --- 4. Tarefa agendada -------------------------------------
$pyw = Join-Path $raiz ".venv\Scripts\pythonw.exe"
$acao = New-ScheduledTaskAction -Execute $pyw `
    -Argument "`"$raiz\bot.py`" --config `"$raiz\config.json`"" `
    -WorkingDirectory $raiz

$gatilho = New-ScheduledTaskTrigger -AtLogOn
$config = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $NomeTarefa -Action $acao -Trigger $gatilho `
    -Settings $config -Description "Bot do Telegram que salva arquivos nas pastas do Holyrics" -Force | Out-Null

Write-Host "==> Tarefa '$NomeTarefa' registrada (inicia com o login)." -ForegroundColor Green

# --- 5. Conferencia + start ---------------------------------
Write-Host "==> Conferindo configuracao:"
& ".\.venv\Scripts\python.exe" bot.py --verificar

Start-ScheduledTask -TaskName $NomeTarefa
Write-Host ""
Write-Host "Bot iniciado. Log em: $raiz\bot.log" -ForegroundColor Green
Write-Host "Parar agora:    Stop-ScheduledTask -TaskName $NomeTarefa"
Write-Host "Iniciar de novo: Start-ScheduledTask -TaskName $NomeTarefa"
