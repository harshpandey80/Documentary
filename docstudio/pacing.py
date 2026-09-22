from docstudio.config import DEAD_AIR_THRESHOLD_SECONDS

# Comprehensive 1-10 Intensity Pacing Engine based on STORY_RULES.md
INTENSITY_PACING_RULES = {
    1: {"target_shot": 6.5, "max_hold": 8.0, "min_hold": 5.0, "motion": "subtle_drift", "ducking_db": -26, "vacuum_pre": False},
    2: {"target_shot": 6.0, "max_hold": 7.5, "min_hold": 4.5, "motion": "subtle_drift", "ducking_db": -26, "vacuum_pre": False},
    3: {"target_shot": 5.5, "max_hold": 7.0, "min_hold": 4.0, "motion": "pan_left", "ducking_db": -20, "vacuum_pre": False},
    4: {"target_shot": 5.0, "max_hold": 6.5, "min_hold": 3.5, "motion": "pan_right", "ducking_db": -20, "vacuum_pre": False},
    5: {"target_shot": 4.5, "max_hold": 6.0, "min_hold": 3.0, "motion": "zoom_in", "ducking_db": -22, "vacuum_pre": False},
    6: {"target_shot": 4.0, "max_hold": 5.5, "min_hold": 2.8, "motion": "zoom_in", "ducking_db": -22, "vacuum_pre": False},
    7: {"target_shot": 3.5, "max_hold": 5.0, "min_hold": 2.5, "motion": "pan_left", "ducking_db": -22, "vacuum_pre": False},
    8: {"target_shot": 3.2, "max_hold": 4.8, "min_hold": 2.2, "motion": "pan_right", "ducking_db": -24, "vacuum_pre": True},
    9: {"target_shot": 3.0, "max_hold": 4.5, "min_hold": 2.0, "motion": "zoom_punch", "ducking_db": -24, "vacuum_pre": True},
    10: {"target_shot": 2.8, "max_hold": 4.2, "min_hold": 1.8, "motion": "zoom_punch", "ducking_db": -26, "vacuum_pre": True},
}

class PacingOptimizer:
    def __init__(self, dead_air_threshold: float = DEAD_AIR_THRESHOLD_SECONDS):
        self.dead_air_threshold = dead_air_threshold

    def calculate_scene_timings(
        self,
        scenes: list[dict],
        total_audio_duration: float,
        word_timestamps: list[dict],
        scene_timings: dict | None = None,
        max_cut_duration: float = 2.4,
        rapid_cuts: bool = True,
    ) -> list[dict]:
        """
        Calculates exact start, end, and duration for each scene tied to STORY_RULES.md's
        1-10 beat intensity scale.
        When rapid_cuts is True (standard for YouTube Shorts/TikTok), enforces a hard
        upper limit of <= max_cut_duration (default 3.0s) per visual shot so the video
        maintains constant visual momentum and prevents viewer drop-off.
        """
        total_scenes = len(scenes)
        if total_scenes == 0:
            return []

        # Derive timings strictly from word_timestamps if scene_timings not provided
        derived_timings = {}
        if not scene_timings and word_timestamps:
            has_scene_ids = any(w.get("scene_id") for w in word_timestamps)
            if has_scene_ids:
                for sc in scenes:
                    sc_id = sc.get("scene_id", "")
                    sc_words = [w for w in word_timestamps if w.get("scene_id") == sc_id]
                    if sc_words:
                        derived_timings[sc_id] = {
                            "start": sc_words[0]["start"],
                            "end": sc_words[-1]["end"],
                            "duration": sc_words[-1]["end"] - sc_words[0]["start"],
                        }
            else:
                import re
                w_cursor = 0
                for sc in scenes:
                    sc_id = sc.get("scene_id", "")
                    clean_words = [re.sub(r"[^\w]", "", w.lower()) for w in sc.get("narration", "").split() if w and not w.startswith("[")]
                    clean_words = [w for w in clean_words if w]
                    if not clean_words:
                        continue
                    matched = []
                    for cw in clean_words:
                        for k in range(w_cursor, min(w_cursor + 25, len(word_timestamps))):
                            cand_w = re.sub(r"[^\w]", "", str(word_timestamps[k].get("word", "")).lower())
                            if cand_w == cw:
                                matched.append(word_timestamps[k])
                                w_cursor = k + 1
                                break
                    if matched:
                        derived_timings[sc_id] = {
                            "start": matched[0]["start"],
                            "end": matched[-1]["end"],
                            "duration": matched[-1]["end"] - matched[0]["start"],
                        }

        active_timings = scene_timings or derived_timings

        timeline_shots = []
        fallback_current_time = 0.0

        # Build clean sequential scene timeline based on spoken word anchors
        for idx, scene in enumerate(scenes):
            sc_id = scene.get("scene_id", f"s{idx}")
            intensity = int(scene.get("intensity", 5))
            intensity = max(1, min(10, intensity))  # Clamp to 1-10
            pacing_rule = INTENSITY_PACING_RULES.get(intensity, INTENSITY_PACING_RULES[5])
            
            # For Shorts / high-cadence storytelling, enforce rapid cuts at <= 2.4s
            effective_max_hold = min(pacing_rule["max_hold"], max_cut_duration) if rapid_cuts else pacing_rule["max_hold"]

            # Determine exact scene boundaries derived from actual word timestamps
            if active_timings and sc_id in active_timings:
                t_info = active_timings[sc_id]
                scene_start = float(t_info["start"])
                # Ensure continuity: start at fallback_current_time if earlier
                if scene_start < fallback_current_time:
                    scene_start = fallback_current_time
                scene_end = float(t_info.get("end", scene_start + float(t_info.get("duration", 2.4))))
            else:
                # When timings missing for a scene, anchor directly to timeline cursor
                scene_start = fallback_current_time
                scene_end = scene_start + 2.4

            # If not the last scene, advance scene_end up to the next scene's start to eliminate dead gaps
            if idx < total_scenes - 1:
                next_sc_id = scenes[idx + 1].get("scene_id", f"s{idx+1}")
                if active_timings and next_sc_id in active_timings:
                    next_start = float(active_timings[next_sc_id]["start"])
                    if next_start > scene_start:
                        scene_end = next_start
            else:
                # Last scene extends to total audio duration with safe 0.8s outro buffer
                scene_end = max(scene_end, total_audio_duration)

            scene_duration = max(0.5, round(scene_end - scene_start, 3))
            fallback_current_time = scene_end

            motion = scene.get("motion") or pacing_rule["motion"]
            sub_prompts = scene.get("sub_prompts", [])
            sub_keywords = scene.get("sub_keywords", [])
            broll_keywords = scene.get("broll_keywords", [])

            # If scene duration exceeds the maximum hold for this intensity level (or rapid cuts <= 3.0s),
            # subdivide into dynamic rhythmic sub-shots with alternating motion
            # strictly bounded within [scene_start, scene_end]
            if scene_duration > effective_max_hold:
                num_sub_shots = int(scene_duration // effective_max_hold) + 1
                sub_shot_dur = scene_duration / num_sub_shots
                motions_palette = ["zoom_in", "pan_left", "zoom_punch", "pan_right", "zoom_out"]

                for sub_i in range(num_sub_shots):
                    sub_motion = motions_palette[(idx * 2 + sub_i) % len(motions_palette)]
                    if intensity >= 8 and sub_i % 2 == 1:
                        sub_motion = "zoom_punch"

                    sub_start = round(scene_start + sub_i * sub_shot_dur, 3)
                    sub_end = round(scene_start + (sub_i + 1) * sub_shot_dur, 3) if sub_i < num_sub_shots - 1 else round(scene_end, 3)
                    actual_sub_dur = round(sub_end - sub_start, 3)

                    # Targeted visual prompt & keywords for this specific 2.5-3.0s cut
                    if sub_prompts and sub_i < len(sub_prompts):
                        shot_prompt = sub_prompts[sub_i]
                    else:
                        shot_prompt = scene.get("visual_prompt", "")

                    if sub_keywords and sub_i < len(sub_keywords):
                        shot_keywords = sub_keywords[sub_i]
                    elif broll_keywords:
                        shot_keywords = [broll_keywords[sub_i % len(broll_keywords)]]
                    else:
                        shot_keywords = []

                    sub_archetypes = scene.get("sub_archetypes", [])
                    shot_archetype = sub_archetypes[sub_i] if (sub_archetypes and sub_i < len(sub_archetypes)) else scene.get("archetype", "")

                    timeline_shots.append({
                        "scene_id": f"{sc_id}_sub{sub_i}",
                        "parent_scene_id": sc_id,
                        "intensity": intensity,
                        "emotional_tag": scene.get("emotional_tag", "tension"),
                        "start_time": sub_start,
                        "end_time": sub_end,
                        "duration": actual_sub_dur,
                        "offset_in_scene": round(sub_start - scene_start, 3),
                        "motion": sub_motion,
                        "broll_keywords": shot_keywords,
                        "visual_prompt": shot_prompt,
                        "archetype": shot_archetype,
                        "sfx": scene.get("sfx", []) if sub_i == 0 else [],
                        "vacuum_pre": pacing_rule["vacuum_pre"] if sub_i == 0 else False,
                    })
            else:
                timeline_shots.append({
                    "scene_id": sc_id,
                    "parent_scene_id": sc_id,
                    "intensity": intensity,
                    "emotional_tag": scene.get("emotional_tag", "tension"),
                    "start_time": round(scene_start, 3),
                    "end_time": round(scene_end, 3),
                    "duration": round(scene_duration, 3),
                    "offset_in_scene": 0.0,
                    "motion": motion,
                    "broll_keywords": scene.get("broll_keywords", []),
                    "visual_prompt": scene.get("visual_prompt", ""),
                    "archetype": scene.get("archetype", ""),
                    "sfx": scene.get("sfx", []),
                    "vacuum_pre": pacing_rule["vacuum_pre"],
                })

        return timeline_shots

    def detect_dead_air(self, word_timestamps: list[dict]) -> list[dict]:
        """Scans for awkward silent gaps exceeding dead_air_threshold (1.2s)"""
        dead_air_incidents = []
        for i in range(len(word_timestamps) - 1):
            gap = word_timestamps[i + 1]["start"] - word_timestamps[i]["end"]
            if gap > self.dead_air_threshold:
                dead_air_incidents.append({
                    "after_word": word_timestamps[i]["word"],
                    "before_word": word_timestamps[i + 1]["word"],
                    "gap_duration": round(gap, 2),
                    "timestamp": round(word_timestamps[i]["end"], 2),
                })
        return dead_air_incidents
