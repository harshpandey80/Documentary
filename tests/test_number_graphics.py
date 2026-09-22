"""
Tests for Phase 8 – NumberGraphicsEngine & Deterministic Overlay Templates
"""

import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from docstudio.number_graphics import (
    GraphicType,
    HumanAnchor,
    NumberGraphicDetector,
    NumberGraphicsEngine,
    align_graphics_with_narration,
    get_nearest_human_anchor,
    normalize_to_meters,
)


class TestNumberGraphicsDetection(unittest.TestCase):
    """Verifies non-LLM detection rules and human anchor library."""

    def setUp(self):
        self.detector = NumberGraphicDetector()

    def test_percentage_classified_as_ring(self):
        res = self.detector.detect_from_text("The British Empire controlled 24% of the global land area.")
        self.assertTrue(any(g.graphic_type == GraphicType.RING and g.numeric_value == 24.0 for g in res))

    def test_four_digit_year_classified_as_timeline(self):
        res = self.detector.detect_from_text("In 1066 the Norman fleet landed at Hastings.")
        self.assertTrue(any(g.graphic_type == GraphicType.TIMELINE and g.numeric_value == 1066.0 for g in res))

    def test_dimension_classified_as_gauge(self):
        res = self.detector.detect_from_text("The abyss plummets 10,984 meters into darkness.")
        gauge_graphics = [g for g in res if g.graphic_type == GraphicType.GAUGE]
        self.assertTrue(len(gauge_graphics) > 0)
        self.assertEqual(gauge_graphics[0].numeric_value, 10984.0)
        self.assertIn("meter", gauge_graphics[0].unit.lower())

    def test_comparison_classified_as_comparison(self):
        res = self.detector.detect_from_text("The blast pressure was 5 times greater than standard depth charges.")
        self.assertTrue(any(g.graphic_type == GraphicType.COMPARISON and g.numeric_value == 5.0 for g in res))

    def test_fraction_classified_as_dot_grid(self):
        res = self.detector.detect_from_text("Nearly 1 in 5 people on Earth lived under the crown.")
        self.assertTrue(any(g.graphic_type == GraphicType.DOT_GRID and g.numeric_value == 5.0 for g in res))

    def test_money_classified_as_countup(self):
        res = self.detector.detect_from_text("The expedition cost over $25 billion in modern funding.")
        self.assertTrue(any(g.graphic_type == GraphicType.COUNTUP and g.numeric_value == 25e9 for g in res))

    def test_human_anchor_selection_nearest_scale(self):
        """Must pick nearest hand-checked scale in log-distance without hallucinating."""
        # 10,984 meters should anchor near Hadal Trench
        anchor = get_nearest_human_anchor(10984.0, "meters")
        self.assertIsNotNone(anchor)
        self.assertIn("Hadal Trench", anchor.name)

        # 300 meters should anchor near Eiffel Tower
        anchor_tower = get_nearest_human_anchor(300.0, "meters")
        self.assertIsNotNone(anchor_tower)
        self.assertIn("Eiffel Tower", anchor_tower.name)

        # $20 billion should anchor near NASA Annual Budget
        anchor_money = get_nearest_human_anchor(20e9, "$")
        self.assertIsNotNone(anchor_money)
        self.assertIn("NASA", anchor_money.name)

    def test_claims_file_detection(self):
        """Direct reading from claims.csv if it exists."""
        claims_p = Path("claims.csv")
        if claims_p.exists():
            graphics = self.detector.detect_from_claims_file(claims_p)
            self.assertGreater(len(graphics), 0)
            # Verify various types exist
            types = {g.graphic_type for g in graphics}
            self.assertTrue(GraphicType.GAUGE in types or GraphicType.TIMELINE in types or GraphicType.RING in types)


class TestTimingAndPacing(unittest.TestCase):
    """Verifies word-timestamp alignment, 15s pacing rule, and landing at spoken word."""

    def test_pacing_filter_enforces_15s_gap(self):
        detector = NumberGraphicDetector()
        g1 = detector.detect_from_text("It was 24%")[0]
        g2 = detector.detect_from_text("reaching 36,000 feet")[0]

        # Word timestamps where numbers occur at t=5.0s and t=12.0s (only 7s apart)
        word_ts = [
            {"word": "it", "start": 0.0, "end": 0.3},
            {"word": "was", "start": 0.3, "end": 0.6},
            {"word": "24", "start": 0.6, "end": 5.0},
            {"word": "reaching", "start": 7.0, "end": 8.0},
            {"word": "36000", "start": 8.0, "end": 12.0},
        ]

        aligned = align_graphics_with_narration([g1, g2], word_ts, min_interval=15.0)
        # Second graphic within 15 seconds must be dropped
        self.assertEqual(len(aligned), 1)
        self.assertEqual(aligned[0].numeric_value, 24.0)

    def test_count_lands_at_spoken_word_end(self):
        detector = NumberGraphicDetector()
        g1 = detector.detect_from_text("It was 1066")[0]
        word_ts = [
            {"word": "it", "start": 1.0, "end": 1.5},
            {"word": "was", "start": 1.5, "end": 2.0},
            {"word": "1066", "start": 2.0, "end": 4.0},
        ]

        aligned = align_graphics_with_narration([g1], word_ts, min_interval=15.0, count_time=1.6)
        self.assertEqual(len(aligned), 1)
        # Spoken end time is 4.0s; graphic starts at 4.0 - 1.6 = 2.4s
        self.assertAlmostEqual(aligned[0].spoken_land_time, 4.0)
        self.assertAlmostEqual(aligned[0].start_time, 2.4)


class TestOverlayTemplatesExecution(unittest.TestCase):
    """Verifies standalone reference template scripts: countup, ring, timeline, comparison."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.tmp_dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_countup_overlay_cli(self):
        dest = self.tmp_dir / "test_countup.webm"
        cmd = [
            sys.executable, "countup_overlay.py",
            "36000", "FEET", "DEEPEST POINT", str(dest),
            "--dur", "1.0", "--count", "0.6", "--width", "320", "--height", "180", "--fps", "15"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"countup_overlay failed: {res.stderr}")
        self.assertTrue(dest.exists())
        self.assertGreater(dest.stat().st_size, 1000)

    def test_ring_overlay_cli(self):
        dest = self.tmp_dir / "test_ring.webm"
        cmd = [
            sys.executable, "ring_overlay.py",
            "75", "%", "GLOBAL LAND SHARE", str(dest),
            "--dur", "1.0", "--count", "0.6", "--width", "320", "--height", "180", "--fps", "15"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"ring_overlay failed: {res.stderr}")
        self.assertTrue(dest.exists())
        self.assertGreater(dest.stat().st_size, 1000)

    def test_timeline_overlay_cli(self):
        dest = self.tmp_dir / "test_timeline.webm"
        cmd = [
            sys.executable, "timeline_overlay.py",
            "1066", "AD", "BATTLE OF HASTINGS", str(dest),
            "--dur", "1.0", "--count", "0.6", "--width", "320", "--height", "180", "--fps", "15"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"timeline_overlay failed: {res.stderr}")
        self.assertTrue(dest.exists())
        self.assertGreater(dest.stat().st_size, 1000)

    def test_comparison_overlay_cli(self):
        dest = self.tmp_dir / "test_comp.webm"
        cmd = [
            sys.executable, "comparison_overlay.py",
            "5.0", "x", "FORCE MULTIPLIER", str(dest),
            "--dur", "1.0", "--count", "0.6", "--width", "320", "--height", "180", "--fps", "15"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"comparison_overlay failed: {res.stderr}")
        self.assertTrue(dest.exists())
        self.assertGreater(dest.stat().st_size, 1000)

    def test_gauge_overlay_cli(self):
        dest = self.tmp_dir / "test_gauge.webm"
        cmd = [
            sys.executable, "gauge_overlay.py",
            "10984", "METERS", "CHALLENGER DEEP", str(dest),
            "--dur", "1.0", "--count", "0.6", "--width", "320", "--height", "180", "--fps", "15"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"gauge_overlay failed: {res.stderr}")
        self.assertTrue(dest.exists())
        self.assertGreater(dest.stat().st_size, 1000)

    def test_dotgrid_overlay_cli(self):
        dest = self.tmp_dir / "test_dotgrid.webm"
        cmd = [
            sys.executable, "dotgrid_overlay.py",
            "5", "PEOPLE", "IMPERIAL RATIO", str(dest),
            "--dur", "1.0", "--count", "0.6", "--width", "320", "--height", "180", "--fps", "15"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, f"dotgrid_overlay failed: {res.stderr}")
        self.assertTrue(dest.exists())
        self.assertGreater(dest.stat().st_size, 1000)


class TestNumberGraphicsEngine(unittest.TestCase):
    """Verifies NumberGraphicsEngine methods and caching."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.engine = NumberGraphicsEngine(cache_dir=Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_render_counter_backwards_compat(self):
        dest = Path(self.tmp.name) / "test_counter.mp4"
        res = self.engine.render_counter(
            final_value="10,928",
            label="CHALLENGER DEEP",
            dest=dest,
            duration=1.0,
            width=320,
            height=180,
            fps=15,
        )
        self.assertIsNotNone(res)
        self.assertTrue(dest.exists())
        self.assertGreater(dest.stat().st_size, 1000)

    def test_render_gauge(self):
        dest = Path(self.tmp.name) / "test_gauge.mp4"
        res = self.engine.render_gauge(
            value=10984.0,
            unit="meters",
            label="CHALLENGER DEEP",
            dest=dest,
            duration=1.0,
            count_time=0.6,
            width=320,
            height=180,
            fps=15,
        )
        self.assertIsNotNone(res)
        self.assertTrue(dest.exists())
        self.assertGreater(dest.stat().st_size, 1000)

    def test_render_dot_grid(self):
        dest = Path(self.tmp.name) / "test_dotgrid.mp4"
        res = self.engine.render_dot_grid(
            ratio_n=5,
            label="1 IN 5 CITIZENS",
            dest=dest,
            duration=1.0,
            count_time=0.6,
            width=320,
            height=180,
            fps=15,
        )
        self.assertIsNotNone(res)
        self.assertTrue(dest.exists())
        self.assertGreater(dest.stat().st_size, 1000)


if __name__ == "__main__":
    unittest.main()
