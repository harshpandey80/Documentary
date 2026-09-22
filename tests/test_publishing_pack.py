"""Tests for Phase 10 – PublishingPackGenerator"""

import tempfile
import unittest
from pathlib import Path


MOCK_SCRIPT = {
    "hook": "A sound no human has ever heard echoed from 10,928 metres below the ocean.",
    "scenes": [
        {"scene_id": "s01", "scene_type": "HOOK",  "duration": 8.0,
         "narration_text": "It came from the deepest place on Earth."},
        {"scene_id": "s02", "scene_type": "BODY",  "duration": 12.0,
         "narration_text": "The Mariana Trench, 2,550 km long, swallows Mount Everest."},
        {"scene_id": "s03", "scene_type": "CTA",   "duration": 6.0,
         "narration_text": "Like and subscribe to uncover the unsealed files."},
    ],
    "cta": "Like and subscribe to uncover the unsealed files.",
    "topic": "Mariana Trench",
}

MOCK_QC = {"status": "PASS", "hook_audit": {"score": 82}, "issues": []}


class TestPublishingPackGenerator(unittest.TestCase):

    def setUp(self):
        from docstudio.publishing_pack import PublishingPackGenerator
        self.gen = PublishingPackGenerator()
        self.tmp = tempfile.TemporaryDirectory()
        self.run_dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_generate_returns_dict(self):
        result = self.gen.generate(
            run_dir=self.run_dir,
            topic="Mariana Trench",
            script_data=MOCK_SCRIPT,
            qc_results=MOCK_QC,
        )
        self.assertIsInstance(result, dict)

    def test_all_required_keys_present(self):
        result = self.gen.generate(
            run_dir=self.run_dir,
            topic="Mariana Trench",
            script_data=MOCK_SCRIPT,
            qc_results=MOCK_QC,
        )
        required = {
            "title", "description", "tags", "chapters",
            "thumbnail_prompt", "shorts_title", "shorts_description",
        }
        self.assertTrue(required.issubset(result.keys()),
                        f"Missing keys: {required - result.keys()}")

    def test_title_not_empty(self):
        result = self.gen.generate(
            run_dir=self.run_dir,
            topic="Mariana Trench",
            script_data=MOCK_SCRIPT,
            qc_results=MOCK_QC,
        )
        self.assertTrue(len(result.get("title", "")) > 5)

    def test_description_contains_cta(self):
        result = self.gen.generate(
            run_dir=self.run_dir,
            topic="Mariana Trench",
            script_data=MOCK_SCRIPT,
            qc_results=MOCK_QC,
        )
        desc = result.get("description", "")
        self.assertIn("subscribe", desc.lower())

    def test_tags_is_list_of_strings(self):
        result = self.gen.generate(
            run_dir=self.run_dir,
            topic="Mariana Trench",
            script_data=MOCK_SCRIPT,
            qc_results=MOCK_QC,
        )
        tags = result.get("tags", [])
        self.assertIsInstance(tags, list)
        for t in tags:
            self.assertIsInstance(t, str)

    def test_tags_count_reasonable(self):
        result = self.gen.generate(
            run_dir=self.run_dir,
            topic="Mariana Trench",
            script_data=MOCK_SCRIPT,
            qc_results=MOCK_QC,
        )
        tags = result.get("tags", [])
        self.assertGreaterEqual(len(tags), 5)
        self.assertLessEqual(len(tags), 30,
                             "Too many tags – YouTube limit is 30")

    def test_chapters_match_scenes(self):
        result = self.gen.generate(
            run_dir=self.run_dir,
            topic="Mariana Trench",
            script_data=MOCK_SCRIPT,
            qc_results=MOCK_QC,
        )
        chapters = result.get("chapters", [])
        self.assertIsInstance(chapters, list)
        self.assertGreaterEqual(len(chapters), 1)

    def test_chapter_format_valid(self):
        """Each chapter must be a dict with 'time' and 'label' keys."""
        result = self.gen.generate(
            run_dir=self.run_dir,
            topic="Mariana Trench",
            script_data=MOCK_SCRIPT,
            qc_results=MOCK_QC,
        )
        for ch in result.get("chapters", []):
            self.assertIn("time", ch)
            self.assertIn("label", ch)

    def test_thumbnail_prompt_not_empty(self):
        result = self.gen.generate(
            run_dir=self.run_dir,
            topic="Mariana Trench",
            script_data=MOCK_SCRIPT,
            qc_results=MOCK_QC,
        )
        self.assertTrue(len(result.get("thumbnail_prompt", "")) > 20)

    def test_output_json_written_to_disk(self):
        """A publishing_pack.json file must appear in run_dir."""
        self.gen.generate(
            run_dir=self.run_dir,
            topic="Mariana Trench",
            script_data=MOCK_SCRIPT,
            qc_results=MOCK_QC,
        )
        out_file = self.run_dir / "publishing_pack.json"
        self.assertTrue(out_file.exists(), "publishing_pack.json not written to disk")

    def test_output_json_parsable(self):
        import json
        self.gen.generate(
            run_dir=self.run_dir,
            topic="Mariana Trench",
            script_data=MOCK_SCRIPT,
            qc_results=MOCK_QC,
        )
        out_file = self.run_dir / "publishing_pack.json"
        if out_file.exists():
            data = json.loads(out_file.read_text(encoding="utf-8"))
            self.assertIsInstance(data, dict)

    def test_shorts_title_under_100_chars(self):
        """YouTube Shorts titles must be ≤ 100 characters."""
        result = self.gen.generate(
            run_dir=self.run_dir,
            topic="Mariana Trench",
            script_data=MOCK_SCRIPT,
            qc_results=MOCK_QC,
        )
        title = result.get("shorts_title", "")
        self.assertLessEqual(len(title), 100,
                             f"Shorts title too long ({len(title)} chars)")

    def test_idempotent(self):
        """Calling generate twice must not raise and must return same keys."""
        r1 = self.gen.generate(
            run_dir=self.run_dir,
            topic="Mariana Trench",
            script_data=MOCK_SCRIPT,
            qc_results=MOCK_QC,
        )
        r2 = self.gen.generate(
            run_dir=self.run_dir,
            topic="Mariana Trench",
            script_data=MOCK_SCRIPT,
            qc_results=MOCK_QC,
        )
        self.assertEqual(r1.keys(), r2.keys())


if __name__ == "__main__":
    unittest.main()
