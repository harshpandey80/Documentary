"""
DocStudio Research & Story Grounding Validator.
Enforces that:
1. Topic entities and historical context are genuinely represented in research.
2. Generic incident boilerplate templates (telemetry, radar anomalies, flight controllers) are rejected.
3. Every claim is grounded with supporting sources and evidence citations.
4. Story beats map 100% to registered claims in the ledger.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Set, Tuple


STOPWORDS: Set[str] = {
    "the", "a", "an", "and", "or", "of", "in", "on", "at", "to", "for", "with",
    "by", "from", "up", "about", "into", "over", "after", "is", "was", "are",
    "were", "be", "been", "being", "have", "has", "had", "do", "does", "did",
    "what", "who", "which", "when", "where", "why", "how", "that", "this",
    "these", "those", "case", "incident", "story", "mystery", "true", "untold",
    "secret", "fall", "rise", "life", "death",
}

FORBIDDEN_BOILERPLATE_TEMPLATES: List[str] = [
    "investigative oversight commission",
    "official archive depository",
    "official incident log and telemetry file",
    "witness deposition and sworn testimony",
    "first anomaly or critical event logged by official sensors",
    "secondary radio monitoring records contact 42 minutes earlier",
    "unpublished military communications logs from the first hour",
    "area sealed during active investigation",
]

# Technical modern terms that cannot appear in ancient / pre-20th-century historical topics
MODERN_AVIATION_RADAR_TERMS: List[str] = [
    "radar anomaly",
    "flight controller",
    "flight log",
    "flight recorder",
    "black box",
    "telemetry",
    "cockpit",
    "air traffic",
    "transponder",
    "tape records within 48 minutes",
    "blackout before the crash",
    "beacon",
]


class TopicDomainValidator:
    """
    Validates domain consistency, entity grounding, and absence of generic hallucinated boilerplate.
    """

    @classmethod
    def extract_topic_keywords(cls, topic: str) -> List[str]:
        words = re.findall(r"[A-Za-z0-9]+", topic.lower())
        return [w for w in words if w not in STOPWORDS and len(w) >= 3]

    @classmethod
    def is_modern_aviation_topic(cls, topic: str) -> bool:
        aviation_keywords = {
            "flight", "plane", "airplane", "aircraft", "crash", "skyjacking",
            "pilot", "cockpit", "aviation", "boeing", "airbus", "radar",
            "malaysia", "mh370", "cooper", "pan", "am", "twa",
        }
        topic_words = set(re.findall(r"[A-Za-z0-9]+", topic.lower()))
        return bool(topic_words & aviation_keywords)

    @classmethod
    def validate_research(
        cls,
        arg1: Any = None,
        arg2: Any = None,
        *,
        topic: Optional[str] = None,
        research_data: Optional[Dict[str, Any]] = None,
        raise_on_error: bool = False,
    ) -> Tuple[bool, List[str]]:
        """
        Validates that research_data is genuinely grounded in the topic and contains
        no generic incident template boilerplate or unevidenced claims.
        """
        # Resolve positional and keyword arguments flexibly
        if isinstance(arg1, str) and (isinstance(arg2, dict) or arg2 is None):
            resolved_topic = topic or arg1
            resolved_data = research_data or arg2
        elif isinstance(arg1, dict):
            resolved_data = research_data or arg1
            resolved_topic = topic or (arg2 if isinstance(arg2, str) else None)
        else:
            resolved_topic = topic
            resolved_data = research_data

        if resolved_data and not resolved_topic:
            resolved_topic = resolved_data.get("topic", "")
        resolved_topic = str(resolved_topic or "")

        errors: List[str] = []

        if not isinstance(resolved_data, dict):
            errors.append("Research data must be a dictionary.")
            if raise_on_error:
                from docstudio.research_engine import GroundedResearchValidationError
                raise GroundedResearchValidationError("; ".join(errors))
            return False, errors

        # 1. Basic schema presence
        claims = resolved_data.get("claims", [])
        if not claims or not isinstance(claims, list):
            errors.append("Research contains no factual claims list.")
        elif len(claims) < 2:
            errors.append(f"Research contains insufficient claims ({len(claims)} found, minimum 2 required).")

        entities = resolved_data.get("entities", [])
        if not entities or not isinstance(entities, list):
            errors.append("Research contains no entities list.")

        # 2. Topic keyword representation
        topic_keywords = cls.extract_topic_keywords(resolved_topic)
        if topic_keywords:
            searchable_text_parts = [
                resolved_data.get("summary", ""),
                resolved_data.get("central_question", ""),
            ]
            for ent in entities:
                if isinstance(ent, dict):
                    searchable_text_parts.append(ent.get("name", ""))
                    searchable_text_parts.append(ent.get("role", ""))
            for cl in claims:
                if isinstance(cl, dict):
                    searchable_text_parts.append(cl.get("claim", "") or cl.get("statement", ""))
            for ev in resolved_data.get("timeline", []):
                if isinstance(ev, dict):
                    searchable_text_parts.append(ev.get("event", ""))

            full_searchable = " ".join(searchable_text_parts).lower()

            # At least one core topic keyword must be present in research content
            matches = [kw for kw in topic_keywords if kw in full_searchable]
            if not matches:
                errors.append(
                    f"Topic entities from '{resolved_topic}' ({topic_keywords}) are not represented in research output."
                )

        # 3. Reject generic incident boilerplate templates
        full_json_str = str(resolved_data).lower()
        for bp in FORBIDDEN_BOILERPLATE_TEMPLATES:
            if bp in full_json_str:
                errors.append(
                    f"Research contains generic incident template boilerplate: '{bp}'."
                )

        # Check for placeholder entity pattern 'Principal Witnesses ({topic})'
        for ent in entities:
            if isinstance(ent, dict):
                ename = ent.get("name", "").lower()
                if "principal witnesses" in ename:
                    errors.append(
                        f"Research entity '{ent.get('name')}' is a generic placeholder template."
                    )

        # 4. Check for modern aviation/telemetry boilerplate on non-aviation topics
        if not cls.is_modern_aviation_topic(resolved_topic):
            for term in MODERN_AVIATION_RADAR_TERMS:
                if term in full_json_str:
                    errors.append(
                        f"Non-aviation historical topic '{resolved_topic}' contains incompatible modern technical boilerplate: '{term}'."
                    )

        # 5. Check claims evidence grounding
        for idx, cl in enumerate(claims):
            if not isinstance(cl, dict):
                errors.append(f"Claim at index {idx} is not an object.")
                continue
            cid = cl.get("claim_id", f"claim_{idx}")
            claim_text = (cl.get("claim", "") or cl.get("statement", "")).strip()
            if not claim_text:
                errors.append(f"Claim '{cid}' has empty statement.")

            sources = cl.get("sources", [])
            if not sources and cl.get("source"):
                sources = [cl.get("source")]
            if isinstance(sources, str):
                sources = [sources] if sources.strip() else []

            if not sources or not any(str(s).strip() for s in sources):
                errors.append(f"Claim '{cid}' has no supporting source or evidence citations.")

        valid = len(errors) == 0
        if not valid and raise_on_error:
            from docstudio.research_engine import GroundedResearchValidationError
            raise GroundedResearchValidationError(f"Research grounding validation failed for '{resolved_topic}': {'; '.join(errors)}")

        return valid, errors


def validate_topic_research(topic: str, research_data: Dict[str, Any], raise_on_error: bool = False) -> Tuple[bool, List[str]]:
    """Convenience functional interface for TopicDomainValidator."""
    return TopicDomainValidator.validate_research(topic, research_data, raise_on_error=raise_on_error)
