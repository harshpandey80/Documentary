"""
docstudio/autonomous_pipeline.py
================================
Autonomous Documentary Production Pipeline (Rules 0, 2, 7, 24, 26, 28, 29).

Orchestrates end-to-end documentary generation directly from a user topic:
Topic -> Deep Research -> Fact Verification -> Story Architecture -> Narration ->
Visual Director -> Shot Storyboard -> Asset Retrieval/Generation -> Motion Graphics ->
Audio Mastering -> FFmpeg Assembly / FCPXML -> Automated QC.

Key Capabilities:
1. Purely autonomous: no manual intervention or prompt steering required.
2. Persistent state: all stage checkpoints stored under jobs/<JOB_ID>/.
3. Granular scene retry: regenerates only failing scenes without repeating research or unaffected footage.
4. Resource safe: monitors disk space and cleans temp files (HP Aero 13 16GB/512GB guard).
5. DaVinci Resolve MCP bridge optional; FFmpeg is the guaranteed renderer.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import soundfile as sf

from docstudio.broll_matcher import BRollMatcher
from docstudio.captions import generate_ass_subtitles
from docstudio.claims_ledger import ClaimsLedger
from docstudio.config import (
    BASE_DIR,
    DEFAULT_CAPTION_STYLE,
    DEFAULT_VOICE,
    DOCSTUDIO_TTS_ENGINE,
    SFX_DIR,
)
from docstudio.evidence_engine import EvidenceVisualizationEngine
from docstudio.job_manager import JobManager
from docstudio.motion_graphics.dispatcher import MotionGraphicsDispatcher
from docstudio.qc_auditor import QCAuditor
from docstudio.research_engine import ResearchEngine
from docstudio.resolve_bridge import DaVinciResolveBridge
from docstudio.scriptwriter import ScriptWriter
from docstudio.storage_manager import StorageManager
from docstudio.story_engine import StoryEngine
from docstudio.timeline import DocumentaryTimeline
from docstudio.tts_engine import TTSEngine
from docstudio.video_assembler import VideoAssembler
from docstudio.visual_director.director import VisualDirector

logger = logging.getLogger("docstudio.autonomous_pipeline")


class AutonomousDocumentaryPipeline:
    def __init__(
        self,
        job_manager: Optional[JobManager] = None,
        storage_manager: Optional[StorageManager] = None,
        voice: str = DEFAULT_VOICE,
        caption_style: str = DEFAULT_CAPTION_STYLE,
        tts_engine: str = DOCSTUDIO_TTS_ENGINE,
    ):
        self.job_manager = job_manager or JobManager()
        self.storage_manager = storage_manager or StorageManager()
        self.voice = voice
        self.caption_style = caption_style
        self.tts_engine = tts_engine

        self.researcher = ResearchEngine()
        self.story_engine = StoryEngine()
        self.scriptwriter = ScriptWriter()
        self.tts = TTSEngine(voice=self.voice, engine=self.tts_engine)
        self.evidence_engine = EvidenceVisualizationEngine()
        self.graphics_dispatcher = MotionGraphicsDispatcher()
        self.qc = QCAuditor()
        self.resolve_bridge = DaVinciResolveBridge()

    def run_job(
        self,
        job_id: str,
        progress_callback: Optional[callable] = None,
        force_stages: Optional[List[str]] = None,
    ) -> dict:
        """
        Executes the 10-stage autonomous documentary production pipeline for a job.
        Stages are checked against disk checkpoints and resumed if already complete.
        """
        status_info = self.job_manager.get_job_status(job_id)
        if not status_info:
            raise ValueError(f"Job not found: {job_id}")

        topic = status_info.get("topic", "")
        cfg = status_info.get("config", {})
        target_dur_s = float(cfg.get("duration_target", 60.0))
        fmt = cfg.get("format", "youtube")
        aspect_ratio = cfg.get("aspect_ratio", "16:9")
        style = cfg.get("style", "cinematic_investigative")
        research_depth = cfg.get("research_depth", "standard")

        # Dimensions & Framerate
        if aspect_ratio == "9:16":
            width, height = 1080, 1920
        else:
            width, height = 1920, 1080
        fps = int(cfg.get("fps", 30))

        force_set = set(force_stages or [])
        job_dir = self.job_manager.get_job_dir(job_id)
        outputs_dir = self.job_manager.get_outputs_dir(job_id)

        # -----------------------------------------------------------------
        # PRE-FLIGHT HARDWARE & STORAGE CHECK
        # -----------------------------------------------------------------
        disk_status = self.storage_manager.check_disk_space(job_dir)
        if disk_status.get("warning"):
            logger.warning(f"[{job_id}] {disk_status['warning']}")

        # -----------------------------------------------------------------
        # STAGE 1: DEEP RESEARCH
        # -----------------------------------------------------------------
        if "research" in force_set or not self.job_manager.is_stage_completed(job_id, "research"):
            self.job_manager.start_stage(job_id, "research", "Conducting autonomous multi-source deep research...")
            if progress_callback:
                progress_callback("research", 20, "Synthesizing historical archives, entities, and sources...")

            try:
                research_data = self.researcher.research_topic(topic=topic, depth=research_depth)
                from docstudio.research_validator import TopicDomainValidator
                TopicDomainValidator.validate_research(research_data, topic=topic, raise_on_error=True)
            except Exception as res_err:
                logger.error(f"[{job_id}] Research validation failed: {res_err}")
                self.job_manager.update_stage_fail(job_id, "research", res_err)
                return {
                    "job_id": job_id,
                    "status": "failed",
                    "stage": "research",
                    "error": str(res_err),
                }

            self.job_manager.save_artifact(job_id, "research.json", research_data)
            self.job_manager.complete_stage(job_id, "research", {
                "entities_count": len(research_data.get("entities", [])),
                "events_count": len(research_data.get("events", [])),
                "claims_count": len(research_data.get("claims", [])),
            })
        else:
            research_data = self.job_manager.load_artifact(job_id, "research.json") or {}
            try:
                from docstudio.research_validator import TopicDomainValidator
                TopicDomainValidator.validate_research(research_data, topic=topic, raise_on_error=True)
            except Exception as res_err:
                logger.error(f"[{job_id}] Cached research failed validation: {res_err}")
                self.job_manager.update_stage_fail(job_id, "research", res_err)
                return {
                    "job_id": job_id,
                    "status": "failed",
                    "stage": "research",
                    "error": str(res_err),
                }

        # -----------------------------------------------------------------
        # STAGE 2: FACT VERIFICATION & CLAIMS PROVENANCE
        # -----------------------------------------------------------------
        if "claims" in force_set or not self.job_manager.is_stage_completed(job_id, "claims"):
            self.job_manager.start_stage(job_id, "claims", "Verifying claim provenance and evidence sources...")
            if progress_callback:
                progress_callback("claims", 40, "Auditing factual assertions against primary sources...")

            try:
                ledger = ClaimsLedger()
                ledger.ingest_research_claims(research_data)
                ledger.validate_claims_grounding(topic=topic)
                claims_data = ledger.export_json()
            except Exception as claims_err:
                logger.error(f"[{job_id}] Claims validation failed: {claims_err}")
                self.job_manager.update_stage_fail(job_id, "claims", claims_err)
                return {
                    "job_id": job_id,
                    "status": "failed",
                    "stage": "claims",
                    "error": str(claims_err),
                }

            self.job_manager.save_artifact(job_id, "claims.json", claims_data)
            self.job_manager.complete_stage(job_id, "claims", {
                "total_claims": len(claims_data.get("claims", [])),
                "verified_claims": sum(1 for c in claims_data.get("claims", []) if c.get("verification_status") == "verified"),
            })
        else:
            claims_data = self.job_manager.load_artifact(job_id, "claims.json") or {}

        # -----------------------------------------------------------------
        # STAGE 3: STORY ARCHITECTURE MODEL
        # -----------------------------------------------------------------
        if "story" in force_set or not self.job_manager.is_stage_completed(job_id, "story"):
            self.job_manager.start_stage(job_id, "story", "Structuring narrative arc and discovery beats...")
            if progress_callback:
                progress_callback("story", 60, "Formulating story model and visual intent separation...")

            try:
                story_data = self.story_engine.generate_story_model(
                    research_data=research_data,
                    target_duration_s=target_dur_s,
                    format=fmt,
                    style=style,
                )
                from docstudio.story_engine import StoryEngine
                StoryEngine.validate_story_grounding(story_data, ledger=claims_data, topic=topic, raise_on_error=True)
            except Exception as story_err:
                logger.error(f"[{job_id}] Story grounding validation failed: {story_err}")
                self.job_manager.update_stage_fail(job_id, "story", story_err)
                return {
                    "job_id": job_id,
                    "status": "failed",
                    "stage": "story",
                    "error": str(story_err),
                }

            self.job_manager.save_artifact(job_id, "story.json", story_data)
            self.job_manager.complete_stage(job_id, "story", {
                "beats_count": len(story_data.get("beats", [])),
                "central_question": story_data.get("central_question", ""),
            })
        else:
            story_data = self.job_manager.load_artifact(job_id, "story.json") or {}
            try:
                from docstudio.story_engine import StoryEngine
                StoryEngine.validate_story_grounding(story_data, ledger=claims_data, topic=topic, raise_on_error=True)
            except Exception as story_err:
                logger.error(f"[{job_id}] Cached story grounding validation failed: {story_err}")
                self.job_manager.update_stage_fail(job_id, "story", story_err)
                return {
                    "job_id": job_id,
                    "status": "failed",
                    "stage": "story",
                    "error": str(story_err),
                }

        # -----------------------------------------------------------------
        # STAGE 4: AUTONOMOUS NARRATION & NEURAL TTS
        # -----------------------------------------------------------------
        narration_audio_path = job_dir / "02_narration.wav"
        timestamps_path = job_dir / "02_word_timestamps.json"
        scenes_audio_dir = job_dir / "scenes_audio"
        scenes_audio_dir.mkdir(exist_ok=True)

        if "narration" in force_set or not self.job_manager.is_stage_completed(job_id, "narration"):
            self.job_manager.start_stage(job_id, "narration", "Generating verified documentary script and synthesising voiceover...")
            if progress_callback:
                progress_callback("narration", 30, "Synthesizing documentary voiceover with exact word boundaries...")

            runtime_str = f"{int(target_dur_s)}s" if target_dur_s <= 90 else f"{max(1, int(target_dur_s // 60))}m"
            narration_data = self.scriptwriter.generate_narration_from_story(
                story_data=story_data,
                claims_data=claims_data,
                runtime_target=runtime_str,
                style=style,
            )
            self.job_manager.save_artifact(job_id, "narration.json", narration_data)

            # Synthesize all scenes
            all_scenes = []
            for act in narration_data.get("acts", []):
                all_scenes.extend(act.get("scenes", []))

            _, word_timestamps, scene_timings, engine_used = self.tts.synthesize_scenes(
                scenes=all_scenes,
                output_audio_path=narration_audio_path,
                output_timestamps_path=timestamps_path,
                scenes_dir=scenes_audio_dir,
            )
            audio_info = sf.info(str(narration_audio_path))
            total_speech_dur = audio_info.duration

            self.job_manager.complete_stage(job_id, "narration", {
                "scenes_count": len(all_scenes),
                "total_duration_s": round(total_speech_dur, 2),
                "engine": engine_used,
            })
        else:
            narration_data = self.job_manager.load_artifact(job_id, "narration.json") or {}
            word_timestamps = []
            if timestamps_path.exists():
                with open(timestamps_path, "r", encoding="utf-8") as f:
                    word_timestamps = json.load(f)
            total_speech_dur = sf.info(str(narration_audio_path)).duration if narration_audio_path.exists() else target_dur_s

        # -----------------------------------------------------------------
        # STAGE 5: SHOT-LEVEL STORYBOARD & SHOT MANIFEST
        # -----------------------------------------------------------------
        if "storyboard" in force_set or not self.job_manager.is_stage_completed(job_id, "storyboard"):
            self.job_manager.start_stage(job_id, "storyboard", "Remote Creative Director orchestrating whole-story visual manifest...")
            if progress_callback:
                progress_callback("storyboard", 50, "Remote Creative Director planning visual narrative and shot manifest...")

            manifest_data = None
            try:
                from docstudio.remote_creative_director import RemoteCreativeDirector
                director = RemoteCreativeDirector()
                manifest_obj = director.plan_manifest(
                    topic=topic,
                    target_duration=target_dur_s,
                    aspect_ratio=aspect_ratio,
                    documentary_style=style,
                    research_data=research_data,
                    claims_data=claims_data,
                    story_data=story_data,
                    narration_data=narration_data,
                    output_file=job_dir / "shot_manifest.json",
                )
                manifest_data = manifest_obj.to_dict()
                self.job_manager.save_artifact(job_id, "shot_manifest.json", manifest_data)
            except Exception as exc:
                print(f"[Pipeline] Notice: RemoteCreativeDirector fallback triggered: {exc}")

            # Flatten narration scenes from acts or scenes
            narr_scenes_flat = []
            if narration_data.get("scenes"):
                narr_scenes_flat = list(narration_data["scenes"])
            elif narration_data.get("acts"):
                for act in narration_data.get("acts", []):
                    narr_scenes_flat.extend(act.get("scenes", []))

            manifest_scenes = manifest_data.get("scenes", []) if manifest_data else []

            if manifest_data and manifest_scenes:
                # 2. SCENE PARITY: Require len(manifest_scenes) == len(narr_scenes) before ID remapping
                if len(manifest_scenes) != len(narr_scenes_flat):
                    print(
                        f"[Pipeline] ERROR: Scene parity mismatch! Shot Manifest has {len(manifest_scenes)} scenes, "
                        f"but narration has {len(narr_scenes_flat)} scenes. Refusing to silently misalign scenes. "
                        f"Falling back to VisualDirector safe path."
                    )
                    visual_director = VisualDirector(width=width, height=height)
                    storyboard_data = visual_director.plan_documentary(
                        narration_data=narration_data,
                        story_data=story_data,
                        claims_data=claims_data,
                    )
                else:
                    # Convert manifest scenes into storyboard_data with guaranteed 1:1 parity
                    storyboard_scenes = []
                    for s_idx, sc in enumerate(manifest_scenes):
                        narr_sc = narr_scenes_flat[s_idx]
                        canonical_sc_id = narr_sc.get("scene_id") or sc.get("scene_id", f"s{s_idx+1}")
                        actual_narration = narr_sc.get("narration", sc.get("narration_text", sc.get("story_beat", "")))
                        scene_intensity = narr_sc.get("intensity", sc.get("intensity", 5))
                        scene_visual_prompt = narr_sc.get("visual_prompt", "")
                        scene_motion = narr_sc.get("motion", "zoom_in")

                        shots_list = []
                        for sh in sc.get("shots", []):
                            shot_entry = dict(sh)
                            shot_entry["scene_id"] = canonical_sc_id

                            # 3. PRESERVE DIRECTOR PROMPTS:
                            # Never overwrite a valid director prompt (from Pass 2 or Pass 1) with narration visual_prompt.
                            # Only fall back to narration visual_prompt when the director prompt is genuinely missing/empty.
                            director_prompt = sh.get("prompt")
                            if director_prompt and str(director_prompt).strip():
                                effective_prompt = str(director_prompt).strip()
                            else:
                                if scene_visual_prompt and str(scene_visual_prompt).strip():
                                    effective_prompt = str(scene_visual_prompt).strip()
                                else:
                                    effective_prompt = str(sh.get("visual_reason") or "").strip()

                            shot_entry["prompt"] = effective_prompt
                            shot_entry["visual_prompt"] = effective_prompt
                            shot_entry["visual_strategy"] = sh.get("visual_type")
                            if not shot_entry.get("motion") or shot_entry["motion"] == "subtle_cinematic_push":
                                shot_entry["motion"] = scene_motion
                            shots_list.append(shot_entry)

                        storyboard_scenes.append({
                            "scene_id": canonical_sc_id,
                            "narration": actual_narration,
                            "story_beat": sc.get("story_beat"),
                            "viewer_takeaway": sc.get("viewer_takeaway"),
                            "intensity": scene_intensity,
                            "shots": shots_list,
                        })

                    storyboard_data = {
                        "documentary_id": manifest_data.get("documentary_id", job_id),
                        "topic": topic,
                        "scenes": storyboard_scenes,
                        "metadata": {
                            "total_shots": sum(len(s.get("shots", [])) for s in storyboard_scenes),
                            "director_type": "RemoteCreativeDirector",
                            "director_notes": manifest_data.get("director_notes", ""),
                        },
                    }
            else:
                visual_director = VisualDirector(width=width, height=height)
                storyboard_data = visual_director.plan_documentary(
                    narration_data=narration_data,
                    story_data=story_data,
                    claims_data=claims_data,
                )

            self.job_manager.save_artifact(job_id, "storyboard.json", storyboard_data)
            self.job_manager.complete_stage(job_id, "storyboard", {
                "scenes_count": len(storyboard_data.get("scenes", [])),
                "total_shots": storyboard_data.get("metadata", {}).get("total_shots", 0),
                "has_shot_manifest": manifest_data is not None,
            })
        else:
            storyboard_data = self.job_manager.load_artifact(job_id, "storyboard.json") or {}

        # -----------------------------------------------------------------
        # STAGE 6: ASSET GENERATION & RETRIEVAL (MANIFEST ROUTER)
        # -----------------------------------------------------------------
        visuals_dir = job_dir / "visuals"
        visuals_dir.mkdir(exist_ok=True)
        matcher = BRollMatcher(cache_dir=visuals_dir)

        if "assets" in force_set or not self.job_manager.is_stage_completed(job_id, "assets"):
            self.job_manager.start_stage(job_id, "assets", "Acquiring authentic archival, AI cinematic, and licensed B-roll...")
            if progress_callback:
                progress_callback("assets", 60, "Matching historical evidence and cinematic footage...")

            from docstudio.remote_creative_director.provider_router import ExecutionRouter
            from docstudio.remote_creative_director.manifest_schema import ShotDirective
            router = ExecutionRouter(cache_dir=visuals_dir, run_dir=job_dir)

            from concurrent.futures import ThreadPoolExecutor, as_completed

            all_shots = []
            for sc in storyboard_data.get("scenes", []):
                sc_id = sc.get("scene_id", "s")
                for shot in sc.get("shots", []):
                    all_shots.append((sc_id, sc.get("narration", ""), shot))

            def _process_single_shot(item):
                sc_id, sc_narration, shot = item
                sh_id = shot.get("shot_id", sc_id)
                prompt = shot.get("visual_prompt", "")
                keywords = shot.get("broll_keywords", [])
                dur = float(shot.get("duration", 2.5))
                strat = shot.get("visual_type", "cinematic_still")

                asset_path = None
                if "source_strategy" in shot:
                    try:
                        shot_directive = ShotDirective.from_dict(shot)
                        asset_path = router.execute_shot(
                            shot=shot_directive,
                            topic=topic,
                            width=width,
                            height=height,
                            fps=fps,
                            scene_narration=sc_narration,
                        )
                    except Exception as r_err:
                        print(f"[Pipeline] Router shot execution notice ({sh_id}): {r_err}")

                if not asset_path:
                    asset_path = matcher.acquire_visual_for_scene(
                        scene_id=sh_id,
                        keywords=keywords,
                        visual_prompt=prompt,
                        topic=topic,
                        width=width,
                        height=height,
                        duration=dur,
                        narration=sc_narration,
                        run_dir=job_dir,
                    )
                return sc_id, sh_id, shot, asset_path

            assets_data: dict[str, str] = {}
            scene_to_shots: dict[str, list[str]] = {}
            max_workers = min(4, max(1, len(all_shots)))
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = [executor.submit(_process_single_shot, item) for item in all_shots]
                for future in as_completed(futures):
                    try:
                        sc_id, sh_id, shot, asset_path = future.result()
                        if sc_id not in scene_to_shots:
                            scene_to_shots[sc_id] = []
                        if sh_id not in scene_to_shots[sc_id]:
                            scene_to_shots[sc_id].append(sh_id)

                        if asset_path:
                            # 4. ASSET ISOLATION: Register asset ONLY under its specific shot_id.
                            # Do NOT register the first shot's asset under parent sc_id as a universal fallback.
                            assets_data[sh_id] = str(asset_path)
                            shot["asset_path"] = str(asset_path)
                    except Exception as exc:
                        print(f"[Pipeline] Error acquiring shot asset: {exc}")

            self.job_manager.save_artifact(job_id, "assets.json", assets_data)
            self.job_manager.save_artifact(job_id, "scene_shots.json", scene_to_shots)
            self.job_manager.complete_stage(job_id, "assets", {
                "assets_acquired": len(assets_data),
            })
        else:
            assets_data = self.job_manager.load_artifact(job_id, "assets.json") or {}

        # -----------------------------------------------------------------
        # STAGE 7: EVIDENCE & MOTION GRAPHICS
        # -----------------------------------------------------------------
        graphics_dir = job_dir / "graphics"
        graphics_dir.mkdir(exist_ok=True)

        if "graphics" in force_set or not self.job_manager.is_stage_completed(job_id, "graphics"):
            self.job_manager.start_stage(job_id, "graphics", "Rendering verified data charts, route maps, and timelines...")
            if progress_callback:
                progress_callback("graphics", 70, "Synthesizing evidence boards and data graphics...")

            # Extract graphic intents from evidence engine
            intents = self.evidence_engine.create_evidence_visuals(
                claims_data=claims_data,
                storyboard_data=storyboard_data,
            )

            # Render graphics through dispatcher
            rendered_graphics = self.graphics_dispatcher.render_graphics(
                intents=intents,
                output_dir=graphics_dir,
                width=width,
                height=height,
            )

            # Merge rendered graphic paths into assets_data
            for rg in rendered_graphics:
                g_shot = rg.get("shot_id")
                g_scene = rg.get("scene_id")
                g_path = rg.get("file_path")
                if g_path:
                    if g_shot:
                        assets_data[g_shot] = g_path
                    elif g_scene:
                        assets_data[g_scene] = g_path

            self.job_manager.save_artifact(job_id, "graphics.json", rendered_graphics)
            self.job_manager.save_artifact(job_id, "assets.json", assets_data)
            self.job_manager.complete_stage(job_id, "graphics", {
                "graphics_rendered": len(rendered_graphics),
            })
        else:
            rendered_graphics = self.job_manager.load_artifact(job_id, "graphics.json") or []

        # -----------------------------------------------------------------
        # STAGE 8: SOUND DESIGN & AUDIO MASTERING
        # -----------------------------------------------------------------
        master_audio_path = job_dir / "05_audio_mix.wav"
        if "audio" in force_set or not self.job_manager.is_stage_completed(job_id, "audio"):
            self.job_manager.start_stage(job_id, "audio", "Mastering 4-layer sound design and dynamic voiceover ducking (-14 LUFS)...")
            if progress_callback:
                progress_callback("audio", 80, "Mixing dialogue, background score, and semantic sound effects...")

            from docstudio.audio_mixer import AudioMixer
            mixer = AudioMixer(sfx_dir=SFX_DIR)
            all_scenes = []
            for act in narration_data.get("acts", []):
                all_scenes.extend(act.get("scenes", []))

            mixer.mix_master_audio(
                voice_audio_path=narration_audio_path,
                word_timestamps=word_timestamps,
                scenes=all_scenes,
                output_path=master_audio_path,
            )
            audio_info_dict = {
                "master_audio_path": str(master_audio_path),
                "sample_rate": 48000,
                "target_lufs": -14.0,
                "speech_gain": 1.0,
                "ducking_db": -24.0,
            }
            self.job_manager.save_artifact(job_id, "audio.json", audio_info_dict)
            self.job_manager.complete_stage(job_id, "audio", audio_info_dict)
        else:
            audio_info_dict = self.job_manager.load_artifact(job_id, "audio.json") or {}

        # -----------------------------------------------------------------
        # STAGE 9: MULTI-LAYER VIDEO ASSEMBLY & TIMELINE EXPORT
        # -----------------------------------------------------------------
        final_video_path = outputs_dir / "final.mp4"
        captions_ass_path = job_dir / "03_captions.ass"

        # Flatten timeline shots from storyboard
        timeline_shots: list[dict] = []
        curr_t = 0.0
        for sc in storyboard_data.get("scenes", []):
            sc_id = sc.get("scene_id", "s")
            for shot in sc.get("shots", []):
                sh_id = shot.get("shot_id", sc_id)
                dur = float(shot.get("duration", 2.5))
                # 4. ASSET ISOLATION: Each shot resolves its own shot_id asset — no falling back to sc_id
                asset_p = assets_data.get(sh_id) or shot.get("asset_path") or ""
                timeline_shots.append({
                    "scene_id": sh_id,
                    "parent_scene_id": sc_id,
                    "start_time": round(curr_t, 3),
                    "end_time": round(curr_t + dur, 3),
                    "duration": dur,
                    "motion": shot.get("motion", "zoom_in"),
                    "intensity": shot.get("intensity", 4),
                    "asset_path": asset_p,
                    "visual_status": shot.get("visual_status", "STOCK"),
                    "archive_source": shot.get("metadata", {}).get("archive_source", ""),
                })
                curr_t += dur

        if "rendering" in force_set or not self.job_manager.is_stage_completed(job_id, "rendering"):
            self.job_manager.start_stage(job_id, "rendering", "Rendering 1080p documentary with dynamic color grade and grain...")
            if progress_callback:
                progress_callback("rendering", 90, "FFmpeg compositing visual layers and animated subtitles...")

            # Generate subtitles
            caption_style_chosen = cfg.get("caption_style", self.caption_style)
            generate_ass_subtitles(
                word_timestamps=word_timestamps,
                output_path=captions_ass_path,
                style_name=caption_style_chosen,
                width=width,
                height=height,
            )

            # FFmpeg assembly
            assembler = VideoAssembler(width=width, height=height)
            temp_render_dir = job_dir / "temp_render"
            temp_render_dir.mkdir(exist_ok=True)

            visual_asset_map = {s["scene_id"]: Path(s["asset_path"]) for s in timeline_shots if s.get("asset_path")}
            assembler.assemble_video(
                timeline_shots=timeline_shots,
                visual_assets=visual_asset_map,
                master_audio_path=master_audio_path,
                captions_ass_path=captions_ass_path,
                output_video_path=final_video_path,
                temp_dir=temp_render_dir,
                color_grade_preset="kodak_2383",
            )

            # Export FCPXML for optional DaVinci Resolve workflow
            timeline = DocumentaryTimeline(run_dir=job_dir, width=width, height=height)
            timeline.build_from_pipeline(
                timeline_shots=timeline_shots,
                visual_assets=visual_asset_map,
                master_audio_path=master_audio_path,
                captions_ass_path=captions_ass_path,
            )
            fcpxml_path = outputs_dir / "timeline.fcpxml"
            try:
                timeline.export_fcpxml(fcpxml_path)
            except Exception as fcpxml_err:
                logger.info(f"FCPXML export notice: {fcpxml_err}")

            timeline_dict = timeline.to_dict()
            self.job_manager.save_artifact(job_id, "timeline.json", timeline_dict)
            self.job_manager.complete_stage(job_id, "rendering", {
                "output_video": str(final_video_path),
                "fcpxml_exported": fcpxml_path.exists(),
            })
        else:
            timeline_dict = self.job_manager.load_artifact(job_id, "timeline.json") or {}

        # -----------------------------------------------------------------
        # STAGE 10: AUTOMATED QUALITY CONTROL (QC)
        # -----------------------------------------------------------------
        if "qc" in force_set or not self.job_manager.is_stage_completed(job_id, "qc"):
            self.job_manager.start_stage(job_id, "qc", "Executing pre-broadcast automated quality audit...")
            if progress_callback:
                progress_callback("qc", 98, "Auditing visual coverage, claim provenance, and media integrity...")

            qc_report_path = job_dir / "qc_report.json"
            qc_result = self.qc.audit_comprehensive_qc(
                script_data=narration_data,
                timeline_shots=timeline_shots,
                word_timestamps=word_timestamps,
                total_audio_duration=total_speech_dur,
                claims_data=claims_data,
                graphics_data=rendered_graphics,
                assets_data=assets_data,
                output_report_path=qc_report_path,
            )

            # Clean ephemeral frames
            self.storage_manager.clean_job_temp_files(job_dir)

            self.job_manager.save_artifact(job_id, "qc.json", qc_result)
            self.job_manager.complete_stage(job_id, "qc", {
                "qc_status": qc_result.get("status", "PASS"),
                "failed_scenes": qc_result.get("failed_scenes", []),
            })
        else:
            qc_result = self.job_manager.load_artifact(job_id, "qc.json") or {}

        # Generate Production Run Report
        try:
            from docstudio.remote_creative_director.run_reporter import ProductionRunReporter
            from docstudio.remote_creative_director.manifest_schema import ShotManifest
            manifest_dict = self.job_manager.load_artifact(job_id, "shot_manifest.json")
            manifest_obj = ShotManifest.from_dict(manifest_dict) if manifest_dict else None
            router_stats = getattr(router, "get_router_stats", lambda: {})() if "router" in locals() else {}
            ProductionRunReporter.generate_report(
                run_id=job_id,
                topic=topic,
                status="completed" if final_video_path.exists() else "failed",
                manifest=manifest_obj,
                validation_result=None,
                router_stats=router_stats,
                final_video_path=final_video_path,
                execution_time_s=round(total_speech_dur, 2),
                output_dir=job_dir,
            )
        except Exception as rep_err:
            logger.warning(f"ProductionRunReporter notice: {rep_err}")

        # Overall Job Completion
        self.job_manager.complete_job(job_id, {
            "video_path": str(final_video_path) if final_video_path.exists() else "",
            "qc_status": qc_result.get("status", "PASS"),
            "runtime_seconds": round(total_speech_dur, 2),
        })

        return {
            "job_id": job_id,
            "status": "completed",
            "video_path": str(final_video_path),
            "qc_status": qc_result.get("status", "PASS"),
            "qc_report": qc_result,
        }

    def regenerate_scene(self, job_id: str, scene_id: str) -> dict:
        """
        Granular scene-level retry (Autonomous Rule 2):
        Regenerates ONLY the visual assets/graphics for scene_id, updates the timeline,
        and re-assembles the video without repeating deep research or unaffected scenes.
        """
        status_info = self.job_manager.get_job_status(job_id)
        if not status_info:
            raise ValueError(f"Job not found: {job_id}")

        job_dir = self.job_manager.get_job_dir(job_id)
        storyboard_data = self.job_manager.load_artifact(job_id, "storyboard.json") or {}
        assets_data = self.job_manager.load_artifact(job_id, "assets.json") or {}
        topic = status_info.get("topic", "")

        # Target scene
        target_scene = next((s for s in storyboard_data.get("scenes", []) if s.get("scene_id") == scene_id), None)
        if not target_scene:
            raise ValueError(f"Scene '{scene_id}' not found in job {job_id}")

        visuals_dir = job_dir / "visuals"
        matcher = BRollMatcher(cache_dir=visuals_dir)

        # Re-acquire assets for shots in target_scene
        for shot in target_scene.get("shots", []):
            sh_id = shot.get("shot_id", scene_id)
            prompt = shot.get("visual_prompt", "")
            keywords = shot.get("broll_keywords", [])
            dur = float(shot.get("duration", 2.5))

            new_asset = matcher.acquire_visual_for_scene(
                scene_id=sh_id,
                keywords=keywords,
                visual_prompt=prompt,
                topic=topic,
                duration=dur,
                force=True,
                run_dir=job_dir,
            )
            if new_asset:
                assets_data[sh_id] = str(new_asset)
                shot["asset_path"] = str(new_asset)

        self.job_manager.save_artifact(job_id, "assets.json", assets_data)
        self.job_manager.save_artifact(job_id, "storyboard.json", storyboard_data)

        # Re-run rendering and QC stages
        return self.run_job(job_id, force_stages=["rendering", "qc"])
