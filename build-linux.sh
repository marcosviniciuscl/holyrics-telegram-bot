#!/usr/bin/env bash
# ============================================================
#  Gera o app de bandeja para Linux (dist/HolyricsBot/HolyricsBot)
#
#  O binário final leva Python, dependências, Tcl/Tk, ffmpeg e ffprobe.
#  Este script NÃO baixa ffmpeg: usa o que já está em bin/ ou no PATH.
#
#  Requisito de build: python3-tk (Tkinter). Em Debian/Ubuntu:
#      sudo apt install python3-tk
#  No binário final o Tk já vai embutido.
#
#  Uso:
#      ./build-linux.sh            # gera em dist/HolyricsBot
#      ./build-linux.sh --instalar # também cria atalho no menu de aplicativos
# ============================================================
set -euo pipefail
cd "$(dirname "$0")"

INSTALAR=0
[ "${1:-}" = "--instalar" ] && INSTALAR=1

echo "==> Verificando o Python/Tkinter"
if ! python3 -c "import tkinter" >/dev/null 2>&1; then
    echo "ERRO: Tkinter não encontrado." >&2
    echo "Instale o pacote do sistema e rode de novo:" >&2
    echo "  Debian/Ubuntu: sudo apt install python3-tk" >&2
    echo "  Fedora:        sudo dnf install python3-tkinter" >&2
    echo "  Arch:          sudo pacman -S tk" >&2
    exit 1
fi
python3 --version

echo "==> Criando .venv (se necessário)"
if [ ! -x ".venv/bin/python" ]; then
    python3 -m venv .venv
fi
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

echo "==> Conferindo ffmpeg/ffprobe (sem baixar nada)"
mkdir -p bin
for nome in ffmpeg ffprobe; do
    if [ ! -x "bin/$nome" ]; then
        origem="$(command -v "$nome" || true)"
        if [ -n "$origem" ]; then
            cp "$origem" "bin/$nome"
            echo "    copiado $nome de $origem"
        else
            echo "ERRO: coloque bin/$nome (o build não baixa nada)." >&2
            exit 1
        fi
    fi
done

echo "==> Gerando o executável (pode levar alguns minutos)"
pyinstaller --noconfirm --clean HolyricsBot.spec

BIN="$PWD/dist/HolyricsBot/HolyricsBot"
if [ ! -x "$BIN" ]; then
    echo "ERRO: o PyInstaller não gerou $BIN" >&2
    exit 1
fi

echo "==> Criando atalho .desktop"
DESKTOP="$PWD/dist/HolyricsBot/HolyricsBot.desktop"
cat > "$DESKTOP" <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=Holyrics Bot
Comment=Recebe arquivos do Telegram e salva no Holyrics
Exec=$BIN
Icon=$PWD/assets/icon.png
Terminal=false
Categories=Utility;Network;
StartupWMClass=HolyricsBot
EOF
chmod +x "$DESKTOP"

if [ "$INSTALAR" -eq 1 ]; then
    mkdir -p "$HOME/.local/share/applications"
    cp "$DESKTOP" "$HOME/.local/share/applications/HolyricsBot.desktop"
    echo "    atalho instalado em ~/.local/share/applications/HolyricsBot.desktop"
fi

echo
echo "Pronto!"
echo "  Executável: $BIN"
echo "  Atalho:     $DESKTOP"
echo "  Dê dois cliques no .desktop (ou rode o executável)."
echo
echo "Obs.: a bandeja precisa de um ambiente com system tray."
echo "      KDE, XFCE, Cinnamon e MATE funcionam. No GNOME, instale a"
echo "      extensão AppIndicator. O atalho abre a janela de qualquer forma."
