#!/usr/bin/env python3
"""Tests CAVIAR_GATE — Groupe 3 (double barrage rendu).

Exécution : python3 F03_PICTOR/HEISENBERG/tests/test_caviar_gate.py
Aucun MP4 requis — le gate est testé sur des manifestes synthétiques.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HB = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(HB))

import caviar_gate  # noqa: E402

BUDGET = json.loads((HB / "caviar_budget.json").read_text(encoding="utf-8"))
FPS = 30


def base_block(**overrides):
    block = {
        "enabled": True,
        "jump_cuts": [{"cut_at_sec": 10, "removes_sec": 0.6}],
        "punchins": [{"at_sec": 5, "scale_to": 1.06}],
        "brolls": [{"at_sec": 8, "numero": 1, "file": "broll/broll_01.mp4", "sfx": "impact"}],
        "smash_audio": [{"at_sec": 20, "duck_db": -12, "duration_sec": 0.8}],
    }
    block.update(overrides)
    return block


class TestCaviarGate(unittest.TestCase):
    def test_bloc_conforme_vert(self):
        errors = caviar_gate.check_caviar_block(base_block(), BUDGET, FPS, "pack")
        self.assertEqual(errors, [])

    def test_depense_excedentaire_rouge(self):
        # base 27u + 2 brolls de plus (24u) + 3 punchins de plus (18u) = 69u > 55u
        block = base_block(
            brolls=[{"at_sec": s, "file": "a.mp4"} for s in (3, 9, 15)],
            punchins=[{"at_sec": s} for s in (4, 6, 12, 18)],
        )
        errors = caviar_gate.check_caviar_block(block, BUDGET, FPS, "pack")
        self.assertTrue(any("dépense 69u" in e for e in errors), errors)

    def test_cap_broll_rouge(self):
        block = base_block(brolls=[{"at_sec": s, "file": "a.mp4"} for s in (3, 9, 15, 22)])
        errors = caviar_gate.check_caviar_block(block, BUDGET, FPS, "pack")
        self.assertTrue(any("cap broll dépassé : 4 > 3" in e for e in errors), errors)

    def test_broll_sans_fichier_rouge(self):
        block = base_block(brolls=[{"at_sec": 8, "numero": 7}])
        errors = caviar_gate.check_caviar_block(block, BUDGET, FPS, "pack")
        self.assertTrue(any("sans fichier résolu" in e for e in errors), errors)

    def test_flash_hors_entree_broll_rouge(self):
        block = base_block(flashes=[{"at_sec": 25}])  # aucun B-roll à 25 s
        errors = caviar_gate.check_caviar_block(block, BUDGET, FPS, "pack")
        self.assertTrue(any("flash hors entrée" in e for e in errors), errors)

    def test_flash_a_l_entree_broll_vert(self):
        block = base_block(flashes=[{"at_sec": 8}])  # = frame du B-roll
        errors = caviar_gate.check_caviar_block(block, BUDGET, FPS, "pack")
        self.assertEqual(errors, [])

    def test_sfx_hors_entree_broll_rouge(self):
        block = base_block(sfx=[{"at_sec": 14}])
        errors = caviar_gate.check_caviar_block(block, BUDGET, FPS, "pack")
        self.assertTrue(any("SFX hors entrée" in e for e in errors), errors)

    def test_sfx_a_l_entree_broll_vert(self):
        block = base_block(sfx=[{"at_sec": 8}])
        errors = caviar_gate.check_caviar_block(block, BUDGET, FPS, "pack")
        self.assertEqual(errors, [])

    def test_deux_events_forts_chevauchent_rouge(self):
        block = base_block(punchins=[{"at_sec": 8.02}])  # broll à 8 s + punchin à 8,02 s
        errors = caviar_gate.check_caviar_block(block, BUDGET, FPS, "pack")
        self.assertTrue(any("deux événements forts" in e for e in errors), errors)

    def test_jump_cuts_ne_comptent_pas_comme_events_forts(self):
        block = base_block(punchins=[{"at_sec": 10}])  # punchin au point de coupe : OK
        errors = caviar_gate.check_caviar_block(block, BUDGET, FPS, "pack")
        self.assertEqual(errors, [])


REAL_PACK_PATH = HB / "tests" / "pack_voxc2_blur_v2.json"


class TestPackV2(unittest.TestCase):
    """Portes v2 (note PERTURABO 2026-09-15) — pack réel voxc-2 en fixture."""

    def setUp(self):
        self.pack = json.loads(REAL_PACK_PATH.read_text(encoding="utf-8")) if REAL_PACK_PATH.exists() else None

    def test_pack_reel_conforme(self):
        if not self.pack: self.skipTest("pack réel absent")
        self.assertEqual(caviar_gate.check_pack_v2(self.pack, BUDGET), [])

    def test_review_no_go_rouge(self):
        if not self.pack: self.skipTest("pack réel absent")
        pack = {**self.pack, "review": {"gate_state": "PENDING", "status": "DRAFT"}}
        errors = caviar_gate.check_pack_v2(pack, BUDGET)
        self.assertTrue(any("review non exécutable" in e for e in errors), errors)

    def test_f06_mode_incoherent_rouge(self):
        if not self.pack: self.skipTest("pack réel absent")
        import copy
        pack = copy.deepcopy(self.pack)
        pack["chain_of_custody"]["f06_gate"]["mode"] = "legacy v2.1"
        errors = caviar_gate.check_pack_v2(pack, BUDGET)
        self.assertTrue(any("≠ caviar_bound" in e for e in errors), errors)

    def test_hierarchie_violee_rouge(self):
        if not self.pack: self.skipTest("pack réel absent")
        import copy
        pack = copy.deepcopy(self.pack)
        pack["montage_instructions"]["body"]["cuts"] = [{"cut_at_sec": 5}]
        pack["montage_instructions"]["body"]["zooms"] = [{"moment_sec": 6}]
        errors = caviar_gate.check_pack_v2(pack, BUDGET)
        self.assertTrue(any("hiérarchie violée" in e for e in errors), errors)

    def test_checksum_divergents_rouge(self):
        if not self.pack: self.skipTest("pack réel absent")
        import copy
        pack = copy.deepcopy(self.pack)
        pack["chain_of_custody"]["f00d_partition"]["checksum16"] = "deadbeefdeadbeef"
        errors = caviar_gate.check_pack_v2(pack, BUDGET)
        self.assertTrue(any("checksum16 divergents" in e for e in errors), errors)

    def test_event_apres_resolution_rouge(self):
        if not self.pack: self.skipTest("pack réel absent")
        import copy
        pack = copy.deepcopy(self.pack)
        pack["caviar_partition"]["resolution_at"] = 20.0
        # smash réel à 28.216 s > 20 s → rouge
        errors = caviar_gate.check_pack_v2(pack, BUDGET)
        self.assertTrue(any("après resolution_at" in e for e in errors), errors)

    def test_budget_mensonger_rouge(self):
        if not self.pack: self.skipTest("pack réel absent")
        import copy
        pack = copy.deepcopy(self.pack)
        pack["caviar_partition"]["budget_state"]["spent_units"] = 10  # réel : 32u
        errors = caviar_gate.check_pack_v2(pack, BUDGET)
        self.assertTrue(any("≠ recalcul" in e for e in errors), errors)

    def test_caps_respected_false_rouge(self):
        if not self.pack: self.skipTest("pack réel absent")
        import copy
        pack = copy.deepcopy(self.pack)
        pack["caviar_partition"]["budget_state"]["caps_respected"] = False
        errors = caviar_gate.check_pack_v2(pack, BUDGET)
        self.assertTrue(any("caps_respected=false" in e for e in errors), errors)


class TestCaviarGateCLI(unittest.TestCase):
    def run_gate(self, manifest: dict) -> int:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(manifest, f)
            path = f.name
        try:
            return subprocess.run(
                [sys.executable, str(HB / "caviar_gate.py"), "--manifest", path],
                capture_output=True, text=True,
            ).returncode
        finally:
            Path(path).unlink(missing_ok=True)

    def test_sans_bloc_caviar_gate_neutre(self):
        self.assertEqual(self.run_gate({"schema_version": "dev10.pur.v1", "entries": []}), 0)

    def test_bloc_desactive_gate_neutre(self):
        self.assertEqual(self.run_gate({"caviar": {"enabled": False}}), 0)

    def test_multi_entrees_budget_par_entree(self):
        # 2 entrées × 2 brolls chacune : conforme PAR entrée (l'agrégat brut
        # compterait 4 brolls et déclencherait le cap à tort).
        manifest = {
            "fps": 30,
            "entries": [
                {"angle_id": "A01", "caviar": base_block()},
                {"angle_id": "A02", "caviar": base_block()},
            ],
        }
        self.assertEqual(self.run_gate(manifest), 0)

    def test_multi_entrees_une_entree_hors_budget_rouge(self):
        bad = base_block(brolls=[{"at_sec": s, "file": "a.mp4"} for s in (3, 9, 15, 22)])
        manifest = {"fps": 30, "entries": [{"angle_id": "A01", "caviar": base_block()},
                                           {"angle_id": "A02", "caviar": bad}]}
        self.assertEqual(self.run_gate(manifest), 1)

    def run_gate_with_pack(self, pack: dict) -> int:
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump({"fps": 30}, f)
            mpath = f.name
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
            json.dump(pack, f)
            ppath = f.name
        try:
            return subprocess.run(
                [sys.executable, str(HB / "caviar_gate.py"), "--manifest", mpath, "--pack-v2", ppath],
                capture_output=True, text=True,
            ).returncode
        finally:
            Path(mpath).unlink(missing_ok=True)
            Path(ppath).unlink(missing_ok=True)

    def test_cli_pack_reel_vert(self):
        if not REAL_PACK_PATH.exists(): self.skipTest("pack réel absent")
        self.assertEqual(self.run_gate_with_pack(json.loads(REAL_PACK_PATH.read_text(encoding="utf-8"))), 0)

    def test_cli_pack_draft_rouge(self):
        if not REAL_PACK_PATH.exists(): self.skipTest("pack réel absent")
        import copy
        pack = copy.deepcopy(json.loads(REAL_PACK_PATH.read_text(encoding="utf-8")))
        pack["review"] = {"gate_state": "PENDING", "status": "DRAFT"}
        self.assertEqual(self.run_gate_with_pack(pack), 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
