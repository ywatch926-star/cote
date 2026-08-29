#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import tempfile
from pathlib import Path

from SHARED.storage_adapter import StorageAdapter, StorageError


def main() -> None:
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        source = root / "source.mp4"
        source.write_bytes(b"storage-test")
        adapter = StorageAdapter(root / "bucket")
        adapter.upload(source, "campaigns/test/IN/source.mp4")
        assert adapter.exists("campaigns/test/IN/source.mp4")
        expected = hashlib.sha256(b"storage-test").hexdigest()
        assert adapter.sha256("campaigns/test/IN/source.mp4") == expected
        adapter.copy("campaigns/test/IN/source.mp4", "campaigns/test/MASTER/master.mp4")
        assert adapter.exists("campaigns/test/MASTER/master.mp4")
        try:
            adapter.exists("../escape.txt")
        except StorageError:
            pass
        else:
            raise AssertionError("path traversal not blocked")
    print("storage tests: ok")


if __name__ == "__main__":
    main()
