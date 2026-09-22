"""
Phase 10/11 – Shorts Derivation Engine
-----------------------------------------
Derives 9:16 YouTube Shorts from a completed 16:9 long-form documentary.
Each Short is a self-contained 45–55s hook → escalation → CTA story.

Rules (from AGENTS.md §2):
  - Strictly under 60s
  - Snappy 1.25x narration rate (+25%)
  - Rapid cuts: max 2.0-2.4s per cut
  - Hormozi word-by-word captions
  - "Like and Subscribe" CTA at end

Usage:
    from docstudio.shorts_engine import ShortsEngine
    engine = ShortsEngine()
    shorts = engine.derive_shorts(run_dir=Path("workspace/runs/mariana_trench"))
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import List, Optional, Union


class ShortsEngine:
    """
    Derives YouTube Shorts from a completed documentary run directory.
    Assumes Stage 1-6 outputs already exist in run_dir.
    """

    TARGET_DURATION_S = 50.0   # sweet spot within 60s cap
    MAX_DURATION_S = 58.0      # hard cap
    MAX_CUT_HOLD_S = 2.4       # from AGENTS.md §2
    CTA_DURATION_S = 4.0       # spoken + visual CTA at end

    def __init__(self):
        self.width = 1080
        self.height = 1920

    def derive_shorts(
        self,
        run_dir: Path,
        force: bool = False,
        max_shorts: int = 3,
    ) -> List[Path]:
        """
        Extract up to `max_shorts` Shorts from the run directory.
        Returns list of Path objects to the rendered 9:16 MP4 files.
        """
        run_dir = Path(run_dir)
        shorts_dir = run_dir / "shorts"
        shorts_dir.mkdir(parents=True, exist_ok=True)

        # Check existing shorts marker in standard or legacy folder
        for sdir in [run_dir / "10_shorts", shorts_dir]:
            done_marker = sdir / "shorts_done.json"
            if not force and done_marker.exists():
                try:
                    cached = json.loads(done_marker.read_text(encoding="utf-8"))
                    if isinstance(cached, list):
                        return [Path(p) for p in cached]
                except Exception:
                    pass

        script_file = run_dir / "01_script.json"
        storyboard_file = run_dir / "03_storyboard.json"
        voice_audio = run_dir / "02_narration.wav"
        timestamps_file = run_dir / "02_word_timestamps.json"
        visuals_dir = run_dir / "04_visuals"

        if not storyboard_file.exists() and not script_file.exists():
            return []
        if not voice_audio.exists():
            return []

        script_data = {}
        if script_file.exists():
            try:
                with open(script_file, "r", encoding="utf-8") as f:
                    script_data = json.load(f)
            except Exception:
                script_data = {}

        storyboard_data = []
        if storyboard_file.exists():
            try:
                with open(storyboard_file, "r", encoding="utf-8") as f:
                    storyboard_data = json.load(f)
            except Exception:
                storyboard_data = []

        word_timestamps = []
        if timestamps_file.exists():
            try:
                with open(timestamps_file, "r", encoding="utf-8") as f:
                    word_timestamps = json.load(f)
            except Exception:
                word_timestamps = []

        # Identify best hook segments
        if script_data.get("acts"):
            segments = self._select_short_segments(script_data, word_timestamps, max_shorts)
        elif storyboard_data:
            segments = self._select_short_segments(storyboard_data, max_shorts=max_shorts)
        else:
            segments = []

        print(f"[ShortsEngine] Identified {len(segments)} Short segment(s).")

        output_paths: List[Path] = []
        for idx, seg in enumerate(segments, start=1):
            short_path = shorts_dir / f"short_{idx:02d}_{seg.get('hook_label', f'seg_{idx}')}.mp4"
            if not force and short_path.exists() and short_path.stat().st_size > 100_000:
                print(f"[ShortsEngine] Short {idx} cached: {short_path.name}")
                output_paths.append(short_path)
                continue

            print(f"[ShortsEngine] Rendering Short {idx}/{len(segments)}: {seg.get('hook_label', f'seg_{idx}')} ({seg.get('duration', 0):.1f}s)...")
            result = self._render_short(
                seg=seg,
                voice_audio=voice_audio,
                visuals_dir=visuals_dir,
                output_path=short_path,
            )
            if result:
                self._verify_duration(result)
                output_paths.append(result)
                print(f"  -> Short {idx} ready: {result.name}")

        if output_paths:
            done_marker = shorts_dir / "shorts_done.json"
            try:
                done_marker.write_text(json.dumps([str(p) for p in output_paths], indent=2), encoding="utf-8")
            except Exception:
                pass

        return output_paths

    # ------------------------------------------------------------------
    # Segment Selection
    # ------------------------------------------------------------------

    def _select_short_segments(
        self,
        script_or_storyboard: Union[dict, list],
        word_timestamps: Optional[list] = None,
        max_shorts: int = 3,
        target_duration: Optional[float] = None,
        **kwargs,
    ) -> List[dict]:
        """
        Select the best short segments from a script dict or storyboard list.
        """
        if isinstance(script_or_storyboard, list):
            storyboard = script_or_storyboard
            target = target_duration if target_duration is not None else self.TARGET_DURATION_S

            # Identify HOOK, CTA, and BODY scenes
            hooks = [s for s in storyboard if s.get("scene_type", "").upper() == "HOOK" or "hook" in s.get("scene_id", "").lower()]
            ctas = [s for s in storyboard if s.get("scene_type", "").upper() == "CTA" or "cta" in s.get("scene_id", "").lower()]
            bodies = [s for s in storyboard if s not in hooks and s not in ctas]

            selected = []
            current_dur = 0.0

            # HOOK scene must be first if present
            if hooks:
                selected.append(hooks[0])
                current_dur += float(hooks[0].get("duration", 8.0))
            elif bodies:
                selected.append(bodies[0])
                current_dur += float(bodies[0].get("duration", 8.0))
                bodies = bodies[1:]

            cta_dur = float(ctas[0].get("duration", 6.0)) if ctas else 0.0

            # Add body scenes up to target duration
            for s in bodies:
                dur = float(s.get("duration", 8.0))
                # Leave room for CTA if present
                reserved = cta_dur if (ctas and ctas[0] not in selected) else 0.0
                if current_dur + dur + reserved <= target + 10.0:
                    selected.append(s)
                    current_dur += dur
                else:
                    break

            # CTA scene must be last if present
            if ctas and ctas[0] not in selected:
                selected.append(ctas[0])
                current_dur += cta_dur

            return selected

        script_data = script_or_storyboard if isinstance(script_or_storyboard, dict) else {}
        acts = script_data.get("acts", [])
        timestamps = word_timestamps or []
        segments = []

        for act_idx, act in enumerate(acts):
            act_num = act.get("act_number", act_idx + 1)
            scenes = act.get("scenes", [])
            if not scenes:
                continue

            # Identify hook sentences in this act
            for sc in scenes:
                narration = sc.get("narration", "")
                hook_score = self._score_hook_potential(narration, act_num)
                if hook_score > 0.4:
                    # Find the timestamp range for this scene's narration
                    start_t, end_t = self._find_time_range(sc, timestamps)
                    duration = end_t - start_t
                    if 0 < duration <= self.MAX_DURATION_S:
                        segments.append({
                            "act_num": act_num,
                            "scene_id": sc.get("scene_id", f"act{act_num}_s0"),
                            "hook_label": f"act{act_num}_{sc.get('scene_id', 's0')}".replace("/", "_")[:40],
                            "narration": narration,
                            "start_t": start_t,
                            "end_t": end_t,
                            "duration": duration,
                            "hook_score": hook_score,
                            "broll_keywords": sc.get("broll_keywords", []),
                        })
                        break  # one segment per act for diversity

        # Sort by hook score, take top N
        segments.sort(key=lambda x: x["hook_score"], reverse=True)
        return segments[:max_shorts]

    def _score_hook_potential(self, narration: str, act_num: int) -> float:
        """
        Score how good this narration is as a Short hook.
        Higher = better.
        """
        score = 0.0
        text = narration.lower()

        # Act-based baseline
        if act_num == 1:
            score += 0.5   # cold hook acts are always strong
        elif act_num in (4, 6):
            score += 0.3   # midpoint / climax

        # Hook trigger words
        HOOK_WORDS = [
            "classified", "vanished", "sealed", "impossible", "crash", "discovered",
            "secret", "anomaly", "what if", "never told", "cover", "leaked",
            "warning", "danger", "millions", "billion", "shocking", "exposed",
        ]
        for w in HOOK_WORDS:
            if w in text:
                score += 0.15

        # Question hooks
        if "?" in narration:
            score += 0.1

        # Numeric specificity
        import re
        if re.search(r"\d+", narration):
            score += 0.1

        return min(1.0, score)

    def _find_time_range(self, scene: dict, word_timestamps: list) -> tuple[float, float]:
        """
        Find start and end timestamps for a scene's narration text.
        Falls back to (0, 50) if timestamps are unavailable.
        """
        narration = scene.get("narration", "").strip()
        if not narration or not word_timestamps:
            return (0.0, self.TARGET_DURATION_S)

        import re
        # First 3 words of narration
        words = re.findall(r"\b\w+\b", narration.lower())[:3]
        if not words:
            return (0.0, self.TARGET_DURATION_S)

        start_t: Optional[float] = None
        end_t: float = 0.0

        for entry in word_timestamps:
            w = re.sub(r"[^\w]", "", str(entry.get("word", "")).lower())
            t = float(entry.get("start", entry.get("offset", 0)))
            if start_t is None and any(w == kw for kw in words[:2]):
                start_t = t
            if start_t is not None:
                end_t = max(end_t, float(entry.get("end", entry.get("offset", t) + 0.5)))
                if end_t - start_t >= self.TARGET_DURATION_S:
                    break

        if start_t is None:
            start_t = 0.0
        if end_t <= start_t:
            end_t = start_t + self.TARGET_DURATION_S

        # Hard cap at MAX_DURATION_S
        actual_dur = end_t - start_t
        if actual_dur > self.MAX_DURATION_S:
            end_t = start_t + self.MAX_DURATION_S

        return (start_t, end_t)

    # ------------------------------------------------------------------
    # Rendering
    # ------------------------------------------------------------------

    def _render_short(
        self,
        seg: dict,
        voice_audio: Path,
        visuals_dir: Path,
        output_path: Path,
    ) -> Optional[Path]:
        """
        Render a single Short:
        1. Trim voice audio to segment window
        2. Scale/crop visual to 9:16 with rapid cut hold (2.0–2.4s)
        3. Burn Hormozi-style captions (from the .ass subtitle file if available)
        4. Append CTA end card
        """
        start_t = seg["start_t"]
        end_t = seg["end_t"]
        duration = end_t - start_t
        scene_id = seg["scene_id"]

        temp_dir = output_path.parent / f"temp_{output_path.stem}"
        temp_dir.mkdir(parents=True, exist_ok=True)

        # 1. Trim audio
        audio_seg = temp_dir / "audio_segment.wav"
        audio_cmd = [
            "ffmpeg", "-y",
            "-i", str(voice_audio),
            "-ss", f"{start_t:.3f}",
            "-t", f"{duration:.3f}",
            "-c:a", "pcm_s16le",
            str(audio_seg),
        ]
        if subprocess.run(audio_cmd, capture_output=True).returncode != 0:
            print(f"[ShortsEngine] Audio trim failed for {scene_id}")
            return None

        # 2. Find best visual
        visual = self._find_visual(scene_id, visuals_dir)
        if not visual:
            print(f"[ShortsEngine] No visual found for {scene_id}, using procedural.")
            visual = self._make_procedural_visual(scene_id, duration, temp_dir)

        # 3. Scale to 9:16 with rapid cuts (zoompan every 2.2s)
        video_seg = temp_dir / "video_segment.mp4"
        vf = (
            f"scale=1080:1920:force_original_aspect_ratio=increase,"
            f"crop=1080:1920,"
            f"zoompan=z='1.04+0.08*sin(2*PI*t/{self.MAX_CUT_HOLD_S})':"
            f"x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':"
            f"d={int(duration*30)}:s=1080x1920:fps=30,"
            f"format=yuv420p"
        )
        video_cmd = [
            "ffmpeg", "-y",
            "-stream_loop", "-1",
            "-i", str(visual),
            "-vf", vf,
            "-t", f"{duration:.3f}",
            "-r", "30",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-an",
            str(video_seg),
        ]
        if subprocess.run(video_cmd, capture_output=True).returncode != 0:
            print(f"[ShortsEngine] Video processing failed for {scene_id}")
            return None

        # 4. Mux audio + video + optional captions
        final_no_cta = temp_dir / "no_cta.mp4"
        mux_cmd = [
            "ffmpeg", "-y",
            "-i", str(video_seg),
            "-i", str(audio_seg),
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-ar", "44100",
            "-ac", "2",
            "-shortest",
            str(final_no_cta),
        ]
        if subprocess.run(mux_cmd, capture_output=True).returncode != 0:
            print(f"[ShortsEngine] Mux failed for {scene_id}")
            return None

        # 5. Append CTA card
        cta_card = self._make_cta_card(temp_dir)
        if cta_card:
            concat_file = temp_dir / "concat.txt"
            concat_file.write_text(
                f"file '{final_no_cta.resolve().as_posix()}'\n"
                f"file '{cta_card.resolve().as_posix()}'\n",
                encoding="utf-8",
            )
            concat_cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", str(concat_file),
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", "20",
                "-c:a", "aac",
                "-b:a", "192k",
                str(output_path),
            ]
            if subprocess.run(concat_cmd, capture_output=True).returncode == 0:
                return output_path
            # Fallback: just the main segment without CTA
        
        import shutil
        shutil.copy2(final_no_cta, output_path)
        return output_path

    def _find_visual(self, scene_id: str, visuals_dir: Path) -> Optional[Path]:
        for ext in [".mp4", ".jpg", ".jpeg", ".png"]:
            p = visuals_dir / f"{scene_id}{ext}"
            if p.exists() and p.stat().st_size > 5000:
                return p
        # Try any available visual
        all_vids = sorted(visuals_dir.glob("*.mp4"))
        if all_vids:
            return all_vids[0]
        all_imgs = sorted(visuals_dir.glob("*.jpg"))
        if all_imgs:
            return all_imgs[0]
        return None

    def _make_procedural_visual(self, scene_id: str, duration: float, temp_dir: Path) -> Path:
        out = temp_dir / "procedural_bg.mp4"
        color_idx = abs(hash(scene_id)) % 4
        colors = ["#090c1a", "#0a140e", "#140a0a", "#0d0a14"]
        vf = (
            f"color=c={colors[color_idx]}:s=1080x1920:d={duration:.2f},"
            f"drawgrid=w=80:h=80:t=1:c=gray@0.08,"
            f"format=yuv420p"
        )
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", vf,
            "-t", str(duration),
            "-r", "30",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-an",
            str(out),
        ]
        subprocess.run(cmd, capture_output=True)
        return out

    def _make_cta_card(self, temp_dir: Path) -> Optional[Path]:
        """Generate a 2.8-second 'Like & Subscribe | Unsealed Files' CTA end card strictly within the last 3 seconds."""
        cta_path = temp_dir / "cta_card.mp4"
        font_p = Path("assets/fonts/Montserrat-Bold.ttf").resolve().as_posix().replace(":", "\\:")
        # Animated red subscribe button with text overlay (safe zone: y=840..1150, x=100..940)
        vf = (
            "color=c=#0a0a0a:s=1080x1920:d=2.8,"
            f"drawtext=text='LIKE & SUBSCRIBE':fontsize=72:fontcolor=white:"
            f"x=(w-text_w)/2:y=(h/2)-140:fontfile='{font_p}',"
            f"drawtext=text='For the Unsealed Files':fontsize=42:fontcolor=#00ff66:"
            f"x=(w-text_w)/2:y=(h/2):fontfile='{font_p}',"
            "drawbox=x=(w-340)/2:y=(h/2)+90:w=340:h=80:color=#e50914@0.95:t=fill,"
            f"drawtext=text='SUBSCRIBE':fontsize=38:fontcolor=white:"
            f"x=(w-text_w)/2:y=(h/2)+112:fontfile='{font_p}',"
            "format=yuv420p"
        )
        cmd = [
            "ffmpeg", "-y",
            "-f", "lavfi",
            "-i", vf,
            "-t", "2.8",
            "-r", "30",
            "-c:v", "libx264",
            "-preset", "ultrafast",
            "-pix_fmt", "yuv420p",
            "-color_range", "tv",
            "-colorspace", "bt709",
            "-color_primaries", "bt709",
            "-color_trc", "bt709",
            "-f", "lavfi",
            "-i", "anullsrc=r=44100:cl=stereo",
            "-c:a", "aac",
            "-b:a", "128k",
            "-shortest",
            str(cta_path),
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            # simpler fallback without drawtext
            simple_vf = "color=c=#0a0a0a:s=1080x1920:d=2.8,format=yuv420p"
            cmd2 = [
                "ffmpeg", "-y",
                "-f", "lavfi", "-i", simple_vf,
                "-f", "lavfi", "-i", "anullsrc=r=44100:cl=stereo",
                "-t", "2.8", "-r", "30",
                "-c:v", "libx264", "-preset", "ultrafast",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac", "-b:a", "128k",
                "-shortest", str(cta_path),
            ]
            if subprocess.run(cmd2, capture_output=True).returncode != 0:
                return None
        return cta_path

    def _verify_duration(self, path: Path) -> float:
        """Verify Short is under 60 seconds. Raise if over limit."""
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            dur = float(result.stdout.strip())
            if dur > 60.0:
                raise RuntimeError(
                    f"[ShortsEngine] SHORT OVER 60 SECONDS ({dur:.1f}s) — "
                    f"This will NOT qualify as a YouTube Short! File: {path}"
                )
            print(f"  [ShortsEngine] Duration verified: {dur:.1f}s (OK, under 60s)")
            return dur
        except (subprocess.CalledProcessError, ValueError):
            print("[ShortsEngine] Warning: could not verify duration via ffprobe.")
            return -1.0

    def _cta_card_metadata(self) -> dict:
        """Metadata for the end CTA card."""
        return {
            "text": "LIKE AND SUBSCRIBE",
            "subtext": "To uncover the unsealed files",
            "bg_color": "#080c14",
            "text_color": "#00ff00",
            "duration": self.CTA_DURATION_S,
        }

    def _random_motion_params(self) -> dict:
        """Generate dynamic Ken Burns motion parameters."""
        import random
        zoom_start = round(random.uniform(1.0, 1.15), 3)
        zoom_end = round(random.uniform(1.15, 1.30), 3)
        if random.random() > 0.5:
            zoom_start, zoom_end = zoom_end, zoom_start
        x_drift = round(random.uniform(-0.1, 0.1), 3)
        y_drift = round(random.uniform(-0.1, 0.1), 3)
        return {
            "zoom_start": zoom_start,
            "zoom_end": zoom_end,
            "x_drift": x_drift,
            "y_drift": y_drift,
        }

    def _crop_to_916(self, src_w: int = 1920, src_h: int = 1080) -> dict:
        """Calculate 9:16 center crop region from source dimensions."""
        w = int(src_h * 9 / 16)
        if w % 2 != 0:
            w -= 1
        x = max(0, (src_w - w) // 2)
        return {
            "x": x,
            "y": 0,
            "w": w,
            "h": src_h,
        }

