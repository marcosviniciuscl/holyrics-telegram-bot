#!/usr/bin/env bash
# ============================================================
#  Instala o Bot do Telegram x Holyrics como serviço (systemd)
#  Uso:  sudo bash install-linux.sh
# ============================================================
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
USUARIO="${SUDO_USER:-$(id -un)}"
SERVICO="holyrics-bot"
DESTINO_UNIT="/etc/systemd/system/${SERVICO}.service"

if [ "$(id -u)" -ne 0 ]; then
  echo "Rode com sudo: sudo bash install-linux.sh"
  exit 1
fi

echo "==> Pasta do bot: $RAIZ"
echo "==> Usuário do serviço: $USUARIO"

echo "==> Criando ambiente virtual e instalando dependências"
if command -v uv >/dev/null 2>&1; then
  su "$USUARIO" -c "cd '$RAIZ' && uv venv .venv && uv pip install --python .venv/bin/python -r requirements.txt"
else
  su "$USUARIO" -c "cd '$RAIZ' && python3 -m venv .venv && .venv/bin/pip install --upgrade pip && .venv/bin/pip install -r requirements.txt"
fi

if [ ! -f "$RAIZ/config.json" ]; then
  cp "$RAIZ/config.example.json" "$RAIZ/config.json"
  echo "==> config.json criado a partir do exemplo."
fi
chown "$USUARIO:$USUARIO" "$RAIZ/config.json"

echo
echo "==> Verificando o ffmpeg (necessário para MP3 e para juntar vídeo+áudio)"
if command -v ffmpeg >/dev/null 2>&1; then
  echo "    ffmpeg já está no sistema: $(command -v ffmpeg)"
else
  echo "    ffmpeg não encontrado — baixando a versão portátil para $RAIZ/bin"
  # portátil: não precisa de admin e não mexe no sistema (pode demorar, ~100 MB)
  su "$USUARIO" -c "cd '$RAIZ' && .venv/bin/python baixar_ffmpeg.py" \
    || echo "    AVISO: não consegui baixar o ffmpeg agora. Rode depois:  cd '$RAIZ' && .venv/bin/python baixar_ffmpeg.py"
fi

echo "==> Instalando serviço em $DESTINO_UNIT"
sed -e "s|CAMINHO_INSTALACAO|$RAIZ|g" -e "s|^User=.*|User=$USUARIO|" \
    "$RAIZ/holyrics-bot.service" > "$DESTINO_UNIT"

systemctl daemon-reload
systemctl enable --now "$SERVICO"

echo
echo "==> Pronto. Situação do serviço:"
systemctl --no-pager --lines=15 status "$SERVICO" || true
echo
echo "Se o token ainda não estiver preenchido, edite $RAIZ/config.json e rode:"
echo "  sudo systemctl restart $SERVICO"
echo "Logs em tempo real:  journalctl -u $SERVICO -f"
