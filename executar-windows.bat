@echo off
REM ============================================================
REM  Abre o Holyrics Bot (sem console) na bandeja do Windows.
REM  Se o executavel ainda nao foi gerado, usa o .venv local.
REM ============================================================
cd /d "%~dp0"

if exist "dist\HolyricsBot\HolyricsBot.exe" (
    start "" "dist\HolyricsBot\HolyricsBot.exe"
    exit /b
)

if exist ".venv\Scripts\pythonw.exe" (
    start "" ".venv\Scripts\pythonw.exe" "holyrics_bot_gui.py"
    exit /b
)

echo O executavel ainda nao foi gerado.
echo Rode:  powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
pause
