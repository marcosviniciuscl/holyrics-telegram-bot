# Holyrics Bot

**v0.0.1** · Aplicativo de bandeja para **Windows e Linux** que recebe arquivos
pelo **Telegram** e salva nas pastas do **Holyrics**.

> Sem instalação, sem serviço e sem build na sua máquina. Baixe o pacote pronto,
> descompacte e clique. O pacote já leva **Python, dependências, Tk, ffmpeg e
> ffprobe**.

## Baixar e rodar (sem instalar nada)

1. No GitHub, abra **Actions → Build**.
   - Se não houver execução recente: **Run workflow**.
2. Baixe o **Artifact**:
   - Windows: **`HolyricsBot-Windows-0.0.1.zip`**
   - Linux: **`HolyricsBot-Linux-0.0.1-x86_64.AppImage`** (recomendado)
     ou `HolyricsBot-Linux-0.0.1.tar.gz`
3. **Windows:** descompacte e dê dois cliques em **`HolyricsBot.exe`**.
   **Linux:** dê permissão e execute o AppImage:
   ```bash
   chmod +x HolyricsBot-Linux-0.0.1-x86_64.AppImage
   ./HolyricsBot-Linux-0.0.1-x86_64.AppImage
   ```
   Se a sua distro não tiver FUSE:
   `./HolyricsBot-Linux-0.0.1-x86_64.AppImage --appimage-extract-and-run`
4. O app abre na **bandeja**. Clique no ícone para configurar.

No Linux, para criar o atalho no menu: abra a janela → aba **Avançado** →
**Criar atalho no menu**.

Os builds rodam automaticamente no GitHub Actions a cada push na `main` e
também podem ser disparados manualmente. Ainda não há tags/releases: a versão
atual é **0.0.1**.

## O que ele faz

- **Salva por tipo** nas pastas configuradas: áudio, vídeo, imagem,
  apresentações, documentos e outros.
- **Normaliza para o Holyrics**:
  - vídeo → **MP4 H.264 + AAC**, 8 bits e *faststart*, mantendo resolução,
    proporção e taxa de quadros;
  - áudio → **MP3**;
  - imagem → **JPG/PNG** (WebP, TIFF, BMP, HEIC, AVIF, JFIF são convertidos,
    com transparência preservada em PNG);
  - a conversão só acontece quando o arquivo **não está no padrão** — o bot
    analisa o codec com `ffprobe`, não só a extensão.
- **PDF → PowerPoint** (.pptx) automaticamente, com **progresso por página**
  (`Convertendo… 60% — página 12 de 20`).
- **YouTube**: link → 2 opções de vídeo (MP4) e 2 de áudio (MP3), com progresso.
- **Arquivos grandes**: acima de 20 MB (limite da API na nuvem), usa o
  **MinIO** e devolve um link curto temporário.
- **Links diretos**: cola um link de arquivo e o bot baixa e salva.
- **Feedback no Telegram** em todas as etapas: download, conversão (com %),
  envio e pasta final.

## Janela de configuração

Abas:

- **Telegram** — token do [@BotFather](https://t.me/BotFather), IDs autorizados
  (use `/id` no bot) e aceitar grupos.
- **Pastas** — uma pasta para cada categoria do Holyrics.
- **Conversão** — perguntar antes de converter, qualidade do MP3, CRF/preset do
  vídeo e opções do PDF.
- **YouTube** — ativar, resolução/duração máximas, bitrate do MP3 e cookies.
- **MinIO** — endpoint, chaves, buckets, link de upload e tempos. O botão
  **Publicar no MinIO** sobe a página de upload e configura o bucket público.
- **Avançado** — links diretos, limite do Telegram, cache de arquivos, nível do
  log e criação do atalho no Linux.
- **Log** — o que o bot está fazendo, em tempo real.

Botões: **Salvar e aplicar**, **Iniciar/Parar bot**, **Abrir pasta** e **Sair**.

Os campos de **tamanho/qualidade** (resolução, bitrate, DPI, CRF, duração e
limites) são **listas de valores padrão**; o valor escolhido é salvo como
número no `config.json`.

O app **recarrega o `config.json` ao abrir a janela** (útil quando você edita o
arquivo por fora). Na aba **Avançado** também há **Recarregar do arquivo** e
**Abrir config.json**, além do caminho exato do arquivo em uso.

## Bandeja

| Ação | O que faz |
|---|---|
| Clique / duplo clique | abre a configuração |
| Botão direito → **Iniciar bot** | inicia o bot |
| Botão direito → **Parar bot** | para o bot |
| Botão direito → **Status** | online/parado/erro |
| Botão direito → **Sair** | fecha o app |
| Fechar a janela (X) | esconde; continua na bandeja |

O ícone muda de cor: verde (online), amarelo (conectando), cinza (parado),
vermelho (erro).

## Conversão de vídeo (o padrão do Holyrics)

| Item | Padrão |
|---|---|
| Contêiner | MP4 |
| Vídeo | H.264 (perfil high) |
| Pixel format | yuv420p (8 bits) |
| Áudio | AAC |
| Extras | `faststart` |

Se já está nesse padrão, **nada é feito**. Se só o contêiner/áudio está fora,
faz **remux/cópia** (rápido, sem perda). Se o codec é incompatível (HEVC, VP9,
MPEG-4, 10 bits…), **reencoda** com `libx264` e CRF configurável (padrão **18**),
sem redimensionar.

Na conversão de **PDF**, a mensagem do Telegram mostra o andamento:
`🔄 Convertendo arquivo.pdf para PowerPoint… 60% — página 12 de 20`.

```json
"converter": {
  "perguntar": false,
  "audio_bitrate_kbps": 192,
  "video_crf": 18,
  "video_preset": "medium"
}
```

## MinIO (arquivos grandes)

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

- Abra a aba **MinIO → Publicar no MinIO** para subir a página e liberar leitura
  pública do bucket (feito pelo próprio app).
- O bot manda um link curto; o usuário sobe pelo navegador; o bot baixa com
  progresso, salva e apaga do MinIO.
- O bucket de destino pode ficar **privado**.

## Estrutura do projeto

```
holyrics_bot/            # pacote do aplicativo
  __init__.py            # versão (0.0.1)
  __main__.py            # python -m holyrics_bot
  bot.py                 # motor: Telegram, pastas, conversão, MinIO
  gui.py                 # janela + bandeja (tkinter + pystray)
  app_core.py            # config.json, execução em thread, instância única
  minio_store.py         # MinIO (S3)
  cache.py               # reaproveitamento de arquivos já enviados
  resources/             # ícones + página de upload
main.py                  # ponto de entrada (usado pelo PyInstaller)
HolyricsBot.spec         # configuração do PyInstaller
pyproject.toml           # dependências e versão
config.example.json      # exemplo de configuração
tests/test_local.py      # testes locais
packaging/appimage/      # AppRun + .desktop do AppImage
.github/workflows/       # build automático dos pacotes
bin/                     # ffmpeg/ffprobe (o CI coloca aqui; não versionado)
```

## Cache de arquivos (evitar baixar de novo)

Ativado por padrão. O bot guarda o `file_unique_id` do Telegram apontando para o
arquivo salvo. Se você reenviar o mesmo arquivo:

- se ele já está no formato final, o bot responde **“já estava salvo”** e não
  baixa de novo;
- se o que está salvo é o **original** de uma conversão que falhou, o bot usa
  esse original para converter outra vez, **sem baixar**;
- se o arquivo não existe mais (ou passou do prazo do cache), baixa normal.

```json
"cache": {
  "reutilizar": true,
  "dias": 30
}
```

O cache fica em `cache_arquivos.json` junto do `config.json`.

## Onde ficam os arquivos

- Configuração: `config.json` **ao lado do executável** (ou do `.tar.gz`).
- Log: `bot.log` ao lado do executável.
- **AppImage** é somente leitura, então configuração e log ficam em
  **`~/.config/holyrics-bot/`**.
- `config.json` guarda token e chaves — **não compartilhe**.

## Desenvolvimento (opcional)

```bash
pip install -e .[build]
python main.py            # abre a janela
python -m holyrics_bot    # idem
python tests/test_local.py
```

Para rodar no fonte, tenha `ffmpeg` no `PATH` ou em `bin/`. Os pacotes prontos
já levam o ffmpeg.

## Removendo o serviço antigo (Linux)

As versões antigas rodavam como serviço systemd. Isso foi removido. Se ainda
houver um serviço instalado:

```bash
sudo systemctl disable --now holyrics-bot
sudo rm -f /etc/systemd/system/holyrics-bot.service
sudo systemctl daemon-reload
```

## Problemas comuns

| Sintoma | O que fazer |
|---|---|
| App não abre | confira se extraiu a pasta inteira (o `_internal` é obrigatório) |
| Windows: “O Windows protegeu o computador” | **Mais informações → Executar assim mesmo** (o .exe não é assinado) |
| Ícone não aparece na bandeja | clique na seta “^” ao lado do relógio |
| Linux: bandeja não aparece | KDE/XFCE/Cinnamon/MATE, ou extensão AppIndicator no GNOME; o atalho/janela continua funcionando |
| Linux: AppImage não abre | instale FUSE ou rode com `--appimage-extract-and-run` |
| “Não autorizado” no Telegram | confira os IDs autorizados (use `/id`) |
| Vídeo não abre no Holyrics | veja o log; se já era H.264/AAC+faststart, o problema pode ser o próprio arquivo |
| YouTube pede verificação | exporte `cookies.txt` e aponte na aba YouTube |
| MinIO não conecta | confira endpoint/chaves e use **Publicar no MinIO** para criar/configurar o bucket |
