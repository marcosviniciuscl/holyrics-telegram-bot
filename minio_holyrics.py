# -*- coding: utf-8 -*-
"""MinIO (S3) para receber arquivos maiores que o limite do Telegram.

Fluxo:
  1. o bot gera um link de upload pré-assinado (POST) e o usuário sobe o arquivo
     pelo navegador (página `minio-uploader/index.html`) direto para o MinIO;
  2. o bot percebe o objeto, baixa, salva na pasta do Holyrics e apaga do MinIO.

O boto3 é importado só quando o MinIO é usado, então quem não ativa a função
não precisa tê-lo instalado.
"""
from __future__ import annotations

import io
import json
import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

LOG = logging.getLogger("holyrics-bot.minio")


class MinioStore:
    def __init__(self, cfg) -> None:
        import boto3
        from botocore.config import Config as BotoConfig

        endpoint = (cfg.minio_endpoint or "").strip()
        if not endpoint.startswith(("http://", "https://")):
            endpoint = ("https://" if cfg.minio_secure else "http://") + endpoint
        self.cfg = cfg
        self.endpoint = endpoint.rstrip("/")
        self.bucket = cfg.minio_bucket
        self.cliente = boto3.client(
            "s3",
            endpoint_url=self.endpoint,
            aws_access_key_id=cfg.minio_access,
            aws_secret_access_key=cfg.minio_secret,
            region_name=cfg.minio_regiao or "us-east-1",
            config=BotoConfig(
                signature_version="s3v4",
                s3={"addressing_style": "path"},
                retries={"max_attempts": 3, "mode": "standard"},
            ),
        )

    # ------------------------------------------------------------------ bucket
    def garantir_bucket(self) -> None:
        from botocore.exceptions import ClientError

        try:
            self.cliente.head_bucket(Bucket=self.bucket)
        except ClientError as e:
            codigo = str(e.response.get("Error", {}).get("Code", ""))
            if codigo in ("404", "NoSuchBucket", "NotFound"):
                self.cliente.create_bucket(Bucket=self.bucket)
                LOG.info("Bucket '%s' criado no MinIO.", self.bucket)
            else:
                raise

    # ------------------------------------------------------- link de upload
    def dados_upload(self, chave: str, redirect: str | None = None) -> dict:
        """Dados do POST pré-assinado para o navegador subir o arquivo."""
        campos: dict = {}
        condicoes: list = []
        if redirect:
            campos["success_action_redirect"] = redirect
            condicoes.append({"success_action_redirect": redirect})
        if self.cfg.minio_max_mb:
            condicoes.append(
                ["content-length-range", 1, self.cfg.minio_max_mb * 1024 * 1024]
            )
        return self.cliente.generate_presigned_post(
            Bucket=self.bucket,
            Key=chave,
            Fields=campos or None,
            Conditions=condicoes or None,
            ExpiresIn=self.cfg.minio_expira_min * 60,
        )

    def url_put(self, chave: str) -> str:
        """Alternativa simples ao POST: URL para `curl -T` (sem página)."""
        return self.cliente.generate_presigned_url(
            "put_object",
            Params={"Bucket": self.bucket, "Key": chave},
            ExpiresIn=self.cfg.minio_expira_min * 60,
        )

    # -------------------------------------------------------------- consulta
    def tamanho(self, chave: str) -> int:
        from botocore.exceptions import ClientError

        try:
            resposta = self.cliente.head_object(Bucket=self.bucket, Key=chave)
            return int(resposta.get("ContentLength") or 0)
        except ClientError:
            return 0

    def guardar_json(self, chave: str, dados: dict, bucket: str | None = None) -> None:
        """Guarda um JSON pequeno (usado para links curtos de upload)."""
        bucket = bucket or self.bucket
        corpo = json.dumps(dados).encode("utf-8")
        self.cliente.put_object(
            Bucket=bucket, Key=chave, Body=io.BytesIO(corpo), ContentLength=len(corpo),
            ContentType="application/json", CacheControl="no-store",
        )

    def limpar_antigos(self, prefixo: str, idade_min: int, bucket: str | None = None) -> int:
        """Remove objetos de um prefixo mais velhos que `idade_min` minutos."""
        bucket = bucket or self.bucket
        limite = datetime.now(timezone.utc) - timedelta(minutes=max(int(idade_min), 1))
        removidos = 0
        try:
            paginador = self.cliente.get_paginator("list_objects_v2")
            for pagina in paginador.paginate(Bucket=bucket, Prefix=prefixo):
                for obj in pagina.get("Contents", []):
                    quando = obj.get("LastModified")
                    if quando and quando < limite:
                        self.apagar(obj["Key"], bucket)
                        removidos += 1
        except Exception as e:  # noqa: BLE001
            LOG.warning("Falha na limpeza do MinIO (%s): %s", prefixo, e)
        return removidos

    def listar(self, prefixo: str) -> list[str]:
        """Chaves existentes sob um prefixo (usado pelo comando /enviar)."""
        chaves: list[str] = []
        paginador = self.cliente.get_paginator("list_objects_v2")
        for pagina in paginador.paginate(Bucket=self.bucket, Prefix=prefixo):
            for obj in pagina.get("Contents", []):
                chaves.append(obj["Key"])
        return chaves

    def baixar(self, chave: str, destino: Path, callback=None) -> None:
        # `callback` recebe o total de bytes transferidos em cada bloco (boto3).
        self.cliente.download_file(self.bucket, chave, str(destino), Callback=callback)
        LOG.info("Baixado do MinIO: %s (%d bytes)", chave, destino.stat().st_size)

    # --------------------------------------------------------------- remoção
    def apagar(self, chave: str, bucket: str | None = None) -> None:
        try:
            self.cliente.delete_object(Bucket=bucket or self.bucket, Key=chave)
            LOG.info("Apagado do MinIO: %s", chave)
        except Exception as e:  # noqa: BLE001 — não pode derrubar o bot
            LOG.warning("Falha ao apagar '%s' do MinIO: %s", chave, e)
