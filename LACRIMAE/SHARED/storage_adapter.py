#!/usr/bin/env python3
"""Stockage indépendant des vidéos dev6.

La MVP utilise le backend filesystem pour les tests sans credentials. Le
contrat est volontairement compatible avec un backend objet futur : l'Oracle
ne manipule que des URI et ne dépend pas d'un compte Modal.
"""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from urllib.parse import urlparse


class StorageError(RuntimeError):
    pass


class StorageAdapter:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, uri: str) -> Path:
        parsed = urlparse(uri)
        if parsed.scheme in ("", "file"):
            candidate = Path(parsed.path if parsed.scheme == "file" else uri)
            if not candidate.is_absolute():
                candidate = self.root / candidate
            candidate = candidate.resolve()
            if self.root not in candidate.parents and candidate != self.root:
                raise StorageError("chemin hors du stockage autorisé")
            return candidate
        raise StorageError(f"backend URI non configuré dans la MVP: {parsed.scheme}")

    def exists(self, uri: str) -> bool:
        return self._path(uri).is_file()

    def upload(self, local_path: str | Path, uri: str) -> str:
        source = Path(local_path).resolve()
        if not source.is_file():
            raise StorageError(f"fichier local absent: {source}")
        destination = self._path(uri)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return str(destination)

    def download(self, uri: str, local_path: str | Path) -> Path:
        source = self._path(uri)
        if not source.is_file():
            raise StorageError(f"objet absent: {uri}")
        destination = Path(local_path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return destination

    def copy(self, source_uri: str, destination_uri: str) -> str:
        source = self._path(source_uri)
        destination = self._path(destination_uri)
        if not source.is_file():
            raise StorageError(f"objet absent: {source_uri}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        return str(destination)

    def sha256(self, uri: str) -> str:
        path = self._path(uri)
        if not path.is_file():
            raise StorageError(f"objet absent: {uri}")
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def delete(self, uri: str) -> None:
        path = self._path(uri)
        if path.is_file():
            path.unlink()
