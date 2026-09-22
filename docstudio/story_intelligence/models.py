"""
docstudio/story_intelligence/models.py
======================================
Data structures and contracts for the Master Story Intelligence Engine.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional


class EvidenceGrade(str, Enum):
    OFFICIAL = "[O]"      # Official platform, government, flight log, declassified record
    ACADEMIC = "[A]"      # Academic / classic peer-reviewed research
    INDUSTRY = "[D]"      # Industry data / empirical benchmarks
    HEURISTIC = "[H]"     # Craft heuristic / editorial convention


class TruthCategory(str, Enum):
    REAL = "REAL"
    RECREATED = "RECREATED"
    AI_ILLUSTRATION = "AI ILLUSTRATION"
    ARCHIVAL = "ARCHIVAL"
    MAP = "MAP"
    DATA = "DATA"
    DOCUMENT = "DOCUMENT"
    B_ROLL = "B-ROLL"


class TransitionType(str, Enum):
    BUT = "BUT"
    THEREFORE = "THEREFORE"
    BECAUSE = "BECAUSE"


class StoryStatus(str, Enum):
    DRAFT = "DRAFT"
    NEEDS_RESEARCH = "NEEDS_RESEARCH"
    NEEDS_REWRITE = "NEEDS_REWRITE"
    LINT_FAILED = "LINT_FAILED"
    QUALITY_FAILED = "QUALITY_FAILED"
    READY_FOR_HUMAN_GATE = "READY_FOR_HUMAN_GATE"
    APPROVED_FOR_CREATIVE_DIRECTOR = "APPROVED_FOR_CREATIVE_DIRECTOR"


class RuleClassification(str, Enum):
    HARD = "HARD"
    SOFT = "SOFT"
    INFORMATIONAL = "INFORMATIONAL"


@dataclass
class ClaimRecord:
    claim_id: str
    claim: str
    source: str
    source_type: str = EvidenceGrade.OFFICIAL.value
    confidence: str = "high"  # high, medium, low
    disputed: bool = False
    hedge_required: bool = False
    graphic_worthy: bool = False
    absolute_claim: bool = False
    human_anchor: str = ""
    relevant_story_beats: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MeaningTest:
    question: str
    stakes: str
    surprise: str
    change: str
    anchor: str
    payoff: str
    is_valid: bool = True
    failure_reasons: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class AudienceDefinition:
    persona: str
    what_they_know: str
    what_they_misunderstand: str
    what_they_care_about: str
    why_they_should_care: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Thesis:
    existing_belief: str
    contradiction: str
    explanation: str
    consequence: str
    formatted_thesis: str  # "Everyone thinks X. But actually Y, because Z, which means W."

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PackagingConcept:
    working_title: str
    thumbnail_concept: str
    thumbnail_text: str  # Max 3-6 words
    central_promise: str
    hook_promise: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class HookCandidate:
    hook_id: str
    pattern_name: str
    spoken_text: str
    first_sentence: str
    first_sentence_words: int
    has_concrete_anchor: bool
    curiosity_score: float = 0.0
    specificity_score: float = 0.0
    stakes_score: float = 0.0
    truthfulness_score: float = 0.0
    title_match_score: float = 0.0
    total_score: float = 0.0

    def calculate_total(self) -> float:
        self.total_score = (
            self.curiosity_score
            + self.specificity_score
            + self.stakes_score
            + self.truthfulness_score
            + self.title_match_score
        )
        return self.total_score

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class StoryBeat:
    beat_id: str
    purpose: str
    claim_ids: List[str]
    narration_intent: str
    visual_intent: str
    emotional_state: str
    information_revealed: str
    question_created: str
    loop_ids: List[str]
    transition_type: str  # BUT, THEREFORE, BECAUSE
    target_duration_s: float
    intensity: int  # 1-10
    truth_category: str = TruthCategory.REAL.value
    narration_draft: str = ""
    ssml_narration: str = ""
    sound_design_intent: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class OpenLoop:
    loop_id: str
    plant_beat_id: str
    plant_timestamp_s: float
    payoff_beat_id: str
    payoff_timestamp_s: float
    description: str
    is_resolved: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class CausalityTransition:
    from_beat_id: str
    to_beat_id: str
    transition_type: str
    causal_link: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class QualityScores:
    stakes: float = 0.0
    surprise: float = 0.0
    question_integrity: float = 0.0
    causality: float = 0.0
    specificity: float = 0.0
    emotional_arc: float = 0.0
    viewer_relevance: float = 0.0
    clarity_for_ear: float = 0.0
    average_score: float = 0.0
    passed: bool = False
    weak_beat_ids: List[str] = field(default_factory=list)
    critique_notes: List[str] = field(default_factory=list)

    def evaluate(self) -> bool:
        scores = [
            self.stakes,
            self.surprise,
            self.question_integrity,
            self.causality,
            self.specificity,
            self.emotional_arc,
            self.viewer_relevance,
            self.clarity_for_ear,
        ]
        self.average_score = round(sum(scores) / len(scores), 2)
        # Average >= 4.0 and no score < 3.0
        self.passed = (self.average_score >= 4.0) and all(s >= 3.0 for s in scores)
        return self.passed

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class LintResult:
    rule_id: int
    rule_name: str
    classification: str  # HARD, SOFT, INFORMATIONAL
    passed: bool
    message: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class MasterStoryOutput:
    story_id: str
    topic: str
    audience: AudienceDefinition
    meaning_test: MeaningTest
    thesis: Thesis
    packaging: PackagingConcept
    title: str
    thumbnail_concept: str
    promise: str
    selected_hook: HookCandidate
    alternate_hook: HookCandidate
    beats: List[StoryBeat]
    loops: List[OpenLoop]
    causality_map: List[CausalityTransition]
    peak_timestamp_s: float
    peak_description: str
    ending_echo: str
    narration: str
    claim_ids: List[str]
    pronunciation_lexicon: Dict[str, str]
    visual_intents: List[Dict[str, Any]]
    audio_intents: List[Dict[str, Any]]
    quality_scores: QualityScores
    lint_results: List[LintResult]
    status: str = StoryStatus.DRAFT.value
    human_approved: bool = False
    human_notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d
