"""
DocStudio Shot-Level Storyboard Generator.
Decomposes narration scenes into multi-shot cinematic sequences with semantic visual strategies,
multi-layer compositions, hardware-accelerated motion directives, and timing.
"""

from __future__ import annotations
import json
import math
from pathlib import Path
from typing import Dict, Any, List, Optional

from docstudio.visual_director.strategies import (
    VisualStrategy,
    VisualStatus,
    VisualLayer,
)
from docstudio.visual_director.classifier import SemanticVisualClassifier
from docstudio.visual_director.continuity import VisualContinuityTracker


class ShotStoryboardGenerator:
    """
    Generates granular, multi-shot storyboard.json from narration paragraphs and claims.
    Enforces the retention rule: maximum cut hold 2.0s - 3.5s per shot.
    """

    def __init__(
        self,
        classifier: Optional[SemanticVisualClassifier] = None,
        continuity_tracker: Optional[VisualContinuityTracker] = None,
    ):
        self.classifier = classifier or SemanticVisualClassifier()
        self.continuity_tracker = continuity_tracker

    def generate_storyboard(
        self,
        narration_data: Dict[str, Any],
        claims_data: Optional[Dict[str, Any]] = None,
        output_file: Optional[Path | str] = None,
    ) -> Dict[str, Any]:
        """
        Builds a comprehensive shot-level storyboard.
        """
        topic = narration_data.get("topic", "Documentary")
        if not self.continuity_tracker:
            self.continuity_tracker = VisualContinuityTracker(topic)

        paragraphs = narration_data.get("paragraphs", [])
        if not paragraphs and "acts" in narration_data:
            # Flatten from acts if needed
            for act in narration_data.get("acts", []):
                for sc in act.get("scenes", []):
                    paragraphs.append({
                        "paragraph_id": sc.get("paragraph_id", sc.get("scene_id")),
                        "scene_id": sc.get("scene_id"),
                        "text": sc.get("narration", ""),
                        "story_beat": sc.get("story_beat", "investigation"),
                        "claim_ids": sc.get("claim_ids", []),
                        "estimated_duration_sec": max(3.0, len(sc.get("narration", "").split()) / 2.3),
                        "visual_prompt": sc.get("visual_prompt", ""),
                        "broll_keywords": sc.get("broll_keywords", []),
                        "intensity": sc.get("intensity", 6),
                    })

        claims_map = {}
        if claims_data and "claims" in claims_data:
            for c in claims_data["claims"]:
                claims_map[c.get("claim_id")] = c

        storyboard_scenes = []
        global_time_offset = 0.0
        total_shot_counter = 1

        for sc_idx, p in enumerate(paragraphs):
            sc_id = p.get("scene_id", f"S{sc_idx+1:02d}")
            text = p.get("text", "")
            s_beat = p.get("story_beat", "investigation")
            claim_ids = p.get("claim_ids", [])
            referenced_claims = [claims_map[cid] for cid in claim_ids if cid in claims_map]
            scene_duration = float(p.get("estimated_duration_sec", 6.0))
            is_cold_hook = (sc_idx == 0)

            # Determine number of shots for this scene (target 2.0s - 3.2s per cut)
            num_shots = max(2, min(5, int(math.ceil(scene_duration / 2.6))))
            shot_duration = round(scene_duration / num_shots, 2)

            shots = []
            motion_choices = ["slow_push", "pan_left", "pan_right", "zoom_punch", "subtle_drift", "crash_zoom"]

            for s_idx in range(num_shots):
                shot_letter = chr(65 + s_idx)
                shot_id = f"{sc_id}_{shot_letter}"

                # Classify strategy & authenticity
                strategy, status, reason = self.classifier.classify_shot(
                    narration=text,
                    story_beat=s_beat,
                    seeing_intent=p.get("visual_prompt", ""),
                    keywords=p.get("broll_keywords", []),
                    referenced_claims=referenced_claims,
                    is_cold_hook=(is_cold_hook and s_idx == 0),
                    shot_index=s_idx,
                    total_shots_in_scene=num_shots,
                )

                # Determine shot purpose
                purpose = self._determine_shot_purpose(strategy, s_idx, num_shots, s_beat)

                # Build multi-layer composition stack
                layers = self._build_layer_stack(strategy, s_idx)

                # Camera motion
                if is_cold_hook and s_idx == 0:
                    motion = "zoom_punch"
                elif strategy in [VisualStrategy.MAP, VisualStrategy.ROUTE_MAP]:
                    motion = "slow_push"
                elif strategy in [VisualStrategy.DATA_CHART, VisualStrategy.STATISTIC]:
                    motion = "subtle_drift"
                else:
                    motion = motion_choices[(sc_idx + s_idx) % len(motion_choices)]

                # Continuity-enriched prompt
                base_prompt = p.get("visual_prompt", f"{topic} {purpose}")
                enriched_prompt = self.continuity_tracker.enrich_prompt(base_prompt, scene_context=text)

                shot_start = round(global_time_offset, 2)
                shot_end = round(global_time_offset + shot_duration, 2)
                global_time_offset += shot_duration

                shots.append({
                    "shot_id": shot_id,
                    "shot_number": total_shot_counter,
                    "purpose": purpose,
                    "visual_type": strategy.value,
                    "visual_strategy": strategy.value,
                    "visual_status": status.value,
                    "strategy_reason": reason,
                    "duration": shot_duration,
                    "start_time_s": shot_start,
                    "end_time_s": shot_end,
                    "motion": motion,
                    "layers": [l.value for l in layers],
                    "prompt": enriched_prompt,
                    "broll_keywords": p.get("broll_keywords", [topic]),
                    "sfx_cue": "deep_braam" if (is_cold_hook and s_idx == 0) else ("whoosh" if s_idx > 0 else ""),
                })
                total_shot_counter += 1

            storyboard_scenes.append({
                "scene_id": sc_id,
                "paragraph_id": p.get("paragraph_id", f"P{sc_idx+1:02d}"),
                "story_beat": s_beat,
                "viewer_takeaway": p.get("viewer_learning", text[:100]),
                "narration": text,
                "claim_ids": claim_ids,
                "scene_duration_s": round(scene_duration, 2),
                "shots": shots,
            })

        storyboard_data = {
            "topic": topic,
            "total_scenes": len(storyboard_scenes),
            "total_shots": total_shot_counter - 1,
            "total_duration_s": round(global_time_offset, 2),
            "scenes": storyboard_scenes,
        }

        if output_file:
            out_p = Path(output_file)
            out_p.parent.mkdir(parents=True, exist_ok=True)
            with open(out_p, "w", encoding="utf-8") as f:
                json.dump(storyboard_data, f, indent=2, ensure_ascii=False)

        return storyboard_data

    def _determine_shot_purpose(
        self,
        strategy: VisualStrategy,
        shot_idx: int,
        total_shots: int,
        story_beat: str,
    ) -> str:
        if strategy in [VisualStrategy.MAP, VisualStrategy.ROUTE_MAP]:
            return "explain_movement_and_geography"
        elif strategy in [VisualStrategy.DATA_CHART, VisualStrategy.STATISTIC]:
            return "quantify_scale_and_trend"
        elif strategy in [VisualStrategy.PRIMARY_DOCUMENT, VisualStrategy.DOCUMENT_HIGHLIGHT]:
            return "present_forensic_evidence"
        elif strategy in [VisualStrategy.COMPARISON, VisualStrategy.EVIDENCE_MATRIX]:
            return "demonstrate_contradiction"
        elif strategy in [VisualStrategy.AI_CINEMATIC_VIDEO, VisualStrategy.HUMAN_RECONSTRUCTION]:
            return "emotional_and_crisis_reconstruction"
        elif strategy in [VisualStrategy.ARCHIVAL_PHOTO, VisualStrategy.ARCHIVAL_VIDEO]:
            return "anchor_historical_reality"
        elif shot_idx == 0:
            return "establish_location"
        else:
            return "maintain_narrative_momentum"

    def _build_layer_stack(self, strategy: VisualStrategy, shot_idx: int) -> List[VisualLayer]:
        layers = [VisualLayer.BACKGROUND, VisualLayer.PRIMARY_VISUAL]
        if strategy in [VisualStrategy.PRIMARY_DOCUMENT, VisualStrategy.DOCUMENT_HIGHLIGHT, VisualStrategy.QUOTE_CARD]:
            layers.append(VisualLayer.ANNOTATION)
            layers.append(VisualLayer.TYPOGRAPHY)
        elif strategy in [VisualStrategy.MAP, VisualStrategy.ROUTE_MAP]:
            layers.append(VisualLayer.MAP)
            layers.append(VisualLayer.ANNOTATION)
        elif strategy in [VisualStrategy.DATA_CHART, VisualStrategy.STATISTIC]:
            layers.append(VisualLayer.TYPOGRAPHY)
            layers.append(VisualLayer.ANNOTATION)
        elif strategy in [VisualStrategy.TIMELINE]:
            layers.append(VisualLayer.TIMELINE)
            layers.append(VisualLayer.TYPOGRAPHY)

        layers.append(VisualLayer.TEXTURE)
        return layers
