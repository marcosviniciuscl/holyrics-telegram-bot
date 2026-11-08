# Holyrics Bot

Aplicativo para **Windows** que recebe arquivos pelo **Telegram** e salva nas
pastas do **Holyrics**. Fica na **bandeja do sistema** com o status do bot e uma
janela de configuração simples.

> Não é serviço, não é tarefa agendada. Você abre com **dois cliques** e ele fica
> na bandeja. Para sair: botão direito no ícone → **Sair**.

## O que ele faz

- **Salva por tipo** nas pastas configuradas: áudio, vídeo, imagem,
  apresentações, documentos e outros.
- **Normaliza para o Holyrics**:
  - vídeo → **MP4 H.264 + AAC**, pixel format 8 bits e *faststart*, mantendo
    resolução, proporção e taxa de quadros;
  - áudio → **MP3**;
  - imagem → **JPG/PNG** (formatos como WebP, TIFF, BMP, HEIC, AVIF, JFIF são
    convertidos, com transparência preservada em PNG).
  - A conversão só acontece quando o arquivo **não está no padrão** — o bot
    analisa o codec de verdade com `ffprobe`, não só a extensão.
- **PDF → PowerPoint** (.pptx) automaticamente.
- **YouTube**: manda o link, escolhe vídeo (MP4) ou áudio (MP3).
- **Arquivos grandes**: acima de 20 MB (limite do Telegram na nuvem), usa o
  **MinIO** e devolve um link curto temporário.
- **Links diretos**: cola um link de arquivo e o bot baixa e salva.
- **Feedback no Telegram** em todas as etapas: download, conversão (com
  porcentagem), envio e pasta final.

## Rodar no Windows

### Opção A — executável (recomendado)

O executável leva **tudo embutido**: Python, dependências, `ffmpeg`, `ffprobe`
e `yt-dlp`. Depois de gerado, **não baixa nada** ao abrir.

Gere uma vez, no Windows:

```powershell
# na pasta do projeto
Set-ExecutionPolicy -Scope Process Bypass -Force
.\build-windows.ps1
```

O script:
- cria o `.venv` e instala as dependências (uma vez);
- usa o `ffmpeg.exe`/`ffprobe.exe` que você já tem (na pasta `bin\` ou no `PATH`)
  — **não baixa ffmpeg**;
- gera **`dist\HolyricsBot\HolyricsBot.exe`**.

Depois é só dar **dois cliques** em `HolyricsBot.exe`.

> O build precisa rodar no Windows (o PyInstaller não gera `.exe` a partir do
> Linux). O executável final é autossuficiente.

### Opção B — sem gerar o .exe

Se o `.venv` já existe na pasta:

```
executar-windows.bat
```

Ele abre com `pythonw.exe` (sem console) e o app vai para a bandeja.

## Primeira configuração

Na primeira vez, a janela de configuração abre. Preencha:

1. **Telegram** → token do [@BotFather](https://t.me/BotFather) e seu ID
   (fale com o [@userinfobot](https://t.me/userinfobot) ou use `/id` no bot).
2. **Pastas** → clique em **Escolher…** em cada categoria e aponte para as
   pastas do Holyrics no Windows (ex.: `C:\Holyrics\files\...`).
3. Clique em **Salvar e aplicar**.

A janela fecha para a bandeja e o bot começa a receber arquivos.

## Bandeja do sistema

| Ação | O que faz |
|---|---|
| Clique / duplo clique no ícone | abre a configuração |
| Botão direito → **Iniciar bot** | inicia o bot |
| Botão direito → **Parar bot** | para o bot |
| Botão direito → **Status** | mostra online/parado/erro |
| Botão direito → **Sair** | fecha o app de verdade |
| Fechar a janela (X) | apenas esconde; continua na bandeja |

O ícone muda de cor conforme o status (verde = online, amarelo = conectando,
cinza = parado, vermelho = erro).

## Abas da configuração

- **Telegram** — token, IDs autorizados e aceitar grupos.
- **Pastas** — uma pasta para cada categoria do Holyrics.
- **Conversão** — perguntar antes de converter, qualidade do MP3, CRF/preset do
  vídeo e opções do PDF.
- **YouTube** — ativar, resolução máxima, duração máxima, bitrate do MP3 e
  cookies.
- **MinIO** — endpoint, chaves, buckets, página de upload e tempos.
- **Avançado** — links diretos, limite do Telegram e nível do log.
- **Log** — o que o bot está fazendo, em tempo real.

## Conversão de vídeo (o padrão do Holyrics)

O Holyrics abre e reproduz de forma confiável com:

| Item | Padrão |
|---|---|
| Contêiner | MP4 |
| Vídeo | H.264 (perfil high) |
| Pixel format | yuv420p (8 bits) |
| Áudio | AAC |
| Extras | `faststart` (começa antes de baixar tudo) |

Se o arquivo já está nesse padrão, **nada é feito**. Se só o contêiner/áudio
está fora, o bot faz **remux/cópia** (rápido, sem perda). Se o codec de vídeo é
incompatível (HEVC, VP9, MPEG-4, 10 bits…), ele **reencoda** com `libx264` e
CRF configurável (padrão **18**), **sem redimensionar**.

Configuração:

```json
"converter": {
  "perguntar": false,
  "audio_bitrate_kbps": 192,
  "video_crf": 18,
  "video_preset": "medium"
}
```

## MinIO (arquivos grandes)

Para arquivos acima do limite do Telegram:

```json
"minio": {
  "ativo": true,
  "endpoint": "https://minio.seudominio.com",
  "access_key": "...",
  "secret_key": "...",
  "bucket": "holyrics-entrada",
  "bucket_publico": "holyrics-publico",
  "url_pagina_upload": "https://minio.seudominio.com/holyrics-publico/uploader.html",
  "expira_min": 120
}
```

- O bot manda um **link curto**; o usuário sobe pelo navegador direto ao MinIO.
- O bot **baixa com progresso**, salva na pasta e **apaga** do MinIO.
- A página `minio-uploader/index.html` vai num bucket público de leitura. O
  script `minio-uploader/publicar.sh` publica com o `mc`.

## YouTube

Mande um link (`youtube.com`, `youtu.be`, Shorts…). O bot oferece **2 opções de
vídeo (sempre MP4)** e **2 de áudio (sempre MP3)**, com progresso. O áudio é
convertido pelo ffmpeg que já vem no app.

## Onde ficam os arquivos

- Configuração: `config.json` **ao lado do executável**.
- Log: `bot.log` ao lado do executável.
- `config.json` guarda token e chaves — **não compartilhe** esse arquivo.

## Removendo o serviço antigo (Linux)

As versões anteriores rodavam como serviço systemd. Isso foi removido do
projeto. Se ainda houver um serviço instalado na máquina Linux:

```bash
sudo systemctl disable --now holyrics-bot
sudo rm -f /etc/systemd/system/holyrics-bot.service
sudo systemctl daemon-reload
```

## Modo CLI (opcional, para desenvolvimento)

O motor do bot continua disponível:

```bash
python bot.py --verificar     # confere a configuração
python bot.py                 # roda em primeiro plano (sem interface)
python testes/teste_local.py  # testa conversão, download, regras, YouTube
```

## Estrutura

```
holyrics_bot_gui.py   # janela + bandeja (tkinter + pystray)
app_core.py           # config.json, execução em thread, instância única
bot.py                # motor do bot (Telegram, pastas, conversão, MinIO)
minio_holyrics.py     # MinIO (S3)
build-windows.ps1     # gera o .exe com tudo embutido
HolyricsBot.spec      # configuração do PyInstaller
executar-windows.bat  # abre pelo .venv (sem gerar .exe)
assets/               # ícones do app/bandeja
minio-uploader/       # página de upload e script de publicação
servidor-bot-api/     # opcional: servidor local do Bot API (sem limite de 20 MB)
```

## Problemas comuns

| Sintoma | O que fazer |
|---|---|
| App não abre | veja se o `HolyricsBot.exe` existe; rode `build-windows.ps1` de novo |
| Ícone não aparece na bandeja | clique na seta “^” ao lado do relógio; o app pode estar atrás |
| “Não autorizado” no Telegram | confira os IDs autorizados (use `/id`) |
| Vídeo ainda não abre no Holyrics | veja o log; se o arquivo já era H.264/AAC+faststart, o problema pode ser o próprio arquivo |
| YouTube pede verificação | exporte `cookies.txt` e aponte na aba YouTube |
| MinIO não conecta | confira endpoint/chaves e se o bucket existe |

---

Feito para Windows 10/11. O executável gerado é autossuficiente — nada de
instalar Python, ffmpeg ou dependências na máquina de quem usa.
