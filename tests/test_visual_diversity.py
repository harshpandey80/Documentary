import unittest
from pathlib import Path
import tempfile
import shutil
from docstudio.vimax_director import (
    ViMaxDirector,
    ARCHETYPE_AI_RECREATION,
    ARCHETYPE_INFOGRAPHIC,
    ARCHETYPE_EVIDENCE,
    ARCHETYPE_ATMOSPHERIC_STOCK,
)
from docstudio.broll_matcher import BRollMatcher

class TestVisualDiversity(unittest.TestCase):
    def test_vimax_archetype_classification(self):
        director = ViMaxDirector(topic="The Bermuda Triangle")

        # 1. Cold Hook should be high-impact AI recreation
        hook_scene = {
            "scene_id": "act1_s1_sub0",
            "narration": "Mayday! Our compasses are spinning completely wild!",
            "broll_keywords": ["cockpit", "compass", "emergency"],
            "visual_prompt": "Vintage 1945 cockpit dials violently spinning out of control",
        }
        arch = director.classify_scene_archetype(hook_scene, is_cold_hook=True)
        self.assertEqual(arch, ARCHETYPE_AI_RECREATION)

        # 2. Map & Coordinates should be Infographic
        map_scene = {
            "scene_id": "act1_s2_sub1",
            "narration": "They vanished across the 500,000 square mile perimeter between Miami, Bermuda, and Puerto Rico.",
            "broll_keywords": ["bermuda", "map", "coordinates", "flight path"],
            "visual_prompt": "Tactical animated map tracing naval flight vectors",
        }
        arch_map = director.classify_scene_archetype(map_scene)
        self.assertEqual(arch_map, ARCHETYPE_INFOGRAPHIC)

        # 3. Classified document should be Forensic Evidence
        doc_scene = {
            "scene_id": "act3_s1_sub2",
            "narration": "The declassified naval board of inquiry inquiry report marked secret.",
            "broll_keywords": ["classified", "naval inquiry", "secret report"],
            "visual_prompt": "Redacted US Navy telegram and investigation dossier",
        }
        arch_doc = director.classify_scene_archetype(doc_scene)
        self.assertEqual(arch_doc, ARCHETYPE_EVIDENCE)

        # 4. Open ocean sunset should be Atmospheric Stock
        stock_scene = {
            "scene_id": "act3_s2_sub1",
            "narration": "Today, thousands of vessels navigate these open waters without incident.",
            "broll_keywords": ["open ocean", "sunset", "clouds passing"],
            "visual_prompt": "Calm tranquil ocean waters stretching to the horizon",
        }
        arch_stock = director.classify_scene_archetype(stock_scene)
        self.assertEqual(arch_stock, ARCHETYPE_ATMOSPHERIC_STOCK)

    def test_visual_storyboard_plan_generation(self):
        director = ViMaxDirector(topic="Flight 19 Vanishing")
        sample_shots = [
            {"scene_id": "s1", "duration": 2.2, "narration": "Five Navy bombers vanish mid-flight", "broll_keywords": ["cockpit", "flight 19"], "visual_prompt": "TBM Avenger flight formation"},
            {"scene_id": "s2", "duration": 2.4, "narration": "Disappearing from naval radar screens", "broll_keywords": ["radar", "map", "telemetry"], "visual_prompt": "Naval radar sweep showing blips fading"},
            {"scene_id": "s3", "duration": 2.1, "narration": "The declassified telegrams show zero wreckage", "broll_keywords": ["telegram", "classified"], "visual_prompt": "Navy telegram declassified stamp"},
            {"scene_id": "s4", "duration": 2.5, "narration": "Across the vast Atlantic expanse", "broll_keywords": ["open ocean", "waves"], "visual_prompt": "Vast empty Atlantic ocean swell"},
        ]

        plan = director.generate_visual_storyboard_plan(sample_shots)
        self.assertEqual(plan["total_shots"], 4)
        self.assertIn("diversity_stats", plan)
        self.assertIn("markdown_plan", plan)
        self.assertIn("| #1 |", plan["markdown_plan"])
        self.assertIn("COLD HOOK", plan["markdown_plan"])

    def test_broll_matcher_accepts_archetype(self):
        temp_dir = Path(tempfile.mkdtemp())
        try:
            matcher = BRollMatcher(cache_dir=temp_dir)
            mock_file = temp_dir / "test_scene.mp4"
            mock_file.write_bytes(b"0" * 25000)
            
            result = matcher.acquire_visual_for_scene(
                scene_id="test_scene",
                keywords=["cockpit"],
                visual_prompt="Cockpit view",
                topic="Aviation",
                duration=2.0,
                archetype=ARCHETYPE_AI_RECREATION,
            )
            self.assertEqual(result, mock_file)
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

if __name__ == "__main__":
    unittest.main()
