#!/usr/bin/env bash
# Abre o Holyrics Bot no Linux (usa o binário gerado ou o .venv).
set -euo pipefail
cd "$(dirname "$0")"

if [ -x "dist/HolyricsBot/HolyricsBot" ]; then
    exec "dist/HolyricsBot/HolyricsBot" "$@"
fi

if [ -x ".venv/bin/python" ]; then
    exec ".venv/bin/python" "holyrics_bot_gui.py" "$@"
fi

exec python3 "holyrics_bot_gui.py" "$@"
