"""
DocStudio Remote Creative Director — Shot Manifest Schema.
Defines the central JSON contract and strict typing for documentary visual direction.
Every shot mandates: purpose, visual_reason, visual_type, duration, narration_range, source_strategy.
"""

from __future__ import annotations
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict


class VisualPurpose(str, Enum):
    """Explicit directorial intent behind every shot."""
    ESTABLISH = "ESTABLISH"
    INTRODUCE_PERSON = "INTRODUCE_PERSON"
    INTRODUCE_LOCATION = "INTRODUCE_LOCATION"
    EXPLAIN_GEOGRAPHY = "EXPLAIN_GEOGRAPHY"
    EXPLAIN_SEQUENCE = "EXPLAIN_SEQUENCE"
    SHOW_SCALE = "SHOW_SCALE"
    SHOW_EVIDENCE = "SHOW_EVIDENCE"
    SHOW_CONTRADICTION = "SHOW_CONTRADICTION"
    SHOW_STATISTICS = "SHOW_STATISTICS"
    SHOW_RELATIONSHIP = "SHOW_RELATIONSHIP"
    SHOW_CAUSE_EFFECT = "SHOW_CAUSE_EFFECT"
    RECONSTRUCT_EVENT = "RECONSTRUCT_EVENT"
    CREATE_EMOTIONAL_WEIGHT = "CREATE_EMOTIONAL_WEIGHT"
    CREATE_TENSION = "CREATE_TENSION"
    RESET_VISUAL_PACING = "RESET_VISUAL_PACING"
    SHOW_CONTEXT = "SHOW_CONTEXT"
    SHOW_TRANSITION = "SHOW_TRANSITION"
    EMPHASIZE_REVEAL = "EMPHASIZE_REVEAL"
    CONCLUDE = "CONCLUDE"


from docstudio.remote_creative_director.visual_registry import (
    VisualType,
    TruthCategory,
    CostClass,
    ComputeClass,
    VisualTypeRegistry,
)


class SourceStrategy(str, Enum):
    """How the local DocStudio engine must acquire or execute the visual."""
    GENERATE_AI_VIDEO = "GENERATE_AI_VIDEO"
    GENERATE_AI_IMAGE = "GENERATE_AI_IMAGE"
    PROCEDURAL_MAP = "PROCEDURAL_MAP"
    PROCEDURAL_CHART = "PROCEDURAL_CHART"
    PROCEDURAL_DOCUMENT = "PROCEDURAL_DOCUMENT"
    RETRIEVE_ARCHIVE_STOCK = "RETRIEVE_ARCHIVE_STOCK"


@dataclass
class NarrationRange:
    start: float
    end: float

    def to_dict(self) -> Dict[str, float]:
        return {"start": round(self.start, 2), "end": round(self.end, 2)}


@dataclass
class ShotDirective:
    shot_id: str
    start: float
    end: float
    duration: float
    purpose: VisualPurpose
    visual_type: VisualType
    visual_reason: str
    source_strategy: SourceStrategy
    scene_id: str = ""
    prompt: str = ""
    motion: str = "subtle_cinematic_push"
    camera: str = "eye_level_medium"
    composition: str = "rule_of_thirds"
    evidence_claims: List[str] = field(default_factory=list)
    visual_status: str = "DIRECTED"
    generation_provider: str = "browser_flow"
    truth_category: TruthCategory = TruthCategory.RECONSTRUCTION
    cost_class: CostClass = CostClass.LOW
    compute_class: ComputeClass = ComputeClass.LOCAL
    transition_in: str = "cut"
    transition_out: str = "cut"
    execution_metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def execution(self) -> Dict[str, Any]:
        return self.execution_metadata

    def to_dict(self) -> Dict[str, Any]:
        return {
            "shot_id": self.shot_id,
            "scene_id": self.scene_id,
            "start": round(self.start, 2),
            "end": round(self.end, 2),
            "duration": round(self.duration, 2),
            "narration_range": {"start": round(self.start, 2), "end": round(self.end, 2)},
            "purpose": self.purpose.value if isinstance(self.purpose, VisualPurpose) else str(self.purpose),
            "visual_type": self.visual_type.value if isinstance(self.visual_type, VisualType) else str(self.visual_type),
            "visual_reason": self.visual_reason,
            "source_strategy": self.source_strategy.value if isinstance(self.source_strategy, SourceStrategy) else str(self.source_strategy),
            "truth_category": self.truth_category.value if isinstance(self.truth_category, TruthCategory) else str(self.truth_category),
            "cost_class": self.cost_class.value if isinstance(self.cost_class, CostClass) else str(self.cost_class),
            "compute_class": self.compute_class.value if isinstance(self.compute_class, ComputeClass) else str(self.compute_class),
            "prompt": self.prompt,
            "motion": self.motion,
            "camera": self.camera,
            "composition": self.composition,
            "evidence_claims": list(self.evidence_claims),
            "visual_status": self.visual_status,
            "generation_provider": self.generation_provider,
            "transition_in": self.transition_in,
            "transition_out": self.transition_out,
            "execution": dict(self.execution_metadata),
            "execution_metadata": dict(self.execution_metadata),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ShotDirective:
        purpose = d.get("purpose", "ESTABLISH")
        try:
            purpose_enum = VisualPurpose(purpose)
        except ValueError:
            purpose_enum = VisualPurpose.ESTABLISH

        vtype = d.get("visual_type", "AI_IMAGE_TO_VIDEO")
        norm_vtype = VisualTypeRegistry.normalize_type(vtype) or VisualType.AI_IMAGE_TO_VIDEO

        strat = d.get("source_strategy", "GENERATE_AI_VIDEO")
        try:
            strat_enum = SourceStrategy(strat)
        except ValueError:
            strat_enum = SourceStrategy.GENERATE_AI_VIDEO

        tcat_raw = d.get("truth_category", "RECONSTRUCTION")
        try:
            tcat_enum = TruthCategory(tcat_raw)
        except ValueError:
            tcat_enum = TruthCategory.RECONSTRUCTION

        cost_raw = d.get("cost_class", "low")
        try:
            cost_enum = CostClass(cost_raw)
        except ValueError:
            cost_enum = CostClass.LOW

        compute_raw = d.get("compute_class", "local")
        try:
            compute_enum = ComputeClass(compute_raw)
        except ValueError:
            compute_enum = ComputeClass.LOCAL

        exec_meta = dict(d.get("execution_metadata") or d.get("execution") or {})

        return cls(
            shot_id=str(d.get("shot_id", "")),
            scene_id=str(d.get("scene_id", "")),
            start=float(d.get("start", 0.0)),
            end=float(d.get("end", 0.0)),
            duration=float(d.get("duration", 0.0)),
            purpose=purpose_enum,
            visual_type=norm_vtype,
            visual_reason=str(d.get("visual_reason", "")),
            source_strategy=strat_enum,
            truth_category=tcat_enum,
            cost_class=cost_enum,
            compute_class=compute_enum,
            prompt=str(d.get("prompt", "")),
            motion=str(d.get("motion", "subtle_cinematic_push")),
            camera=str(d.get("camera", "eye_level_medium")),
            composition=str(d.get("composition", "rule_of_thirds")),
            evidence_claims=list(d.get("evidence_claims", [])),
            visual_status=str(d.get("visual_status", "DIRECTED")),
            generation_provider=str(d.get("generation_provider", "browser_flow")),
            transition_in=str(d.get("transition_in", "cut")),
            transition_out=str(d.get("transition_out", "cut")),
            execution_metadata=exec_meta,
        )


@dataclass
class SceneManifest:
    scene_id: str
    story_beat: str
    viewer_takeaway: str
    narration_range: NarrationRange
    shots: List[ShotDirective] = field(default_factory=list)
    narration_text: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "story_beat": self.story_beat,
            "viewer_takeaway": self.viewer_takeaway,
            "narration_range": self.narration_range.to_dict(),
            "narration_text": self.narration_text,
            "shots": [s.to_dict() for s in self.shots],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> SceneManifest:
        nr = d.get("narration_range", {"start": 0.0, "end": 0.0})
        return cls(
            scene_id=str(d.get("scene_id", "")),
            story_beat=str(d.get("story_beat", "")),
            viewer_takeaway=str(d.get("viewer_takeaway", "")),
            narration_range=NarrationRange(
                start=float(nr.get("start", 0.0)),
                end=float(nr.get("end", 0.0)),
            ),
            shots=[ShotDirective.from_dict(s) for s in d.get("shots", [])],
            narration_text=str(d.get("narration_text", "")),
        )


@dataclass
class ContinuityBible:
    characters: List[Dict[str, Any]] = field(default_factory=list)
    locations: List[Dict[str, Any]] = field(default_factory=list)
    key_objects: List[Dict[str, Any]] = field(default_factory=list)
    style_guide: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "characters": list(self.characters),
            "locations": list(self.locations),
            "key_objects": list(self.key_objects),
            "style_guide": dict(self.style_guide),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ContinuityBible:
        return cls(
            characters=list(d.get("characters", [])),
            locations=list(d.get("locations", [])),
            key_objects=list(d.get("key_objects", [])),
            style_guide=dict(d.get("style_guide", {})),
        )


@dataclass
class ShotManifest:
    """The central contractual object produced by the Remote Creative Director."""
    documentary_id: str
    topic: str
    total_duration: float
    aspect_ratio: str = "16:9"
    version: int = 1
    director_notes: str = ""
    visual_rationale: str = ""
    continuity_bible: ContinuityBible = field(default_factory=ContinuityBible)
    scenes: List[SceneManifest] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "documentary_id": self.documentary_id,
            "version": self.version,
            "topic": self.topic,
            "total_duration": round(self.total_duration, 2),
            "aspect_ratio": self.aspect_ratio,
            "director_notes": self.director_notes,
            "visual_rationale": self.visual_rationale,
            "continuity_bible": self.continuity_bible.to_dict(),
            "scenes": [s.to_dict() for s in self.scenes],
            "metadata": dict(self.metadata),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> ShotManifest:
        return cls(
            documentary_id=str(d.get("documentary_id", "")),
            topic=str(d.get("topic", "")),
            total_duration=float(d.get("total_duration", 0.0)),
            aspect_ratio=str(d.get("aspect_ratio", "16:9")),
            version=int(d.get("version", 1)),
            director_notes=str(d.get("director_notes", "")),
            visual_rationale=str(d.get("visual_rationale", "")),
            continuity_bible=ContinuityBible.from_dict(d.get("continuity_bible", {})),
            scenes=[SceneManifest.from_dict(s) for s in d.get("scenes", [])],
            metadata=dict(d.get("metadata", {})),
        )

    def get_all_shots(self) -> List[ShotDirective]:
        shots = []
        for s in self.scenes:
            shots.extend(s.shots)
        return shots
