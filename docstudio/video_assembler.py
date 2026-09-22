import os
import subprocess
from pathlib import Path
from docstudio.config import DEFAULT_WIDTH, DEFAULT_HEIGHT, DEFAULT_FPS
from docstudio.motion import get_ken_burns_filter

def sanitize_ffmpeg_path(path: Path) -> str:
    r"""
    Format Windows file paths for FFmpeg filtergraph arguments:
    e.g. C:\path\sub.ass -> C\\:/path/sub.ass
    """
    p_str = str(path.resolve()).replace("\\", "/")
    if len(p_str) > 1 and p_str[1] == ":":
        p_str = p_str[0] + "\\:" + p_str[2:]
    return p_str

class VideoAssembler:
    def __init__(
        self,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        fps: int = DEFAULT_FPS,
    ):
        self.width = width
        self.height = height
        self.fps = fps

    COLOR_GRADE_PRESETS = {
        "kodak_2383": "eq=contrast=1.08:brightness=0.01:saturation=1.12,colorchannelmixer=rr=1.02:gg=1.0:bb=0.96",
        "fuji_eterna": "eq=contrast=1.02:brightness=0.0:saturation=0.92,colorchannelmixer=rr=0.98:gg=1.01:bb=1.02",
        "bleach_bypass": "eq=contrast=1.22:brightness=-0.03:saturation=0.65,colorchannelmixer=rr=1.05:gg=1.02:bb=0.98",
        "monochrome_noir": "eq=contrast=1.20:brightness=-0.02:saturation=0.0,colorchannelmixer=rr=0.30:gg=0.59:bb=0.11",
        "cinematic_cool": "eq=contrast=1.06:saturation=1.05,colorchannelmixer=rr=0.98:bb=1.04",
        "archival_warm": "eq=contrast=1.1:saturation=0.95,colorchannelmixer=rr=1.04:gg=1.01:bb=0.94",
        "neutral": "eq=contrast=1.0:saturation=1.0",
    }

    def assemble_video(
        self,
        timeline_shots: list[dict],
        visual_assets: dict[str, Path],
        master_audio_path: Path,
        captions_ass_path: Path,
        output_video_path: Path,
        temp_dir: Path,
        force: bool = False,
        append_outro: bool = True,
        color_grade_preset: str = "kodak_2383",
    ) -> Path:
        """
        Assemble the final high-retention documentary video:
        1. Render video segments for each timeline shot (splicing real MP4 footage and animated motion).
        2. Concat video clips with exact audio synchronization.
        3. Apply single global color-grade preset from project.yaml.
        4. Burn word-by-word animated ASS subtitles using bundled SIL OFL fonts.
        5. Multiplex master audio bed and export broadcast-grade 1080p MP4 (BT.709, yuv420p, ~8Mbps).
        """
        temp_dir.mkdir(parents=True, exist_ok=True)
        if force:
            for old_f in temp_dir.glob("seg_*.mp4"):
                try:
                    old_f.unlink()
                except Exception:
                    pass
            concat_old = temp_dir / "concat_list.txt"
            if concat_old.exists():
                try:
                    concat_old.unlink()
                except Exception:
                    pass

        rendered_segments = []

        total_shots = len(timeline_shots)
        print(f"  [VideoAssembler] Assembling {total_shots} timeline shots ({self.width}x{self.height} @ {self.fps}fps)...")
        # 1. Render all shots to identical spec temp segments in parallel
        shots = timeline_shots
        shot_tasks = []
        for idx, shot in enumerate(shots):
            scene_id = shot.get("scene_id", shot.get("shot_id"))
            parent_id = shot.get("parent_scene_id", shot.get("scene_id", scene_id))
            asset_path = visual_assets.get(scene_id) or visual_assets.get(parent_id)

            if not asset_path or not Path(asset_path).exists():
                visuals_dir = temp_dir.parent / "04_visuals"
                cand_mp4 = visuals_dir / f"{scene_id}.mp4"
                cand_jpg = visuals_dir / f"{scene_id}.jpg"
                if not cand_mp4.exists():
                    cand_mp4 = visuals_dir / f"{parent_id}.mp4"
                if not cand_jpg.exists():
                    cand_jpg = visuals_dir / f"{parent_id}.jpg"

                if cand_mp4.exists():
                    asset_path = cand_mp4
                elif cand_jpg.exists():
                    asset_path = cand_jpg
                else:
                    available = sorted(list(visuals_dir.glob("*.mp4")) + list(visuals_dir.glob("*.jpg")))
                    asset_path = available[idx % len(available)] if available else None

            duration = shot["duration"]
            start_offset = float(shot.get("offset_in_scene", 0.0))
            motion_type = shot.get("motion", "zoom_in")
            seg_path = temp_dir / f"seg_{idx:03d}.mp4"
            shot_tasks.append((idx, asset_path, duration, motion_type, seg_path, start_offset))

        def _render_task(task):
            t_idx, t_asset, t_dur, t_motion, t_seg, t_offset = task
            if force or not t_seg.exists() or t_seg.stat().st_size < 1000:
                if (t_idx + 1) % 5 == 0 or t_idx == 0 or t_idx == total_shots - 1:
                    print(f"  [VideoAssembler] Shot {t_idx+1}/{total_shots} ({t_dur:.1f}s, offset={t_offset:.1f}s, asset: {Path(t_asset).name if t_asset else 'procedural'})...")
                self._render_shot_segment(t_asset, t_dur, t_motion, t_seg, start_offset=t_offset)
            return t_idx, t_seg

        from concurrent.futures import ThreadPoolExecutor, as_completed
        max_workers = min(4, max(1, len(shot_tasks)))
        print(f"  [VideoAssembler] Parallel rendering {len(shot_tasks)} shot segments with {max_workers} workers...")
        rendered_map = {}
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(_render_task, t) for t in shot_tasks]
            for future in as_completed(futures):
                try:
                    t_idx, t_seg = future.result()
                    rendered_map[t_idx] = t_seg
                except Exception as exc:
                    print(f"  [VideoAssembler] Segment render error: {exc}")

        rendered_segments = [rendered_map[i] for i in range(len(shot_tasks)) if i in rendered_map]

        # 2. Build concat demuxer list
        concat_list_file = temp_dir / "concat_list.txt"
        with open(concat_list_file, "w", encoding="utf-8") as f:
            for seg in rendered_segments:
                seg_abs = seg.resolve().as_posix()
                f.write(f"file '{seg_abs}'\n")

        raw_video_path = temp_dir / "concatenated_raw.mp4"
        concat_cmd = [
            "ffmpeg", "-y",
            "-f", "concat",
            "-safe", "0",
            "-i", str(concat_list_file),
            "-c", "copy",
            str(raw_video_path)
        ]
        res = subprocess.run(concat_cmd, capture_output=True, text=True)
        if res.returncode != 0:
            raise RuntimeError(f"FFmpeg concat failed: {res.stderr}")

        # 3. Apply Unified Global Color Grade & Burn ASS Subtitles
        output_video_path.parent.mkdir(parents=True, exist_ok=True)
        escaped_ass = sanitize_ffmpeg_path(captions_ass_path)
        fonts_dir_escaped = sanitize_ffmpeg_path(Path("assets/fonts"))
        grade_filter = self.COLOR_GRADE_PRESETS.get(color_grade_preset, self.COLOR_GRADE_PRESETS["kodak_2383"])
        vf_filter = f"{grade_filter},subtitles='{escaped_ass}':fontsdir='{fonts_dir_escaped}'"

        final_cmd = [
            "ffmpeg", "-y",
            "-i", str(raw_video_path),
            "-i", str(master_audio_path),
            "-vf", vf_filter,
            "-c:v", "libx264",
            "-profile:v", "high",
            "-preset", "fast",
            "-b:v", "8000k",
            "-maxrate", "8500k",
            "-bufsize", "16000k",
            "-pix_fmt", "yuv420p",
            "-color_range", "tv",
            "-colorspace", "bt709",
            "-color_primaries", "bt709",
            "-color_trc", "bt709",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "44100",
            "-ac", "2",
            "-shortest",
            str(output_video_path)
        ]
        final_res = subprocess.run(final_cmd, capture_output=True, text=True)
        if final_res.returncode != 0:
            print(f"[VideoAssembler] Subtitles filter warning: {final_res.stderr[:200]}. Retrying with base grade.")
            fallback_cmd = [
                "ffmpeg", "-y",
                "-i", str(raw_video_path),
                "-i", str(master_audio_path),
                "-vf", grade_filter,
                "-c:v", "libx264",
                "-profile:v", "high",
                "-preset", "fast",
                "-pix_fmt", "yuv420p",
                "-color_range", "tv",
                "-colorspace", "bt709",
                "-color_primaries", "bt709",
                "-color_trc", "bt709",
                "-b:v", "8000k",
                "-c:a", "aac",
                "-b:a", "192k",
                "-ar", "44100",
                "-ac", "2",
                "-shortest",
                str(output_video_path)
            ]
            subprocess.run(fallback_cmd, check=True)

        # 4. Optional Animated Channel Outro Append (Like & Subscribe / Follow)
        if append_outro:
            orientation = "vertical" if self.height > self.width else "horizontal"
            outro_path = Path(f"assets/narrated_outro_{orientation}.mp4")
            if outro_path.exists():
                base_duration = 0.0
                try:
                    probe_res = subprocess.run(
                        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", str(output_video_path)],
                        capture_output=True, text=True, check=True
                    )
                    base_duration = float(probe_res.stdout.strip())
                except Exception:
                    pass

                # If vertical and base video + outro would exceed strict 60.00s Shorts ceiling, skip external outro
                if orientation == "vertical" and (base_duration + 4.5 > 60.0):
                    print(f"  [VideoAssembler] [OUTRO] Skipping external outro: base duration is {base_duration:.1f}s, appending 4.5s outro would breach 60.00s YouTube Shorts ceiling.")
                else:
                    print(f"  [VideoAssembler] [OUTRO] Appending animated channel outro: {outro_path.name}...")
                    appended_path = temp_dir / "final_with_outro.mp4"
                    concat_cmd = [
                        "ffmpeg", "-y",
                        "-i", str(output_video_path),
                        "-i", str(outro_path),
                        "-filter_complex", "[0:v][0:a][1:v][1:a]concat=n=2:v=1:a=1[outv][outa]",
                        "-map", "[outv]",
                        "-map", "[outa]",
                        "-c:v", "libx264",
                        "-preset", "fast",
                        "-crf", "18",
                        "-c:a", "aac",
                        "-b:a", "192k",
                        str(appended_path)
                    ]
                    c_res = subprocess.run(concat_cmd, capture_output=True, text=True)
                    if c_res.returncode == 0:
                        import shutil
                        shutil.move(str(appended_path), str(output_video_path))
                        print("  [VideoAssembler] [DONE] Channel outro appended successfully!")

        return output_video_path


    def _render_shot_segment(
        self,
        asset_path: Path | None,
        duration: float,
        motion_type: str,
        output_path: Path,
        start_offset: float = 0.0,
    ):
        """Render a single shot segment from video footage or Ken Burns still photo"""
        if asset_path and Path(asset_path).exists():
            suffix = Path(asset_path).suffix.lower()
            if suffix in [".mp4", ".webm", ".mov", ".mkv", ".m4v"]:
                # Real video clip: seek to start_offset, scale, crop to target aspect ratio, loop if needed
                vf = f"scale={self.width}:{self.height}:force_original_aspect_ratio=increase,crop={self.width}:{self.height},format=yuv420p"
                cmd = [
                    "ffmpeg", "-y",
                    "-ss", f"{max(0.0, start_offset):.3f}",
                    "-stream_loop", "-1",
                    "-i", str(asset_path),
                    "-vf", vf,
                    "-t", str(duration),
                    "-r", str(self.fps),
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p",
                    "-an",
                    str(output_path)
                ]
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode == 0:
                    return
                print(f"  [VideoAssembler] Video clip render fallback: {res.stderr[:100]}")

            elif suffix in [".jpg", ".jpeg", ".png", ".webp"]:
                # Still photo: Ken Burns cinematic motion drift
                kb_filter = get_ken_burns_filter(motion_type, duration, self.width, self.height, self.fps)
                cmd = [
                    "ffmpeg", "-y",
                    "-loop", "1",
                    "-i", str(asset_path),
                    "-vf", f"{kb_filter},format=yuv420p",
                    "-t", str(duration),
                    "-r", str(self.fps),
                    "-c:v", "libx264",
                    "-preset", "ultrafast",
                    "-pix_fmt", "yuv420p",
                    "-an",
                    str(output_path)
                ]
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode == 0:
                    return

        # Fallback: Procedural atmospheric motion loop
        vf = (
            f"color=c=#090c14:s={self.width}x{self.height}:d={duration},"
            f"drawgrid=w=140:h=140:t=1:c=gray@0.12,"
            f"format=yuv420p"
        )
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", vf,
            "-t", str(duration),
            "-r", str(self.fps),
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-an",
            str(output_path)
        ]
        subprocess.run(cmd, check=True, capture_output=True)
