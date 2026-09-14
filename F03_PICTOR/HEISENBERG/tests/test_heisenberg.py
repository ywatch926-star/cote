#!/usr/bin/env python3
"""Tests HEISENBERG — sous-frégate Caviar (F03_PICTOR).

Exécution : python3 F03_PICTOR/HEISENBERG/tests/test_heisenberg.py
Aucun MP4 requis : les analyses lourdes (ffmpeg/whisper) sont mockées.
"""
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

HB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HB))
sys.path.insert(0, str(HB.parents[1] / "F00_INGEST" / "CODEBASE"))

import heisenberg as hb  # noqa: E402
import caviar  # noqa: E402


def _fake_probe(**overrides):
    base = {"codec": "h264", "width": 1080, "height": 1920,
            "duration_sec": 30.0, "has_audio": True}
    base.update(overrides)
    return base


def _fake_analysis(silences=1, climaxes=None, speech_ratio=0.85, whisper_ok=True):
    n = silences
    return {
        "silences": [{"start": 10.0 + i, "end": 10.5 + i, "duration_sec": 0.5} for i in range(n)],
        "silence_count": n,
        "speech_ratio": speech_ratio,
        "trim_proposals": [{"cut_at_sec": 10.5, "removes_sec": 0.5, "kind": "jump_cut",
                            "status": "PROPOSAL"}] * n,
        "rms_peak_clusters": [{"peak_sec": c} for c in (climaxes or [])],
        "climax_proposals": list(climaxes or []),
        "whisper": ({"available": True, "model": "base/cpu-int8", "word_count": 90,
                     "punchline_proposal_sec": 21.4, "strong_punctuation_ends": [21.4]}
                    if whisper_ok else {"available": False, "reason": "indisponible"}),
    }


class TestBudget(unittest.TestCase):
    """Le Budget d'Attention — la frégate dépense avant d'écrire."""

    def test_budget_vide(self):
        b = hb.compute_budget({}, silences_count=0, duration_sec=30.0)
        self.assertEqual(b["spend_units"], 0)
        self.assertEqual(b["breathing_units"], 100)
        self.assertTrue(b["spend_ok"])

    def test_pack_conforme_dans_le_budget(self):
        narrative = {"broll": [{}, {}, {}], "is_climax": [14.2],
                     "zooms": [{}, {}, {}, {}]}
        b = hb.compute_budget(narrative, silences_count=8, duration_sec=30.0)
        # 3*12 + 1*8 + 4*6 + 8*1 = 76 → dépensé mais caps respectés
        self.assertEqual(b["spend_units"], 76)
        self.assertFalse(b["spend_ok"], "> 55 u doit être refusé")
        self.assertTrue(all(c["ok"] for c in b["caps"].values()))

    def test_mix_caviar_moderne(self):
        narrative = {"broll": [{}], "is_climax": [14.2, 27.8], "zooms": [{}, {}]}
        b = hb.compute_budget(narrative, silences_count=3, duration_sec=30.0)
        # 12 + 16 + 12 + 3 = 43 u ≤ 55 → OK, 57 u de respiration
        self.assertEqual(b["spend_units"], 43)
        self.assertTrue(b["spend_ok"])
        self.assertEqual(b["breathing_units"], 57)

    def test_caps_broll(self):
        b = hb.compute_budget({"broll": [{}, {}, {}, {}]}, 0, 30.0)
        self.assertFalse(b["caps"]["broll"]["ok"])
        b2 = hb.compute_budget({"broll": [{}, {}, {}]}, 0, 30.0)
        self.assertTrue(b2["caps"]["broll"]["ok"])

    def test_caps_jumpcut(self):
        b = hb.compute_budget({}, silences_count=9, duration_sec=30.0)
        self.assertFalse(b["caps"]["jumpcut"]["ok"])
        self.assertEqual(b["caps"]["jumpcut"]["max"], 8)


class TestVerdict(unittest.TestCase):
    """Verdicts d'entrée et refus documenté (segment mauvais)."""

    def test_refus_trop_de_silences(self):
        with mock.patch.object(hb, "probe", return_value=_fake_probe()), \
             mock.patch.object(hb, "_director") as d:
            d.return_value.analyze_clip.return_value = _fake_analysis(silences=9)
            m = hb.build_caviar_manifest(Path("fake.mp4"))
        self.assertEqual(m["verdict"], "REFUSED")
        self.assertIn("segment mauvais", m["refusal_reason"])
        self.assertEqual(m["proposals"], {})

    def test_verdict_ok(self):
        with mock.patch.object(hb, "probe", return_value=_fake_probe()), \
             mock.patch.object(hb, "_director") as d:
            d.return_value.analyze_clip.return_value = _fake_analysis(silences=2, climaxes=[14.2])
            m = hb.build_caviar_manifest(Path("fake.mp4"))
        self.assertEqual(m["verdict"], "OK")
        self.assertEqual(m["analysis"]["silence_count"], 2)
        self.assertEqual(m["analysis"]["climax_candidates"], [14.2])

    def test_verdict_blocked_sans_audio(self):
        with mock.patch.object(hb, "probe", return_value=_fake_probe(has_audio=False)):
            m = hb.build_caviar_manifest(Path("fake.mp4"))
        self.assertEqual(m["verdict"], "BLOCKED")
        self.assertFalse(m["entry_gate"]["ok"])

    def test_verdict_blocked_mauvais_codec(self):
        with mock.patch.object(hb, "probe", return_value=_fake_probe(codec="mpeg2video")):
            m = hb.build_caviar_manifest(Path("fake.mp4"))
        self.assertEqual(m["verdict"], "BLOCKED")

    def test_propositions_structure(self):
        with mock.patch.object(hb, "probe", return_value=_fake_probe()), \
             mock.patch.object(hb, "_director") as d:
            d.return_value.analyze_clip.return_value = _fake_analysis(silences=1, climaxes=[14.2])
            m = hb.build_caviar_manifest(Path("fake.mp4"))
        p = m["proposals"]
        self.assertEqual(len(p["jump_cut_proposals"]), 1)
        self.assertEqual(p["jump_cut_proposals"][0]["kind"], "jump_cut")
        self.assertEqual(len(p["smash_audio_proposals"]), 1)
        self.assertEqual(p["smash_audio_proposals"][0]["at_sec"], 14.2)
        self.assertEqual(p["smash_audio_proposals"][0]["duck_db"], -12)
        # Pas de flash sans B-roll demandé (anti-stroboscope)
        self.assertEqual(p["flash_proposals"], [])
        self.assertEqual(p["broll_proposals"], [])
        self.assertTrue(p["punchline"]["silence_before_punchline"])

    def test_manifeste_est_advisory(self):
        with mock.patch.object(hb, "probe", return_value=_fake_probe()), \
             mock.patch.object(hb, "_director") as d:
            d.return_value.analyze_clip.return_value = _fake_analysis()
            m = hb.build_caviar_manifest(Path("fake.mp4"))
        joined = json.dumps(m, ensure_ascii=False)
        self.assertIn("PROPOSITIONS", joined)
        self.assertIn("perturabo", m["doctrine"])
        self.assertIn("warsmith", m["doctrine"])


class TestBrollNumerote(unittest.TestCase):
    """Le contrat : PERTURABO donne un numéro, jamais le fichier."""

    def test_resolution_numero(self):
        r = hb.resolve_broll_number(1)
        self.assertEqual(r["broll_number"], 1)
        self.assertEqual(r["asset_ref"], "broll#1")
        self.assertTrue(r["entry_flash"])
        self.assertIn("sfx", r)

    def test_numero_inconnu(self):
        with self.assertRaises(KeyError):
            hb.resolve_broll_number(999)

    def test_ordre_langage_naturel(self):
        self.assertEqual(hb.parse_broll_order("met le numéro 1"), [1])
        self.assertEqual(hb.parse_broll_order("numeros 1 et 3"), [1, 3])
        self.assertEqual(hb.parse_broll_order(""), [])

    def test_emotion_vers_numeros(self):
        nums = hb.suggest_broll_by_emotion("moqueur")
        self.assertIn(1, nums)
        self.assertIn(4, nums)
        self.assertEqual(hb.suggest_broll_by_emotion("inconnu_total"), [])

    def test_registre_ne_expose_pas_de_chemin_dans_la_reponse(self):
        r = hb.resolve_broll_number(2)
        self.assertNotIn("file", r)
        self.assertNotIn(".mp4", json.dumps(r))


class TestPackChunk(unittest.TestCase):
    """Le chunk PERTURABO — optionnel et rétrocompatible v1."""

    def test_chunk_structure(self):
        chunk = hb.emit_pack_chunk(HB / "OUT" / "caviar_manifest_fake.mp4.json") \
            if (HB / "OUT" / "caviar_manifest_fake.mp4.json").exists() else None
        if chunk is None:
            manifest = {
                "analysis": {"climax_candidates": [14.2]},
                "proposals": {"jump_cut_proposals": [{"cut_at_sec": 10.5}],
                              "smash_audio_proposals": [], "punchline": {"at_sec": 21.4}},
            }
            with mock.patch.object(hb, "load_registry", return_value={"clips": {"1": {}, "4": {}}}):
                with mock.patch.object(Path, "read_text", return_value=json.dumps(manifest)):
                    chunk = hb.emit_pack_chunk(Path("x.json"))
        self.assertEqual(chunk["origin"], "HEISENBERG")
        self.assertIn("optionnel", chunk["note"])
        self.assertIn("is_climax_proposals", chunk["narrative"])
        self.assertIn("broll_available_numbers", chunk)


class TestLedger(unittest.TestCase):
    def test_ledger_write_roundtrip(self):
        with mock.patch.object(hb, "HEISENBERG_ROOT", HB):
            hb.ledger_write({"at": "t", "kind": "test"}, kind="gate")
            data = json.loads((HB / "LEDGER" / "gate_history.json").read_text())
            self.assertTrue(any(e.get("kind") == "test" for e in data["entries"]))
            # nettoyage
            data["entries"] = [e for e in data["entries"] if e.get("kind") != "test"]
            (HB / "LEDGER" / "gate_history.json").write_text(json.dumps(data, indent=2))


class TestPortePCavInchangee(unittest.TestCase):
    """La porte P-CAV du bras armé doit rester verte (non-régression Groupe 1)."""

    def test_bypass_v1(self):
        pack = {"montage_instructions": {"segment": {}}}
        ok, errs = caviar.gate_pcav_budgets(pack)
        self.assertTrue(ok and not errs)

    def test_budget_conforme_passe(self):
        pack = {"montage_instructions": {
            "mode": "pur", "segment": {},
            "narrative": {"hook_type": "reframe", "is_climax": [14.2], "resolution_at": 24.0,
                          "energy_curve": ["rise", "peak", "fall"]},
            "zooms": [{"moment_frame": 430, "white_flash": True}],
            "sfx_list": [{"type": "impact", "moment_frame": 430}],
            "broll": [{"asset_file": "broll/x.png", "start_sec": 8.5, "duration_frames": 36,
                       "sfx": "impact", "entry_flash": True}],
        }}
        ok, errs = caviar.gate_pcav_budgets(pack, expected_duration=30.0)
        self.assertTrue(ok, errs)


if __name__ == "__main__":
    unittest.main(verbosity=2)
