import importlib.util
import json
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("f00_ingest", ROOT / "F00_INGEST/CODEBASE/f00_ingest.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ManifestTests(unittest.TestCase):
    def test_target_duration_and_virtual_timeline(self):
        data = MODULE.build_manifest(
            Path("source.mp4"),
            {
                "target_duration_seconds": 10,
                "cut_interval_frames": 7,
                "candidate_count": 100,
                "shuffle_seed": 2026,
            },
            {"width": 1920, "height": 1080, "fps": 30.0, "duration_seconds": 30.0, "total_frames": 900},
        )
        self.assertEqual(data["total_frames"], 300)
        self.assertEqual(len(data["sequences"]), 43)
        self.assertEqual(data["audio_policy"].split(";")[0], "source video audio ignored")
        self.assertEqual(data["sequences"][0]["timeline_start_frame"], 0)
        self.assertEqual(data["sequences"][-1]["timeline_end_frame"], 299)
        self.assertTrue(all("file" not in item for item in data["sequences"]))


if __name__ == "__main__":
    unittest.main()
