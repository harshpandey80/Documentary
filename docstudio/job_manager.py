"""
DocStudio Autonomous Job Manager & State Persistence Engine.
Manages persistent documentary jobs under jobs/<JOB_ID>/ with granular stage checkpointing.
Supports independent stage retry, artifact caching, and resilience against process restarts.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from docstudio.config import BASE_DIR

JOBS_DIR = BASE_DIR / "jobs"
JOBS_DIR.mkdir(parents=True, exist_ok=True)

STAGE_SEQUENCE = [
    "research",
    "claims",
    "story",
    "narration",
    "storyboard",
    "assets",
    "graphics",
    "audio",
    "rendering",
    "qc",
]

STAGE_DISPLAY_NAMES = {
    "research": "Deep Research",
    "claims": "Fact Verification",
    "story": "Story Architecture",
    "narration": "Autonomous Narration",
    "storyboard": "Shot-Level Storyboard",
    "assets": "Asset Generation & Retrieval",
    "graphics": "Evidence & Motion Graphics",
    "audio": "Sound Design & Audio Mastering",
    "rendering": "Multi-Layer Video Assembly",
    "qc": "Automated Quality Control",
}

STAGE_WEIGHTS = {
    "research": 10,
    "claims": 10,
    "story": 10,
    "narration": 10,
    "storyboard": 10,
    "assets": 15,
    "graphics": 10,
    "audio": 10,
    "rendering": 10,
    "qc": 5,
}


def slugify(text: str) -> str:
    slug = re.sub(r"[^\w\s-]", "", text.lower())
    return re.sub(r"[-\s]+", "_", slug).strip("_")


def generate_job_id(topic: str) -> str:
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    topic_slug = slugify(topic)[:28] or "doc"
    return f"{topic_slug}_{timestamp}"


class JobManager:
    """
    Manages persistent jobs and disk-backed state checkpoints.
    Every job is stored in its own folder: jobs/<JOB_ID>/
    """

    def __init__(self, root_dir: Path | None = None):
        self.root_dir = Path(root_dir) if root_dir else JOBS_DIR
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def get_job_dir(self, job_id: str) -> Path:
        return self.root_dir / job_id

    def create_job(
        self,
        topic: str,
        duration_target: float = 300.0,
        format: str = "youtube",
        aspect_ratio: str = "16:9",
        style: str = "cinematic_investigative",
        research_depth: str = "deep",
        job_id: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """Creates a new job with initialized status.json and empty artifact slots."""
        actual_id = job_id or generate_job_id(topic)
        job_dir = self.get_job_dir(actual_id)
        job_dir.mkdir(parents=True, exist_ok=True)
        (job_dir / "outputs").mkdir(parents=True, exist_ok=True)
        (job_dir / "temp_render").mkdir(parents=True, exist_ok=True)

        merged_cfg = dict(config or {})
        merged_cfg.update(kwargs)

        dur = float(merged_cfg.get("duration_target", duration_target))
        fmt = str(merged_cfg.get("format", format))
        ar = str(merged_cfg.get("aspect_ratio", aspect_ratio))
        sty = str(merged_cfg.get("style", style))
        rdepth = str(merged_cfg.get("research_depth", research_depth))

        now_iso = datetime.now().isoformat()
        stages = {}
        for s in STAGE_SEQUENCE:
            stages[s] = {
                "name": STAGE_DISPLAY_NAMES[s],
                "status": "pending",
                "duration_s": 0.0,
                "error": None,
                "updated_at": now_iso,
                "details": "",
            }

        params_dict = {
            "topic": topic,
            "duration_target": dur,
            "format": fmt,
            "aspect_ratio": ar,
            "style": sty,
            "research_depth": rdepth,
            **merged_cfg,
        }

        job_state = {
            "job_id": actual_id,
            "topic": topic,
            "status": "created",
            "current_stage": None,
            "progress_percent": 0,
            "created_at": now_iso,
            "updated_at": now_iso,
            "error": None,
            "params": params_dict,
            "config": params_dict,
            "stages": stages,
            "artifacts": {},
        }

        self._save_status(actual_id, job_state)
        return job_state

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        status_path = self.get_job_dir(job_id) / "status.json"
        if not status_path.exists():
            return None
        try:
            with open(status_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return None

    def list_jobs(self) -> List[Dict[str, Any]]:
        jobs = []
        if not self.root_dir.exists():
            return jobs

        for d in sorted(self.root_dir.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True):
            if d.is_dir() and (d / "status.json").exists():
                st = self.get_job(d.name)
                if st:
                    # Provide summary fields for fast listing
                    final_mp4 = d / "outputs" / "final_documentary.mp4"
                    jobs.append({
                        "job_id": st["job_id"],
                        "topic": st.get("topic", d.name),
                        "status": st.get("status", "unknown"),
                        "current_stage": st.get("current_stage"),
                        "progress_percent": st.get("progress_percent", 0),
                        "created_at": st.get("created_at"),
                        "updated_at": st.get("updated_at"),
                        "has_video": final_mp4.exists(),
                        "video_url": f"/media/jobs/{st['job_id']}/outputs/final_documentary.mp4" if final_mp4.exists() else "",
                    })
        return jobs

    def update_stage_start(self, job_id: str, stage_name: str) -> Dict[str, Any]:
        st = self.get_job(job_id)
        if not st:
            raise FileNotFoundError(f"Job {job_id} does not exist.")

        now_iso = datetime.now().isoformat()
        st["status"] = f"running_{stage_name}"
        st["current_stage"] = stage_name
        st["updated_at"] = now_iso
        st["stages"][stage_name]["status"] = "in_progress"
        st["stages"][stage_name]["start_time"] = time.time()
        st["stages"][stage_name]["updated_at"] = now_iso
        st["progress_percent"] = self._calculate_progress(st)

        self._save_status(job_id, st)
        return st

    def update_stage_complete(
        self, job_id: str, stage_name: str, details: str = ""
    ) -> Dict[str, Any]:
        st = self.get_job(job_id)
        if not st:
            raise FileNotFoundError(f"Job {job_id} does not exist.")

        now_iso = datetime.now().isoformat()
        stage_info = st["stages"][stage_name]
        start_t = stage_info.get("start_time", time.time())
        duration_s = round(time.time() - start_t, 2)

        stage_info["status"] = "done"
        stage_info["duration_s"] = duration_s
        stage_info["details"] = details
        stage_info["error"] = None
        stage_info["updated_at"] = now_iso

        # If last stage, mark entire job complete
        if stage_name == STAGE_SEQUENCE[-1] or all(
            st["stages"][s]["status"] == "done" for s in STAGE_SEQUENCE
        ):
            st["status"] = "completed"
            st["current_stage"] = None
            st["progress_percent"] = 100
        else:
            st["progress_percent"] = self._calculate_progress(st)

        st["updated_at"] = now_iso
        self._save_status(job_id, st)
        return st

    def update_stage_fail(
        self, job_id: str, stage_name: str, error: Exception | str
    ) -> Dict[str, Any]:
        st = self.get_job(job_id)
        if not st:
            raise FileNotFoundError(f"Job {job_id} does not exist.")

        now_iso = datetime.now().isoformat()
        err_msg = str(error)

        st["status"] = "failed"
        st["error"] = f"Stage [{stage_name}] failed: {err_msg}"
        st["updated_at"] = now_iso
        if stage_name in st["stages"]:
            st["stages"][stage_name]["status"] = "failed"
            st["stages"][stage_name]["error"] = err_msg
            st["stages"][stage_name]["updated_at"] = now_iso

        self._save_status(job_id, st)
        return st

    # Aliases & Convenience Helpers
    def get_job_status(self, job_id: str) -> Optional[Dict[str, Any]]:
        """Alias for get_job(job_id)"""
        return self.get_job(job_id)

    def get_outputs_dir(self, job_id: str) -> Path:
        """Returns the outputs directory for a given job"""
        out_dir = self.get_job_dir(job_id) / "outputs"
        out_dir.mkdir(parents=True, exist_ok=True)
        return out_dir

    def is_stage_completed(self, job_id: str, stage_name: str) -> bool:
        """Checks if a stage is already marked done in status.json"""
        st = self.get_job(job_id)
        if not st or stage_name not in st.get("stages", {}):
            return False
        return st["stages"][stage_name].get("status") == "done"

    def start_stage(self, job_id: str, stage_name: str, details: str = "") -> Dict[str, Any]:
        """Convenience method to start a stage"""
        st = self.update_stage_start(job_id, stage_name)
        if details:
            st["stages"][stage_name]["details"] = details
            self._save_status(job_id, st)
        return st

    def complete_stage(self, job_id: str, stage_name: str, details: Any = "") -> Dict[str, Any]:
        """Convenience method to complete a stage with metadata"""
        det_str = json.dumps(details) if isinstance(details, (dict, list)) else str(details)
        return self.update_stage_complete(job_id, stage_name, details=det_str)

    def complete_job(self, job_id: str, summary: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Marks the entire job complete and updates final summary"""
        st = self.get_job(job_id)
        if not st:
            raise FileNotFoundError(f"Job {job_id} does not exist.")
        now_iso = datetime.now().isoformat()
        st["status"] = "completed"
        st["current_stage"] = None
        st["progress_percent"] = 100
        st["updated_at"] = now_iso
        if summary:
            st.setdefault("summary", {}).update(summary)
        self._save_status(job_id, st)
        return st

    def save_artifact(self, job_id: str, artifact_name: str, data: Any) -> Path:
        """Saves a JSON or text artifact directly into the job directory."""
        job_dir = self.get_job_dir(job_id)
        job_dir.mkdir(parents=True, exist_ok=True)

        if not artifact_name.endswith((".json", ".md", ".txt", ".ass", ".xml", ".csv")):
            file_path = job_dir / f"{artifact_name}.json"
        else:
            file_path = job_dir / artifact_name

        if isinstance(data, (dict, list)):
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        else:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(str(data))

        # Register artifact in status
        st = self.get_job(job_id)
        if st:
            st.setdefault("artifacts", {})[file_path.name] = str(file_path)
            st["updated_at"] = datetime.now().isoformat()
            self._save_status(job_id, st)

        return file_path

    def load_artifact(self, job_id: str, artifact_name: str) -> Optional[Any]:
        job_dir = self.get_job_dir(job_id)
        candidate = job_dir / artifact_name
        if not candidate.exists() and not artifact_name.endswith(".json"):
            candidate = job_dir / f"{artifact_name}.json"

        if not candidate.exists():
            return None

        if candidate.suffix == ".json":
            with open(candidate, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            with open(candidate, "r", encoding="utf-8") as f:
                return f.read()

    def has_artifact(self, job_id: str, artifact_name: str) -> bool:
        job_dir = self.get_job_dir(job_id)
        candidate = job_dir / artifact_name
        if not candidate.exists() and not artifact_name.endswith(".json"):
            candidate = job_dir / f"{artifact_name}.json"
        return candidate.exists()

    def retry_stage(self, job_id: str, stage_name: str) -> Dict[str, Any]:
        """
        Clears the requested stage and any downstream stages without re-running upstream stages.
        For instance, retrying 'rendering' preserves 'research.json', 'claims.json', 'story.json',
        'narration.json', 'storyboard.json', 'assets.json', etc.
        """
        if stage_name not in STAGE_SEQUENCE:
            raise ValueError(f"Unknown stage '{stage_name}'. Valid stages: {STAGE_SEQUENCE}")

        st = self.get_job(job_id)
        if not st:
            raise FileNotFoundError(f"Job {job_id} does not exist.")

        target_idx = STAGE_SEQUENCE.index(stage_name)
        now_iso = datetime.now().isoformat()

        # Reset target stage and all downstream stages to pending
        for i in range(target_idx, len(STAGE_SEQUENCE)):
            s = STAGE_SEQUENCE[i]
            st["stages"][s]["status"] = "pending"
            st["stages"][s]["error"] = None
            st["stages"][s]["duration_s"] = 0.0
            st["stages"][s]["details"] = ""
            st["stages"][s]["updated_at"] = now_iso

        st["status"] = f"ready_to_run_{stage_name}"
        st["current_stage"] = stage_name
        st["error"] = None
        st["progress_percent"] = self._calculate_progress(st)
        st["updated_at"] = now_iso

        self._save_status(job_id, st)
        return st

    def _calculate_progress(self, job_state: Dict[str, Any]) -> int:
        total = 0
        for stage_name, info in job_state.get("stages", {}).items():
            weight = STAGE_WEIGHTS.get(stage_name, 10)
            status = info.get("status")
            if status == "done":
                total += weight
            elif status == "in_progress":
                total += weight // 2
        return min(100, total)

    def _save_status(self, job_id: str, state: Dict[str, Any]) -> None:
        status_path = self.get_job_dir(job_id) / "status.json"
        with open(status_path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
