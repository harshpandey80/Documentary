import unittest
import tempfile
from pathlib import Path
from docstudio.project_config import (
    ProjectConfig,
    StyleProfile,
    load_project_config,
    save_project_config,
    create_default_project_yaml,
)
from docstudio.memory_guard import MemoryGuard, check_system_memory

class TestProjectConfig(unittest.TestCase):
    def test_default_config_creation_and_fields(self):
        cfg = ProjectConfig(topic="The Vela Incident", thesis="Secret nuclear test in 1979.")
        self.assertEqual(cfg.topic, "The Vela Incident")
        self.assertEqual(cfg.thesis, "Secret nuclear test in 1979.")
        self.assertEqual(cfg.aspect_ratio, "16:9")
        self.assertEqual(cfg.cut_length, 3.0)
        self.assertEqual(cfg.tts_engine, "voxcpm")
        self.assertEqual(cfg.width, 1920)
        self.assertEqual(cfg.height, 1080)
        self.assertAlmostEqual(cfg.target_cuts, 100) # 5m = 300s / 3.0s = 100 cuts
        self.assertFalse(cfg.is_short)

    def test_shorts_config(self):
        cfg = ProjectConfig(
            topic="Deep Ocean Mystery",
            thesis="Unexplained acoustic anomalies.",
            runtime="50s",
            aspect_ratio="9:16",
            cut_length=2.4,
        )
        self.assertTrue(cfg.is_short)
        self.assertEqual(cfg.width, 1080)
        self.assertEqual(cfg.height, 1920)
        self.assertEqual(cfg.target_cuts, 21) # ceil(50 / 2.4) = 21 cuts

    def test_yaml_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yaml_path = Path(tmpdir) / "project.yaml"
            cfg_orig = ProjectConfig(
                topic="Voyager Golden Record",
                thesis="Humanity's message across the interstellar medium.",
                runtime="8m",
                aspect_ratio="16:9",
                cut_length=3.0,
                tts_engine="draft",
            )
            save_project_config(cfg_orig, yaml_path)
            self.assertTrue(yaml_path.exists())

            loaded = load_project_config(yaml_path)
            self.assertEqual(loaded.topic, "Voyager Golden Record")
            self.assertEqual(loaded.runtime_seconds, 480.0)
            self.assertEqual(loaded.tts_engine, "draft")
            self.assertEqual(loaded.style_profile.accent_color, "#00FF66")

    def test_invalid_aspect_ratio_raises(self):
        with self.assertRaises(ValueError):
            ProjectConfig(topic="Test", thesis="Test", aspect_ratio="4:3")

    def test_invalid_cut_length_raises(self):
        with self.assertRaises(ValueError):
            ProjectConfig(topic="Test", thesis="Test", cut_length=0.2)

    def test_memory_guard_api(self):
        # Verify MemoryGuard can inspect system memory without crashing
        mem_info = MemoryGuard.get_memory_status()
        self.assertIn("total_gb", mem_info)
        self.assertIn("available_gb", mem_info)
        self.assertIn("percent_used", mem_info)
        self.assertGreater(mem_info["total_gb"], 1.0)

        # check_system_memory returns True or False without error
        status = check_system_memory(min_gb=1.0)
        self.assertIsInstance(status, bool)

if __name__ == "__main__":
    unittest.main()
