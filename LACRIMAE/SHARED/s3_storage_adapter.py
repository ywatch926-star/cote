#!/usr/bin/env python3
"""Adaptateur S3-compatible pour Backblaze B2, R2 ou autre fournisseur.

Configuration uniquement par variables d'environnement :
STORAGE_S3_ENDPOINT, STORAGE_S3_REGION, STORAGE_S3_BUCKET,
STORAGE_S3_ACCESS_KEY_ID, STORAGE_S3_SECRET_ACCESS_KEY.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path

try:
    import boto3
    from botocore.config import Config
except ImportError as exc:  # pragma: no cover
    boto3 = None
    _IMPORT_ERROR = exc


class S3StorageError(RuntimeError):
    pass


class S3StorageAdapter:
    def __init__(self) -> None:
        if boto3 is None:
            raise S3StorageError("boto3 absent : installez boto3 avant le backend S3") from _IMPORT_ERROR
        self.endpoint = os.environ["STORAGE_S3_ENDPOINT"]
        self.region = os.environ.get("STORAGE_S3_REGION", "us-east-005")
        self.bucket = os.environ["STORAGE_S3_BUCKET"]
        self.client = boto3.client(
            "s3",
            endpoint_url=self.endpoint if self.endpoint.startswith("http") else f"https://{self.endpoint}",
            region_name=self.region,
            aws_access_key_id=os.environ["STORAGE_S3_ACCESS_KEY_ID"],
            aws_secret_access_key=os.environ["STORAGE_S3_SECRET_ACCESS_KEY"],
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
        )

    def upload(self, local_path: str | Path, key: str) -> str:
        path = Path(local_path)
        if not path.is_file():
            raise S3StorageError(f"fichier absent: {path}")
        self.client.upload_file(str(path), self.bucket, key)
        return f"s3://{self.bucket}/{key}"

    def download(self, key: str, local_path: str | Path) -> Path:
        destination = Path(local_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        self.client.download_file(self.bucket, key, str(destination))
        return destination

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception as exc:
            if getattr(exc, "response", {}).get("ResponseMetadata", {}).get("HTTPStatusCode") == 404:
                return False
            raise

    def sha256(self, key: str) -> str:
        digest = hashlib.sha256()
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        body = response["Body"]
        for chunk in iter(lambda: body.read(1024 * 1024), b""):
            digest.update(chunk)
        body.close()
        return digest.hexdigest()

    def presigned_get(self, key: str, expires_seconds: int = 3600) -> str:
        return self.client.generate_presigned_url(
            "get_object",
            Params={"Bucket": self.bucket, "Key": key},
            ExpiresIn=expires_seconds,
        )
