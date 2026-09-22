"""
DocStudio Remote Creative Director — Context Builder.
Assembles the complete narrative and evidence package across the entire documentary
so the Remote AI can reason globally rather than sentence-by-sentence.
"""

from __future__ import annotations
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from docstudio.remote_creative_director.manifest_schema import ContinuityBible


@dataclass
class VisualBudget:
    max_ai_videos: int = 4
    max_ai_images: int = 12
    max_browser_operations: int = 6
    max_regeneration_attempts: int = 2

    def to_dict(self) -> Dict[str, int]:
        return {
            "max_ai_videos": self.max_ai_videos,
            "max_ai_images": self.max_ai_images,
            "max_browser_operations": self.max_browser_operations,
            "max_regeneration_attempts": self.max_regeneration_attempts,
        }


@dataclass
class DirectorialContext:
    topic: str
    target_duration: float
    aspect_ratio: str
    documentary_style: str
    research_summary: Dict[str, Any]
    verified_claims: List[Dict[str, Any]]
    story_beats: List[Dict[str, Any]]
    narration_scenes: List[Dict[str, Any]]
    continuity_bible: ContinuityBible
    visual_budget: VisualBudget
    available_assets: List[Dict[str, Any]] = field(default_factory=list)

    @property
    def scenes(self) -> List[Dict[str, Any]]:
        return self.narration_scenes or self.story_beats

    @property
    def claims(self) -> List[Dict[str, Any]]:
        return self.verified_claims

    def to_dict(self) -> Dict[str, Any]:
        return {
            "topic": self.topic,
            "target_duration": self.target_duration,
            "aspect_ratio": self.aspect_ratio,
            "documentary_style": self.documentary_style,
            "research_summary": self.research_summary,
            "verified_claims_count": len(self.verified_claims),
            "verified_claims": self.verified_claims,
            "story_beats": self.story_beats,
            "narration_scenes": self.narration_scenes,
            "continuity_bible": self.continuity_bible.to_dict(),
            "visual_budget": self.visual_budget.to_dict(),
            "available_assets_count": len(self.available_assets),
        }


class ContextBuilder:
    """
    Constructs high-density directorial context from persistent job artifacts.
    """

    @staticmethod
    def build_context(
        topic: str,
        target_duration: float,
        aspect_ratio: str = "16:9",
        documentary_style: str = "cinematic_investigative",
        research_data: Optional[Dict[str, Any]] = None,
        claims_data: Optional[Dict[str, Any]] = None,
        story_data: Optional[Dict[str, Any]] = None,
        narration_data: Optional[Dict[str, Any]] = None,
        budget: Optional[VisualBudget] = None,
    ) -> DirectorialContext:
        research = research_data or {}
        claims_raw = claims_data.get("claims", []) if claims_data else []

        # Flatten narration scenes from nested acts structure (narration.json: acts[*].scenes[*])
        narr_scenes: list = []
        if narration_data:
            if narration_data.get("scenes"):
                narr_scenes = narration_data["scenes"]
            elif narration_data.get("acts"):
                for act in narration_data["acts"]:
                    for sc in act.get("scenes", []):
                        narr_scenes.append({
                            "scene_id": sc.get("scene_id", ""),
                            "narration": sc.get("narration", sc.get("text", "")),
                            "visual_prompt": sc.get("visual_prompt", ""),
                            "motion": sc.get("motion", "zoom_in"),
                            "duration": sc.get("estimated_duration_sec", 10.0),
                            "broll_keywords": sc.get("broll_keywords", ""),
                        })

        # Flatten story scenes/beats from beats (story.json: beats[*]) or nested acts
        story_scenes: list = []
        if story_data:
            if story_data.get("beats"):
                for beat in story_data["beats"]:
                    if isinstance(beat, dict):
                        story_scenes.append(dict(beat))
            elif story_data.get("scenes"):
                story_scenes = list(story_data["scenes"])
            elif story_data.get("acts"):
                for act in story_data["acts"]:
                    for sc in act.get("scenes", []):
                        story_scenes.append({
                            "scene_id": sc.get("scene_id", ""),
                            "narration": sc.get("narration", sc.get("text", "")),
                            "visual_prompt": sc.get("visual_prompt", ""),
                            "motion": sc.get("motion", "zoom_in"),
                            "duration": sc.get("estimated_duration_sec", 10.0),
                            "broll_keywords": sc.get("broll_keywords", ""),
                        })

        # Build research summary
        research_summary = {
            "entities": research.get("entities", [])[:10],
            "locations": research.get("locations", [])[:8],
            "timeline": research.get("timeline", [])[:12],
            "statistics": research.get("statistics", [])[:8],
            "primary_sources": research.get("primary_sources", [])[:6],
            "conflicts": research.get("conflicts", [])[:4],
        }

        # Build Continuity Bible from research & entities
        characters = []
        for ent in research.get("entities", []):
            if isinstance(ent, dict) and ent.get("type") in ["person", "historical_figure"]:
                characters.append({
                    "name": ent.get("name"),
                    "role": ent.get("role", "subject"),
                    "appearance": ent.get("description", "period accurate attire"),
                })
            elif isinstance(ent, str):
                characters.append({"name": ent, "appearance": "period accurate attire"})

        locations = []
        for loc in research.get("locations", []):
            if isinstance(loc, dict):
                locations.append({
                    "name": loc.get("name"),
                    "coordinates": loc.get("coordinates", ""),
                    "visual_features": loc.get("description", "atmospheric historical setting"),
                })
            elif isinstance(loc, str):
                locations.append({"name": loc, "visual_features": "atmospheric historical setting"})

        continuity = ContinuityBible(
            characters=characters[:5],
            locations=locations[:5],
            key_objects=[],
            style_guide={
                "color_palette": "muted cinematic teal and tungsten",
                "lens_style": "anamorphic 35mm shallow depth of field",
                "mood": "forensic, mysterious, grounded realism",
            },
        )

        # Budget allocation based on duration
        if budget is None:
            if target_duration <= 60.0:  # Shorts / Reels
                budget = VisualBudget(max_ai_videos=2, max_ai_images=8, max_browser_operations=3)
            elif target_duration <= 300.0:  # 5 min doc
                budget = VisualBudget(max_ai_videos=5, max_ai_images=16, max_browser_operations=6)
            else:  # Long form
                budget = VisualBudget(max_ai_videos=8, max_ai_images=30, max_browser_operations=10)

        # Filter and summarize claims for context efficiency
        verified_claims = []
        for c in claims_raw:
            if isinstance(c, dict):
                verified_claims.append({
                    "claim_id": c.get("claim_id", ""),
                    "statement": c.get("claim_text", c.get("statement", "")),
                    "source": c.get("source", ""),
                    "is_disputed": c.get("status") == "disputed",
                })

        return DirectorialContext(
            topic=topic,
            target_duration=target_duration,
            aspect_ratio=aspect_ratio,
            documentary_style=documentary_style,
            research_summary=research_summary,
            verified_claims=verified_claims,
            story_beats=story_scenes,
            narration_scenes=narr_scenes,
            continuity_bible=continuity,
            visual_budget=budget,
        )
