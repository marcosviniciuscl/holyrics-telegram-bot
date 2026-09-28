#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Baixa o ffmpeg portátil para a pasta bin/ do bot (Windows, Linux e macOS).

Não precisa de administrador e não mexe no sistema: só põe o executável
dentro da pasta do próprio bot. O bot detecta e usa sozinho.

Uso:
    python baixar_ffmpeg.py                 # baixa se ainda não existir
    python baixar_ffmpeg.py --forcar        # baixa de novo mesmo se já existir
    python baixar_ffmpeg.py --conferir      # só mostra a situação atual
    python baixar_ffmpeg.py --destino C:\\outra\\pasta
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.request
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
REPO = "BtbN/FFmpeg-Builds"
API_RELEASE = f"https://api.github.com/repos/{REPO}/releases/latest"
URL_FALLBACK = f"https://github.com/{REPO}/releases/download/latest"

NOMES_BINARIOS = ["ffmpeg", "ffprobe"]


def alvo_plataforma() -> tuple[str, str]:
    """Devolve (alvo_dos_arquivos, extensão do pacote)."""
    sistema = platform.system().lower()
    maquina = platform.machine().lower()
    arm = maquina in ("aarch64", "arm64", "armv8")
    x86 = maquina in ("x86_64", "amd64", "x64")

    if sistema.startswith("win"):
        if arm:
            return "winarm64", ".zip"
        if x86:
            return "win64", ".zip"
    elif sistema == "linux":
        if arm:
            return "linuxarm64", ".tar.xz"
        if x86:
            return "linux64", ".tar.xz"
    elif sistema == "darwin":
        return "osx64", ".zip"
    raise SystemExit(f"ERRO: plataforma não suportada ({sistema}/{maquina}). Instale o ffmpeg manualmente.")


def binarios_pretendidos(destino: Path) -> list[Path]:
    exe = ".exe" if platform.system().lower().startswith("win") else ""
    return [destino / f"{nome}{exe}" for nome in NOMES_BINARIOS]


def versao_do(executavel: Path) -> str | None:
    """Roda 'ffmpeg -version' e devolve a primeira linha, ou None se não funcionar."""
    try:
        saida = subprocess.run(
            [str(executavel), "-version"],
            capture_output=True, text=True, timeout=60,
        )
        if saida.returncode == 0:
            return (saida.stdout or "").splitlines()[0].strip()
    except Exception:
        pass
    return None


def situacao_atual(destino: Path) -> tuple[Path | None, str]:
    for binario in binarios_pretendidos(destino):
        versao = versao_do(binario)
        if versao:
            return binario, f"portátil do bot ({binario.parent})"
    no_path = shutil.which("ffmpeg")
    if no_path:
        return Path(no_path), "instalado no sistema (PATH)"
    return None, "não encontrado"


def escolher_asset(alvo: str, extensao: str) -> tuple[str, str]:
    """Consulta o GitHub e escolhe o pacote do ffmpeg para a plataforma."""
    pedido = urllib.request.Request(
        API_RELEASE,
        headers={"User-Agent": "holyrics-bot-installer", "Accept": "application/vnd.github+json"},
    )
    try:
        with urllib.request.urlopen(pedido, timeout=30) as resposta:
            dados = json.load(resposta)
    except Exception as e:
        nome = f"ffmpeg-master-latest-{alvo}-gpl{extensao}"
        print(f"  (não consegui consultar o GitHub: {e} — usando o endereço padrão)")
        return f"{URL_FALLBACK}/{nome}", nome

    candidatos = [
        a for a in dados.get("assets", [])
        if alvo in a["name"] and a["name"].endswith(extensao) and "gpl" in a["name"]
    ]
    if not candidatos:
        raise SystemExit(f"ERRO: nenhum pacote para {alvo} encontrado na versão {dados.get('tag_name')}.")

    def chave(asset: dict) -> tuple:
        nome = asset["name"]
        estavel = 0 if "master" not in nome else 1  # builds de versão fixa primeiro
        versao = re.search(r"ffmpeg-n?(\d+)\.(\d+)", nome)
        return (estavel, -(int(versao.group(1)) if versao else 0), -(int(versao.group(2)) if versao else 0))

    escolhido = sorted(candidatos, key=chave)[0]
    return escolhido["browser_download_url"], escolhido["name"]


def baixar(url: str, destino: Path) -> None:
    pedido = urllib.request.Request(url, headers={"User-Agent": "holyrics-bot-installer"})
    with urllib.request.urlopen(pedido, timeout=120) as resposta, open(destino, "wb") as saida:
        total = int(resposta.headers.get("Content-Length") or 0)
        feito = 0
        ultimo = -1
        while True:
            bloco = resposta.read(1024 * 1024)
            if not bloco:
                break
            saida.write(bloco)
            feito += len(bloco)
            if total:
                pct = int(feito * 100 / total)
                if pct != ultimo and (pct % 10 == 0 or pct == 100):
                    ultimo = pct
                    print(f"\r  baixando... {pct:3d}%  ({feito / 1e6:.1f} de {total / 1e6:.1f} MB)", end="", flush=True)
            else:
                print(f"\r  baixando... {feito / 1e6:.1f} MB", end="", flush=True)
    print()


def extrair(pacote: Path, destino: Path, temp: Path) -> None:
    destino.mkdir(parents=True, exist_ok=True)
    if pacote.suffix == ".zip":
        with zipfile.ZipFile(pacote) as z:
            z.extractall(temp)
    else:
        with tarfile.open(pacote, "r:xz") as t:
            try:
                t.extractall(temp, filter="data")  # Python 3.12+ (nas versões antigas vem do próprio pacote)
            except TypeError:
                t.extractall(temp)

    for nome in NOMES_BINARIOS:
        encontrados = [
            p for p in temp.rglob(f"{nome}*")
            if p.is_file() and p.name in (nome, f"{nome}.exe")
        ]
        if not encontrados:
            raise SystemExit(f"ERRO: '{nome}' não veio no pacote baixado.")
        origem = encontrados[0]
        saida = destino / origem.name
        shutil.copy2(origem, saida)
        try:
            os.chmod(saida, 0o755)
        except Exception:
            pass
        print(f"  {saida.name} -> {saida}")


def instalar(destino: Path, forcar: bool) -> int:
    encontrado, onde = situacao_atual(destino)
    if encontrado and not forcar:
        print(f"ffmpeg já disponível: {encontrado}")
        print(f"  origem: {onde}")
        print("  (use --forcar para baixar a versão portátil de qualquer forma)")
        return 0

    alvo, extensao = alvo_plataforma()
    print(f"Sistema: {platform.system()} / {platform.machine()}  ->  pacote {alvo}{extensao}")
    url, nome = escolher_asset(alvo, extensao)
    print(f"  pacote escolhido: {nome}")

    with tempfile.TemporaryDirectory(prefix="ffmpeg-install-") as d:
        temp = Path(d)
        pacote = temp / nome
        try:
            baixar(url, pacote)
        except (urllib.error.URLError, TimeoutError) as e:
            print(f"\nERRO ao baixar: {e}")
            print("Instale manualmente:")
            print("  Linux:  sudo apt install ffmpeg   (ou dnf/pacman)")
            print("  Windows: winget install Gyan.FFmpeg  (ou baixe em ffmpeg.org e aponte youtube.ffmpeg)")
            return 1
        print(f"  extraindo ({pacote.stat().st_size / 1e6:.1f} MB)...")
        extrair(pacote, destino, temp / "extraido")

    binario, _ = situacao_atual(destino)
    if not binario:
        print("ERRO: o arquivo foi copiado mas o ffmpeg não executou. Instale manualmente.")
        return 1
    print(f"\nffmpeg instalado: {binario}")
    print(f"  versão: {versao_do(binario)}")
    print("\nO bot usa essa cópia automaticamente (pasta bin/), não precisa mudar o config.json.")
    print("Se quiser apontar para outro ffmpeg, use a chave 'youtube.ffmpeg'.")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Baixa o ffmpeg portátil para o bot")
    parser.add_argument("--destino", default=str(RAIZ / "bin"), help="pasta de destino (padrão: bin/ do bot)")
    parser.add_argument("--forcar", action="store_true", help="baixa mesmo que já exista ffmpeg")
    parser.add_argument("--conferir", action="store_true", help="só mostra a situação atual")
    args = parser.parse_args()

    destino = Path(args.destino)
    encontrado, onde = situacao_atual(destino)

    if args.conferir:
        print(f"ffmpeg: {encontrado or 'NÃO ENCONTRADO'}")
        if encontrado:
            print(f"  origem: {onde}")
            print(f"  versão: {versao_do(encontrado)}")
        return 0 if encontrado else 1

    try:
        return instalar(destino, args.forcar)
    except KeyboardInterrupt:
        print("\nCancelado.")
        return 130


if __name__ == "__main__":
    sys.exit(main())
