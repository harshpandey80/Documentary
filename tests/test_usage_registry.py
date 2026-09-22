"""Tests for Phase 6 – UsageRegistry and RelevanceScorer"""

import tempfile
import unittest
from pathlib import Path


class TestUsageRegistry(unittest.TestCase):

    def setUp(self):
        from docstudio.usage_registry import UsageRegistry
        self.tmp = tempfile.TemporaryDirectory()
        self.run_dir = Path(self.tmp.name)
        self.reg = UsageRegistry(run_dir=self.run_dir, max_reuse=2)

    def tearDown(self):
        self.tmp.cleanup()

    def test_can_use_unregistered_asset(self):
        asset = self.run_dir / "fake_clip.mp4"
        asset.write_bytes(b"0" * 100)
        self.assertTrue(self.reg.can_use(asset, "scene_001"))

    def test_max_reuse_enforced(self):
        from docstudio.usage_registry import UsageRegistry
        asset = self.run_dir / "clip_a.mp4"
        asset.write_bytes(b"0" * 100)

        reg = UsageRegistry(run_dir=self.run_dir, max_reuse=2)
        reg.register(asset, "s001", "CINEMATIC_STOCK")
        reg.register(asset, "s002", "CINEMATIC_STOCK")
        # Third use must be rejected
        self.assertFalse(reg.can_use(asset, "s003"))

    def test_register_increments_uses(self):
        asset = self.run_dir / "clip_b.mp4"
        asset.write_bytes(b"0" * 100)
        self.reg.register(asset, "s010", "AI_CINEMATIC_RECREATION")
        self.reg.register(asset, "s011", "AI_CINEMATIC_RECREATION")
        key = str(asset.resolve())
        self.assertEqual(len(self.reg._asset_uses[key]), 2)

    def test_tier_distribution_counts(self):
        asset = self.run_dir / "clip_c.mp4"
        asset.write_bytes(b"0" * 100)
        self.reg.register(asset, "s020", "AI_CINEMATIC_RECREATION")
        self.reg.register(asset, "s021", "INFOGRAPHIC_CODE2VIDEO")
        self.reg.register(asset, "s022", "FORENSIC_ARCHIVAL")
        self.reg.register(asset, "s023", "CINEMATIC_STOCK")
        dist = self.reg.tier_distribution(total_shots=4)
        self.assertEqual(dist["AI_CINEMATIC_RECREATION"], 25.0)
        self.assertEqual(dist["INFOGRAPHIC_CODE2VIDEO"], 25.0)
        self.assertEqual(dist["FORENSIC_ARCHIVAL"], 25.0)
        self.assertEqual(dist["CINEMATIC_STOCK"], 25.0)

    def test_audit_detects_stock_over_limit(self):
        asset = self.run_dir / "clip_d.mp4"
        asset.write_bytes(b"0" * 100)
        for i in range(4):
            a = self.run_dir / f"clip_{i}.mp4"
            a.write_bytes(b"0" * 100)
            self.reg.register(a, f"s{i:03d}", "CINEMATIC_STOCK")
        violations = self.reg.audit_diversity(total_shots=4)
        self.assertTrue(any("CINEMATIC_STOCK" in v for v in violations))

    def test_summary_report_runs_without_error(self):
        asset = self.run_dir / "clip_e.mp4"
        asset.write_bytes(b"0" * 100)
        self.reg.register(asset, "s100", "AI_CINEMATIC_RECREATION")
        report = self.reg.summary_report(total_shots=4)
        self.assertIn("UsageRegistry", report)

    def test_persistence_roundtrip(self):
        from docstudio.usage_registry import UsageRegistry
        asset = self.run_dir / "clip_f.mp4"
        asset.write_bytes(b"0" * 100)
        self.reg.register(asset, "s200", "FORENSIC_ARCHIVAL")

        # Reload from disk
        reg2 = UsageRegistry(run_dir=self.run_dir, max_reuse=2)
        self.assertEqual(reg2.scene_count(), 1)


class TestRelevanceScorer(unittest.TestCase):

    def setUp(self):
        from docstudio.relevance_scorer import RelevanceScorer
        self.scorer = RelevanceScorer(threshold=0.15)

    def test_exact_keyword_match_high_score(self):
        score = self.scorer.score(
            keywords=["mariana", "trench", "ocean"],
            asset_path=Path("mariana_trench_deep_ocean.jpg"),
        )
        self.assertGreater(score, 0.3)

    def test_no_match_low_score(self):
        score = self.scorer.score(
            keywords=["mariana", "trench", "ocean", "submarine"],
            asset_path=Path("corporate_office_meeting.jpg"),
        )
        self.assertLess(score, 0.5)

    def test_empty_keywords_returns_one(self):
        score = self.scorer.score(keywords=[], asset_path=Path("anything.jpg"))
        self.assertEqual(score, 1.0)

    def test_relevance_threshold_gate(self):
        # Completely unrelated asset
        self.assertFalse(
            self.scorer.is_relevant(
                ["classified", "cockpit", "plane"],
                Path("random_xyz_123.jpg"),
            )
        )

    def test_score_bounded_0_1(self):
        score = self.scorer.score(
            keywords=["deep", "deep", "deep", "deep", "deep"],
            asset_path=Path("deep_deep_deep_deep.jpg"),
            context="deep ocean abyss very deep extremely deep water",
        )
        self.assertLessEqual(score, 1.0)
        self.assertGreaterEqual(score, 0.0)


if __name__ == "__main__":
    unittest.main()
