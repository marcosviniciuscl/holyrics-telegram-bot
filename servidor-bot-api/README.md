# Servidor local do Telegram Bot API

A API na nuvem do Telegram só entrega para bots arquivos de até **20 MB**.
Rodando um servidor local do Bot API, o limite some: o bot passa a **baixar
arquivos sem limite de tamanho** e a **enviar até ~2 GB**.

> Fonte oficial: <https://github.com/tdlib/telegram-bot-api>

## 1. Pegue o `api_id` e o `api_hash`

1. Acesse <https://my.telegram.org> e faça login com seu número.
2. Em **API development tools**, crie um aplicativo (qualquer nome).
3. Anote o **api_id** (número) e o **api_hash** (texto).

## 2. Instale o servidor

### Opção A — compilar (recomendado para rodar no mesmo PC do bot)

Você pode gerar as instruções prontas para o seu sistema em
<https://tdlib.github.io/telegram-bot-api/build.html> (escolha Linux).

Resumo no Ubuntu/Debian:

```bash
sudo apt update
sudo apt install -y make git zlib1g-dev libssl-dev gperf cmake clang libc++-dev

git clone --recursive https://github.com/tdlib/telegram-bot-api.git
cd telegram-bot-api
mkdir build && cd build
cmake -DCMAKE_BUILD_TYPE=Release ..
cmake --build . --target install    # instala em /usr/local/bin/telegram-bot-api
```

### Opção B — Docker

```bash
cd servidor-bot-api
cp .env.example .env      # edite com seu api_id e api_hash
docker compose up -d
```

O `docker-compose.yml` já monta `/var/lib/telegram-bot-api` no mesmo caminho do
host, para o bot conseguir ler os arquivos.

## 3. Suba o serviço (modo nativo)

```bash
# edite o api_id/api_hash e o usuário no arquivo antes
sudo cp servidor-bot-api/telegram-bot-api.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now telegram-bot-api
systemctl status telegram-bot-api
```

O serviço roda em `http://127.0.0.1:8081` e guarda os arquivos em
`/home/marcos/.telegram-bot-api`.

## 4. Aponte o bot para o servidor local

No `config.json` do bot:

```json
"telegram": {
  "token": "SEU_TOKEN",
  "api_id": 123456,
  "api_hash": "seu_api_hash",
  "base_url": "http://127.0.0.1:8081/bot",
  "base_file_url": "http://127.0.0.1:8081/file/bot",
  "local_mode": true
},
"download": {
  "tamanho_maximo_mb": 2000
}
```

Depois reinicie o bot:

```bash
sudo systemctl restart holyrics-bot
```

## Importante

- **Só um servidor por vez:** um bot não pode rodar ao mesmo tempo na nuvem e no
  servidor local. Se tiver problemas, chame `logOut` na API da nuvem (ou apenas
  garanta que só o bot apontando para o servidor local esteja rodando).
- **Mesmo host:** em modo `--local`, o `getFile` devolve o **caminho absoluto** do
  arquivo. O bot precisa enxergar esse caminho — o mais simples é rodar o
  servidor e o bot na mesma máquina e com o mesmo usuário.
- Os arquivos baixados ficam em `/home/marcos/.telegram-bot-api/<token>/` e podem
  ser apagados de vez em quando para liberar espaço.
