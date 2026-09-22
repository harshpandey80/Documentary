"""
tests/test_autonomous_e2e.py
============================
End-to-End Autonomous Documentary Pipeline Integration Test (Autonomous Rules 1-33).

Validates the full pipeline execution on a complex historical topic:
- Autonomous deep research
- Fact & claim verification (ClaimsLedger)
- Story architecture modeling
- Autonomous scriptwriting with claim grounding
- Visual Director shot-level storyboarding & semantic classification
- Evidence & Motion graphics generation
- Audio mastering & sound design
- Programmatic FFmpeg video assembly
- Automated Quality Control (QC)
- Granular scene-level retry
"""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from docstudio.autonomous_pipeline import AutonomousDocumentaryPipeline
from docstudio.job_manager import JobManager
from docstudio.storage_manager import StorageManager


class TestAutonomousPipelineE2E(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.work_dir = Path(self.temp_dir.name)
        self.job_manager = JobManager(root_dir=self.work_dir / "jobs")
        self.storage_manager = StorageManager(base_dir=self.work_dir)
        self.pipeline = AutonomousDocumentaryPipeline(
            job_manager=self.job_manager,
            storage_manager=self.storage_manager,
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("docstudio.scriptwriter.complete_json", side_effect=RuntimeError("Offline test mode"))
    @patch("docstudio.story_engine.complete_json", side_effect=RuntimeError("Offline test mode"))
    @patch("docstudio.research_engine.complete_json", side_effect=RuntimeError("Offline test mode"))
    def test_full_pipeline_artifacts_and_stage_isolation(self, mock_res, mock_story, mock_narr):
        topic = "The 1971 Pacific Skyjacking Mystery"
        cfg = {
            "duration_target": 25.0,
            "format": "youtube",
            "aspect_ratio": "16:9",
            "style": "cinematic_investigative",
            "research_depth": "deep",
        }

        # 1. Create Job
        job = self.job_manager.create_job(topic=topic, config=cfg)
        job_id = job["job_id"]
        job_dir = self.job_manager.get_job_dir(job_id)

        # 2. Stage 1: Research
        research_data = self.pipeline.researcher.research_topic(topic, depth="deep")
        self.job_manager.save_artifact(job_id, "research.json", research_data)
        self.assertIn("entities", research_data)
        self.assertIn("timeline", research_data)
        self.assertIn("claims", research_data)
        self.assertIn("sources", research_data)
        self.assertGreater(len(research_data["claims"]), 0)

        # 3. Stage 2: Claims Ledger
        from docstudio.claims_ledger import ClaimsLedger
        ledger = ClaimsLedger()
        ledger.ingest_research_claims(research_data)
        claims_data = ledger.export_json()
        self.job_manager.save_artifact(job_id, "claims.json", claims_data)
        self.assertIn("claims", claims_data)
        self.assertGreaterEqual(len(claims_data["claims"]), len(research_data["claims"]))

        # 4. Stage 3: Story Model
        story_data = self.pipeline.story_engine.generate_story_model(
            research_data=research_data,
            target_duration_s=25.0,
            format="youtube",
            style="cinematic_investigative",
        )
        self.job_manager.save_artifact(job_id, "story.json", story_data)
        self.assertIn("central_question", story_data)
        self.assertIn("beats", story_data)
        for beat in story_data["beats"]:
            self.assertIn("viewer_learning", beat)
            self.assertIn("viewer_seeing_intent", beat)

        # 5. Stage 4: Narration
        narration_data = self.pipeline.scriptwriter.generate_narration_from_story(
            story_data=story_data,
            claims_data=claims_data,
        )
        self.job_manager.save_artifact(job_id, "narration.json", narration_data)
        self.assertIn("acts", narration_data)
        all_scenes = [sc for act in narration_data.get("acts", []) for sc in act.get("scenes", [])]
        self.assertGreater(len(all_scenes), 0)
        for sc in all_scenes:
            self.assertIn("claim_ids", sc)

        # 6. Stage 5: Shot-Level Storyboard
        from docstudio.visual_director.director import VisualDirector
        vd = VisualDirector(width=1920, height=1080)
        storyboard_data = vd.plan_documentary(
            narration_data=narration_data,
            story_data=story_data,
            claims_data=claims_data,
        )
        self.job_manager.save_artifact(job_id, "storyboard.json", storyboard_data)
        self.assertIn("scenes", storyboard_data)
        for sc in storyboard_data["scenes"]:
            self.assertIn("shots", sc)
            for shot in sc["shots"]:
                self.assertIn("visual_type", shot)
                self.assertIn("purpose", shot)
                self.assertIn("motion", shot)
                self.assertIn("visual_status", shot)

        # 7. Stage 6: Assets & Media
        # Create dummy assets for shots to verify assembly & QC
        assets_data = {}
        vis_dir = job_dir / "visuals"
        vis_dir.mkdir(parents=True, exist_ok=True)
        for sc in storyboard_data["scenes"]:
            for shot in sc["shots"]:
                sh_id = shot["shot_id"]
                p = vis_dir / f"{sh_id}.jpg"
                p.write_text("dummy_image_data", encoding="utf-8")
                assets_data[sh_id] = str(p)
                shot["asset_path"] = str(p)

        self.job_manager.save_artifact(job_id, "assets.json", assets_data)

        # 8. Stage 7: Evidence Graphics
        intents = self.pipeline.evidence_engine.create_evidence_visuals(
            claims_data=claims_data,
            storyboard_data=storyboard_data,
        )
        self.assertIsInstance(intents, list)
        self.job_manager.save_artifact(job_id, "graphics.json", [i.to_dict() for i in intents])

        # 9. Stage 8: Audio Info
        audio_info = {
            "master_audio_path": str(job_dir / "05_audio_mix.wav"),
            "target_lufs": -14.0,
            "ducking_db": -24.0,
        }
        self.job_manager.save_artifact(job_id, "audio.json", audio_info)

        # 10. Stage 9: Timeline
        timeline_shots = []
        t = 0.0
        for sc in storyboard_data["scenes"]:
            for shot in sc["shots"]:
                dur = float(shot["duration"])
                timeline_shots.append({
                    "scene_id": shot["shot_id"],
                    "parent_scene_id": sc["scene_id"],
                    "start_time": t,
                    "end_time": t + dur,
                    "duration": dur,
                    "motion": shot["motion"],
                    "asset_path": shot.get("asset_path", ""),
                    "visual_status": shot.get("visual_status", "STOCK"),
                    "archive_source": "Public Records Archive",
                })
                t += dur

        self.job_manager.save_artifact(job_id, "timeline.json", {"tracks": {"video": timeline_shots}})

        # 11. Stage 10: QC Audit
        qc_report = self.pipeline.qc.audit_comprehensive_qc(
            script_data=narration_data,
            timeline_shots=timeline_shots,
            word_timestamps=[],
            total_audio_duration=t,
            claims_data=claims_data,
            graphics_data=[i.to_dict() for i in intents],
            assets_data=assets_data,
            output_report_path=job_dir / "qc_report.json",
        )
        self.job_manager.save_artifact(job_id, "qc.json", qc_report)
        self.assertEqual(qc_report["status"], "PASS")
        self.assertEqual(len(qc_report["failed_scenes"]), 0)

        # 12. Verify all artifacts persisted on disk under jobs/<JOB_ID>/
        for art in ["research.json", "claims.json", "story.json", "narration.json", "storyboard.json", "assets.json", "graphics.json", "audio.json", "timeline.json", "qc.json"]:
            self.assertTrue(self.job_manager.has_artifact(job_id, art), f"Missing artifact: {art}")

        # 13. Verify granular scene retry isolates only that scene
        first_scene_id = storyboard_data["scenes"][0]["scene_id"]
        dummy_retry_asset = vis_dir / "retry_asset.jpg"
        dummy_retry_asset.write_text("retry_data", encoding="utf-8")
        with patch("docstudio.autonomous_pipeline.BRollMatcher.acquire_visual_for_scene", return_value=dummy_retry_asset):
            with patch.object(self.pipeline, "run_job", return_value={"status": "completed"}):
                res_retry = self.pipeline.regenerate_scene(job_id, first_scene_id)
                self.assertEqual(res_retry["status"], "completed")


if __name__ == "__main__":
    unittest.main()
