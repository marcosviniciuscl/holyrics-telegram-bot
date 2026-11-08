# -*- coding: utf-8 -*-
"""Cache de arquivos já recebidos, para evitar baixar de novo.

A chave é o `file_unique_id` do Telegram (estável para o mesmo arquivo). O
registro guarda o caminho salvo e se ele é o arquivo final ou o original que
falhou na conversão (para tentar converter de novo sem baixar).
"""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from pathlib import Path

LOG = logging.getLogger("holyrics-bot.cache")


class CacheArquivos:
    def __init__(self, caminho: Path, dias: int = 30):
        self.caminho = Path(caminho)
        self.dias = max(int(dias), 1)
        self._lock = threading.Lock()
        self._dados: dict = self._carregar()

    def _carregar(self) -> dict:
        try:
            return json.loads(self.caminho.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            return {}

    def _salvar(self) -> None:
        try:
            self.caminho.parent.mkdir(parents=True, exist_ok=True)
            temporario = self.caminho.with_suffix(self.caminho.suffix + ".tmp")
            temporario.write_text(
                json.dumps(self._dados, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            os.replace(temporario, self.caminho)
        except Exception as e:  # noqa: BLE001
            LOG.warning("Falha ao salvar o cache %s: %s", self.caminho, e)

    def _limpar(self) -> None:
        limite = time.time() - self.dias * 86400
        for uid, item in list(self._dados.items()):
            caminho = Path(item.get("caminho") or "")
            quando = float(item.get("quando") or 0)
            if quando < limite or not caminho.is_file():
                self._dados.pop(uid, None)

    def buscar(self, uid: str) -> dict | None:
        if not uid:
            return None
        with self._lock:
            self._limpar()
            item = self._dados.get(uid)
            if item and Path(item.get("caminho") or "").is_file():
                return dict(item)
            return None

    def registrar(self, uid: str, caminho: Path, nome: str, tamanho: int,
                  tipo: str = "final") -> None:
        if not uid or not caminho:
            return
        with self._lock:
            self._limpar()
            self._dados[uid] = {
                "caminho": str(caminho),
                "nome": nome,
                "tamanho": int(tamanho or 0),
                "tipo": tipo,
                "quando": time.time(),
            }
            self._salvar()
