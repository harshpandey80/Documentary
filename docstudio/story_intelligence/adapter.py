"""
docstudio/story_intelligence/adapter.py
=======================================
Adapts MasterStoryOutput into backward-compatible story.json and narration.json
formats required by RemoteCreativeDirector, AutonomousPipeline, and TTSEngine.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List

from docstudio.story_intelligence.models import MasterStoryOutput, StoryBeat


class StoryAdapter:
    """Bridges MasterStoryOutput to legacy downstream documentary representations."""

    @staticmethod
    def to_legacy_story_json(master: MasterStoryOutput) -> Dict[str, Any]:
        """Converts MasterStoryOutput into docstudio story.json structure."""
        beats_json = []
        for b in master.beats:
            mood_val = "tension"
            if b.intensity >= 8:
                mood_val = "dramatic"
            elif "investigat" in b.purpose.lower():
                mood_val = "investigative"
            elif "revelation" in b.purpose.lower() or "climax" in b.purpose.lower():
                mood_val = "reveal"

            story_func = "investigation"
            if "hook" in b.purpose.lower() or "cold" in b.purpose.lower():
                story_func = "hook"
            elif "climax" in b.purpose.lower() or "payoff" in b.purpose.lower() or "peak" in b.purpose.lower():
                story_func = "revelation"
            elif "resolution" in b.purpose.lower() or "echo" in b.purpose.lower():
                story_func = "resolution"
            elif "contradiction" in b.purpose.lower() or "discrepancy" in b.purpose.lower():
                story_func = "contradiction"

            beats_json.append({
                "beat_id": b.beat_id,
                "beat_name": b.purpose,
                "story_function": story_func,
                "viewer_learning": b.information_revealed or b.narration_intent,
                "viewer_seeing_intent": b.visual_intent,
                "target_duration_s": b.target_duration_s,
                "claim_ids": b.claim_ids,
                "intensity": b.intensity,
                "mood": mood_val,
                "truth_category": b.truth_category,
                "transition_type": b.transition_type,
            })

        total_dur = sum(b.target_duration_s for b in master.beats)

        return {
            "topic": master.topic,
            "story_id": master.story_id,
            "logline": f"An unvarnished investigation into {master.topic}, anchored by the thesis: {master.thesis.formatted_thesis}",
            "central_question": master.meaning_test.question,
            "stakes": master.meaning_test.stakes,
            "structure_type": "investigative_forensic",
            "target_total_duration_s": total_dur,
            "thesis": master.thesis.to_dict(),
            "audience": master.audience.to_dict(),
            "packaging": master.packaging.to_dict(),
            "selected_hook": master.selected_hook.to_dict(),
            "alternate_hook": master.alternate_hook.to_dict(),
            "beats": beats_json,
            "loops": [l.to_dict() for l in master.loops],
            "causality_map": [c.to_dict() for c in master.causality_map],
            "peak_timestamp_s": master.peak_timestamp_s,
            "peak_description": master.peak_description,
            "ending_echo": master.ending_echo,
            "ending_takeaway": master.meaning_test.payoff,
            "unanswered_questions": [master.meaning_test.question],
            "status": master.status,
            "human_approved": master.human_approved,
            "human_notes": master.human_notes,
        }

    @staticmethod
    def to_legacy_narration_json(master: MasterStoryOutput) -> Dict[str, Any]:
        """Converts MasterStoryOutput into docstudio narration.json structure."""
        paragraphs = []
        scenes = []

        for i, b in enumerate(master.beats):
            pid = f"P{i+1:02d}"
            sid = f"S{i+1:02d}"

            # Emotional tag mapping
            etag = "tension"
            if b.intensity >= 9:
                etag = "reveal"
            elif b.intensity <= 4:
                etag = "somber"
            elif "climax" in b.purpose.lower() or "payoff" in b.purpose.lower():
                etag = "triumphant"

            # Motion mapping
            motion_choice = "zoom_in"
            if b.intensity >= 8:
                motion_choice = "zoom_punch"
            elif b.intensity <= 4:
                motion_choice = "subtle_drift"
            elif i % 2 == 0:
                motion_choice = "pan_left"
            else:
                motion_choice = "zoom_out"

            # Extract clean broll keywords
            keywords = [
                w.lower()
                for w in re.findall(r"\b[a-zA-Z]{4,}\b", b.visual_intent + " " + master.topic)
                if w.lower() not in {"this", "that", "with", "from", "were", "been", "have", "they", "their", "into"}
            ][:5]

            # SFX triggers
            sfx_list = ["subtle_drone"]
            if b.intensity >= 8:
                sfx_list = ["impact_hit", "cinematic_riser"]
            elif "document" in b.truth_category.lower() or "archive" in b.truth_category.lower():
                sfx_list = ["camera_shutter", "paper_rustle"]

            paragraphs.append({
                "paragraph_id": pid,
                "beat_id": b.beat_id,
                "text": b.narration_draft,
                "ssml_text": b.ssml_narration,
                "claim_ids": b.claim_ids,
                "visual_intent": b.visual_intent,
                "truth_category": b.truth_category,
                "emotional_tag": etag,
            })

            scenes.append({
                "scene_id": sid,
                "beat_id": b.beat_id,
                "intensity": b.intensity,
                "emotional_tag": etag,
                "narration": b.narration_draft,
                "ssml_narration": b.ssml_narration,
                "visual_prompt": b.visual_intent,
                "truth_category": b.truth_category,
                "broll_keywords": keywords,
                "motion": motion_choice,
                "sfx": sfx_list,
                "duration_target": b.target_duration_s,
            })

        return {
            "topic": master.topic,
            "logline": f"An unvarnished investigation into {master.topic}",
            "central_open_loop": master.meaning_test.question,
            "paragraphs": paragraphs,
            "acts": [
                {
                    "act_number": 1,
                    "act_name": master.packaging.working_title,
                    "scenes": scenes,
                }
            ],
            "pronunciation_lexicon": master.pronunciation_lexicon,
            "status": master.status,
            "master_story_id": master.story_id,
        }
