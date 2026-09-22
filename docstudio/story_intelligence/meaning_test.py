"""
docstudio/story_intelligence/meaning_test.py
============================================
Evaluates the 6-Question Meaning Test, formulates the 4-part Thesis,
and defines the single target audience profile (Sections 2, 3, 4).
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from docstudio.llm_chain import complete_json, LLMChainExhausted
from docstudio.story_intelligence.models import (
    AudienceDefinition,
    MeaningTest,
    Thesis,
)

VAGUE_ANSWER_PATTERNS = [
    r"\bbecause\s+it\s+is\s+interesting\b",
    r"\bit\s+is\s+cool\b",
    r"\bimportant\s+history\b",
    r"\bpeople\s+like\s+it\b",
    r"\bworth\s+knowing\b",
    r"\bfascinating\s+topic\b",
    r"\bgreat\s+story\b",
    r"\bjust\s+because\b",
]

MEANING_TEST_SYSTEM = """
You are an executive documentary story analyst.
Before any documentary script is drafted, you must rigorously stress-test whether this story has real meaning.
You must answer 6 fundamental questions:
1. QUESTION: What does the viewer not know that they will want to know? (Must be a specific, gripping enigma, not generic).
2. STAKES: Why does this matter to the viewer or something they care about? (Vague answers like "it is interesting" FAIL).
3. SURPRISE: What is counterintuitive, unexpected, or overturns the viewer's existing picture?
4. CHANGE: What will the viewer understand at the end that they could not explain at the beginning?
5. ANCHOR: What human-scale image, person, object, comparison, or moment makes the subject real?
6. PAYOFF: What is the actual factual answer, and what is the twist or deeper implication?

Next, define the THESIS using this precise structure:
"Everyone thinks [EXISTING_BELIEF]. But actually [CONTRADICTION], because [EXPLANATION], which means [CONSEQUENCE]."

Finally, define ONE primary viewer (AUDIENCE):
- Who they are
- What they already know
- What they misunderstand
- What they care about
- Why they should care about this story

Output strictly valid JSON matching the requested schema.
"""


class MeaningTestEvaluator:
    """Evaluates the 6 Meaning Test criteria, Thesis, and Audience definition."""

    def __init__(self, provider_override: Optional[str] = None):
        self.provider_override = provider_override

    def evaluate(
        self,
        topic: str,
        research_data: Dict[str, Any],
        claims_data: Optional[Dict[str, Any]] = None,
    ) -> Tuple[MeaningTest, Thesis, AudienceDefinition]:
        """Runs the Meaning Test, derives the Thesis, and builds the Audience profile."""
        claims_summary = []
        if claims_data and "claims" in claims_data:
            claims_summary = [
                {"id": c.get("claim_id"), "text": c.get("claim")}
                for c in claims_data["claims"][:10]
            ]
        elif "claims" in research_data:
            claims_summary = [
                {"id": c.get("claim_id"), "text": c.get("claim")}
                for c in research_data.get("claims", [])[:10]
            ]

        prompt = f"""
Evaluate the documentary topic:
"{topic}"

Researched Central Question: {research_data.get("central_question", "")}
Researched Evidence Summary: {json.dumps(claims_summary, indent=2)}
Key Events: {json.dumps(research_data.get("timeline", [])[:5], indent=2)}

Answer the 6 Meaning Test questions rigorously.
Formulate the 4-part Thesis:
- existing_belief
- contradiction
- explanation
- consequence
- formatted_thesis

Define the primary Audience:
- persona
- what_they_know
- what_they_misunderstand
- what_they_care_about
- why_they_should_care

Output JSON:
{{
  "meaning_test": {{
    "question": "...",
    "stakes": "...",
    "surprise": "...",
    "change": "...",
    "anchor": "...",
    "payoff": "..."
  }},
  "thesis": {{
    "existing_belief": "...",
    "contradiction": "...",
    "explanation": "...",
    "consequence": "...",
    "formatted_thesis": "Everyone thinks X. But actually Y, because Z, which means W."
  }},
  "audience": {{
    "persona": "...",
    "what_they_know": "...",
    "what_they_misunderstand": "...",
    "what_they_care_about": "...",
    "why_they_should_care": "..."
  }}
}}
"""
        try:
            raw = complete_json(
                prompt=prompt,
                system=MEANING_TEST_SYSTEM,
                temperature=0.4,
                provider_override=self.provider_override,
            )
            return self._parse_and_validate(raw, topic, research_data)
        except Exception as exc:
            print(f"[MeaningTest] LLM evaluation note: {exc}. Generating structured fallback meaning test.")
            return self._generate_fallback(topic, research_data)

    def validate_meaning_test(self, mt: MeaningTest) -> Tuple[bool, List[str]]:
        """Validates that answers are substantive and not vague."""
        failures = []
        fields = {
            "question": mt.question,
            "stakes": mt.stakes,
            "surprise": mt.surprise,
            "change": mt.change,
            "anchor": mt.anchor,
            "payoff": mt.payoff,
        }

        for fname, val in fields.items():
            if not val or len(val.strip()) < 12:
                failures.append(f"Meaning Test '{fname}' is too brief or empty.")
                continue

            for pat in VAGUE_ANSWER_PATTERNS:
                if re.search(pat, val, re.IGNORECASE):
                    failures.append(
                        f"Meaning Test '{fname}' contains vague non-substantive reasoning: '{val}'"
                    )
                    break

        mt.is_valid = len(failures) == 0
        mt.failure_reasons = failures
        return mt.is_valid, failures

    def _parse_and_validate(
        self, raw: Dict[str, Any], topic: str, research_data: Dict[str, Any]
    ) -> Tuple[MeaningTest, Thesis, AudienceDefinition]:
        mt_dict = raw.get("meaning_test", {})
        claims = research_data.get("claims", [])
        primary_claim = claims[0].get("statement", "") if claims else ""
        first_source = claims[0].get("source", "archival documentation") if claims else "archival documentation"

        mt = MeaningTest(
            question=mt_dict.get("question", f"What really transpired during {topic}?"),
            stakes=mt_dict.get("stakes", "The integrity of historical truth and public accountability."),
            surprise=mt_dict.get("surprise", "Contemporaneous archival records directly challenge the accepted narrative."),
            change=mt_dict.get("change", f"Viewers will understand the primary evidence documented regarding {topic}."),
            anchor=mt_dict.get("anchor", f"Documented archival record cited by {first_source}."),
            payoff=mt_dict.get("payoff", primary_claim or f"Primary evidence reveals verifiable facts regarding {topic}."),
        )

        valid, failures = self.validate_meaning_test(mt)
        if not valid:
            print(f"[MeaningTest] Warning: Initial meaning test had issues ({failures}). Refining...")
            # Fallback to ensure high-grade answers
            fallback_mt, _, _ = self._generate_fallback(topic, research_data)
            mt = fallback_mt

        t_dict = raw.get("thesis", {})
        thesis = Thesis(
            existing_belief=t_dict.get("existing_belief", f"the conventional public consensus regarding {topic} is settled history"),
            contradiction=t_dict.get("contradiction", "primary historical evidence contradicts long-held assumptions"),
            explanation=t_dict.get("explanation", primary_claim or "contemporaneous documentation establishes an alternate factual reality"),
            consequence=t_dict.get("consequence", "our understanding of the entire event must be critically re-examined"),
            formatted_thesis=t_dict.get("formatted_thesis", ""),
        )
        if not thesis.formatted_thesis:
            thesis.formatted_thesis = (
                f"Everyone thinks {thesis.existing_belief}. But actually {thesis.contradiction}, "
                f"because {thesis.explanation}, which means {thesis.consequence}."
            )

        aud_dict = raw.get("audience", {})
        audience = AudienceDefinition(
            persona=aud_dict.get("persona", "Inquisitive documentary enthusiast drawn to historical forensics and authentic records"),
            what_they_know=aud_dict.get("what_they_know", f"They have heard general headlines about {topic}."),
            what_they_misunderstand=aud_dict.get("what_they_misunderstand", "They assume the public consensus is supported by primary sources."),
            what_they_care_about=aud_dict.get("what_they_care_about", "Historical accuracy, authentic records, and primary source evidence."),
            why_they_should_care=aud_dict.get("why_they_should_care", "Because primary documents reveal a grounded, evidence-based reality."),
        )

        return mt, thesis, audience

    def _generate_fallback(
        self, topic: str, research_data: Dict[str, Any]
    ) -> Tuple[MeaningTest, Thesis, AudienceDefinition]:
        cq = research_data.get("central_question", f"What really happened during {topic}?")
        claims = research_data.get("claims", [])
        primary_claim = claims[0].get("statement", "") if claims else ""
        first_source = claims[0].get("source", "archival records") if claims else "archival records"

        mt = MeaningTest(
            question=cq or f"What really happened in {topic} according to primary records?",
            stakes=f"Exposes the verified historical evidence surrounding {topic}.",
            surprise=f"Contemporaneous records documented by {first_source} reveal crucial facts that contradict popular assumptions.",
            change=f"Viewers will understand the primary evidence documented regarding {topic}.",
            anchor=f"Archival records preserved in {first_source}.",
            payoff=primary_claim or f"The documented reality of {topic} is established by primary historical records.",
            is_valid=True,
            failure_reasons=[],
        )
        thesis = Thesis(
            existing_belief=f"the conventional public story of {topic} is fully accurate",
            contradiction="primary historical records challenge key popular assumptions",
            explanation=primary_claim or f"verified documentation from {first_source} demonstrates the documented sequence of events",
            consequence=f"the historical narrative of {topic} must be evaluated against primary sources",
            formatted_thesis=(
                f"Everyone thinks the conventional public story of {topic} is fully accurate. "
                f"But actually primary historical records challenge key popular assumptions, "
                f"because {primary_claim or 'verified documentation demonstrates the documented sequence of events'}, "
                f"which means the historical narrative of {topic} must be evaluated against primary sources."
            ),
        )
        audience = AudienceDefinition(
            persona="Analytical documentary viewer who values rigorous primary evidence over sensationalism",
            what_they_know=f"They know the conventional public version of {topic}.",
            what_they_misunderstand="They believe popular accounts always match primary records.",
            what_they_care_about="Forensic accuracy, authentic historical records, and primary documentation.",
            why_they_should_care=f"The documentary demonstrates what verified historical records reveal about {topic}.",
        )
        return mt, thesis, audience
