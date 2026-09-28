@echo off
REM ============================================================
REM  Bot do Telegram x Holyrics - executa em primeiro plano
REM  (usado pelo Agendador de Tarefas; se fechar a janela, o bot para)
REM ============================================================
cd /d "%~dp0"
".venv\Scripts\python.exe" bot.py --config config.json
pause
