#!/usr/bin/env bash
# Cria o atalho .desktop com o caminho desta pasta (rode uma vez).
# Funciona tanto no fonte quanto no pacote gerado pelo build.
set -euo pipefail
cd "$(dirname "$0")"

ICONE="$PWD/_internal/assets/icon.png"
[ -f "$ICONE" ] || ICONE="$PWD/assets/icon.png"

cat > HolyricsBot.desktop <<EOF
[Desktop Entry]
Type=Application
Version=1.0
Name=Holyrics Bot
Comment=Recebe arquivos do Telegram e salva no Holyrics
Exec=$PWD/HolyricsBot
Icon=$ICONE
Terminal=false
Categories=Utility;Network;
StartupWMClass=HolyricsBot
EOF
chmod +x HolyricsBot.desktop

echo "Atalho criado: $PWD/HolyricsBot.desktop"
echo "Para aparecer no menu de aplicativos:"
echo "  cp \"$PWD/HolyricsBot.desktop\" ~/.local/share/applications/"
