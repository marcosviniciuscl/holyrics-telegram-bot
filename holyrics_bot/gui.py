# -*- coding: utf-8 -*-
"""Holyrics Bot — app de bandeja para Windows.

Dois cliques no executável: o bot sobe e fica na bandeja do sistema.
Clique (ou duplo clique) no ícone abre a janela de configuração.
Menu do botão direito: abrir, iniciar/parar e sair.
"""
from __future__ import annotations

import copy
import logging
import os
import queue
import re
import shlex
import shutil
import sys
import threading
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from PIL import Image, ImageDraw, ImageTk

from . import __version__, app_core, bot

try:
    import pystray
except Exception:  # noqa: BLE001 — permite abrir a janela mesmo sem bandeja
    pystray = None

LOG = logging.getLogger("holyrics-bot.gui")

# ---------------------------------------------------------------------------
# Visual
# ---------------------------------------------------------------------------
COR_FUNDO = "#0f172a"
COR_CARD = "#1e293b"
COR_CARD2 = "#172033"
COR_BORDA = "#334155"
COR_TEXTO = "#e2e8f0"
COR_MUTED = "#94a3b8"
COR_AZUL = "#2563eb"
COR_AZUL2 = "#1d4ed8"
COR_VERDE = "#22c55e"
COR_AMARELO = "#eab308"
COR_VERMELHO = "#ef4444"
COR_CIANO = "#7dd3fc"

FONTE = "Segoe UI"


def dir_assets() -> Path:
    candidatos = (
        bot.RAIZ / "holyrics_bot" / "resources",
        bot.DIR_APP / "holyrics_bot" / "resources",
        Path(__file__).resolve().parent / "resources",
    )
    for base in candidatos:
        if base.is_dir():
            return base
    return candidatos[0]


# ---------------------------------------------------------------------------
# Formulário rolável
# ---------------------------------------------------------------------------

class PainelRolavel(ttk.Frame):
    def __init__(self, master):
        super().__init__(master)
        self.canvas = tk.Canvas(self, bg=COR_FUNDO, highlightthickness=0)
        self.barra = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.conteudo = ttk.Frame(self.canvas, padding=(18, 14))
        self.conteudo.columnconfigure(1, weight=1)
        self._janela = self.canvas.create_window((0, 0), window=self.conteudo, anchor="nw")
        self.canvas.configure(yscrollcommand=self.barra.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        self.barra.pack(side="right", fill="y")
        self.conteudo.bind("<Configure>", self._config_conteudo)
        self.canvas.bind("<Configure>", self._config_canvas)
        self.canvas.bind("<Enter>", lambda e: self._wheel(True))
        self.canvas.bind("<Leave>", lambda e: self._wheel(False))

    def _config_conteudo(self, _evento=None):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _config_canvas(self, evento):
        self.canvas.itemconfigure(self._janela, width=evento.width)

    def _wheel(self, ativo: bool):
        if ativo:
            self.canvas.bind_all("<MouseWheel>", self._rolar)
            self.canvas.bind_all("<Button-4>", self._rolar)
            self.canvas.bind_all("<Button-5>", self._rolar)
        else:
            for evento in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                self.canvas.unbind_all(evento)

    def _rolar(self, evento):
        numero = getattr(evento, "num", None)
        if numero == 4:
            delta = -1
        elif numero == 5:
            delta = 1
        else:
            delta = -1 if getattr(evento, "delta", 0) > 0 else 1
        self.canvas.yview_scroll(delta, "units")


class Formulario:
    def __init__(self, painel: PainelRolavel):
        self.frame = painel.conteudo
        self.linha = 0

    def secao(self, texto: str):
        if self.linha:
            ttk.Separator(self.frame).grid(
                row=self.linha, column=0, columnspan=4, sticky="ew", pady=(14, 8)
            )
            self.linha += 1
        ttk.Label(self.frame, text=texto, style="Secao.TLabel").grid(
            row=self.linha, column=0, columnspan=4, sticky="w", pady=(0, 6)
        )
        self.linha += 1

    def _rotulo(self, texto: str):
        ttk.Label(self.frame, text=texto).grid(
            row=self.linha, column=0, sticky="w", padx=(0, 14), pady=5
        )

    def campo(self, rotulo, var, show=None, botao=None, dica=None) -> ttk.Entry:
        self._rotulo(rotulo)
        entrada = ttk.Entry(self.frame, textvariable=var, show=show or "")
        entrada.grid(row=self.linha, column=1, columnspan=(1 if botao else 3),
                     sticky="ew", pady=5)
        if botao:
            ttk.Button(self.frame, text=botao[0], command=botao[1],
                       style="Ghost.TButton").grid(row=self.linha, column=2,
                                                   columnspan=2, sticky="e",
                                                   padx=(8, 0), pady=5)
        self.linha += 1
        if dica:
            ttk.Label(self.frame, text=dica, style="Muted.TLabel").grid(
                row=self.linha, column=1, columnspan=3, sticky="w", pady=(0, 2)
            )
            self.linha += 1
        return entrada

    def spin(self, rotulo, var, de, ate, passo=1, dica=None) -> ttk.Spinbox:
        self._rotulo(rotulo)
        caixa = ttk.Spinbox(self.frame, from_=de, to=ate, increment=passo,
                            textvariable=var)
        caixa.grid(row=self.linha, column=1, sticky="w", pady=5)
        self.linha += 1
        if dica:
            ttk.Label(self.frame, text=dica, style="Muted.TLabel").grid(
                row=self.linha, column=1, columnspan=3, sticky="w", pady=(0, 2)
            )
            self.linha += 1
        return caixa

    def combo(self, rotulo, var, valores, dica=None) -> ttk.Combobox:
        self._rotulo(rotulo)
        caixa = ttk.Combobox(self.frame, textvariable=var, values=valores,
                             state="readonly")
        caixa.grid(row=self.linha, column=1, sticky="w", pady=5)
        self.linha += 1
        if dica:
            ttk.Label(self.frame, text=dica, style="Muted.TLabel").grid(
                row=self.linha, column=1, columnspan=3, sticky="w", pady=(0, 2)
            )
            self.linha += 1
        return caixa

    def check(self, texto, var) -> ttk.Checkbutton:
        caixa = ttk.Checkbutton(self.frame, text=texto, variable=var)
        caixa.grid(row=self.linha, column=1, columnspan=3, sticky="w", pady=5)
        self.linha += 1
        return caixa

    def botao(self, texto, comando) -> ttk.Button:
        botao = ttk.Button(self.frame, text=texto, style="Ghost.TButton",
                           command=comando)
        botao.grid(row=self.linha, column=1, sticky="w", pady=6)
        self.linha += 1
        return botao

    def nota(self, texto: str):
        ttk.Label(self.frame, text=texto, style="Muted.TLabel",
                  wraplength=430, justify="left").grid(
            row=self.linha, column=1, columnspan=3, sticky="w", pady=(2, 8)
        )
        self.linha += 1


# ---------------------------------------------------------------------------
# Aplicativo
# ---------------------------------------------------------------------------

class Aplicativo:
    def __init__(self, caminho_config: Path, instancia: app_core.InstanciaUnica):
        self.caminho_config = caminho_config
        self.instancia = instancia
        self.fila_log: "queue.Queue[str]" = queue.Queue()
        self.fila_ui: "queue.Queue" = queue.Queue()
        self._estado = "parado"
        self._avisou_bandeja = False
        self._icone_base = self._carregar_icone()
        self.v: dict[str, tk.Variable] = {}

        # O backend do pystray no Linux reclama quando não há bandeja (no
        # Windows funciona normalmente). Não polui o log com isso.
        logging.getLogger("pystray").setLevel(logging.CRITICAL)

        raiz = logging.getLogger()
        raiz.setLevel(logging.INFO)
        for antigo in list(raiz.handlers):
            raiz.removeHandler(antigo)
        handler = app_core.FilaHandler(self.fila_log)
        handler.setFormatter(logging.Formatter("%(asctime)s  %(message)s", "%H:%M:%S"))
        raiz.addHandler(handler)

        self.dados = app_core.carregar(self.caminho_config)
        self.runner = app_core.BotRunner(self.caminho_config, self._status_cb)

        self.root = tk.Tk()
        self.root.withdraw()
        self.root.title("Holyrics Bot")
        self.root.geometry("780x720")
        self.root.minsize(700, 560)
        self.root.configure(bg=COR_FUNDO)
        self.root.protocol("WM_DELETE_WINDOW", self._ocultar_ui)
        self._aplicar_estilo()
        self._definir_icone_janela()
        self._criar_vars()
        self._criar_cabecalho()
        self._criar_abas()
        self._criar_rodape()

        self.root.after(120, self._poll_ui)
        self.root.after(150, self._poll_log)

        self._criar_bandeja()
        self.instancia.escutar(lambda: self._post(self._mostrar_janela_ui))

        # Já configurado? Sobe direto e fica na bandeja.
        if self._pronto_para_iniciar():
            self._iniciar_bot()
        else:
            self._mostrar_janela_ui()

    # ------------------------------------------------------------------ visual
    def _aplicar_estilo(self):
        estilo = ttk.Style(self.root)
        try:
            estilo.theme_use("clam")
        except tk.TclError:
            pass
        estilo.configure(".", background=COR_FUNDO, foreground=COR_TEXTO,
                         fieldbackground=COR_CARD, bordercolor=COR_BORDA,
                         font=(FONTE, 10))
        estilo.configure("TFrame", background=COR_FUNDO)
        estilo.configure("Card.TFrame", background=COR_CARD)
        estilo.configure("TLabel", background=COR_FUNDO, foreground=COR_TEXTO)
        estilo.configure("Muted.TLabel", foreground=COR_MUTED)
        estilo.configure("Title.TLabel", font=(FONTE + " Semibold", 19),
                         foreground=COR_TEXTO)
        estilo.configure("Sub.TLabel", font=(FONTE, 9), foreground=COR_MUTED)
        estilo.configure("Secao.TLabel", font=(FONTE + " Semibold", 11),
                         foreground=COR_CIANO)
        estilo.configure("TButton", padding=(14, 8), borderwidth=0,
                         background=COR_CARD, foreground=COR_TEXTO)
        estilo.map("TButton", background=[("active", COR_BORDA)])
        estilo.configure("Accent.TButton", background=COR_AZUL,
                         foreground="#ffffff")
        estilo.map("Accent.TButton", background=[("active", COR_AZUL2)])
        estilo.configure("Ghost.TButton", background=COR_CARD,
                         foreground=COR_TEXTO)
        estilo.map("Ghost.TButton", background=[("active", COR_BORDA)])
        estilo.configure("TNotebook", background=COR_FUNDO, borderwidth=0)
        estilo.configure("TNotebook.Tab", background=COR_CARD,
                         foreground=COR_MUTED, padding=(18, 9))
        estilo.map("TNotebook.Tab",
                   background=[("selected", COR_AZUL)],
                   foreground=[("selected", "#ffffff")])
        estilo.configure("TEntry", fieldbackground=COR_CARD,
                         foreground=COR_TEXTO, insertcolor=COR_TEXTO,
                         bordercolor=COR_BORDA, padding=6)
        estilo.configure("TSpinbox", fieldbackground=COR_CARD,
                         foreground=COR_TEXTO, arrowcolor=COR_TEXTO,
                         bordercolor=COR_BORDA, padding=4)
        estilo.configure("TCombobox", fieldbackground=COR_CARD,
                         background=COR_CARD, foreground=COR_TEXTO,
                         arrowcolor=COR_TEXTO, bordercolor=COR_BORDA,
                         selectbackground=COR_CARD, selectforeground=COR_TEXTO,
                         padding=4)
        estilo.map(
            "TCombobox",
            fieldbackground=[("readonly", COR_CARD)],
            background=[("readonly", COR_CARD)],
            foreground=[("readonly", COR_TEXTO)],
            selectbackground=[("readonly", COR_CARD)],
            selectforeground=[("readonly", COR_TEXTO)],
        )
        self.root.option_add("*TCombobox*Listbox.background", COR_CARD)
        self.root.option_add("*TCombobox*Listbox.foreground", COR_TEXTO)
        self.root.option_add("*TCombobox*Listbox.selectBackground", COR_AZUL)
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        estilo.configure("TCheckbutton", background=COR_FUNDO, foreground=COR_TEXTO)
        estilo.map("TCheckbutton", background=[("active", COR_FUNDO)])
        estilo.configure("TSeparator", background=COR_BORDA)

    def _definir_icone_janela(self):
        try:
            ico = dir_assets() / "icon.png"
            if ico.is_file():
                imagem = ImageTk.PhotoImage(Image.open(ico).resize((64, 64)))
                self.root.iconphoto(True, imagem)
                self._icone_janela = imagem
        except Exception:  # noqa: BLE001
            pass

    def _criar_cabecalho(self):
        cabecalho = ttk.Frame(self.root, padding=(22, 18, 22, 8))
        cabecalho.pack(fill="x")
        cabecalho.columnconfigure(0, weight=1)

        ttk.Label(cabecalho, text="Holyrics Bot", style="Title.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        ttk.Label(
            cabecalho,
            text=f"Recebe arquivos do Telegram e salva nas pastas do Holyrics · v{__version__}",
            style="Sub.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(2, 0))

        self.lbl_status = tk.Label(
            cabecalho, text="● Parado", bg=COR_FUNDO, fg=COR_MUTED,
            font=(FONTE + " Semibold", 10),
        )
        self.lbl_status.grid(row=0, column=1, sticky="e")
        self.lbl_detalhe = ttk.Label(cabecalho, text="", style="Sub.TLabel")
        self.lbl_detalhe.grid(row=1, column=1, sticky="e")

    def _criar_abas(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=18, pady=(4, 0))

        self._aba_telegram = self._nova_aba("Telegram")
        self._aba_pastas = self._nova_aba("Pastas")
        self._aba_conversao = self._nova_aba("Conversão")
        self._aba_youtube = self._nova_aba("YouTube")
        self._aba_minio = self._nova_aba("MinIO")
        self._aba_avancado = self._nova_aba("Avançado")
        self._aba_log = self._nova_log("Log")

        self._montar_telegram(self._aba_telegram)
        self._montar_pastas(self._aba_pastas)
        self._montar_conversao(self._aba_conversao)
        self._montar_youtube(self._aba_youtube)
        self._montar_minio(self._aba_minio)
        self._montar_avancado(self._aba_avancado)

    def _nova_aba(self, titulo: str) -> PainelRolavel:
        painel = PainelRolavel(self.notebook)
        self.notebook.add(painel, text=titulo)
        return painel

    def _nova_log(self, titulo: str) -> ttk.Frame:
        quadro = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(quadro, text=titulo)
        quadro.rowconfigure(0, weight=1)
        quadro.columnconfigure(0, weight=1)
        self.txt_log = tk.Text(
            quadro, bg="#0b1220", fg=COR_TEXTO, insertbackground=COR_TEXTO,
            relief="flat", wrap="word", font=("Consolas", 9), padx=10, pady=8,
        )
        self.txt_log.grid(row=0, column=0, sticky="nsew")
        barra = ttk.Scrollbar(quadro, orient="vertical", command=self.txt_log.yview)
        barra.grid(row=0, column=1, sticky="ns")
        self.txt_log.configure(yscrollcommand=barra.set, state="disabled")
        ttk.Button(quadro, text="Limpar log", style="Ghost.TButton",
                   command=self._limpar_log).grid(row=1, column=0, sticky="e",
                                                  pady=(8, 0))
        return quadro

    # ------------------------------------------------------------------ abas
    def _criar_vars(self):
        def sv(caminho, padrao=""):
            return tk.StringVar(value=str(self._get(caminho, padrao)))
        def bv(caminho, padrao=False):
            return tk.BooleanVar(value=bool(self._get(caminho, padrao)))

        for caminho in (
            "telegram.token", "telegram.usuarios",
            "pastas.audio", "pastas.video", "pastas.imagem", "pastas.apresentacao",
            "pastas.documento", "pastas.outros",
            "youtube.altura_maxima", "youtube.duracao_maxima_min",
            "youtube.mp3_bitrate_kbps", "youtube.cookies",
            "converter.audio_bitrate_kbps", "converter.video_crf",
            "converter.video_preset",
            "pdf.dpi", "pdf.qualidade_jpeg",
            "download.tamanho_maximo_mb",
            "links.tamanho_maximo_mb",
            "minio.endpoint", "minio.access_key", "minio.secret_key",
            "minio.bucket", "minio.regiao", "minio.url_pagina_upload",
            "minio.bucket_publico", "minio.prefixo", "minio.expira_min",
            "minio.espera_max_min", "minio.tamanho_maximo_mb",
        ):
            self.v[caminho] = sv(caminho)
        for caminho in (
            "telegram.aceitar_grupos", "youtube.ativo", "converter.perguntar",
            "pdf.converter_para_pptx", "pdf.manter_pdf_original",
            "links.ativo", "minio.ativo", "minio.secure",
        ):
            self.v[caminho] = bv(caminho)
        self.v["log.nivel"] = tk.StringVar(value=str(self._get("log.nivel", "INFO")))

    def _preencher_vars(self):
        for caminho, var in self.v.items():
            valor = self._get(caminho, "")
            var.set(valor)

    def _get(self, caminho: str, padrao=""):
        atual = self.dados
        for parte in caminho.split("."):
            if not isinstance(atual, dict) or parte not in atual:
                return padrao
            atual = atual[parte]
        return atual

    def _montar_telegram(self, painel):
        f = Formulario(painel)
        f.secao("Conexão")
        f.campo("Token do bot", self.v["telegram.token"], show="•",
                dica="No Telegram, fale com @BotFather → /newbot e copie o token.")
        f.campo("IDs autorizados", self.v["telegram.usuarios"],
                dica="Separe por vírgula. Use /id no bot para descobrir o seu.")
        f.check("Aceitar mensagens em grupos", self.v["telegram.aceitar_grupos"])
        f.secao("Dica")
        f.nota("O bot só responde a quem estiver em “IDs autorizados”. "
               "Se a lista ficar vazia, qualquer pessoa que encontrar o bot "
               "pode usá-lo.")

    def _montar_pastas(self, painel):
        f = Formulario(painel)
        f.secao("Pastas do Holyrics")
        f.nota("O bot salva cada arquivo na pasta da categoria. "
               "Caminhos vazios usam a pasta “outros”.")
        for categoria, rotulo in (
            ("audio", "Áudio"),
            ("video", "Vídeo"),
            ("imagem", "Imagem"),
            ("apresentacao", "Apresentações"),
            ("documento", "Documentos"),
            ("outros", "Outros"),
        ):
            chave = f"pastas.{categoria}"
            f.campo(rotulo, self.v[chave],
                    botao=("Escolher…", lambda c=chave: self._escolher_pasta(c)))

    def _montar_conversao(self, painel):
        f = Formulario(painel)
        f.secao("Formatos aceitos pelo Holyrics")
        f.nota("Vídeo → MP4 (H.264 + AAC, faststart), mantendo resolução e "
               "proporção. Áudio → MP3. Imagem → JPG/PNG. A conversão acontece "
               "só quando o arquivo não está no padrão.")
        f.check("Perguntar antes de converter", self.v["converter.perguntar"])
        f.spin("MP3 — qualidade (kbps)", self.v["converter.audio_bitrate_kbps"],
               64, 320, 32)
        f.spin("Vídeo — CRF (menor = melhor)", self.v["converter.video_crf"],
               0, 35, 1, dica="18 é alta qualidade. 23 é menor arquivo.")
        f.combo("Vídeo — preset", self.v["converter.video_preset"],
                ["ultrafast", "veryfast", "fast", "medium", "slow", "slower"])
        f.secao("PDF")
        f.check("Converter PDF para PowerPoint (.pptx)",
                self.v["pdf.converter_para_pptx"])
        f.spin("DPI da conversão", self.v["pdf.dpi"], 100, 400, 50)
        f.spin("Qualidade JPEG", self.v["pdf.qualidade_jpeg"], 50, 100, 5)
        f.check("Manter também o PDF original", self.v["pdf.manter_pdf_original"])

    def _montar_youtube(self, painel):
        f = Formulario(painel)
        f.secao("YouTube")
        f.check("Ativar download do YouTube", self.v["youtube.ativo"])
        f.spin("Altura máxima de vídeo (p)", self.v["youtube.altura_maxima"],
               144, 2160, 120)
        f.spin("Duração máxima (min)", self.v["youtube.duracao_maxima_min"],
               1, 1440, 10)
        f.spin("Bitrate do MP3 (kbps)", self.v["youtube.mp3_bitrate_kbps"],
               64, 320, 32)
        f.campo("Cookies (opcional)", self.v["youtube.cookies"],
                botao=("Escolher…", self._escolher_cookies),
                dica="Arquivo cookies.txt (formato Netscape) se o YouTube pedir verificação.")
        f.nota("O áudio é sempre salvo em MP3 e o vídeo em MP4. "
               "O ffmpeg/ffprobe já vêm no app — não é preciso instalar nada.")

    def _montar_minio(self, painel):
        f = Formulario(painel)
        f.secao("MinIO (arquivos grandes)")
        f.check("Ativar MinIO", self.v["minio.ativo"])
        f.nota("Arquivos acima do limite do Telegram (20 MB na nuvem) vão para "
               "o MinIO e voltam por um link temporário.")
        f.campo("Endpoint", self.v["minio.endpoint"],
                dica="Ex.: https://minio.seudominio.com")
        f.campo("Access key", self.v["minio.access_key"])
        f.campo("Secret key", self.v["minio.secret_key"], show="•")
        f.campo("Bucket de entrada", self.v["minio.bucket"])
        f.campo("Bucket público (link curto)", self.v["minio.bucket_publico"])
        f.campo("Página de upload", self.v["minio.url_pagina_upload"],
                botao=("Publicar no MinIO", self._publicar_pagina))
        f.campo("Prefixo", self.v["minio.prefixo"])
        f.campo("Região", self.v["minio.regiao"])
        f.check("Usar HTTPS", self.v["minio.secure"])
        f.spin("Link expira em (min)", self.v["minio.expira_min"], 1, 1440, 10)
        f.spin("Aguardar envio (min)", self.v["minio.espera_max_min"], 1, 1440, 10)
        f.spin("Tamanho máximo (MB, 0 = sem limite)",
               self.v["minio.tamanho_maximo_mb"], 0, 10000, 100)

    def _montar_avancado(self, painel):
        f = Formulario(painel)
        f.secao("Links diretos")
        f.check("Baixar links de arquivos colados no chat",
                self.v["links.ativo"])
        f.spin("Tamanho máximo do link (MB, 0 = sem limite)",
               self.v["links.tamanho_maximo_mb"], 0, 10000, 100)
        f.secao("Telegram")
        f.spin("Tamanho máximo recebido (MB)", self.v["download.tamanho_maximo_mb"],
               1, 2000, 10,
               dica="Na API na nuvem o máximo é 20 MB. Com MinIO, o excedente vira link.")
        f.secao("Registro")
        f.combo("Nível do log", self.v["log.nivel"],
                ["DEBUG", "INFO", "WARNING", "ERROR"])
        f.nota(f"Configuração: {self.caminho_config}\n"
               f"Log: {bot.DIR_APP / 'bot.log'}")
        f.secao("Atalho")
        f.nota("No Linux, cria o atalho no menu de aplicativos. "
               "No Windows, use o atalho do próprio executável.")
        f.botao("Criar atalho no menu", self._criar_atalho)

    # ------------------------------------------------------------------ rodapé
    def _criar_rodape(self):
        rodape = ttk.Frame(self.root, padding=(18, 10, 18, 16))
        rodape.pack(fill="x")
        ttk.Button(rodape, text="Salvar e aplicar", style="Accent.TButton",
                   command=self._salvar_ui).pack(side="left")
        self.btn_bot = ttk.Button(rodape, text="Iniciar bot", style="Ghost.TButton",
                                  command=self._alternar_bot_ui)
        self.btn_bot.pack(side="left", padx=(8, 0))
        ttk.Button(rodape, text="Abrir pasta", style="Ghost.TButton",
                   command=self._abrir_pasta).pack(side="left", padx=(8, 0))
        ttk.Button(rodape, text="Sair", style="Ghost.TButton",
                   command=self._sair_ui).pack(side="right")

    # ------------------------------------------------------------------ dados
    def _coletar(self) -> dict:
        d = copy.deepcopy(self.dados)

        def definir(caminho, valor):
            partes = caminho.split(".")
            atual = d
            for parte in partes[:-1]:
                atual = atual.setdefault(parte, {})
            atual[partes[-1]] = valor

        def texto(caminho):
            return self.v[caminho].get().strip()

        def inteiro(caminho, padrao=0):
            try:
                return int(float(texto(caminho).replace(",", ".")))
            except Exception:  # noqa: BLE001
                return padrao

        definir("telegram.token", texto("telegram.token"))
        ids = re.split(r"[\s,;]+", texto("telegram.usuarios"))
        definir("telegram.usuarios_autorizados",
                [int(u) for u in ids if u.isdigit()])
        definir("telegram.aceitar_grupos", self.v["telegram.aceitar_grupos"].get())

        for categoria in ("audio", "video", "imagem", "apresentacao",
                          "documento", "outros"):
            definir(f"pastas.{categoria}", texto(f"pastas.{categoria}"))

        definir("converter.perguntar", self.v["converter.perguntar"].get())
        definir("converter.audio_bitrate_kbps",
                inteiro("converter.audio_bitrate_kbps", 192))
        definir("converter.video_crf", inteiro("converter.video_crf", 18))
        definir("converter.video_preset", texto("converter.video_preset") or "medium")

        definir("pdf.converter_para_pptx", self.v["pdf.converter_para_pptx"].get())
        definir("pdf.dpi", inteiro("pdf.dpi", 200))
        definir("pdf.qualidade_jpeg", inteiro("pdf.qualidade_jpeg", 90))
        definir("pdf.manter_pdf_original", self.v["pdf.manter_pdf_original"].get())

        definir("youtube.ativo", self.v["youtube.ativo"].get())
        definir("youtube.altura_maxima", inteiro("youtube.altura_maxima", 1080))
        definir("youtube.duracao_maxima_min",
                inteiro("youtube.duracao_maxima_min", 120))
        definir("youtube.mp3_bitrate_kbps", inteiro("youtube.mp3_bitrate_kbps", 192))
        definir("youtube.cookies", texto("youtube.cookies"))

        definir("download.tamanho_maximo_mb",
                inteiro("download.tamanho_maximo_mb", 20))
        definir("links.ativo", self.v["links.ativo"].get())
        definir("links.tamanho_maximo_mb", inteiro("links.tamanho_maximo_mb", 0))

        definir("minio.ativo", self.v["minio.ativo"].get())
        for campo in ("endpoint", "access_key", "secret_key", "bucket",
                      "regiao", "url_pagina_upload", "bucket_publico", "prefixo"):
            definir(f"minio.{campo}", texto(f"minio.{campo}"))
        definir("minio.secure", self.v["minio.secure"].get())
        definir("minio.expira_min", inteiro("minio.expira_min", 120))
        definir("minio.espera_max_min", inteiro("minio.espera_max_min", 120))
        definir("minio.tamanho_maximo_mb", inteiro("minio.tamanho_maximo_mb", 0))

        definir("log.nivel", texto("log.nivel") or "INFO")
        return d

    def _salvar_silencioso(self) -> bool:
        dados = self._coletar()
        erros = app_core.validar(dados)
        if erros:
            self._mostrar_janela_ui()
            messagebox.showerror("Configuração", "\n".join(erros))
            return False
        app_core.salvar(self.caminho_config, dados)
        self.dados = dados
        return True

    def _salvar_ui(self):
        if not self._salvar_silencioso():
            return
        self._reiniciar_se_rodando()
        self._aplicar_status("iniciando" if self.runner.rodando else self._estado,
                             "Configuração salva")

    def _reiniciar_se_rodando(self):
        if self.runner.rodando:
            self._status_cb("iniciando", "Reiniciando…")
            threading.Thread(target=self._reiniciar_thread, daemon=True).start()

    def _reiniciar_thread(self):
        self.runner.parar(timeout=10)
        self.runner.iniciar()

    def _pronto_para_iniciar(self) -> bool:
        return bool(self.dados["telegram"].get("token", "").strip()) and bool(
            self.dados["pastas"].get("outros", "").strip()
        )

    # ------------------------------------------------------------------ bot
    def _iniciar_bot(self):
        if not self._salvar_silencioso():
            return
        self._aplicar_status("iniciando", "Conectando…")
        self.runner.iniciar()

    def _alternar_bot_ui(self):
        if self.runner.rodando:
            self._aplicar_status("parado", "Parando…")
            threading.Thread(target=self.runner.parar, daemon=True).start()
        else:
            self._iniciar_bot()

    def _status_cb(self, estado: str, detalhe: str):
        self._post(lambda: self._aplicar_status(estado, detalhe))

    def _aplicar_status(self, estado: str, detalhe: str = ""):
        self._estado = estado
        rotulos = {
            "online": "● Online", "iniciando": "● Conectando…",
            "parado": "● Parado", "erro": "● Erro",
        }
        cores = {
            "online": COR_VERDE, "iniciando": COR_AMARELO,
            "parado": COR_MUTED, "erro": COR_VERMELHO,
        }
        try:
            resumo = " ".join(str(detalhe or "").split())[:80]
            self.lbl_status.configure(text=rotulos.get(estado, "● ?"),
                                      fg=cores.get(estado, COR_MUTED))
            self.lbl_detalhe.configure(text=resumo)
            self.btn_bot.configure(text="Parar bot" if self.runner.rodando else "Iniciar bot")
        except tk.TclError:
            return
        self._atualizar_bandeja()

    # ------------------------------------------------------------------ bandeja
    def _carregar_icone(self) -> Image.Image:
        caminho = dir_assets() / "icon.png"
        if caminho.is_file():
            try:
                return Image.open(caminho).convert("RGBA")
            except Exception:  # noqa: BLE001
                pass
        imagem = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
        desenho = ImageDraw.Draw(imagem)
        desenho.rounded_rectangle([8, 8, 248, 248], radius=52, fill=COR_FUNDO)
        desenho.ellipse([48, 48, 208, 208], fill=COR_AZUL)
        desenho.polygon([(110, 90), (110, 166), (172, 128)], fill="#ffffff")
        return imagem

    def _imagem_status(self, estado: str) -> Image.Image:
        imagem = self._icone_base.copy().resize((64, 64))
        desenho = ImageDraw.Draw(imagem)
        cor = {
            "online": COR_VERDE, "iniciando": COR_AMARELO,
            "parado": COR_MUTED, "erro": COR_VERMELHO,
        }.get(estado, COR_MUTED)
        desenho.ellipse([44, 44, 62, 62], fill=cor, outline=COR_FUNDO, width=3)
        return imagem

    def _montar_menu(self):
        if pystray is None:
            return None
        status = {
            "online": "Status: Online", "iniciando": "Status: Conectando…",
            "parado": "Status: Parado", "erro": "Status: Erro",
        }.get(self._estado, "Status: ?")
        return pystray.Menu(
            pystray.MenuItem("Abrir configuração",
                             lambda i, item: self._post(self._mostrar_janela_ui),
                             default=True),
            pystray.MenuItem("Iniciar bot",
                             lambda i, item: self._post(self._iniciar_bot),
                             enabled=not self.runner.rodando),
            pystray.MenuItem("Parar bot",
                             lambda i, item: self._post(self._alternar_bot_ui),
                             enabled=self.runner.rodando),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(status, None, enabled=False),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem("Sair", lambda i, item: self._post(self._sair_ui)),
        )

    def _criar_bandeja(self):
        if pystray is None:
            return
        self.icon = pystray.Icon("holyrics-bot", self._imagem_status("parado"),
                                 "Holyrics Bot", self._montar_menu())
        threading.Thread(target=self.icon.run, name="bandeja", daemon=True).start()

    def _atualizar_bandeja(self):
        if pystray is None or not hasattr(self, "icon"):
            return
        try:
            self.icon.icon = self._imagem_status(self._estado)
            self.icon.title = {
                "online": "Holyrics Bot — online",
                "iniciando": "Holyrics Bot — conectando",
                "parado": "Holyrics Bot — parado",
                "erro": "Holyrics Bot — erro",
            }.get(self._estado, "Holyrics Bot")
            self.icon.menu = self._montar_menu()
            self.icon.update_menu()
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------ janela
    def _mostrar_janela_ui(self):
        self.root.deiconify()
        self.root.lift()
        try:
            self.root.focus_force()
        except Exception:  # noqa: BLE001
            pass

    def _ocultar_ui(self):
        self.root.withdraw()
        if not self._avisou_bandeja and pystray is not None and hasattr(self, "icon"):
            self._avisou_bandeja = True
            try:
                self.icon.notify("O app continua rodando na bandeja.", "Holyrics Bot")
            except Exception:  # noqa: BLE001
                pass

    def _abrir_pasta(self):
        pasta = Path(bot.DIR_APP)
        try:
            import os
            os.startfile(str(pasta))  # type: ignore[attr-defined]
        except Exception:  # noqa: BLE001
            try:
                import subprocess
                subprocess.Popen(["xdg-open", str(pasta)])
            except Exception:
                messagebox.showinfo("Pasta", str(pasta))

    def _escolher_pasta(self, chave: str):
        inicial = self.v[chave].get() or str(Path.home())
        escolhida = filedialog.askdirectory(initialdir=inicial,
                                            title="Escolher pasta")
        if escolhida:
            self.v[chave].set(escolhida)

    def _escolher_cookies(self):
        inicial = self.v["youtube.cookies"].get() or str(Path.home())
        escolhido = filedialog.askopenfilename(
            initialdir=inicial, title="Arquivo de cookies",
            filetypes=[("Cookies", "*.txt"), ("Todos", "*.*")],
        )
        if escolhido:
            self.v["youtube.cookies"].set(escolhido)

    # ------------------------------------------------------------------ MinIO
    def _log_ui(self, texto: str) -> None:
        try:
            self.txt_log.configure(state="normal")
            self.txt_log.insert("end", texto + "\n")
            self.txt_log.see("end")
            self.txt_log.configure(state="disabled")
        except tk.TclError:
            pass

    def _publicar_pagina(self):
        dados = self._coletar()
        minio = dados["minio"]
        if not all(minio.get(campo) for campo in
                   ("endpoint", "access_key", "secret_key")):
            messagebox.showwarning(
                "MinIO", "Preencha endpoint, access key e secret key antes de publicar."
            )
            return
        # Salva já (sem exigir token/pastas) para não perder o que foi digitado.
        app_core.salvar(self.caminho_config, dados)
        self.dados = dados
        self._log_ui("Publicando a página de upload no MinIO…")
        threading.Thread(target=self._publicar_pagina_thread, args=(dados,),
                         daemon=True).start()

    def _publicar_pagina_thread(self, dados: dict):
        try:
            import types
            m = dados["minio"]
            cfg = types.SimpleNamespace(
                minio_endpoint=m.get("endpoint", ""),
                minio_access=m.get("access_key", ""),
                minio_secret=m.get("secret_key", ""),
                minio_bucket=m.get("bucket") or "holyrics-entrada",
                minio_secure=bool(m.get("secure", True)),
                minio_regiao=m.get("regiao") or "us-east-1",
                minio_expira_min=int(m.get("expira_min") or 120),
                minio_max_mb=int(m.get("tamanho_maximo_mb") or 0),
            )
            store = bot.MinioStore(cfg)
            bucket = m.get("bucket_publico") or "holyrics-publico"
            url = store.publicar_pagina(dir_assets() / "uploader.html", bucket)
            self._post(lambda: self._pagina_publicada(url))
        except Exception as e:  # noqa: BLE001
            LOG.exception("Falha ao publicar a página no MinIO")
            self._post(lambda: messagebox.showerror(
                "MinIO", f"Falha ao publicar a página:\n{e}"
            ))

    def _pagina_publicada(self, url: str):
        self.v["minio.url_pagina_upload"].set(url)
        if not self.v["minio.bucket_publico"].get().strip():
            self.v["minio.bucket_publico"].set("holyrics-publico")
        dados = self._coletar()
        app_core.salvar(self.caminho_config, dados)
        self.dados = dados
        self._log_ui(f"Página publicada: {url}")
        messagebox.showinfo("MinIO", f"Página publicada com sucesso:\n{url}")

    # ------------------------------------------------------------------ atalho
    def _criar_atalho(self):
        if not sys.platform.startswith("linux"):
            messagebox.showinfo(
                "Atalho", "No Windows, use o atalho do próprio executável."
            )
            return
        try:
            congelado = bool(getattr(sys, "frozen", False))
            appimage = os.environ.get("APPIMAGE")
            if appimage:
                exe = Path(appimage).resolve()
                origem_icone = Path(getattr(sys, "_MEIPASS", exe.parent)) / \
                    "holyrics_bot/resources/icon.png"
                destino_icone = Path.home() / ".local/share/icons/holyrics-bot.png"
                destino_icone.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(origem_icone, destino_icone)
                icone = destino_icone
                comando = shlex.quote(str(exe))
            elif congelado:
                exe = Path(sys.executable).resolve()
                icone = Path(getattr(sys, "_MEIPASS", exe.parent)) / \
                    "holyrics_bot/resources/icon.png"
                comando = shlex.quote(str(exe))
            else:
                exe = Path(sys.executable).resolve()
                principal = Path(__file__).resolve().parent.parent / "main.py"
                icone = Path(__file__).resolve().parent / "resources/icon.png"
                comando = f"{shlex.quote(str(exe))} {shlex.quote(str(principal))}"
            destino = Path.home() / ".local/share/applications/HolyricsBot.desktop"
            destino.parent.mkdir(parents=True, exist_ok=True)
            destino.write_text(
                "[Desktop Entry]\n"
                "Type=Application\n"
                "Version=1.0\n"
                "Name=Holyrics Bot\n"
                "Comment=Recebe arquivos do Telegram e salva no Holyrics\n"
                f"Exec={comando}\n"
                f"Icon={icone}\n"
                "Terminal=false\n"
                "Categories=Utility;Network;\n"
                "StartupWMClass=HolyricsBot\n",
                encoding="utf-8",
            )
            destino.chmod(0o755)
            self._log_ui(f"Atalho criado: {destino}")
            messagebox.showinfo("Atalho", f"Atalho criado em:\n{destino}")
        except Exception as e:  # noqa: BLE001
            messagebox.showerror("Atalho", f"Falha ao criar o atalho:\n{e}")

    def _sair_ui(self):
        try:
            self._aplicar_status("parado", "Saindo…")
        except Exception:  # noqa: BLE001
            pass
        try:
            self.runner.parar(timeout=8)
        except Exception:  # noqa: BLE001
            pass
        try:
            if pystray is not None and hasattr(self, "icon"):
                self.icon.stop()
        except Exception:  # noqa: BLE001
            pass
        self.instancia.fechar()
        try:
            self.root.destroy()
        except Exception:  # noqa: BLE001
            pass

    # ------------------------------------------------------------------ filas
    def _post(self, funcao):
        self.fila_ui.put(funcao)

    def _poll_ui(self):
        try:
            while True:
                funcao = self.fila_ui.get_nowait()
                try:
                    funcao()
                except Exception:  # noqa: BLE001
                    LOG.exception("Erro na interface")
        except queue.Empty:
            pass
        try:
            self.root.after(100, self._poll_ui)
        except tk.TclError:
            pass

    def _poll_log(self):
        try:
            while True:
                linha = self.fila_log.get_nowait()
                self.txt_log.configure(state="normal")
                self.txt_log.insert("end", linha + "\n")
                self.txt_log.see("end")
                self.txt_log.configure(state="disabled")
        except queue.Empty:
            pass
        try:
            self.root.after(250, self._poll_log)
        except tk.TclError:
            pass

    def _limpar_log(self):
        self.txt_log.configure(state="normal")
        self.txt_log.delete("1.0", "end")
        self.txt_log.configure(state="disabled")

    # ------------------------------------------------------------------ run
    def executar(self):
        self.root.mainloop()


def main() -> None:
    caminho = bot.DIR_APP / "config.json"
    for i, arg in enumerate(sys.argv):
        if arg == "--config" and i + 1 < len(sys.argv):
            caminho = Path(sys.argv[i + 1]).resolve()

    instancia = app_core.InstanciaUnica()
    if not instancia.tentar():
        # Outra instância já está aberta: ela foi avisada para mostrar a janela.
        return

    # Se o config.json ainda não existe, cria um modelo para o usuário editar.
    if not caminho.is_file():
        try:
            app_core.salvar(caminho, app_core.carregar(caminho))
        except Exception:  # noqa: BLE001
            pass

    app = Aplicativo(caminho, instancia)
    app.executar()



