import json
import tempfile
import unittest
from pathlib import Path

from docstudio.qc_auditor import QCAuditor


class TestQCAuditorComprehensive(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.work_dir = Path(self.temp_dir.name)
        self.qc = QCAuditor()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_passing_qc_audit(self):
        # Create a valid dummy media asset
        dummy_asset = self.work_dir / "valid_cut.mp4"
        dummy_asset.write_text("content", encoding="utf-8")

        script_data = {
            "acts": [
                {
                    "act_number": 1,
                    "scenes": [
                        {
                            "scene_id": "sc_01",
                            "narration": "In the archives, officials found the log.",
                            "claim_ids": ["C001"],
                        }
                    ]
                }
            ]
        }
        timeline_shots = [
            {
                "scene_id": "sc_01",
                "duration": 3.0,
                "asset_path": str(dummy_asset),
                "motion": "slow_zoom",
                "visual_status": "AUTHENTIC_SOURCE",
                "archive_source": "National Records Archive",
            }
        ]
        word_timestamps = [
            {"word": "In", "start": 0.0, "end": 0.5},
            {"word": "archives", "start": 0.5, "end": 2.9},
        ]
        claims_data = {
            "claims": [
                {
                    "claim_id": "C001",
                    "claim": "Log was found in archives",
                    "verification_status": "verified",
                    "sources": ["National Records Archive"],
                }
            ]
        }
        graphics_data = [
            {
                "purpose": "show_archive_date",
                "source_claims": ["C001"],
                "key_message": "Document dated 1945",
                "visualization_type": "timeline",
                "data": [{"year": 1945, "event": "Record logged"}],
            }
        ]

        report_path = self.work_dir / "qc_report.json"
        res = self.qc.audit_comprehensive_qc(
            script_data=script_data,
            timeline_shots=timeline_shots,
            word_timestamps=word_timestamps,
            total_audio_duration=3.0,
            claims_data=claims_data,
            graphics_data=graphics_data,
            output_report_path=report_path,
        )

        self.assertEqual(res["status"], "PASS")
        self.assertEqual(res["failed_scenes"], [])
        self.assertTrue(report_path.exists())
        self.assertTrue(report_path.with_suffix(".md").exists())

    def test_failing_claim_and_missing_media(self):
        script_data = {
            "acts": [
                {
                    "act_number": 1,
                    "scenes": [
                        {
                            "scene_id": "sc_broken",
                            "narration": "An unverified assertion is made here.",
                            "claim_ids": ["C_UNVERIFIED_999"],
                        }
                    ]
                }
            ]
        }
        timeline_shots = [
            {
                "scene_id": "sc_broken",
                "duration": 2.5,
                "asset_path": str(self.work_dir / "non_existent_video.mp4"),
                "motion": "pan",
            }
        ]
        claims_data = {
            "claims": [
                {"claim_id": "C001", "verification_status": "verified"}
            ]
        }

        res = self.qc.audit_comprehensive_qc(
            script_data=script_data,
            timeline_shots=timeline_shots,
            word_timestamps=[],
            total_audio_duration=2.5,
            claims_data=claims_data,
        )

        self.assertEqual(res["status"], "FAILED")
        self.assertIn("sc_broken", res["failed_scenes"])
        # Check specific violation categories
        categories = [v["category"] for v in res["violations"]]
        self.assertIn("CLAIM_PROVENANCE", categories)
        self.assertIn("MISSING_MEDIA", categories)


if __name__ == "__main__":
    unittest.main()
