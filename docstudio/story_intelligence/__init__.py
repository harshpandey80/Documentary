"""
docstudio/story_intelligence
============================
Master Story Intelligence Engine package for DocStudio.
"""

from docstudio.story_intelligence.models import (
    EvidenceGrade,
    TruthCategory,
    TransitionType,
    StoryStatus,
    RuleClassification,
    ClaimRecord,
    MeaningTest,
    AudienceDefinition,
    Thesis,
    PackagingConcept,
    HookCandidate,
    StoryBeat,
    OpenLoop,
    CausalityTransition,
    QualityScores,
    LintResult,
    MasterStoryOutput,
)
from docstudio.story_intelligence.engine import StoryIntelligenceEngine
from docstudio.story_intelligence.claim_tracer import ClaimTracer
from docstudio.story_intelligence.meaning_test import MeaningTestEvaluator
from docstudio.story_intelligence.packaging import PackagingStrategist
from docstudio.story_intelligence.hook_lab import HookLab
from docstudio.story_intelligence.story_skeleton import StorySkeletonEngine
from docstudio.story_intelligence.narration_craft import NarrationCrafter
from docstudio.story_intelligence.machine_lint import MachineLinter
from docstudio.story_intelligence.quality_gate import QualityGate
from docstudio.story_intelligence.human_gate import HumanGateController
from docstudio.story_intelligence.adapter import StoryAdapter

__all__ = [
    "StoryIntelligenceEngine",
    "MasterStoryOutput",
    "StoryStatus",
    "EvidenceGrade",
    "TruthCategory",
    "TransitionType",
    "RuleClassification",
    "ClaimRecord",
    "MeaningTest",
    "AudienceDefinition",
    "Thesis",
    "PackagingConcept",
    "HookCandidate",
    "StoryBeat",
    "OpenLoop",
    "CausalityTransition",
    "QualityScores",
    "LintResult",
    "ClaimTracer",
    "MeaningTestEvaluator",
    "PackagingStrategist",
    "HookLab",
    "StorySkeletonEngine",
    "NarrationCrafter",
    "MachineLinter",
    "QualityGate",
    "HumanGateController",
    "StoryAdapter",
]
