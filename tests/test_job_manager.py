import tempfile
from pathlib import Path
import pytest
from docstudio.job_manager import JobManager, STAGE_SEQUENCE

def test_job_lifecycle():
    with tempfile.TemporaryDirectory() as tmpdir:
        jm = JobManager(root_dir=Path(tmpdir))
        
        # 1. Create Job
        job = jm.create_job(
            topic="The Mystery of Flight 19",
            duration_target=300,
            format="youtube",
            aspect_ratio="16:9",
            style="cinematic_investigative",
        )
        assert job["job_id"].startswith("the_mystery_of_flight_19_")
        assert job["status"] == "created"
        assert job["progress_percent"] == 0
        assert len(job["stages"]) == len(STAGE_SEQUENCE)

        job_id = job["job_id"]

        # 2. Start Stage 1 (research)
        st = jm.update_stage_start(job_id, "research")
        assert st["status"] == "running_research"
        assert st["current_stage"] == "research"
        assert st["stages"]["research"]["status"] == "in_progress"

        # 3. Save Research Artifact
        research_data = {"topic": "Flight 19", "entities": ["Lt. Charles Taylor"]}
        art_path = jm.save_artifact(job_id, "research.json", research_data)
        assert art_path.exists()
        assert jm.has_artifact(job_id, "research.json")
        loaded = jm.load_artifact(job_id, "research.json")
        assert loaded["entities"] == ["Lt. Charles Taylor"]

        # 4. Complete Stage 1
        st = jm.update_stage_complete(job_id, "research", details="Found 12 primary sources")
        assert st["stages"]["research"]["status"] == "done"
        assert st["stages"]["research"]["details"] == "Found 12 primary sources"
        assert st["progress_percent"] >= 10

        # 5. Simulate failure on 'rendering'
        jm.update_stage_start(job_id, "rendering")
        st_fail = jm.update_stage_fail(job_id, "rendering", "FFmpeg out of memory")
        assert st_fail["status"] == "failed"
        assert "FFmpeg out of memory" in st_fail["error"]
        assert st_fail["stages"]["rendering"]["status"] == "failed"

        # 6. Retry rendering stage: should reset rendering to pending, but keep research done!
        st_retry = jm.retry_stage(job_id, "rendering")
        assert st_retry["stages"]["research"]["status"] == "done"
        assert st_retry["stages"]["rendering"]["status"] == "pending"
        assert jm.has_artifact(job_id, "research.json")
