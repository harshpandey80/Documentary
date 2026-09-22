import tempfile
import unittest
from pathlib import Path

from docstudio.resolve_bridge import DaVinciResolveBridge
from docstudio.storage_manager import StorageManager


class TestStorageAndResolve(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.work_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_storage_manager_disk_check(self):
        sm = StorageManager(base_dir=self.work_dir, min_free_gb=0.1)
        res = sm.check_disk_space()
        self.assertIn("free_gb", res)
        self.assertIn("total_gb", res)
        self.assertIn("sufficient", res)

    def test_storage_manager_clean_temp_files(self):
        sm = StorageManager(base_dir=self.work_dir)
        temp_sub = self.work_dir / "temp_render"
        temp_sub.mkdir()
        (temp_sub / "frame_001.tmp").write_text("data")

        res = sm.clean_job_temp_files(self.work_dir)
        self.assertFalse(temp_sub.exists())
        self.assertGreaterEqual(res["cleaned_bytes"], 4)

    def test_resolve_bridge_fallback(self):
        # Resolve bridge without active Resolve should gracefully return fallback
        bridge = DaVinciResolveBridge(mcp_url="http://127.0.0.1:99999/mcp")
        status = bridge.get_backend_status()
        self.assertFalse(status["available"])
        self.assertEqual(status["renderer_mode"], "ffmpeg_fallback")

        # Calling render_timeline should tell caller to use FFmpeg
        res = bridge.render_timeline("proj", self.work_dir / "out.mp4")
        self.assertFalse(res["success"])
        self.assertEqual(res["renderer"], "ffmpeg")


if __name__ == "__main__":
    unittest.main()
