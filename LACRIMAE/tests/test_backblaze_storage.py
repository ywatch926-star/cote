#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import os
import tempfile
from pathlib import Path
from urllib.parse import quote

import requests
from botocore.awsrequest import AWSRequest
from botocore.auth import SigV4Auth
from botocore.credentials import Credentials

endpoint = os.environ["STORAGE_S3_ENDPOINT"].rstrip("/")
region = os.environ.get("STORAGE_S3_REGION", "us-east-005")
bucket = os.environ["STORAGE_S3_BUCKET"]
access_key = os.environ["STORAGE_S3_ACCESS_KEY_ID"]
secret_key = os.environ["STORAGE_S3_SECRET_ACCESS_KEY"]
key = "campaigns/storage_test/dev6_probe.txt"
payload = b"LACRIMAE dev6 Backblaze storage probe\n"
expected = hashlib.sha256(payload).hexdigest()


def signed_request(method: str, object_key: str, body: bytes | None = None) -> requests.Response:
    url = f"{endpoint}/{quote(bucket, safe='')}/{quote(object_key, safe='/')}"
    request = AWSRequest(method=method, url=url, data=body, headers={"Host": url.split('/')[2]})
    SigV4Auth(Credentials(access_key, secret_key), "s3", region).add_auth(request)
    signed = request.prepare()
    prepared = requests.PreparedRequest()
    prepared.prepare(method=method, url=url, headers=dict(signed.headers), data=body)
    return requests.Session().send(prepared, timeout=30)


with tempfile.TemporaryDirectory() as temp:
    downloaded = Path(temp) / "downloaded.txt"
    put = signed_request("PUT", key, payload)
    if put.status_code not in (200, 201):
        raise RuntimeError(f"upload failed: HTTP {put.status_code} {put.text[:300]}")
    try:
        get = signed_request("GET", key)
        if get.status_code != 200:
            raise RuntimeError(f"download failed: HTTP {get.status_code} {get.text[:300]}")
        downloaded.write_bytes(get.content)
        actual = hashlib.sha256(downloaded.read_bytes()).hexdigest()
        if actual != expected:
            raise RuntimeError("hash mismatch on downloaded probe")
        print(f"BACKBLAZE_STORAGE_TEST=OK bucket={bucket} key={key} sha256={actual}")
    finally:
        delete = signed_request("DELETE", key)
        if delete.status_code not in (200, 204):
            raise RuntimeError(f"cleanup failed: HTTP {delete.status_code} {delete.text[:300]}")
        print("BACKBLAZE_STORAGE_TEST_CLEANUP=OK")
