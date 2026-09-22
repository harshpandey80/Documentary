import json
import xml.etree.ElementTree as ET
from pathlib import Path
from docstudio.config import DEFAULT_WIDTH, DEFAULT_HEIGHT, DEFAULT_FPS

class TimelineClip:
    def __init__(
        self,
        clip_id: str,
        asset_path: str,
        start_time: float,
        end_time: float,
        duration: float,
        motion: str = "zoom_in",
        intensity: int = 3,
        emotional_tag: str = "tension",
    ):
        self.clip_id = clip_id
        self.asset_path = asset_path
        self.start_time = start_time
        self.end_time = end_time
        self.duration = duration
        self.motion = motion
        self.intensity = intensity
        self.emotional_tag = emotional_tag

    def to_dict(self) -> dict:
        return {
            "clip_id": self.clip_id,
            "asset_path": self.asset_path,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration": self.duration,
            "motion": self.motion,
            "intensity": self.intensity,
            "emotional_tag": self.emotional_tag,
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            clip_id=data["clip_id"],
            asset_path=data["asset_path"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            duration=data["duration"],
            motion=data.get("motion", "zoom_in"),
            intensity=data.get("intensity", 3),
            emotional_tag=data.get("emotional_tag", "tension"),
        )

class DocumentaryTimeline:
    """
    Agent-programmable multi-track timeline inspired by Palmier Pro.
    Allows AI agents and users to inspect, swap b-roll, ripple-trim cuts,
    and export to Final Cut Pro XML (FCPXML) / DaVinci Resolve.
    """
    def __init__(self, run_dir: Path, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT, fps: int = DEFAULT_FPS):
        self.run_dir = run_dir
        self.width = width
        self.height = height
        self.fps = fps
        self.timeline_file = run_dir / "timeline.json"
        self.video_clips: list[TimelineClip] = []
        self.audio_track_path: str = ""
        self.subtitle_track_path: str = ""

        if self.timeline_file.exists():
            self.load()

    def build_from_pipeline(
        self,
        timeline_shots: list[dict],
        visual_assets: dict[str, Path],
        master_audio_path: Path,
        captions_ass_path: Path,
    ):
        """Construct the multi-track timeline model from a pipeline render"""
        self.video_clips = []
        self.audio_track_path = str(master_audio_path)
        self.subtitle_track_path = str(captions_ass_path)

        for shot in timeline_shots:
            sc_id = shot["scene_id"]
            parent_id = shot.get("parent_scene_id", sc_id)
            img_path = str(visual_assets.get(sc_id) or visual_assets.get(parent_id) or "")

            clip = TimelineClip(
                clip_id=sc_id,
                asset_path=img_path,
                start_time=shot["start_time"],
                end_time=shot["end_time"],
                duration=shot["duration"],
                motion=shot.get("motion", "zoom_in"),
                intensity=shot.get("intensity", 3),
                emotional_tag=shot.get("emotional_tag", "tension"),
            )
            self.video_clips.append(clip)

        self.save()

    def swap_clip(self, clip_id: str, new_asset_path: str) -> bool:
        """Swap out a B-roll image or clip for an existing scene (Palmier Pro feature)"""
        for clip in self.video_clips:
            if clip.clip_id == clip_id or clip.clip_id.startswith(f"{clip_id}_"):
                clip.asset_path = new_asset_path
                self.save()
                return True
        return False

    def trim_clip(self, clip_id: str, delta_seconds: float) -> bool:
        """Ripple trim a scene duration and adjust subsequent clips (Palmier Pro feature)"""
        found_idx = -1
        for i, clip in enumerate(self.video_clips):
            if clip.clip_id == clip_id:
                found_idx = i
                break

        if found_idx == -1:
            return False

        target_clip = self.video_clips[found_idx]
        new_dur = max(1.0, target_clip.duration + delta_seconds)
        actual_delta = new_dur - target_clip.duration
        target_clip.duration = round(new_dur, 3)
        target_clip.end_time = round(target_clip.start_time + new_dur, 3)

        # Ripple subsequent clips
        for j in range(found_idx + 1, len(self.video_clips)):
            c = self.video_clips[j]
            c.start_time = round(c.start_time + actual_delta, 3)
            c.end_time = round(c.end_time + actual_delta, 3)

        self.save()
        return True

    def export_fcpxml(self, output_path: Path) -> Path:
        """
        Export timeline to Apple Final Cut Pro XML 1.8 using @chatoctopus/timeline.
        Uses frame-accurate rational time math and enforces validation before writing.
        """
        import subprocess
        self.save()

        script_path = Path(__file__).resolve().parent.parent / "scripts" / "generate_fcpxml.mjs"
        if not script_path.exists():
            raise FileNotFoundError(f"FCPXML generator script not found at {script_path}")

        cmd = ["node", str(script_path), str(self.timeline_file), str(output_path)]
        res = subprocess.run(cmd, capture_output=True, text=True)

        if res.returncode != 0:
            err_msg = res.stderr.strip() or res.stdout.strip() or "Unknown validation error"
            raise RuntimeError(f"FCPXML Validation Failed: {err_msg}")

        return output_path

    def to_dict(self) -> dict:
        return {
            "version": "1.0",
            "resolution": {"width": self.width, "height": self.height, "fps": self.fps},
            "tracks": {
                "video": [c.to_dict() for c in self.video_clips],
                "audio_master": self.audio_track_path,
                "subtitles": self.subtitle_track_path,
            },
        }

    def save(self):
        """Serialize timeline to timeline.json"""
        data = self.to_dict()
        with open(self.timeline_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def load(self):
        """Load timeline from timeline.json"""
        with open(self.timeline_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.video_clips = [TimelineClip.from_dict(c) for c in data.get("tracks", {}).get("video", [])]
        self.audio_track_path = data.get("tracks", {}).get("audio_master", "")
        self.subtitle_track_path = data.get("tracks", {}).get("subtitles", "")

    def sync_to_palmier_mcp(self) -> bool:
        """
        Pushes this timeline structure to an active local Palmier Pro instance
        via MCP (http://127.0.0.1:19789/mcp) if available.
        """
        from docstudio.palmier_bridge import PalmierBridge
        bridge = PalmierBridge()
        return bridge.sync_timeline_to_mcp(self.to_dict())

