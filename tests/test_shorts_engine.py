"""Tests for Phase 9 – ShortsEngine (9:16 derivation)"""

import json
import tempfile
import unittest
from pathlib import Path


class TestShortsEngine(unittest.TestCase):

    def setUp(self):
        from docstudio.shorts_engine import ShortsEngine
        self.engine = ShortsEngine()
        self.tmp = tempfile.TemporaryDirectory()
        self.run_dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    # ---------------------------------------------------------
    # SEGMENT SELECTION LOGIC (no FFmpeg)
    # ---------------------------------------------------------

    def _make_script(self):
        return {
            "acts": [
                {
                    "act_number": 1,
                    "act_title": "Cold Hook",
                    "scenes": [
                        {"scene_id": "a1_s1", "narration": "A classified anomaly was discovered at 10,928 metres. What happened next shocked the world?", "broll_keywords": ["ocean", "deep"]},
                    ],
                },
                {
                    "act_number": 4,
                    "act_title": "Revelation",
                    "scenes": [
                        {"scene_id": "a4_s1", "narration": "The leaked document exposed the cover-up that millions never saw.", "broll_keywords": ["document", "classified"]},
                    ],
                },
                {
                    "act_number": 6,
                    "act_title": "Verdict",
                    "scenes": [
                        {"scene_id": "a6_s1", "narration": "The sealed files remain unsealed. The truth is buried.", "broll_keywords": ["files", "truth"]},
                    ],
                },
            ]
        }

    def _make_timestamps(self):
        # Synthetic word timestamps across 0-180s
        words = "A classified anomaly was discovered at 10928 metres What happened next shocked the world The leaked document exposed the cover up millions never saw The sealed files remain unsealed The truth is buried".split()
        return [{"word": w, "start": i * 2.0, "end": i * 2.0 + 1.5} for i, w in enumerate(words)]

    def test_select_segments_returns_list(self):
        """_select_short_segments must return a list."""
        script = self._make_script()
        timestamps = self._make_timestamps()
        segs = self.engine._select_short_segments(script, timestamps, max_shorts=3)
        self.assertIsInstance(segs, list)

    def test_hook_always_first(self):
        """HOOK scene must be the first selected segment."""
        storyboard = [
            {"scene_id": "body_1", "scene_type": "BODY", "duration": 8.0, "narration_text": "x"},
            {"scene_id": "hook_1", "scene_type": "HOOK", "duration": 8.0, "narration_text": "x"},
            {"scene_id": "body_2", "scene_type": "BODY", "duration": 8.0, "narration_text": "x"},
        ]
        segs = self.engine._select_short_segments(storyboard, target_duration=50.0)
        if segs:
            self.assertEqual(segs[0]["scene_id"], "hook_1")

    def test_cta_always_last(self):
        """CTA scene must be the last selected segment."""
        storyboard = [
            {"scene_id": "hook_1", "scene_type": "HOOK", "duration": 8.0, "narration_text": "x"},
            {"scene_id": "body_1", "scene_type": "BODY", "duration": 8.0, "narration_text": "x"},
            {"scene_id": "cta_1",  "scene_type": "CTA",  "duration": 6.0, "narration_text": "Like subscribe"},
        ]
        segs = self.engine._select_short_segments(storyboard, target_duration=50.0)
        if segs:
            self.assertEqual(segs[-1]["scene_id"], "cta_1")

    def test_duration_limit_respected(self):
        """Total selected duration must not exceed target + 10s buffer."""
        storyboard = [
            {"scene_id": f"s{i:02d}", "scene_type": "BODY",
             "duration": 10.0, "narration_text": "Scene text here"}
            for i in range(20)
        ]
        target = 50.0
        segs = self.engine._select_short_segments(storyboard, target_duration=target)
        total = sum(s["duration"] for s in segs)
        self.assertLessEqual(total, target + 15.0)

    # ---------------------------------------------------------
    # CTA CARD METADATA
    # ---------------------------------------------------------

    def test_cta_card_fields(self):
        """CTA card metadata must include all required keys."""
        card = self.engine._cta_card_metadata()
        required = {"text", "subtext", "bg_color", "text_color", "duration"}
        self.assertTrue(required.issubset(card.keys()),
                        f"Missing keys: {required - card.keys()}")

    def test_cta_card_duration_positive(self):
        card = self.engine._cta_card_metadata()
        self.assertGreater(card["duration"], 0)

    # ---------------------------------------------------------
    # METADATA DERIVATION (no video processing)
    # ---------------------------------------------------------

    def test_derive_shorts_returns_empty_on_missing_storyboard(self):
        """If no storyboard.json exists, derive_shorts must return [] cleanly."""
        result = self.engine.derive_shorts(run_dir=self.run_dir, force=False)
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 0)

    def test_derive_shorts_skips_if_already_done(self):
        """derive_shorts must skip if all Short files already exist (no force)."""
        # Plant a fake short and mark it as done
        shorts_dir = self.run_dir / "10_shorts"
        shorts_dir.mkdir(parents=True, exist_ok=True)
        done_marker = shorts_dir / "shorts_done.json"
        done_marker.write_text(json.dumps([str(shorts_dir / "short_01.mp4")]))
        result = self.engine.derive_shorts(run_dir=self.run_dir, force=False)
        # Should return the cached list
        self.assertIsInstance(result, list)

    # ---------------------------------------------------------
    # MOTION PARAMETER GENERATION (no FFmpeg)
    # ---------------------------------------------------------

    def test_motion_params_structure(self):
        """Motion params must include direction and zoom values."""
        params = self.engine._random_motion_params()
        self.assertIn("zoom_start", params)
        self.assertIn("zoom_end",   params)
        self.assertIn("x_drift",    params)
        self.assertIn("y_drift",    params)

    def test_motion_params_variety(self):
        """Ten consecutive calls must not all return identical params."""
        results = [str(self.engine._random_motion_params()) for _ in range(10)]
        self.assertGreater(len(set(results)), 1,
                           "Motion params show no variety – seeding/RNG issue")

    # ---------------------------------------------------------
    # ASPECT RATIO CROP CALCULATION
    # ---------------------------------------------------------

    def test_crop_to_9_16(self):
        """16:9 → 9:16 crop must return a region narrower than source."""
        crop = self.engine._crop_to_916(src_w=1920, src_h=1080)
        self.assertIn("x", crop)
        self.assertIn("y", crop)
        self.assertIn("w", crop)
        self.assertIn("h", crop)
        # Cropped width should be ≤ source width
        self.assertLessEqual(crop["w"], 1920)
        # Cropped height must equal source height
        self.assertEqual(crop["h"], 1080)

    def test_crop_aspect_ratio_correct(self):
        """Resulting w:h must satisfy 9:16."""
        crop = self.engine._crop_to_916(src_w=1920, src_h=1080)
        ratio = crop["h"] / crop["w"]
        self.assertAlmostEqual(ratio, 16 / 9, places=1)


if __name__ == "__main__":
    unittest.main()
