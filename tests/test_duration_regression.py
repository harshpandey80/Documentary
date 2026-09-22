import unittest
from pathlib import Path
from docstudio.pipeline import (
    parse_runtime_seconds,
    verify_render_duration,
)

class TestDurationRegression(unittest.TestCase):
    def test_parse_runtime_seconds(self):
        self.assertEqual(parse_runtime_seconds("5m"), 300.0)
        self.assertEqual(parse_runtime_seconds("10m"), 600.0)
        self.assertEqual(parse_runtime_seconds("8m"), 480.0)
        self.assertEqual(parse_runtime_seconds("3m"), 180.0)
        self.assertEqual(parse_runtime_seconds("120s"), 120.0)
        self.assertEqual(parse_runtime_seconds("250"), 250.0)

    def test_hard_fail_on_10s_toy_regression(self):
        """
        Assert that the pipeline HARD FAILS if a 10-second toy output
        is evaluated against a requested 5m or 10m target runtime.
        """
        stale_10s_render = Path("workspace/runs/the_vela_incident/06_final_render.mp4")
        if stale_10s_render.exists():
            with self.assertRaises(RuntimeError) as ctx:
                verify_render_duration(stale_10s_render, runtime_target="5m", max_deviation_ratio=0.05)
            self.assertIn("CRITICAL HARD REGRESSION FAILURE", str(ctx.exception))
            self.assertIn("5%", str(ctx.exception))

if __name__ == "__main__":
    unittest.main()
