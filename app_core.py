# -*- coding: utf-8 -*-
"""Núcleo do app de bandeja do Holyrics.

Cuida da configuração (config.json), da execução do bot em segundo plano e da
instância única. Não importa tkinter, então dá para testar sem interface.
"""
from __future__ import annotations

import asyncio
import copy
import json
import logging
import os
import queue
import socket
import threading
from pathlib import Path
from typing import Callable

from telegram import Update

import bot

LOG = logging.getLogger("holyrics-bot.app")

PORTA_INSTANCIA = 47823


# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------

DEFAULTS: dict = {
    "telegram": {
        "token": "",
        "usuarios_autorizados": [],
        "aceitar_grupos": False,
        "api_id": 0,
        "api_hash": "",
        "base_url": "https://api.telegram.org/bot",
        "base_file_url": "https://api.telegram.org/file/bot",
        "local_mode": False,
    },
    "pastas": {
        "audio": "",
        "video": "",
        "imagem": "",
        "apresentacao": "",
        "documento": "",
        "outros": "",
    },
    "pdf": {
        "converter_para_pptx": True,
        "dpi": 200,
        "largura_max_px": 2400,
        "qualidade_jpeg": 90,
        "manter_pdf_original": False,
    },
    "converter": {
        "perguntar": False,
        "audio_bitrate_kbps": 192,
        "video_crf": 18,
        "video_preset": "medium",
    },
    "youtube": {
        "ativo": True,
        "altura_maxima": 1080,
        "duracao_maxima_min": 120,
        "mp3_bitrate_kbps": 192,
        "ffmpeg": "",
        "cookies": "",
    },
    "download": {
        "intervalo_progresso_segundos": 2,
        "tamanho_maximo_mb": 20,
    },
    "links": {
        "ativo": True,
        "tamanho_maximo_mb": 0,
        "hosts_bloqueados": [],
    },
    "minio": {
        "ativo": False,
        "endpoint": "",
        "access_key": "",
        "secret_key": "",
        "bucket": "holyrics-entrada",
        "secure": True,
        "regiao": "us-east-1",
        "url_pagina_upload": "",
        "bucket_publico": "",
        "prefixo": "entrada/",
        "expira_min": 120,
        "intervalo_verificacao_s": 10,
        "espera_max_min": 120,
        "tamanho_maximo_mb": 0,
    },
    "log": {
        "arquivo": "bot.log",
        "nivel": "INFO",
    },
}


def mesclar(base, novo):
    """Mescla `novo` sobre `base` sem perder chaves desconhecidas."""
    if isinstance(base, dict) and isinstance(novo, dict):
        resultado = copy.deepcopy(base)
        for chave, valor in novo.items():
            resultado[chave] = mesclar(resultado.get(chave), valor)
        return resultado
    return copy.deepcopy(novo)


def carregar(caminho: Path) -> dict:
    """Lê o config.json (ou devolve os padrões se não existir)."""
    if caminho.is_file():
        try:
            dados = json.loads(caminho.read_text(encoding="utf-8"))
            return mesclar(DEFAULTS, dados)
        except Exception as e:  # noqa: BLE001
            LOG.warning("config.json inválido (%s); usando padrões.", e)
    return copy.deepcopy(DEFAULTS)


def salvar(caminho: Path, dados: dict) -> None:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    temporario = caminho.with_suffix(caminho.suffix + ".tmp")
    temporario.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    os.replace(temporario, caminho)


def validar(dados: dict) -> list[str]:
    erros: list[str] = []
    if not str(dados["telegram"].get("token", "")).strip():
        erros.append("Informe o token do bot (BotFather).")
    if not str(dados["pastas"].get("outros", "")).strip():
        erros.append("Escolha pelo menos a pasta 'outros'.")
    if dados["minio"].get("ativo"):
        for campo in ("endpoint", "access_key", "secret_key"):
            if not str(dados["minio"].get(campo, "")).strip():
                erros.append(f"MinIO ativo: preencha o campo '{campo}'.")
    return erros


# ---------------------------------------------------------------------------
# Log -> fila para a interface
# ---------------------------------------------------------------------------

class FilaHandler(logging.Handler):
    def __init__(self, fila: "queue.Queue[str]"):
        super().__init__()
        self.fila = fila

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.fila.put_nowait(self.format(record))
        except Exception:  # noqa: BLE001
            pass


# ---------------------------------------------------------------------------
# Execução do bot em segundo plano
# ---------------------------------------------------------------------------

class BotRunner:
    """Roda a Application do Telegram numa thread com o próprio event loop."""

    def __init__(self, caminho_config: Path,
                 ao_status: Callable[[str, str], None] | None = None):
        self.caminho_config = Path(caminho_config)
        self.ao_status = ao_status or (lambda estado, detalhe: None)
        self.fila_log: "queue.Queue[str]" = queue.Queue()
        self._thread: threading.Thread | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._app = None
        self._rodando = False
        self._parando = False

    @property
    def rodando(self) -> bool:
        return self._rodando

    def _status(self, estado: str, detalhe: str = "") -> None:
        try:
            self.ao_status(estado, detalhe)
        except Exception:  # noqa: BLE001
            pass

    def iniciar(self) -> None:
        if self._rodando or (self._thread and self._thread.is_alive()):
            return
        self._parando = False
        self._thread = threading.Thread(target=self._rodar, name="holyrics-bot", daemon=True)
        self._thread.start()

    def _rodar(self) -> None:
        try:
            # Em thread no Windows, o loop Selector é mais previsível que o
            # Proactor (usado por padrão no thread principal).
            if os.name == "nt":
                asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
            self._status("iniciando", "Conectando ao Telegram…")
            cfg = bot.Config(self.caminho_config)
            bot.configurar_log(cfg)
            handler = FilaHandler(self.fila_log)
            handler.setFormatter(logging.Formatter("%(asctime)s  %(message)s", "%H:%M:%S"))
            logging.getLogger().addHandler(handler)

            app = bot.preparar_aplicacao(cfg)
            self._app = app

            loop = asyncio.new_event_loop()
            self._loop = loop
            asyncio.set_event_loop(loop)
            loop.run_until_complete(app.initialize())
            loop.run_until_complete(app.start())
            loop.run_until_complete(
                app.updater.start_polling(
                    drop_pending_updates=True, allowed_updates=Update.ALL_TYPES
                )
            )
            self._rodando = True
            self._status("online", "Bot conectado")
            loop.run_forever()
        except (Exception, SystemExit) as e:  # noqa: BLE001
            LOG.exception("Falha ao iniciar o bot")
            self._status("erro", str(e))
        finally:
            self._rodando = False
            self._encerrar()
            if self._parando:
                self._status("parado", "Parado")

    def _encerrar(self) -> None:
        loop = self._loop
        if loop and not loop.is_closed():
            try:
                tarefas = [t for t in asyncio.all_tasks(loop) if not t.done()]
                for tarefa in tarefas:
                    tarefa.cancel()
                if tarefas:
                    loop.run_until_complete(
                        asyncio.gather(*tarefas, return_exceptions=True)
                    )
            except Exception:  # noqa: BLE001
                pass
            try:
                loop.close()
            except Exception:  # noqa: BLE001
                pass
        self._loop = None
        self._app = None
        try:
            asyncio.set_event_loop(None)
        except Exception:  # noqa: BLE001
            pass

    def parar(self, timeout: float = 15.0) -> None:
        loop = self._loop
        app = self._app
        self._parando = True
        if loop and app:
            async def _desligar():
                for etapa in ("updater.stop", "stop", "shutdown"):
                    try:
                        if etapa == "updater.stop":
                            if app.updater and app.updater.running:
                                await app.updater.stop()
                        elif etapa == "stop":
                            await app.stop()
                        else:
                            await app.shutdown()
                    except Exception:  # noqa: BLE001
                        pass

            try:
                futuro = asyncio.run_coroutine_threadsafe(_desligar(), loop)
                futuro.result(timeout=timeout)
            except Exception:  # noqa: BLE001
                pass
            try:
                loop.call_soon_threadsafe(loop.stop)
            except Exception:  # noqa: BLE001
                pass
        if self._thread:
            self._thread.join(timeout=timeout)
        self._thread = None
        self._rodando = False


# ---------------------------------------------------------------------------
# Instância única
# ---------------------------------------------------------------------------

class InstanciaUnica:
    """Impede abrir dois apps e avisa o primeiro para mostrar a janela."""

    def __init__(self, porta: int = PORTA_INSTANCIA):
        self.porta = porta
        self._socket: socket.socket | None = None

    def tentar(self) -> bool:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            s.bind(("127.0.0.1", self.porta))
            s.listen(1)
            self._socket = s
            return True
        except OSError:
            s.close()
            try:
                with socket.create_connection(("127.0.0.1", self.porta), timeout=1.5) as c:
                    c.sendall(b"show")
            except Exception:  # noqa: BLE001
                pass
            return False

    def escutar(self, ao_mostrar: Callable[[], None]) -> None:
        if self._socket is None:
            return

        def laco():
            while True:
                try:
                    conexao, _ = self._socket.accept()
                except OSError:
                    break
                try:
                    dados = conexao.recv(16)
                    if dados.startswith(b"show"):
                        ao_mostrar()
                except Exception:  # noqa: BLE001
                    pass
                finally:
                    conexao.close()

        threading.Thread(target=laco, name="instancia-unica", daemon=True).start()

    def fechar(self) -> None:
        try:
            if self._socket:
                self._socket.close()
        except Exception:  # noqa: BLE001
            pass
        self._socket = None
