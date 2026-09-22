"""
DocStudio Deep Research Engine.
Performs autonomous structured investigative research on any documentary topic.
Extracts entities, timeline, primary/secondary sources, verified claims, statistics,
conflicts, and evidence provenance into research.json before scriptwriting begins.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from docstudio.llm_chain import complete_json, LLMChainExhausted
from docstudio.research_validator import TopicDomainValidator, validate_topic_research


class ResearchFailureError(RuntimeError):
    """Raised when autonomous research fails and insufficient grounded material is available."""
    pass


class GroundedResearchValidationError(ValueError):
    """Raised when research output fails topic-domain consistency or evidence grounding."""
    pass

RESEARCH_SYSTEM_PROMPT = """
You are an elite chief investigative researcher for high-end historical and forensic documentaries (in the style of LEMMiNO, Frontline, and BBC Horizon).
Your task is to conduct deep, structured investigative research on the user's topic.

CRITICAL RULES:
1. Do NOT fabricate sources, court citations, or quotes.
2. If an event or number is disputed or uncertain, explicitly record it in "conflicts" and "unknowns" rather than presenting false certainty.
3. Every claim in the "claims" list MUST have a unique claim_id (e.g. "C001", "C002"), a verification_status ("verified", "disputed", or "uncertain"), and source citations.
4. Extract all exact dates, times, coordinates, distances, financial figures, and physical quantities into "statistics" and "timeline".
5. Output purely valid JSON matching the exact schema provided.
"""

RESEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "topic": {"type": "string"},
        "summary": {"type": "string"},
        "central_question": {"type": "string"},
        "entities": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "role": {"type": "string"},
                    "type": {"type": "string", "enum": ["person", "organization", "vehicle", "facility", "location"]},
                },
                "required": ["name", "role", "type"],
            },
        },
        "locations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "coordinates": {"type": "string"},
                    "significance": {"type": "string"},
                },
                "required": ["name", "significance"],
            },
        },
        "timeline": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date_or_time": {"type": "string"},
                    "event": {"type": "string"},
                    "significance": {"type": "string"},
                },
                "required": ["date_or_time", "event"],
            },
        },
        "statistics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "value": {"type": "string"},
                    "unit": {"type": "string"},
                    "context": {"type": "string"},
                    "verified_source": {"type": "string"},
                },
                "required": ["value", "context"],
            },
        },
        "primary_sources": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "author_or_institution": {"type": "string"},
                    "type": {"type": "string", "enum": ["declassified_record", "official_report", "court_transcript", "flight_recorder", "manifest", "newspaper_archive"]},
                    "description": {"type": "string"},
                },
                "required": ["title", "author_or_institution"],
            },
        },
        "secondary_sources": {
            "type": "array",
            "items": {"type": "string"},
        },
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim_id": {"type": "string"},
                    "claim": {"type": "string"},
                    "sources": {"type": "array", "items": {"type": "string"}},
                    "source_type": {"type": "string", "enum": ["primary", "secondary", "investigative_consensus", "disputed_witness"]},
                    "verification_status": {"type": "string", "enum": ["verified", "disputed", "uncertain"]},
                    "confidence": {"type": "number", "minimum": 0.0, "maximum": 1.0},
                    "number_or_date": {"type": "string"},
                    "unit": {"type": "string"},
                },
                "required": ["claim_id", "claim", "verification_status"],
            },
        },
        "conflicts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "topic_of_contention": {"type": "string"},
                    "claim_a": {"type": "string"},
                    "claim_b": {"type": "string"},
                    "current_status": {"type": "string"},
                },
                "required": ["topic_of_contention", "claim_a", "claim_b"],
            },
        },
        "unknowns": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["topic", "summary", "central_question", "entities", "timeline", "claims"],
}


class ResearchEngine:
    """
    Autonomous research engine transforming a raw user topic into a verified research package.
    """

    def __init__(self, provider_override: Optional[str] = None):
        self.provider_override = provider_override

    def research_topic(
        self,
        topic: str,
        depth: str = "deep",
        custom_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Alias for conduct_research for autonomous pipeline and test compatibility."""
        return self.conduct_research(topic=topic, research_depth=depth, custom_notes=custom_notes)

    def conduct_research(
        self,
        topic: str,
        research_depth: str = "deep",
        custom_notes: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes structured topic research using complete_json.
        Falls back to a structured deterministic research template if LLM is unavailable.
        """
        prompt = f"""
Conduct exhaustive investigative research for a high-production documentary on:
"{topic}"

Research Depth: {research_depth.upper()}
{f'Additional Context / User Directives: {custom_notes}' if custom_notes else ''}

Identify:
1. All key individuals, military units, organizations, and vehicles involved.
2. A chronological timeline with exact dates and timestamps.
3. Quantifiable data points, measurements, financial values, speeds, distances, or casualties.
4. Key primary source documents (official reports, declassified memos, telemetry, manifests).
5. At least 8-15 specific factual claims with unique claim_ids (C001, C002, ...), their exact numbers/dates, and verification status.
6. Crucial contradictions, disputed accounts, and unsolved mysteries.

Return purely valid JSON matching the schema.
"""

        try:
            parsed = complete_json(
                prompt=prompt,
                system=RESEARCH_SYSTEM_PROMPT,
                temperature=0.2,
                provider_override=self.provider_override,
            )
            is_valid, validation_errors = TopicDomainValidator.validate_research(topic, parsed)
            if not is_valid:
                raise GroundedResearchValidationError(
                    f"LLM research failed topic-domain consistency validation: {'; '.join(validation_errors)}"
                )
            if "sources" not in parsed or not parsed["sources"]:
                srcs = [s.get("title", "") for s in parsed.get("primary_sources", [])] + parsed.get("secondary_sources", [])
                parsed["sources"] = [s for s in srcs if s]
            return parsed
        except GroundedResearchValidationError:
            raise
        except Exception as e:
            # Rule 2 & 3: A fallback MUST NEVER invent historical entities, events, documents,
            # telemetry, investigations, witnesses, dates, or claims.
            # If Gemini research fails and there is insufficient grounded material to construct
            # the requested documentary, FAIL/CANCEL the documentary job.
            print(f"[ResearchEngine] Research generation failed for topic '{topic}': {e}")
            raise ResearchFailureError(
                f"Gemini research failed for topic '{topic}' and no grounded research material is available: {e}"
            ) from e

    def _clean_and_parse_json(self, raw_text: str) -> Dict[str, Any]:
        cleaned = raw_text.strip()
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned, flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned, flags=re.MULTILINE).strip()
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            cleaned = match.group(0)
        return json.loads(cleaned)

    def _validate_research_data(self, data: Dict[str, Any], topic: Optional[str] = None) -> bool:
        if not isinstance(data, dict):
            return False
        if not data.get("topic") or not data.get("claims"):
            return False
        if len(data.get("claims", [])) < 2:
            return False
        if topic:
            is_valid, _ = TopicDomainValidator.validate_research(topic, data)
            return is_valid
        return True

    def _generate_fallback_research(
        self, topic: str, grounded_claims: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Grounded research package strictly projecting from user-supplied grounded material.
        NEVER invents synthetic historical entities, radar anomalies, or fictional inquiries.
        """
        if not grounded_claims:
            raise ResearchFailureError(
                f"Cannot generate fallback research for '{topic}': inventing synthetic historical facts is strictly prohibited."
            )

        return {
            "topic": topic,
            "summary": f"Historical and investigative documentary dossier on {topic}.",
            "central_question": f"What really happened during the events of {topic}?",
            "entities": [
                {"name": topic, "role": "Subject of Inquiry", "type": "person"},
            ],
            "locations": [],
            "timeline": [],
            "statistics": [],
            "primary_sources": [],
            "secondary_sources": [],
            "claims": grounded_claims,
            "conflicts": [],
            "unknowns": [],
            "sources": [s for c in grounded_claims for s in c.get("sources", []) if s],
        }
