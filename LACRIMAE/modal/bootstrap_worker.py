"""Bootstrap des poids depuis le stockage objet indépendant vers un Volume Modal."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_manifest(path: str | Path = "models_manifest.json") -> dict:
    manifest = json.loads(Path(path).read_text(encoding="utf-8"))
    if manifest.get("schema_version") != "1.0.0":
        raise ValueError("version de manifeste de modèles non supportée")
    expanded = []
    for item in manifest.get("models", []):
        for field in ("id", "object_key", "sha256", "destination"):
            if not item.get(field):
                raise ValueError(f"champ modèle absent: {field}")
        expanded.append({k: item[k] for k in ("id", "object_key", "sha256", "destination")})
        for index, companion in enumerate(item.get("companion_files", []), start=1):
            for field in ("object_key", "sha256", "destination"):
                if not companion.get(field):
                    raise ValueError(f"champ fichier compagnon absent: {field}")
            expanded.append(
                {
                    "id": f"{item['id']}-companion-{index}",
                    "object_key": companion["object_key"],
                    "sha256": companion["sha256"],
                    "destination": companion["destination"],
                }
            )
    return {**manifest, "models": expanded}


def ensure_models(manifest_path: str | Path, destination_root: str | Path) -> list[dict]:
    """Télécharge les modèles absents ou invalides depuis le backend S3."""
    try:
        import boto3
        from botocore.config import Config
    except ImportError as exc:
        raise RuntimeError("boto3 est requis pour le bootstrap objet") from exc

    manifest = load_manifest(manifest_path)
    root = Path(destination_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    client = boto3.client(
        "s3",
        endpoint_url=os.environ["STORAGE_S3_ENDPOINT"],
        region_name=os.environ.get("STORAGE_S3_REGION", "us-east-005"),
        aws_access_key_id=os.environ["STORAGE_S3_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["STORAGE_S3_SECRET_ACCESS_KEY"],
        config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
    )
    results = []
    for item in manifest["models"]:
        target = (root / item["destination"]).resolve()
        if root not in target.parents:
            raise ValueError(f"destination hors du Volume: {item['destination']}")
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.is_file() or sha256(target) != item["sha256"]:
            client.download_file(os.environ["STORAGE_S3_BUCKET"], item["object_key"], str(target))
        actual = sha256(target)
        if actual != item["sha256"]:
            raise RuntimeError(f"hash modèle invalide: {item['id']}")
        results.append({"id": item["id"], "destination": str(target), "sha256": actual})
    return results
