# Tests F00-PUR (unitaires, sans réseau)
# Run: pytest -q F00_INGEST/tests/test_f00_pur.py
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "CODEBASE"))
import f00_pur  # noqa: E402

FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.mark.parametrize("fixture", ["pur_A01.json", "pur_A02.json", "pur_A03.json"])
def test_g0_pack_valide(fixture):
    pack = json.loads((FIXTURES / fixture).read_text(encoding="utf-8"))
    ok, errors = f00_pur.gate_g0_pack(pack)
    assert ok, errors


def test_g0_rejete_sans_vod():
    ok, errors = f00_pur.gate_g0_pack({"mode": "pur", "source": {}})
    assert not ok
    assert any("vod_url" in e for e in errors)


def test_g0_rejete_mauvais_mode():
    ok, _ = f00_pur.gate_g0_pack({"mode": "logo", "source": {"vod_url": "x", "start_sec": 0, "end_sec": 5}})
    assert not ok


def test_g0_rejete_segment_inverse():
    pack = {"mode": "pur", "source": {"vod_url": "x", "start_sec": 10, "end_sec": 5},
            "montage_instructions": {"segment": {"start_sec": 10, "end_sec": 5}}}
    ok, errors = f00_pur.gate_g0_pack(pack)
    assert not ok
    assert any("end" in e for e in errors)


def test_g0_rejete_segment_trop_long():
    pack = {"mode": "pur", "source": {"vod_url": "x", "start_sec": 0, "end_sec": 500},
            "montage_instructions": {"segment": {"start_sec": 0, "end_sec": 500}}}
    ok, errors = f00_pur.gate_g0_pack(pack)
    assert not ok
    assert any("trop long" in e for e in errors)


def test_seconds_to_hms():
    assert f00_pur.seconds_to_hms(737.48) == "00:12:17.480"
    assert f00_pur.seconds_to_hms(0) == "00:00:00.000"
    assert f00_pur.seconds_to_hms(3661.5) == "01:01:01.500"


def test_build_ytdlp_command():
    cmd = f00_pur.build_ytdlp_command("https://twitch.tv/videos/1", 737.48, 767.48, Path("out/pur_A01"))
    assert cmd[0] == "yt-dlp"
    assert "--download-sections" in cmd
    sections = cmd[cmd.index("--download-sections") + 1]
    assert sections.startswith("*") and "00:12:17.480-00:12:47.480" in sections
    assert "--force-keyframes-at-cuts" in cmd
    assert "bv*[height<=1080]+ba/b" in cmd
    assert "--no-playlist" in cmd


def test_find_downloaded_file_prefers_mp4(tmp_path):
    (tmp_path / "pur_A01.mkv").write_bytes(b"x")
    (tmp_path / "pur_A01.mp4").write_bytes(b"x")
    found = f00_pur.find_downloaded_file(tmp_path)
    assert found is not None and found.suffix == ".mp4"
