"""
Test suite verifying 100% narration-grounded AI visual generation.
Ensures repetitive procedural templates (dossier overlays, generic maps)
are completely bypassed and every cut gets an authentic, photographic AI visual
prompted directly from the narrator's line.
"""

from pathlib import Path
import tempfile
import unittest

from docstudio.broll_matcher import BRollMatcher
from docstudio.project_config import ProjectConfig
from docstudio.usage_registry import UsageRegistry


class TestAIVisualGrounding(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.cache_dir = Path(self.tmp.name) / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.matcher = BRollMatcher(cache_dir=self.cache_dir, all_ai_visuals=True)

    def tearDown(self):
        self.tmp.cleanup()

    def test_default_config_has_all_ai_visuals(self):
        cfg = ProjectConfig(topic="The Antwerp Heist", thesis="The heist was flawless.")
        self.assertTrue(cfg.all_ai_visuals)

    def test_forensic_document_prompt_grounded_in_narration(self):
        narration = "Investigators discovered a half-eaten salami sandwich and empty velvet jewel boxes inside vault 109."
        prompt = self.matcher._build_narration_grounded_ai_prompt(
            narration=narration,
            visual_prompt="forensic evidence inside vault",
            keywords=["sandwich", "vault"],
            topic="Antwerp Diamond Heist",
            archetype="FORENSIC_EVIDENCE",
        )
        self.assertIn("half-eaten salami sandwich", prompt)
        self.assertIn("forensic", prompt.lower())
        self.assertIn("photorealistic 8k", prompt.lower())

    def test_map_route_prompt_grounded_in_narration(self):
        narration = "Satellite telemetry traced the black Peugeot fleeing south on the E19 highway toward Brussels."
        prompt = self.matcher._build_narration_grounded_ai_prompt(
            narration=narration,
            visual_prompt="satellite car tracking",
            keywords=["satellite", "highway"],
            topic="Antwerp Diamond Heist",
            archetype="INFOGRAPHIC_CODE2VIDEO",
        )
        self.assertIn("E19 highway", prompt)
        self.assertIn("satellite", prompt.lower())
        self.assertIn("photorealistic 8k", prompt.lower())

    def test_usage_registry_allows_100_percent_ai(self):
        reg = UsageRegistry(run_dir=self.cache_dir, max_reuse=2, allow_all_ai=True)
        for i in range(5):
            clip = self.cache_dir / f"ai_clip_{i}.mp4"
            clip.write_bytes(b"dummy")
            reg.register(clip, f"s{i:03d}", "AI_CINEMATIC_RECREATION")
        violations = reg.audit_diversity(total_shots=5)
        self.assertEqual(violations, [])


if __name__ == "__main__":
    unittest.main()
