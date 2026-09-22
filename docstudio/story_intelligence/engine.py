"""
docstudio/story_intelligence/engine.py
======================================
Master Story Intelligence Engine for DocStudio (Sections 1-27).
Orchestrates the complete 12-pass storytelling intelligence process,
enforcing causal structure, truthful claim provenance, ear writing,
deterministic 21-rule linting, 8-criteria quality gating, and editorial human gate.
"""

from __future__ import annotations

import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

from docstudio.story_intelligence.claim_tracer import ClaimTracer
from docstudio.story_intelligence.hook_lab import HookLab
from docstudio.story_intelligence.human_gate import HumanGateController
from docstudio.story_intelligence.machine_lint import MachineLinter
from docstudio.story_intelligence.meaning_test import MeaningTestEvaluator
from docstudio.story_intelligence.models import (
    ClaimRecord,
    MasterStoryOutput,
    StoryStatus,
)
from docstudio.story_intelligence.narration_craft import NarrationCrafter
from docstudio.story_intelligence.packaging import PackagingStrategist
from docstudio.story_intelligence.quality_gate import QualityGate
from docstudio.story_intelligence.story_skeleton import StorySkeletonEngine


class StoryIntelligenceEngine:
    """
    Master Story Intelligence Engine.
    Transforms raw research and claims into a meaningful, causal,
    and verified documentary narrative.
    """

    def __init__(
        self,
        provider_override: Optional[str] = None,
        max_rewrite_cycles: int = 2,
    ):
        self.provider_override = provider_override
        self.max_rewrite_cycles = max_rewrite_cycles

        # Internal specialized engines
        self.claim_tracer = ClaimTracer()
        self.meaning_evaluator = MeaningTestEvaluator(provider_override=self.provider_override)
        self.packaging_strategist = PackagingStrategist(provider_override=self.provider_override)
        self.hook_lab = HookLab(provider_override=self.provider_override)
        self.skeleton_engine = StorySkeletonEngine(provider_override=self.provider_override)
        self.narration_crafter = NarrationCrafter(provider_override=self.provider_override)
        self.linter = MachineLinter(claim_tracer=self.claim_tracer)
        self.quality_gate = QualityGate(provider_override=self.provider_override)

    def generate_master_story(
        self,
        topic: str,
        research_data: Dict[str, Any],
        claims_data: Optional[Dict[str, Any]] = None,
        target_duration_s: float = 300.0,
        format: str = "youtube",
        style: str = "cinematic_investigative",
        auto_approve_human_gate: bool = False,
    ) -> MasterStoryOutput:
        """
        Executes the 12-pass storytelling intelligence pipeline:
        Pass 1: Research & Claims Ledger Tracing
        Pass 2: Meaning Test & Thesis & Audience
        Pass 3: Packaging Concept
        Pass 4: Hook Lab (5 Candidates + Scoring)
        Pass 5: Story Skeleton & Causal Beat Sheet & Open Loops
        Pass 6: Beat-by-Beat Narration Draft
        Pass 7: Critique & Weak Beat Identification
        Pass 8: Targeted Beat Rewrite
        Pass 9: Ear Pass & Spoken TTS Polish
        Pass 10: Deterministic 21-Rule Machine Lint
        Pass 11: 8-Criteria Quality Gate Rubric
        Pass 12: Editorial Human Gate
        """
        story_id = f"story_{uuid.uuid4().hex[:8]}"
        is_short_form = (format == "shorts") or (target_duration_s <= 90.0)

        print(f"\n[StoryIntelligenceEngine] =========================================")
        print(f"[StoryIntelligenceEngine] Initiating Master Story Intelligence Pipeline")
        print(f"[StoryIntelligenceEngine] Topic: '{topic}' | Target Duration: {target_duration_s:.0f}s ({format})")
        print(f"[StoryIntelligenceEngine] =========================================")

        # -------------------------------------------------------------
        # PASS 1: Research & Claim Ledger Tracing
        # -------------------------------------------------------------
        print(f"[StoryIntelligenceEngine] [Pass 1/12] Ingesting & auditing factual claims ledger...")
        claim_records: Dict[str, ClaimRecord] = self.claim_tracer.process_research_claims(
            research_data if not claims_data else claims_data
        )
        print(f"[StoryIntelligenceEngine] Registered {len(claim_records)} verified/hedged claims.")

        # -------------------------------------------------------------
        # PASS 2: Meaning Test, Thesis & Audience Definition
        # -------------------------------------------------------------
        print(f"[StoryIntelligenceEngine] [Pass 2/12] Running 6-Question Meaning Test & Thesis formulation...")
        meaning_test, thesis, audience = self.meaning_evaluator.evaluate(
            topic=topic,
            research_data=research_data,
            claims_data=claims_data,
        )
        print(f"[StoryIntelligenceEngine] Thesis formulated: \"{thesis.formatted_thesis}\"")

        # -------------------------------------------------------------
        # PASS 3: Packaging Concept (Title, Thumbnail, Promise)
        # -------------------------------------------------------------
        print(f"[StoryIntelligenceEngine] [Pass 3/12] Designing pre-script packaging concept...")
        packaging = self.packaging_strategist.create_packaging(
            topic=topic,
            thesis=thesis,
            meaning_test=meaning_test,
        )
        print(f"[StoryIntelligenceEngine] Working Title: \"{packaging.working_title}\" | Thumbnail: \"{packaging.thumbnail_text}\"")

        # -------------------------------------------------------------
        # PASS 4: Hook Lab (5 candidates + scoring)
        # -------------------------------------------------------------
        print(f"[StoryIntelligenceEngine] [Pass 4/12] Hook Lab generating 5 distinct candidates...")
        champion_hook, runner_up_hook, all_hooks = self.hook_lab.generate_and_select_hooks(
            topic=topic,
            thesis=thesis,
            meaning_test=meaning_test,
            packaging=packaging,
            is_short_form=is_short_form,
        )
        print(f"[StoryIntelligenceEngine] Champion Hook ({champion_hook.pattern_name}, score {champion_hook.total_score:.1f}/25): \"{champion_hook.first_sentence}\"")

        # -------------------------------------------------------------
        # PASS 5: Story Skeleton & Open Loop Map
        # -------------------------------------------------------------
        print(f"[StoryIntelligenceEngine] [Pass 5/12] Assembling causal beat sheet & loop architecture...")
        beats, loops, causality_map, peak_time, peak_desc, echo = self.skeleton_engine.generate_skeleton(
            topic=topic,
            thesis=thesis,
            meaning_test=meaning_test,
            packaging=packaging,
            hook=champion_hook,
            claim_records=claim_records,
            target_duration_s=target_duration_s,
        )
        print(f"[StoryIntelligenceEngine] Structured {len(beats)} causal beats with {len(loops)} open loops. Peak scheduled at {peak_time:.1f}s.")

        # -------------------------------------------------------------
        # PASS 6: Draft Narration for the Ear
        # -------------------------------------------------------------
        print(f"[StoryIntelligenceEngine] [Pass 6/12] Drafting beat-by-beat narration for spoken ear delivery...")
        (
            full_narration,
            beats,
            lexicon,
            visual_intents,
            audio_intents,
        ) = self.narration_crafter.draft_narration(
            topic=topic,
            thesis=thesis,
            hook=champion_hook,
            beats=beats,
            claim_records=claim_records,
            target_duration_s=target_duration_s,
        )

        # -------------------------------------------------------------
        # PASS 7 & 8: Critique & Targeted Rewrite Loop
        # -------------------------------------------------------------
        print(f"[StoryIntelligenceEngine] [Pass 7/12] Auditing beat strength & executing targeted rewrites...")
        for cycle in range(self.max_rewrite_cycles):
            q_eval = self.quality_gate.evaluate_story(
                topic=topic,
                thesis=thesis,
                meaning_test=meaning_test,
                beats=beats,
                full_narration=full_narration,
            )
            if q_eval.weak_beat_ids and not q_eval.passed:
                print(f"[StoryIntelligenceEngine] Rewrite cycle {cycle+1}: targeted rewrite of beats {q_eval.weak_beat_ids}...")
                beats = self.narration_crafter.rewrite_weak_beats(
                    weak_beat_ids=q_eval.weak_beat_ids,
                    beats=beats,
                    critique_notes=q_eval.critique_notes,
                    claim_records=claim_records,
                )
                full_narration = " ".join(b.narration_draft for b in beats).strip()
            else:
                break

        # -------------------------------------------------------------
        # PASS 9: Final Ear Pass
        # -------------------------------------------------------------
        print(f"[StoryIntelligenceEngine] [Pass 9/12] Polishing spoken prosody & cleaning banned phrases...")
        for b in beats:
            b.narration_draft = self.narration_crafter.apply_ear_pass(b.narration_draft)
            b.ssml_narration = self.narration_crafter.apply_ear_pass(b.ssml_narration)
        full_narration = " ".join(b.narration_draft for b in beats).strip()

        # -------------------------------------------------------------
        # PASS 10: Deterministic 21-Rule Machine Lint
        # -------------------------------------------------------------
        print(f"[StoryIntelligenceEngine] [Pass 10/12] Running deterministic 21-rule machine lint...")
        quality_scores = self.quality_gate.evaluate_story(
            topic=topic,
            thesis=thesis,
            meaning_test=meaning_test,
            beats=beats,
            full_narration=full_narration,
        )
        hard_passed, lint_results = self.linter.lint_story(
            topic=topic,
            thesis=thesis,
            meaning_test=meaning_test,
            packaging=packaging,
            hook=champion_hook,
            beats=beats,
            loops=loops,
            full_narration=full_narration,
            claim_records=claim_records,
            target_duration_s=target_duration_s,
            quality_scores=quality_scores,
        )

        passed_count = sum(1 for r in lint_results if r.passed)
        print(f"[StoryIntelligenceEngine] Machine Linter completed: {passed_count}/{len(lint_results)} checks passed.")

        # -------------------------------------------------------------
        # PASS 11: Quality Gate Rubric
        # -------------------------------------------------------------
        print(f"[StoryIntelligenceEngine] [Pass 11/12] Applying 8-criteria quality rubric...")
        quality_scores.evaluate()
        print(
            f"[StoryIntelligenceEngine] Quality Score: {quality_scores.average_score:.2f}/5.0 "
            f"(Stakes: {quality_scores.stakes}, Surprise: {quality_scores.surprise}, Causality: {quality_scores.causality})"
        )

        # -------------------------------------------------------------
        # PASS 12: Editorial Human Gate
        # -------------------------------------------------------------
        master_output = MasterStoryOutput(
            story_id=story_id,
            topic=topic,
            audience=audience,
            meaning_test=meaning_test,
            thesis=thesis,
            packaging=packaging,
            title=packaging.working_title,
            thumbnail_concept=packaging.thumbnail_concept,
            promise=packaging.central_promise,
            selected_hook=champion_hook,
            alternate_hook=runner_up_hook,
            beats=beats,
            loops=loops,
            causality_map=causality_map,
            peak_timestamp_s=peak_time,
            peak_description=peak_desc,
            ending_echo=echo,
            narration=full_narration,
            claim_ids=list(claim_records.keys()),
            pronunciation_lexicon=lexicon,
            visual_intents=visual_intents,
            audio_intents=audio_intents,
            quality_scores=quality_scores,
            lint_results=lint_results,
            status=StoryStatus.DRAFT.value,
        )

        gate_status = HumanGateController.evaluate_machine_readiness(master_output)
        print(f"[StoryIntelligenceEngine] [Pass 12/12] Machine gate resolved to: {gate_status.value}")

        if auto_approve_human_gate and master_output.status == StoryStatus.READY_FOR_HUMAN_GATE.value:
            HumanGateController.approve_for_creative_director(
                master_output,
                reviewer_name="Autonomous Studio Chief",
                notes="Automated approval enabled for unassisted production job.",
            )

        print(f"[StoryIntelligenceEngine] Master Story Package finalized (status: {master_output.status}).\n")
        return master_output
