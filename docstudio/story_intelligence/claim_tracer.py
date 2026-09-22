"""
docstudio/story_intelligence/claim_tracer.py
============================================
Claim ledger tracing, source verification, absolute claim auditing,
evidence grades, and human-scale number anchoring (Sections 1, 14, 20).
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Set, Tuple

from docstudio.claims_ledger import ClaimsLedger, ClaimEntry
from docstudio.story_intelligence.models import ClaimRecord, EvidenceGrade


ABSOLUTE_WORDS_PATTERN = re.compile(
    r"\b(first\s+ever|largest\s+ever|smallest\s+ever|never|always|unprecedented|impossible|completely\s+unique|all-time|without\s+exception|undeniably)\b",
    re.IGNORECASE,
)

HEDGE_MARKERS = [
    "disputed", "claimed", "alleged", "conflicting", "uncertain",
    "unconfirmed", "debated", "some argue", "according to", "reportedly",
    "purported", "contested", "unresolved", "historians debate", "records suggest"
]


class ClaimTracer:
    """
    Traces and audits factual claims, sources, numbers, and absolutes.
    Integrates with existing ClaimsLedger.
    """

    def __init__(self, ledger: Optional[ClaimsLedger] = None):
        self.ledger = ledger or ClaimsLedger()

    def process_research_claims(
        self, research_data: Dict[str, Any]
    ) -> Dict[str, ClaimRecord]:
        """
        Converts raw research claims into structured ClaimRecord instances.
        Enforces source requirements, absolute claim flags, and human anchors.
        """
        raw_claims = research_data.get("claims", [])
        records: Dict[str, ClaimRecord] = {}

        for i, c in enumerate(raw_claims):
            cid = str(c.get("claim_id", f"C{i+1:03d}")).strip()
            text = str(c.get("claim", c.get("statement", ""))).strip()
            raw_sources = c.get("sources", c.get("source", []))
            if isinstance(raw_sources, list):
                source_str = ", ".join(str(s) for s in raw_sources if s)
            else:
                source_str = str(raw_sources).strip()

            # Evidence grade classification
            source_lower = source_str.lower()
            if any(k in source_lower for k in ["nasa", "declassified", "faa", "official", "kgb", "pentagon", "flight log", "manifest", "court"]):
                grade = EvidenceGrade.OFFICIAL.value
            elif any(k in source_lower for k in ["university", "journal", "academic", "peer-reviewed", "archive", "history", "paper"]):
                grade = EvidenceGrade.ACADEMIC.value
            elif any(k in source_lower for k in ["industry", "report", "benchmark", "analysis", "census", "stat"]):
                grade = EvidenceGrade.INDUSTRY.value
            else:
                grade = EvidenceGrade.HEURISTIC.value if not source_str else EvidenceGrade.INDUSTRY.value

            # Disputed status
            status_val = str(c.get("verification_status", c.get("status", "verified"))).lower()
            disputed = status_val in ("disputed", "uncertain", "debated")

            # Absolute claims
            is_absolute = bool(ABSOLUTE_WORDS_PATTERN.search(text)) or bool(c.get("absolute_claim", False))
            absolute_ok = bool(c.get("absolute_ok", False)) or (status_val == "verified" and len(source_str) > 0)

            # Human anchor generation for large numbers
            human_anchor = str(c.get("human_anchor", "")).strip()
            if not human_anchor:
                human_anchor = self._generate_human_anchor(text)

            record = ClaimRecord(
                claim_id=cid,
                claim=text,
                source=source_str or "UNSOURCED",
                source_type=grade,
                confidence=str(c.get("confidence", "high")),
                disputed=disputed,
                hedge_required=disputed,
                graphic_worthy=bool(c.get("graphic_worthy", False)),
                absolute_claim=is_absolute and not absolute_ok,
                human_anchor=human_anchor,
                relevant_story_beats=[],
            )
            records[cid] = record

        return records

    def audit_narration_claims(
        self,
        narration_text: str,
        claim_records: Dict[str, ClaimRecord],
        allow_unverified_numbers: bool = False,
    ) -> Tuple[bool, List[str]]:
        """
        Audits narration text against the claim ledger:
        1. Verifies that disputed claims in narration have hedge markers.
        2. Detects unsupported absolutes.
        3. Validates numbers against claim ledger.
        """
        violations: List[str] = []
        text_lower = narration_text.lower()

        # Check unsupported absolutes in spoken text
        absolute_matches = ABSOLUTE_WORDS_PATTERN.findall(narration_text)
        for match in absolute_matches:
            # Check if any verified claim explicitly authorizes this absolute
            authorized = any(
                c.claim_id in claim_records
                and match.lower() in claim_records[c.claim_id].claim.lower()
                and not claim_records[c.claim_id].absolute_claim
                for c in claim_records.values()
            )
            if not authorized:
                violations.append(
                    f"Unsupported absolute claim spoken: '{match}'. Absolute superlatives require explicit verified evidence."
                )

        # Check hedging for disputed claims
        for cid, record in claim_records.items():
            if record.disputed:
                # If key tokens of the claim appear in narration, ensure hedge marker is present
                claim_words = [w for w in record.claim.lower().split() if len(w) > 5]
                matches_count = sum(1 for w in claim_words if w in text_lower)
                if matches_count >= 2:
                    has_hedge = any(m in text_lower for m in HEDGE_MARKERS)
                    if not has_hedge:
                        violations.append(
                            f"Disputed claim '{cid}' mentioned in narration without required hedging marker "
                            f"(e.g. 'reportedly', 'conflicting accounts', 'allegedly')."
                        )

        # Check numbers
        extracted_numbers = self.ledger.extract_numbers_from_text(narration_text)
        for num in extracted_numbers:
            clean_num = num.replace(",", "").strip()
            # If ledger has indexed numbers, check match
            if self.ledger.number_index:
                if clean_num not in self.ledger.number_index and not allow_unverified_numbers:
                    violations.append(
                        f"Spoken number '{num}' has no matching verified source in the Claims Ledger."
                    )

        return (len(violations) == 0), violations

    def _generate_human_anchor(self, text: str) -> str:
        """Generates a relatable human-scale comparison for large numbers."""
        # Detect large distances or weights or monetary sums
        m_millions = re.search(r"(\d+(?:\.\d+)?)\s*(?:million|m)\s*(?:dollars|\$)", text, re.IGNORECASE)
        if m_millions:
            val = float(m_millions.group(1))
            if val >= 100:
                return "Enough to purchase a fleet of commercial airliners"
            return "More than an average worker earns in fifty lifetimes"

        m_dist = re.search(r"(\d+(?:\.\d+)?)\s*(?:miles|km|kilometers)", text, re.IGNORECASE)
        if m_dist:
            val = float(m_dist.group(1))
            if val > 1000:
                return "Roughly the distance from New York to London"
            if val > 200:
                return "Equivalent to driving non-stop for four hours"

        m_altitude = re.search(r"(\d+(?:\.\d+)?)\s*(?:feet|ft|meters|m)\s*(?:altitude|high|deep)", text, re.IGNORECASE)
        if m_altitude:
            val = float(m_altitude.group(1))
            if val > 30000:
                return "Cruising altitude of a transatlantic jetliner"
            if val > 1000:
                return "Taller than the Empire State Building"

        return ""
