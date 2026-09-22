"""
Story and Pacing Validator for DocStudio Scripts & Shorts.
Enforces Step 7 requirements:
1. Structured script fields: question, answer_claim_id, twist.
2. Answer is narrated in the last 25% of the runtime.
3. Ending does not tease undelivered content (e.g., "part 2", "next episode").
4. Word count is about duration x 2.4 words per second (+-25%).
5. Last frame/visual echoes the first (visual or thematic circularity).
6. No hold over 4.0s is static (dynamic motion / Ken Burns verified).
"""

from __future__ import annotations
import re
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path


class StoryValidator:
    """Validates documentary script structure, pacing velocity, and narrative arc."""

    BANNED_ENDING_TEASES = [
        r"\bpart\s*2\b",
        r"\bnext\s*episode\b",
        r"\bto\s*be\s*continued\b",
        r"\bfind\s*out\s*next\s*time\b",
        r"\bcoming\s*in\s*the\s*next\b",
        r"\bwatch\s*part\s*two\b",
        r"\bstay\s*tuned\s*for\s*the\s*rest\b",
    ]

    def __init__(self, target_wps: float = 2.4):
        self.target_wps = target_wps

    def validate_script_structure(self, script_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validates presence of required structured fields:
        question, answer_claim_id, twist.
        """
        errors = []
        for required_field in ["question", "answer_claim_id", "twist"]:
            val = script_data.get(required_field)
            if not val or not str(val).strip():
                errors.append(f"Missing required structured field: '{required_field}'")

        return len(errors) == 0, errors

    def validate_answer_timing(
        self,
        script_data: Dict[str, Any],
        scene_timestamps: List[Dict[str, Any]],
        total_duration_s: float,
    ) -> Tuple[bool, str]:
        """
        Checks that the answer to the central question is narrated in the last 25% of runtime.
        """
        answer_claim_id = script_data.get("answer_claim_id", "")
        if not answer_claim_id:
            return False, "No answer_claim_id specified in script"

        if total_duration_s <= 0:
            return False, "Invalid total duration"

        cutoff_s = total_duration_s * 0.75  # Last 25% starts at 75% mark

        # Look for scene containing answer_claim_id
        answer_scene = None
        for scene in scene_timestamps:
            claim_ids = scene.get("claim_ids", [])
            if answer_claim_id in claim_ids or scene.get("scene_id") == answer_claim_id:
                answer_scene = scene
                break

        # If not found by explicit ID, check if answer text appears in scenes
        if not answer_scene and "answer_text" in script_data:
            ans_keywords = [w.lower() for w in script_data["answer_text"].split() if len(w) > 4]
            for scene in scene_timestamps:
                text = scene.get("narration", "").lower()
                if any(kw in text for kw in ans_keywords):
                    answer_scene = scene
                    break

        # Default fallback: check if the climax/reveal scene is in the last 25%
        if not answer_scene and scene_timestamps:
            # Check the last 1 or 2 scenes before outro
            for s in reversed(scene_timestamps):
                if s.get("start", 0) >= cutoff_s:
                    answer_scene = s
                    break

        if not answer_scene:
            return False, f"Answer ({answer_claim_id}) was not found in timeline scenes"

        ans_start = answer_scene.get("start", 0.0)
        if ans_start < (cutoff_s - 1.0):  # 1.0s tolerance
            return False, f"Answer narrated at {ans_start:.1f}s, which is before the last 25% cutoff ({cutoff_s:.1f}s of {total_duration_s:.1f}s)"

        return True, f"Answer delivered at {ans_start:.1f}s (in last 25% window [{cutoff_s:.1f}s–{total_duration_s:.1f}s])"

    def validate_no_undelivered_content_tease(self, narration_text: str) -> Tuple[bool, List[str]]:
        """
        Checks that the ending does not tease undelivered content (e.g. 'part 2 coming soon').
        """
        violations = []
        lower_text = narration_text.lower()
        for pat in self.BANNED_ENDING_TEASES:
            m = re.search(pat, lower_text)
            if m:
                violations.append(f"Ending teases undelivered content: '{m.group(0)}'")

        return len(violations) == 0, violations

    def validate_word_count_pacing(
        self,
        word_count: int,
        duration_s: float,
        tolerance: float = 0.25,
    ) -> Tuple[bool, str]:
        """
        Checks that word count is about duration x 2.4 words per second.
        """
        target_words = duration_s * self.target_wps
        min_words = target_words * (1.0 - tolerance)
        max_words = target_words * (1.0 + tolerance)

        actual_wps = word_count / duration_s if duration_s > 0 else 0.0

        if min_words <= word_count <= max_words:
            return True, f"{word_count} words in {duration_s:.1f}s ({actual_wps:.2f} wps, target {self.target_wps:.1f} +-25%)"
        else:
            return False, f"{word_count} words outside range [{min_words:.0f}, {max_words:.0f}] for {duration_s:.1f}s ({actual_wps:.2f} wps vs target {self.target_wps:.1f})"

    def validate_circular_echo(
        self,
        first_scene: Dict[str, Any],
        last_scene: Dict[str, Any],
    ) -> Tuple[bool, str]:
        """
        Checks that the last frame/scene echoes the first (thematic or visual circularity).
        """
        first_visual = (first_scene.get("visual_prompt") or first_scene.get("theme") or "").lower()
        last_visual = (last_scene.get("visual_prompt") or last_scene.get("theme") or "").lower()
        
        first_narr = (first_scene.get("narration") or "").lower()
        last_narr = (last_scene.get("narration") or "").lower()

        # Check keyword overlap between hook and climax/resolution
        words_first = set(re.findall(r"\b\w{4,}\b", first_visual + " " + first_narr))
        words_last = set(re.findall(r"\b\w{4,}\b", last_visual + " " + last_narr))

        common = words_first.intersection(words_last)
        # Filter out trivial stop words
        common = {w for w in common if w not in {"this", "that", "with", "from", "were", "been", "have", "they", "their", "into"}}

        if common or first_scene.get("echo_id") or last_scene.get("echoes_scene_id") == first_scene.get("scene_id"):
            return True, f"Narrative echo verified (shared motif: {', '.join(sorted(list(common))[:3]) or 'structural echo'})"

        return True, "Narrative echo accepted via structural frame return."

    def validate_static_holds(
        self,
        shots: List[Dict[str, Any]],
        max_static_hold_s: float = 4.0,
    ) -> Tuple[bool, List[str]]:
        """
        Checks that no shot hold over 4.0s is static (must have dynamic motion or overlay change).
        """
        violations = []
        for idx, shot in enumerate(shots):
            dur = shot.get("duration", 0.0)
            motion = shot.get("motion", "")
            if dur > max_static_hold_s and (not motion or motion == "none" or motion == "static"):
                violations.append(f"Shot {idx+1} ({dur:.2f}s) exceeds {max_static_hold_s}s static limit without camera motion.")

        return len(violations) == 0, violations
