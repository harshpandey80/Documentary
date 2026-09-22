import json
import time
import traceback
from datetime import datetime
from pathlib import Path
from docstudio.config import RUNS_DIR

WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
PROGRESS_FILE = WORKSPACE_ROOT / "PROGRESS.md"

CORE_CHECKPOINTS = [
    ("01_script.json", "Script & Storyboard Cues"),
    ("02_narration.wav", "Master Voiceover Narration"),
    ("03_captions.ass", "Word-Aligned Subtitles"),
    ("04_visuals", "Visual B-Roll & Manifest"),
    ("05_audio_mix.wav", "Ducked Audio Bed & SFX Mix"),
    ("06_final_render.mp4", "Composited 1080p Video"),
]

STAGE_NAMES = {
    1: "Script Generation",
    2: "Narration Voiceover (Edge-TTS + Kokoro Failover)",
    3: "Word-Aligned Subtitle Assembly",
    4: "B-Roll Visual Acquisition & Color Grade",
    5: "Audio Bed Ducking & SFX Mastering",
    6: "FFmpeg Compositing & Burn-in",
    7: "Retention QC & Distribution Packaging",
}

class ProgressTracker:
    def __init__(self, run_dir: Path | None = None, topic: str = ""):
        self.run_dir = run_dir
        self.topic = topic
        self.run_id = run_dir.name if run_dir else "unknown"
        self.start_time = time.time()
        self.current_stage = 0
        self.overall_status = "INITIALIZING"
        self.stages = {
            i: {"name": STAGE_NAMES[i], "status": "pending", "duration_s": 0.0, "details": ""}
            for i in range(1, 8)
        }
        self.error_info = None

        if self.run_dir and (self.run_dir / "run_state.json").exists():
            try:
                with open(self.run_dir / "run_state.json", "r", encoding="utf-8") as f:
                    old_state = json.load(f)
                    if "stages" in old_state:
                        for k, v in old_state["stages"].items():
                            k_int = int(k)
                            if k_int in self.stages and v.get("status") == "done":
                                self.stages[k_int] = v
            except Exception:
                pass

    def start_run(self, run_id: str, topic: str, run_dir: Path):
        self.run_id = run_id
        self.topic = topic
        self.run_dir = run_dir
        self.overall_status = "RUNNING"

        # Restore previously completed stages if resuming an existing run
        state_path = run_dir / "run_state.json"
        if state_path.exists():
            try:
                with open(state_path, "r", encoding="utf-8") as f:
                    old_state = json.load(f)
                    if "stages" in old_state:
                        for k, v in old_state["stages"].items():
                            k_int = int(k)
                            if k_int in self.stages and v.get("status") == "done":
                                self.stages[k_int] = v
            except Exception:
                pass

        self._write_progress_md()
        self._write_run_state_json()

    def stage_start(self, stage_num: int):
        self.current_stage = stage_num
        if stage_num in self.stages:
            self.stages[stage_num]["status"] = "in progress"
            self.stages[stage_num]["start_t"] = time.time()
        self._write_progress_md()

    def stage_complete(self, stage_num: int, details: str = ""):
        if stage_num in self.stages:
            st = self.stages[stage_num].get("start_t", time.time())
            dur = round(time.time() - st, 2)
            self.stages[stage_num]["status"] = "done"
            self.stages[stage_num]["duration_s"] = dur
            self.stages[stage_num]["details"] = details
        self._write_progress_md()
        self._write_run_state_json()

    def stage_fail(self, stage_num: int, error: Exception | str):
        self.overall_status = "FAILED"
        err_msg = str(error)
        tb = traceback.format_exc() if isinstance(error, Exception) else ""
        if stage_num in self.stages:
            self.stages[stage_num]["status"] = f"failed: {err_msg}"
        self.error_info = {
            "failed_stage": stage_num,
            "stage_name": STAGE_NAMES.get(stage_num, "Unknown"),
            "error_message": err_msg,
            "traceback": tb,
            "timestamp": datetime.now().isoformat(),
        }
        self._write_progress_md()
        self._write_run_state_json()

    def complete_run(self):
        self.overall_status = "COMPLETED"
        self._write_progress_md()
        self._write_run_state_json()

    def _checkpoints_state(self) -> list[dict]:
        results = []
        if not self.run_dir or not self.run_dir.exists():
            for filename, desc in CORE_CHECKPOINTS:
                results.append({"filename": filename, "description": desc, "exists": False, "size_str": "0 KB"})
            return results

        for filename, desc in CORE_CHECKPOINTS:
            p = self.run_dir / filename
            exists = p.exists()
            size_str = "N/A"
            if exists:
                if p.is_file():
                    kb = p.stat().st_size / 1024
                    size_str = f"{kb:.1f} KB" if kb < 1024 else f"{kb/1024:.2f} MB"
                elif p.is_dir():
                    count = len(list(p.glob("*")))
                    size_str = f"{count} files"
            results.append({
                "filename": filename,
                "description": desc,
                "exists": exists,
                "size_str": size_str,
            })
        return results

    def _write_progress_md(self):
        elapsed = round(time.time() - self.start_time, 1)
        checkpoints = self._checkpoints_state()

        lines = [
            "# DocStudio Pipeline Progress Dashboard",
            "",
            f"> **Last Updated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ",
            f"> **Active Run ID**: `{self.run_id}`  ",
            f"> **Topic**: *{self.topic}*  ",
            f"> **Overall Status**: **{self.overall_status}** ({elapsed}s elapsed)  ",
            "",
            "---",
            "",
        ]

        if self.error_info:
            lines.extend([
                "> [!CAUTION]",
                f"> **PIPELINE FAILURE IN STAGE {self.error_info['failed_stage']}: {self.error_info['stage_name']}**",
                f"> **Error**: `{self.error_info['error_message']}`",
                f"> **Timestamp**: {self.error_info['timestamp']}",
                "",
                "```text",
                self.error_info.get("traceback", "").strip() or self.error_info["error_message"],
                "```",
                "",
                "---",
                "",
            ])

        lines.extend([
            "## 1. Core Checkpoints Status (6 Required Stages)",
            "",
            "| Stage | Checkpoint File | Description | Status | File Size |",
            "| :---: | :--- | :--- | :---: | :---: |",
        ])

        for idx, cp in enumerate(checkpoints, 1):
            icon = "✅ Exists" if cp["exists"] else "⏳ Missing / In Progress"
            lines.append(f"| {idx} | `{cp['filename']}` | {cp['description']} | {icon} | {cp['size_str']} |")

        lines.extend([
            "",
            "---",
            "",
            "## 2. Active Stage Execution Log",
            "",
            "| # | Pipeline Stage | Status | Duration | Stage Details |",
            "| :---: | :--- | :---: | :---: | :--- |",
        ])

        for num in range(1, 8):
            st = self.stages[num]
            stat = st["status"]
            icon = "⚪ Pending"
            if stat == "in progress":
                icon = "🟡 In Progress"
            elif stat == "done":
                icon = "🟢 Done"
            elif stat.startswith("failed"):
                icon = "🔴 Failed"

            dur_str = f"{st['duration_s']}s" if st["duration_s"] > 0 else "-"
            lines.append(f"| {num} | {st['name']} | {icon} | {dur_str} | {st['details']} |")

        lines.extend([
            "",
            "---",
            "",
            "## 3. Quick CLI Commands",
            "```powershell",
            f"# Check current active run progress on demand",
            f"uv run python -m docstudio status --run-id {self.run_id}",
            "",
            "# Check all runs",
            "uv run python -m docstudio status --all",
            "```",
            "",
        ])

        try:
            with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
        except Exception:
            pass

    def _write_run_state_json(self):
        if not self.run_dir:
            return
        state_path = self.run_dir / "run_state.json"
        total_render_s = round(time.time() - self.start_time, 2)
        data = {
            "run_id": self.run_id,
            "topic": self.topic,
            "started_at": datetime.fromtimestamp(self.start_time).isoformat(),
            "updated_at": datetime.now().isoformat(),
            "overall_status": self.overall_status,
            "total_duration_seconds": total_render_s,
            "stages": self.stages,
            "error": self.error_info,
        }
        try:
            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    @staticmethod
    def get_run_status(run_id: str) -> dict | None:
        run_path = RUNS_DIR / run_id
        if not run_path.exists():
            return None

        state_file = run_path / "run_state.json"
        if state_file.exists():
            try:
                with open(state_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass

        # Fallback inspection of files
        final_mp4 = run_path / "06_final_render.mp4"
        script_json = run_path / "01_script.json"
        status = "completed" if final_mp4.exists() else ("partial" if script_json.exists() else "empty")
        return {
            "run_id": run_id,
            "topic": run_id.replace("_", " ").title(),
            "overall_status": status.upper(),
            "total_duration_seconds": 0.0,
            "stages": {},
        }

    @staticmethod
    def list_all_runs() -> list[dict]:
        if not RUNS_DIR.exists():
            return []
        runs = []
        for p in sorted(RUNS_DIR.iterdir()):
            if p.is_dir():
                info = ProgressTracker.get_run_status(p.name)
                if info:
                    runs.append(info)
        return runs
