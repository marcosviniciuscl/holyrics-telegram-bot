#!/usr/bin/env bash
# Publica a página de upload (index.html) num bucket público de leitura do MinIO.
#
# Uso:
#   ./publicar.sh <alias-do-mc> <bucket-publico> [nome-do-objeto]
#
# Exemplo:
#   mc alias set meuminio https://minio.seudominio.com ACCESS SECRET   # uma vez
#   ./publicar.sh meuminio publico
#
# No fim ele imprime a URL para colar em minio.url_pagina_upload (config.json).
set -euo pipefail

ALIAS="${1:-meuminio}"
BUCKET="${2:-publico}"
OBJ="${3:-uploader.html}"
DIR="$(cd "$(dirname "$0")" && pwd)"

if ! command -v mc >/dev/null 2>&1; then
  echo "ERRO: o cliente 'mc' do MinIO não está instalado." >&2
  echo "Baixe em: https://min.io/docs/minio/linux/reference/minio-mc.html" >&2
  exit 1
fi

echo "→ Garantindo o bucket público '$BUCKET'…"
mc mb --ignore-existing "$ALIAS/$BUCKET"
mc anonymous set download "$ALIAS/$BUCKET"

echo "→ Publicando a página…"
mc cp --attr "Content-Type=text/html; charset=utf-8" "$DIR/index.html" "$ALIAS/$BUCKET/$OBJ"

BASE="$(mc alias list --json "$ALIAS" 2>/dev/null \
  | python3 -c 'import sys,json;print((json.load(sys.stdin).get("url") or "").rstrip("/"))' 2>/dev/null || true)"
if [ -n "$BASE" ]; then
  echo
  echo "Pronto! Coloque isto no config.json:"
  echo "  \"url_pagina_upload\": \"$BASE/$BUCKET/$OBJ\","
  echo "  \"bucket_publico\": \"$BUCKET\""
else
  echo
  echo "Pronto! No config.json, use:"
  echo "  \"url_pagina_upload\": \"https://SEU-MINIO/$BUCKET/$OBJ\","
  echo "  \"bucket_publico\": \"$BUCKET\""
fi
