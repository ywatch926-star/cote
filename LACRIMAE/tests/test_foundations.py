#!/usr/bin/env python3
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORACLE = ROOT / "ORACLE" / "oracle.py"
CUSTOS = ROOT / "LAC_CUSTOS_VIDEO.py"


def run(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run([sys.executable, *args], cwd=ROOT, text=True, capture_output=True, check=False)


def test_create_and_simulate_campaign() -> None:
    with tempfile.TemporaryDirectory() as temp:
        base = Path(temp)
        source = base / "source.mp4"
        source.write_bytes(b"dev6-test-source")
        created = run(str(ORACLE), "create", "--root", str(base), "--campaign-id", "test_001", "--source", str(source))
        assert created.returncode == 0, created.stderr
        for _ in range(10):
            advanced = run(str(ORACLE), "simulate", "--root", str(base), "--campaign-id", "test_001")
            assert advanced.returncode == 0, advanced.stderr
        state = json.loads((base / "campaigns" / "test_001" / "campaign_state.json").read_text())
        assert state["status"] == "SEALED"
        assert len(state["completed_stages"]) == 10
        check = run(str(CUSTOS), "--root", str(base), "--campaign-id", "test_001", "--stage", "F00_INGEST")
        assert check.returncode == 0, check.stderr


if __name__ == "__main__":
    test_create_and_simulate_campaign()
    print("foundation tests: ok")
