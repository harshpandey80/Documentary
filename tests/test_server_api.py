import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient

from docstudio.server import app, job_manager_instance


class TestServerAPI(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.work_dir = Path(self.temp_dir.name)
        job_manager_instance.root_dir = self.work_dir
        self.client = TestClient(app)

    def tearDown(self):
        self.temp_dir.cleanup()

    @patch("docstudio.server._run_autonomous_job_task")
    def test_generate_documentary_endpoint(self, mock_run_task):
        payload = {
            "topic": "The Mystery of the Oak Island Money Pit",
            "duration_target": 180,
            "format": "youtube",
            "aspect_ratio": "16:9",
            "style": "cinematic_investigative",
            "research_depth": "standard",
        }
        res = self.client.post("/api/documentary/generate", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("job_id", data)
        self.assertEqual(data["status"], "researching")
        mock_run_task.assert_called_once()

    def test_get_and_list_jobs(self):
        job = job_manager_instance.create_job(
            topic="Bermuda Triangle Anomaly",
            config={"duration_target": 60},
        )
        job_id = job["job_id"]

        # List jobs
        res = self.client.get("/api/documentary/jobs")
        self.assertEqual(res.status_code, 200)
        jobs = res.json()
        self.assertTrue(any(j["job_id"] == job_id for j in jobs))

        # Get job
        res2 = self.client.get(f"/api/documentary/jobs/{job_id}")
        self.assertEqual(res2.status_code, 200)
        j_data = res2.json()
        self.assertEqual(j_data["job_id"], job_id)
        self.assertIn("resolve_status", j_data)

    def test_override_artifact(self):
        job = job_manager_instance.create_job(
            topic="The Lost Colony of Roanoke",
            config={"duration_target": 60},
        )
        job_id = job["job_id"]

        override_payload = {
            "artifact_name": "story.json",
            "data": {"central_question": "What happened to the settlers?"},
        }
        res = self.client.post(f"/api/documentary/jobs/{job_id}/override", json=override_payload)
        self.assertEqual(res.status_code, 200)

        # Retrieve artifact
        res_art = self.client.get(f"/api/documentary/jobs/{job_id}/artifact/story.json")
        self.assertEqual(res_art.status_code, 200)
        self.assertEqual(res_art.json()["central_question"], "What happened to the settlers?")


if __name__ == "__main__":
    unittest.main()
