# Bot do Telegram × Holyrics

Bot do Telegram que recebe arquivos e salva cada um **na pasta correspondente do
Holyrics**. PDF é **convertido para PowerPoint (.pptx)** — o formato de
apresentação que o Holyrics usa — e salvo na pasta de apresentações.

Roda como **serviço** no Windows (Agendador de Tarefas) e no Linux (systemd),
com tudo configurado em um único `config.json`.

---

## Como se comporta

1. Você envia um arquivo no Telegram.
2. O bot responde **na mesma mensagem**: `📥 Recebi arquivo.mp4 (12,3 MB) / Baixando… 47%`.
   O texto é atualizado na própria mensagem (nada de enxurrada de mensagens).
3. Ao terminar ele edita a mensagem para o resultado final:

```
✅ missa.pdf
🔄 Convertido para PowerPoint (14 slides)
📁 Salvo em:
C:\Holyrics\files\Apresentacoes\missa.pptx
📦 3,1 MB
```

| Você envia | Vai para a pasta |
|---|---|
| áudio (mp3, wav, m4a, ogg, flac, …) | `pastas.audio` |
| vídeo (mp4, mkv, avi, mov, webm, …) | `pastas.video` |
| imagem (jpg, png, gif, webp, …) | `pastas.imagem` |
| **PDF** | convertido em `.pptx` → `pastas.apresentacao` |
| PowerPoint (pptx, ppt, ppsx) | `pastas.apresentacao` |
| documento (txt, docx, rtf, odt, csv, srt…) | `pastas.documento` |
| qualquer outra coisa | `pastas.outros` |

Foto/áudio/voz/vídeo enviados "pelo modo rápido" do Telegram (sem ser como
arquivo) também funcionam: o nome recebe a data/hora automaticamente.
Se já existir um arquivo com o mesmo nome, o bot cria `nome (2).ext` — nunca
sobrescreve nada.

### Conversão para os formatos do Holyrics (MP3 / MP4)

O Holyrics se comporta melhor com **MP3** para áudio e **MP4** para vídeo. Por
isso, se você enviar um arquivo nessas categorias com outro formato, o bot
**pergunta** se quer converter, com dois botões:

```
📥 musica.m4a (11,4 MB) recebido.
O Holyrics funciona melhor com MP3 para áudio. Quer converter?
   [ ✅ Converter para MP3 ]   [ Salvar como está ]
```

- **Converter** → usa o ffmpeg para gerar o MP3 (ou MP4) e salva na pasta certa.
- **Salvar como está** → guarda o original.
- Se você não responder em 1 hora, o bot salva o original para não perder nada.
- PDF continua sendo convertido para PowerPoint automaticamente (sem perguntar).

Configuração:

```json
"converter": {
  "perguntar": true,        // false = nunca pergunta, salva como veio
  "audio_bitrate_kbps": 192 // qualidade do MP3 gerado
}
```

### Link do YouTube

Mande um link de vídeo do YouTube (funciona com `youtu.be`, `shorts`, `live`,
`m.youtube.com` e `music.youtube.com`) e o bot:

1. **verifica o vídeo** e responde com o título, o canal, a duração e as opções
   (com tamanho aproximado de cada uma):

```
🎬 Hino Teste — Ação de Graças
👤 Canal Teste · ⏱ 4:13
Escolha o formato para baixar:
   [ 🎬 1080p · ~140,3 MB ]  [ 🎬 720p · ~80,2 MB ]
   [ 🎵 MP3 192k · ~4,9 MB ]  [ 🎵 MP3 128k (leve) ]
```

> O **áudio do YouTube é sempre salvo em MP3** e o **vídeo em MP4** — os formatos
> que o Holyrics prefere.

2. Ao clicar em uma opção, mostra o **progresso do download** (%, tamanho,
   velocidade e tempo restante) e depois o **progresso da conversão**
   (`🎧 Convertendo para MP3…` ou `🎬 Juntando vídeo + áudio…`), tudo na mesma
   mensagem.

3. No fim, informa onde salvou:

```
✅ Hino Teste
🎵 MP3 192 kbps
📁 Salvo em:
C:\Holyrics\files\Audios\Hino Teste.mp3
📦 6,1 MB · ⏱ 4:13
```

Vídeo vai para `pastas.video`, áudio para `pastas.audio`.
**Não existe o limite de 20 MB aqui** — esse limite é só para arquivos enviados
pelo Telegram; do YouTube o download é feito direto, com o tamanho que o vídeo tiver.

Configuração:

```json
"youtube": {
  "ativo": true,
  "altura_maxima": 1080,      // maior resolução oferecida
  "duracao_maxima_min": 120,  // recusa vídeos mais longos que isso
  "mp3_bitrate_kbps": 192,    // qualidade do MP3 convertido
  "ffmpeg": "",               // caminho do ffmpeg (vazio = usa o do PATH)
  "cookies": ""               // opcional, veja abaixo
}
```

Para o MP3 e para juntar vídeo+áudio (qualquer coisa acima de 360p) o bot usa o
**ffmpeg**. Os instaladores já cuidam disso: se não houver ffmpeg na máquina, eles
baixam uma **versão portátil** para a pasta `bin/` do próprio bot (~100 MB, uma
vez só) — **não precisa de administrador e não mexe no sistema**. O bot encontra
essa cópia sozinho.

A ordem de procura do bot é: `youtube.ffmpeg` no config → `bin/` do bot → PATH do
sistema. Se preferir instalar no sistema: `sudo apt install ffmpeg` (Linux),
`winget install Gyan.FFmpeg` (Windows) ou baixe em
[ffmpeg.org](https://ffmpeg.org/download.html) e aponte em `youtube.ffmpeg`.

Para baixar/conferir/atualizar a qualquer momento:

```bash
python baixar_ffmpeg.py --conferir   # mostra qual ffmpeg o bot está usando
python baixar_ffmpeg.py              # baixa o portátil se ainda não tiver
python baixar_ffmpeg.py --forcar     # baixa de novo (atualizar a versão)
```

Sem ffmpeg o bot continua funcionando, mas só oferece formatos prontos e sem MP3
(ele avisa isso na mensagem de opções).

O YouTube às vezes pede verificação ("Sign in to confirm you're not a bot"),
principalmente em servidor/VPS. Nesse caso exporte os cookies do navegador
(extensão *Get cookies.txt*) para um arquivo e aponte em `youtube.cookies`.
Também vale atualizar o yt-dlp quando o YouTube mudar algo:

```bash
.venv/bin/pip install -U yt-dlp     # Linux
.venv\Scripts\pip install -U yt-dlp # Windows
```

### Link de arquivo (http/https)

Cole um **link direto** de arquivo (um `.mp4`, `.mp3`, `.pdf`, `.zip`…) e o bot
baixa e salva na pasta da categoria, igual a um arquivo enviado. Formato e nome
vêm do próprio link ou do cabeçalho `Content-Disposition`.

```json
"links": {
  "ativo": true,
  "tamanho_maximo_mb": 0,   // 0 = sem limite
  "hosts_bloqueados": []    // ex.: ["drive.google.com"] para recusar
}
```

### Arquivos maiores que 20 MB

A API do Telegram só entrega para bots arquivos de **até 20 MB**. Há três formas
de contornar (podem ser usadas juntas):

**1) Servidor local do Bot API (recomendado)** — remove o limite e o usuário
continua só mandando o arquivo no chat (até ~2 GB). Passo a passo em
[`servidor-bot-api/README.md`](servidor-bot-api/README.md). Depois, no `config.json`:

```json
"telegram": {
  "api_id": 123456,
  "api_hash": "seu_api_hash",
  "base_url": "http://127.0.0.1:8081/bot",
  "base_file_url": "http://127.0.0.1:8081/file/bot",
  "local_mode": true
},
"download": { "tamanho_maximo_mb": 2000 }
```

**2) Link de upload no MinIO** — quando o arquivo passa do limite, o bot manda um
link; o usuário abre no navegador, o arquivo sobe para o seu MinIO, e o bot então
baixa, salva na pasta certa e **apaga do MinIO**. Durante o download do MinIO o
bot mostra o **progresso** (%, bytes) na mensagem.

```json
"minio": {
  "ativo": true,
  "endpoint": "https://minio.seudominio.com",
  "access_key": "SUA_ACCESS_KEY",
  "secret_key": "SUA_SECRET_KEY",
  "bucket": "holyrics-entrada",
  "secure": true,
  "url_pagina_upload": "https://minio.seudominio.com/publico/uploader.html",
  "bucket_publico": "publico",
  "expira_min": 120
}
```

A página de upload é o arquivo [`minio-uploader/index.html`](minio-uploader/index.html);
veja como publicá-la no MinIO na seção *Página de upload no MinIO*, no fim deste
arquivo.

O `bucket_publico` é onde o bot guarda um JSONzinho com a assinatura do upload.
Com ele configurado, o link enviado no Telegram fica **curto**
(`.../uploader.html#5fd179036184be15`) em vez de carregar a assinatura toda
(que ocupava a tela). O JSON é apagado assim que o upload termina (ou por
expiração). Se ficar vazio, o bot volta ao link longo.

> **Dica — evite subir o arquivo duas vezes.** Quando você manda um arquivo no
> Telegram, o seu próprio app faz o upload completo para os servidores do
> Telegram **antes** de o bot receber a mensagem; só então o bot gera o link do
> MinIO e você sobe de novo. Para não repetir o envio, use o comando
> **`/enviar`** (`/enviar video`, `/enviar audio`, …): ele devolve o link **antes**,
> você envia uma única vez, direto ao MinIO, e o bot salva na pasta certa
> inferindo a categoria pelo nome do arquivo.

**3) Link direto** — o usuário hospeda o arquivo onde quiser e cola o link no
chat (seção anterior).

---

## 1. Criar o bot no Telegram

1. No Telegram, fale com **@BotFather** → `/newbot` → escolha nome e usuário.
2. Copie o **token** (algo como `8123456789:AAH...`).
3. Descubra **seu ID** de usuário: fale com **@userinfobot** (é o número que ele
   responde). Você vai colocar esse número em `usuarios_autorizados` — assim
   só você consegue mandar arquivos para o bot.

## 2. Configurar o `config.json`

Copie `config.example.json` para `config.json` e ajuste:

```json
{
  "telegram": {
    "token": "8123456789:AAH...",     // token do BotFather
    "usuarios_autorizados": [123456789], // seu ID; lista vazia = qualquer pessoa
    "aceitar_grupos": false           // true = também aceita em grupos
  },
  "pastas": {
    "audio":        "C:\\Holyrics\\files\\Audios",
    "video":        "C:\\Holyrics\\files\\Videos",
    "imagem":       "C:\\Holyrics\\files\\Imagens",
    "apresentacao": "C:\\Holyrics\\files\\Apresentacoes",
    "documento":    "C:\\Holyrics\\files\\Documentos",
    "outros":       "C:\\Holyrics\\files\\Outros"
  },
  "pdf": {
    "converter_para_pptx": true,  // false = salva o PDF original
    "dpi": 200,                   // qualidade da conversão
    "largura_max_px": 2400,       // limite da imagem de cada slide
    "qualidade_jpeg": 90,
    "manter_pdf_original": false  // true = guarda o PDF junto do .pptx
  },
  "download": {
    "intervalo_progresso_segundos": 2, // de quanto em quanto tempo atualiza o %
    "tamanho_maximo_mb": 20
  },
  "log": { "arquivo": "bot.log", "nivel": "INFO" }
}
```

Detalhes importantes:

* **Caminhos**: use `\\` (barra dupla) ou `/` no JSON. Também aceita
  `%USERPROFILE%`, `{USERPROFILE}`, `{DOCUMENTS}` e `~`. Caminho relativo é
  resolvido a partir da pasta do `config.json`. As pastas que não existirem são
  criadas automaticamente quando o primeiro arquivo chegar.
* **Onde ficam as pastas do Holyrics**: abra o Holyrics → tela de Arquivos/Mídias
  e veja o caminho das pastas usadas pela sua instalação. Os caminhos do exemplo
  são só sugestão — troque pelos seus. Em muitas instalações a biblioteca fica
  dentro de `Documentos\Holyrics\...`.
* Se depois de copiar o arquivo ele não aparecer na hora no Holyrics, use o
  botão de **atualizar/importar** da tela de arquivos dele (o bot só grava no
  disco; ele não mexe no banco do Holyrics).
* **PDF → PPTX**: cada página do PDF vira um slide em 16:9 (13,333 × 7,5 pol.).
  Página retrato (A4) entra centralizada, sem cortar nada.

## 3. Instalar

### Windows

```powershell
cd C:\caminho\do\bot
Set-ExecutionPolicy -Scope Process Bypass -Force
.\install-windows.ps1
```

O script cria o `.venv`, instala as dependências, cria o `config.json` (se não
existir), registra a tarefa **BotHolyrics** (inicia com o seu login e reinicia
sozinho se cair) e já sobe o bot.

```powershell
Start-ScheduledTask  -TaskName BotHolyrics   # iniciar
Stop-ScheduledTask   -TaskName BotHolyrics   # parar
.\install-windows.ps1 -Desinstalar           # remover a tarefa
```

Para rodar sem ninguém logado no Windows, use o [NSSM](https://nssm.cc):
`nssm install BotHolyrics "C:\caminho\do\bot\.venv\Scripts\python.exe" "C:\caminho\do\bot\bot.py"`.

### Linux

```bash
cd /caminho/do/bot
sudo bash install-linux.sh         # cria o serviço systemd holyrics-bot
journalctl -u holyrics-bot -f      # ver o log
sudo systemctl restart holyrics-bot
```

### Testar antes de instalar

```bash
python bot.py --verificar    # mostra as pastas resolvidas e se dá para escrever nelas
python baixar_ffmpeg.py --conferir # mostra qual ffmpeg o bot está usando
python testes/teste_local.py # testa PDF→PPTX, download com progresso e YouTube
python bot.py                # roda em primeiro plano (Ctrl+C encerra)
```

Requisitos: **Python 3.10+** e internet. O `ffmpeg` é baixado automaticamente pelo
instalador quando não existe na máquina (versão portátil na pasta `bin/`).

## Comandos do bot

| Comando | O que faz |
|---|---|
| `/start` | ajuda |
| `/pastas` | lista as pastas configuradas e o estado de cada uma (✅ / ⚠️ / ❌) |
| `/id` | mostra seu ID do Telegram (para pôr em `usuarios_autorizados`) |
| `/enviar [categoria]` | gera um link do MinIO para você enviar um arquivo grande **direto**, sem passar pelo Telegram |

Os comandos aparecem automaticamente no **menu do Telegram** quando você digita
`/` na conversa com o bot.

---

## Página de upload no MinIO

Para o usuário enviar arquivos grandes pelo navegador, publique
`minio-uploader/index.html` num bucket com leitura pública. Com o cliente `mc`:

```bash
# 1) configure o alias uma vez
mc alias set meuminio https://minio.seudominio.com SUA_ACCESS_KEY SUA_SECRET_KEY

# 2) crie um bucket público de leitura
mc mb meuminio/publico
mc anonymous set download meuminio/publico

# 3) publique a página (importante: tipo HTML)
mc cp --attr "Content-Type=text/html; charset=utf-8" \
  minio-uploader/index.html meuminio/publico/uploader.html
```

Depois coloque a URL em `minio.url_pagina_upload`
(`https://minio.seudominio.com/publico/uploader.html`) e o **mesmo bucket** em
`minio.bucket_publico` (`publico`) — é onde o bot guarda o JSONzinho que deixa o
link curto. O arquivo vai direto para o MinIO e **nunca passa pelo Telegram**.

O bucket de destino (`minio.bucket`, padrão `holyrics-entrada`) pode continuar
**privado** — os links são assinados e temporários.

---

## Limites e observações

* **20 MB por arquivo enviado no Telegram**: limite do próprio Telegram para bots
  baixarem arquivos (não é do programa). Para arquivos maiores use o **servidor
  local do Bot API**, o **link de upload no MinIO** ou um **link direto**. Isso
  não vale para links do YouTube nem para links de arquivo, que são baixados
  direto (sem esse limite).
* O bot **não altera** o banco de dados do Holyrics — apenas grava os arquivos
  nas pastas. O importar/atualizar é feito pelo próprio Holyrics.
* Biblioteca de conversão: `pypdfium2` (renderiza o PDF) + `python-pptx`.
  Não precisa de LibreOffice, Office nem Ghostscript instalados.
* Requisitos: Python 3.10+. O `ffmpeg` (para MP3/merge do YouTube) é baixado
  automaticamente pelo instalador — versão portátil em `bin/`, sem precisar de
  administrador.
* Os instaladores só **baixam** o ffmpeg quando ele não existe na máquina; se já
  existir no PATH, nada é baixado.

## Problemas comuns

| Sintoma | Causa provável |
|---|---|
| `ERRO: config não encontrado` | renomeie `config.example.json` para `config.json` |
| Bot não responde | token errado, ou outro programa usando o mesmo token (só um `getUpdates` por vez) |
| `🔒 Não autorizado` | seu ID não está em `usuarios_autorizados` (use `/id`) |
| `Falha ao receber ... Permission denied` | a pasta do Holyrics exige permissão de administrador — dê permissão de escrita ao usuário do serviço |
| PDF virou PowerPoint mas com barras brancas | a página do PDF é retrato/A4; o slide é 16:9 — o conteúdo não é cortado |
| Arquivo some depois de enviado | veja o `bot.log` na pasta do bot |
| Link do YouTube: "Sign in to confirm you're not a bot" | o YouTube pediu verificação — configure `youtube.cookies` |
| Link do YouTube: falha com "ffmpeg" | instale o ffmpeg ou aponte `youtube.ffmpeg` |
| Link do YouTube: só aparece "Melhor disponível" | o yt-dlp não conseguiu listar resoluções — atualize com `pip install -U yt-dlp` |
| Botão do YouTube: "Essa escolha expirou" | a opção foi consumida (ou o bot foi reiniciado) — mande o link de novo |
