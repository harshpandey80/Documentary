"""
DocStudio Story Architecture Engine.
Builds the narrative and storytelling model from researched evidence (research.json)
before writing narration. Determines what the viewer is learning and separates narrative
structure from visual representation decisions.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from docstudio.llm_chain import complete_json, LLMChainExhausted


class StoryGroundingError(ValueError):
    """Raised when story model fails grounding against claims ledger."""
    pass


class InsufficientGroundedMaterialError(RuntimeError):
    """Raised when research or claims lack sufficient material to construct story."""
    pass

STORY_SYSTEM_PROMPT = """
You are an award-winning executive documentary showrunner and story architect (in the caliber of Ken Burns, Errol Morris, and Vox Senior Editors).
Your goal is to transform a structured investigative research package (research.json) into a captivating documentary story model (story.json).

CRITICAL STORY RULES:
1. Do NOT force every story into a rigid generic 3-act template. Tailor the structure (investigative_forensic, escalating_crisis, parallel_threads, or revelatory_chronology) to the nature of the facts.
2. Separate the story into two distinct parallel tracks for every beat:
   - "viewer_learning": Exactly what factual information, twist, or insight the viewer learns.
   - "viewer_seeing_intent": The visual storytelling strategy to accompany it (e.g. animated radar map, authentic document zoom, reconstructed cockpit, data chart).
3. Ground every beat in the researched claims by referencing valid claim_ids.
4. Scale the number of story beats and target durations to fit the requested runtime.
5. Return purely valid JSON matching the schema.
"""

STORY_SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string"},
        "logline": {"type": "string"},
        "central_question": {"type": "string"},
        "stakes": {"type": "string"},
        "structure_type": {
            "type": "string",
            "enum": [
                "investigative_forensic",
                "escalating_crisis",
                "parallel_threads",
                "revelatory_chronology",
                "inquiry_and_controversy",
            ],
        },
        "target_total_duration_s": {"type": "number"},
        "beats": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "beat_id": {"type": "string"},
                    "beat_name": {"type": "string"},
                    "story_function": {
                        "type": "string",
                        "enum": [
                            "hook",
                            "context",
                            "investigation",
                            "turning_point",
                            "contradiction",
                            "revelation",
                            "resolution",
                        ],
                    },
                    "viewer_learning": {"type": "string"},
                    "viewer_seeing_intent": {"type": "string"},
                    "target_duration_s": {"type": "number"},
                    "claim_ids": {"type": "array", "items": {"type": "string"}},
                    "intensity": {"type": "integer", "minimum": 1, "maximum": 10},
                    "mood": {
                        "type": "string",
                        "enum": ["tension", "reveal", "somber", "investigative", "dramatic"],
                    },
                },
                "required": [
                    "beat_id",
                    "beat_name",
                    "story_function",
                    "viewer_learning",
                    "viewer_seeing_intent",
                    "target_duration_s",
                    "claim_ids",
                    "intensity",
                ],
            },
        },
        "unanswered_questions": {"type": "array", "items": {"type": "string"}},
        "ending_takeaway": {"type": "string"},
    },
    "required": [
        "topic",
        "logline",
        "central_question",
        "structure_type",
        "beats",
        "ending_takeaway",
    ],
}


class StoryEngine:
    """
    Transforms researched evidence and claims into a cohesive, beat-by-beat story architecture.
    Powered by the Master Story Intelligence Engine.
    """

    def __init__(self, provider_override: Optional[str] = None):
        self.provider_override = provider_override
        from docstudio.story_intelligence.engine import StoryIntelligenceEngine
        self.intel_engine = StoryIntelligenceEngine(provider_override=provider_override)

    def generate_story_model(
        self,
        research_data: Dict[str, Any],
        target_duration_s: float = 300.0,
        format: str = "youtube",
        style: str = "cinematic_investigative",
        auto_approve_human_gate: bool = True,
    ) -> Dict[str, Any]:
        """Alias for build_story_model for autonomous pipeline compatibility."""
        return self.build_story_model(
            research_data=research_data,
            duration_target_s=target_duration_s,
            format=format,
            style=style,
            auto_approve_human_gate=auto_approve_human_gate,
        )

    def build_story_model(
        self,
        research_data: Dict[str, Any],
        duration_target_s: float = 300.0,
        format: str = "youtube",
        style: str = "cinematic_investigative",
        auto_approve_human_gate: bool = True,
    ) -> Dict[str, Any]:
        """
        Builds story.json from research.json using Master Story Intelligence Engine.
        Enforces strict grounding against verified research claims.
        """
        from docstudio.story_intelligence.adapter import StoryAdapter

        topic = research_data.get("topic", "Documentary")
        claims = research_data.get("claims", [])
        if not claims or len(claims) < 2:
            raise InsufficientGroundedMaterialError(
                f"Insufficient grounded claims ({len(claims)}) in research to build story model for '{topic}'."
            )

        story_data = None
        try:
            master_story = self.intel_engine.generate_master_story(
                topic=topic,
                research_data=research_data,
                target_duration_s=duration_target_s,
                format=format,
                style=style,
                auto_approve_human_gate=auto_approve_human_gate,
            )
            story_data = StoryAdapter.to_legacy_story_json(master_story)
        except Exception as exc:
            print(f"[StoryEngine] StoryIntelligence notice: {exc}. Using grounded fallback model strictly derived from research claims.")
            story_data = self._generate_fallback_story(research_data, duration_target_s)

        is_valid, story_errors = self.validate_story_grounding(story_data, research_data)
        if not is_valid:
            raise StoryGroundingError(
                f"Story model failed grounding validation: {'; '.join(story_errors)}"
            )

        return story_data

    @classmethod
    def validate_story_grounding(
        cls,
        story_data: Dict[str, Any],
        claims_data: Optional[Dict[str, Any] | Any] = None,
        *,
        ledger: Optional[Dict[str, Any] | Any] = None,
        topic: Optional[str] = None,
        raise_on_error: bool = False,
    ) -> Tuple[bool, List[str]]:
        """
        Validates that:
        1. Every beat in story_data has a non-empty claim_ids list.
        2. Every claim_id in beat['claim_ids'] resolves to a registered claim in claims_data/ledger.
        3. No ungrounded generic incident boilerplate terms appear in story beats.
        """
        claims_source = claims_data or ledger
        errors = []
        if not isinstance(story_data, dict):
            errors.append("Story data is not a dictionary.")
            if raise_on_error:
                raise StoryGroundingError(errors[0])
            return False, errors

        registered_cids: Set[str] = set()
        if isinstance(claims_source, dict):
            for c in claims_source.get("claims", []):
                cid = c.get("claim_id")
                if cid:
                    registered_cids.add(str(cid).strip())
        elif hasattr(claims_source, "claims"):
            registered_cids = {str(cid).strip() for cid in claims_source.claims.keys()}

        beats = story_data.get("beats", [])
        if not beats or not isinstance(beats, list):
            errors.append("Story contains no beats.")
            if raise_on_error:
                raise StoryGroundingError(errors[0])
            return False, errors

        for idx, beat in enumerate(beats):
            bid = beat.get("beat_id", f"B{idx+1:02d}")
            cids = beat.get("claim_ids", [])
            if not cids:
                errors.append(f"Beat '{bid}' has no supporting claim_ids linked to research.")
                continue

            for cid in cids:
                cid_clean = str(cid).strip()
                if registered_cids and cid_clean not in registered_cids:
                    errors.append(
                        f"Beat '{bid}' references unknown claim_id '{cid_clean}' absent from claims ledger."
                    )

        # Check for ungrounded generic incident boilerplate in story text
        full_story_str = str(story_data).lower()
        effective_topic = topic or story_data.get("topic", "")
        from docstudio.research_validator import MODERN_AVIATION_RADAR_TERMS, TopicDomainValidator
        if not TopicDomainValidator.is_modern_aviation_topic(effective_topic):
            for term in MODERN_AVIATION_RADAR_TERMS:
                if term in full_story_str:
                    errors.append(
                        f"Story contains ungrounded technical boilerplate '{term}' incompatible with topic '{effective_topic}'."
                    )

        valid = len(errors) == 0
        if not valid and raise_on_error:
            raise StoryGroundingError(f"Story grounding validation failed: {'; '.join(errors)}")

        return valid, errors

    def _validate_story_data(self, data: Dict[str, Any]) -> bool:
        if not isinstance(data, dict):
            return False
        if not data.get("beats") or len(data.get("beats", [])) < 2:
            return False
        return True

    def _generate_fallback_story(
        self, research_data: Dict[str, Any], duration_target_s: float
    ) -> Dict[str, Any]:
        """
        Generates a strictly evidence-backed story architecture from research_data.
        NEVER invents fictional incidents, radar anomalies, or ungrounded claims.
        """
        topic = research_data.get("topic", "Documentary")
        claims = [c for c in research_data.get("claims", []) if (c.get("claim") or c.get("statement"))]
        if not claims or len(claims) < 2:
            raise InsufficientGroundedMaterialError(
                f"Cannot build fallback story for '{topic}': at least 2 verified claims required, found {len(claims)}."
            )

        if duration_target_s >= 180.0:
            num_beats = 4
        elif duration_target_s <= 60.0:
            num_beats = min(3, max(2, len(claims)))
        else:
            num_beats = min(5, max(3, len(claims)))

        beat_duration = duration_target_s / float(num_beats)

        beats = []
        for idx in range(num_beats):
            cl = claims[idx % len(claims)]
            cid = cl.get("claim_id", f"C{idx+1:03d}")
            claim_text = (cl.get("claim") or cl.get("statement") or "").strip()

            if idx == 0:
                s_func = "hook"
                b_name = f"Core Historical Premise ({cid})"
                mood = "tension"
                intensity = 9
            elif idx == num_beats - 1:
                s_func = "resolution"
                b_name = f"Historical Consensus & Verdict ({cid})"
                mood = "reveal"
                intensity = 6
            elif idx % 2 == 1:
                s_func = "investigation"
                b_name = f"Forensic Evidence ({cid})"
                mood = "investigative"
                intensity = 7
            else:
                s_func = "turning_point"
                b_name = f"Critical Turning Point ({cid})"
                mood = "dramatic"
                intensity = 8

            summary_snippet = claim_text[:70].rstrip(".")
            seeing_intent = f"Archival historical documentation, contextual maps, and evidence examination of {summary_snippet}."

            beats.append({
                "beat_id": f"B{len(beats)+1:02d}",
                "beat_name": b_name,
                "story_function": s_func,
                "viewer_learning": claim_text,
                "viewer_seeing_intent": seeing_intent,
                "target_duration_s": round(beat_duration, 1),
                "claim_ids": [cid],
                "intensity": intensity,
                "mood": mood,
            })

        return {
            "topic": topic,
            "logline": f"An evidence-grounded investigation into {topic}, examining verified historical records and core claims.",
            "central_question": research_data.get(
                "central_question", f"What really transpired during {topic}?"
            ),
            "stakes": "Historical accuracy, archival truth, and the evidentiary record.",
            "structure_type": "investigative_forensic",
            "target_total_duration_s": duration_target_s,
            "beats": beats,
            "unanswered_questions": research_data.get("unknowns", []),
            "ending_takeaway": f"The historical record of {topic} is defined by verified evidence rather than unsubstantiated speculation.",
        }
