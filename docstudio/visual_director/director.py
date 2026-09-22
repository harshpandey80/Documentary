"""
DocStudio Visual Director.
Autonomous executive visual director for documentary film production.
Coordinates semantic visual classification, shot-level storyboards,
continuity bible tracking, and visual diversity verification.
"""

from __future__ import annotations
import json
from pathlib import Path
from typing import Dict, Any, List, Optional, Union

from docstudio.visual_director.strategies import (
    VisualStrategy,
    VisualStatus,
    STRATEGY_NAMES,
    GRAPHIC_STRATEGIES,
    AI_VIDEO_STRATEGIES,
    ARCHIVAL_STRATEGIES,
)
from docstudio.visual_director.classifier import SemanticVisualClassifier
from docstudio.visual_director.continuity import VisualContinuityTracker
from docstudio.visual_director.storyboard import ShotStoryboardGenerator
from docstudio.vimax_director import ViMaxDirector


class VisualDirector:
    """
    Main directorial engine for transforming narration and story into a granular,
    multi-shot documentary storyboard with deliberate visual intent.
    """

    def __init__(self, topic: str = "Documentary", width: int = 1920, height: int = 1080):
        self.topic = topic
        self.width = width
        self.height = height
        self.continuity_tracker = VisualContinuityTracker(topic)
        self.classifier = SemanticVisualClassifier()
        self.storyboard_generator = ShotStoryboardGenerator(
            classifier=self.classifier,
            continuity_tracker=self.continuity_tracker,
        )
        # Wrap legacy ViMaxDirector for full backward compatibility
        self.vimax = ViMaxDirector(topic)

    def plan_documentary(
        self,
        narration_data: Dict[str, Any],
        story_data: Optional[Dict[str, Any]] = None,
        claims_data: Optional[Dict[str, Any]] = None,
        output_file: Optional[Union[Path, str]] = None,
    ) -> Dict[str, Any]:
        """Alias for create_storyboard for autonomous pipeline compatibility."""
        return self.create_storyboard(
            narration_data=narration_data,
            claims_data=claims_data,
            story_data=story_data,
            output_file=output_file,
        )

    def create_storyboard(
        self,
        narration_data: Dict[str, Any],
        claims_data: Optional[Dict[str, Any]] = None,
        story_data: Optional[Dict[str, Any]] = None,
        output_file: Optional[Path | str] = None,
    ) -> Dict[str, Any]:
        """
        Builds the complete shot-level storyboard.json.
        """
        # Register entities from story if available
        if story_data:
            topic = story_data.get("topic", self.topic)
            central_q = story_data.get("central_question", "")

        storyboard = self.storyboard_generator.generate_storyboard(
            narration_data=narration_data,
            claims_data=claims_data,
            output_file=output_file,
        )

        # Attach directorial analytics
        analytics = self._compute_directorial_analytics(storyboard)
        storyboard["directorial_analytics"] = analytics

        if output_file:
            out_p = Path(output_file)
            with open(out_p, "w", encoding="utf-8") as f:
                json.dump(storyboard, f, indent=2, ensure_ascii=False)

        return storyboard

    def _compute_directorial_analytics(self, storyboard: Dict[str, Any]) -> Dict[str, Any]:
        scenes = storyboard.get("scenes", [])
        total_shots = 0
        strategy_counts: Dict[str, int] = {}
        status_counts: Dict[str, int] = {}

        for sc in scenes:
            for sh in sc.get("shots", []):
                total_shots += 1
                strat = sh.get("visual_strategy", "UNKNOWN")
                status = sh.get("visual_status", "UNKNOWN")
                strategy_counts[strat] = strategy_counts.get(strat, 0) + 1
                status_counts[status] = status_counts.get(status, 0) + 1

        return {
            "total_shots": total_shots,
            "total_scenes": len(scenes),
            "strategy_distribution": strategy_counts,
            "authenticity_distribution": status_counts,
            "has_motion_graphics": any(k in strategy_counts for k in [s.value for s in GRAPHIC_STRATEGIES]),
            "has_ai_video_or_stills": any(k in strategy_counts for k in [s.value for s in AI_VIDEO_STRATEGIES]),
            "has_archival_evidence": any(k in strategy_counts for k in [s.value for s in ARCHIVAL_STRATEGIES]),
        }

    # Backward compatibility aliases for ViMaxDirector callers
    def classify_scene_archetype(self, scene: Dict[str, Any], is_cold_hook: bool = False) -> str:
        return self.vimax.classify_scene_archetype(scene, is_cold_hook=is_cold_hook)

    def orchestrate_scene_archetypes(self, scenes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return self.vimax.orchestrate_scene_archetypes(scenes)
