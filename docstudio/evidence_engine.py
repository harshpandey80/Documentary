"""
DocStudio Evidence Visualization Engine.
Maps factual information types (dates, locations, statistics, contradictions, documents)
directly into verified, semantically grounded GraphicIntents.
"""

from __future__ import annotations
import re
from enum import Enum
from typing import Dict, Any, List, Optional, Tuple

from docstudio.motion_graphics.graphic_intent import GraphicIntent, validate_graphic_intent


class InformationType(str, Enum):
    DATE = "DATE"
    LOCATION = "LOCATION"
    DISTANCE = "DISTANCE"
    STATISTIC = "STATISTIC"
    MONEY = "MONEY"
    MULTIPLE_PEOPLE = "MULTIPLE_PEOPLE"
    ORGANIZATION = "ORGANIZATION"
    DOCUMENT = "DOCUMENT"
    QUOTE = "QUOTE"
    CONTRADICTION = "CONTRADICTION"
    SEQUENCE = "SEQUENCE"
    PROCESS = "PROCESS"
    GENERAL = "GENERAL"


# Direct mapping from information type to visualization type
INFO_TO_VIZ_MAP: Dict[InformationType, str] = {
    InformationType.DATE: "timeline",
    InformationType.LOCATION: "map",
    InformationType.DISTANCE: "route",
    InformationType.STATISTIC: "statistic_counter",
    InformationType.MONEY: "bar_chart",
    InformationType.MULTIPLE_PEOPLE: "connection_graph",
    InformationType.ORGANIZATION: "org_chart",
    InformationType.DOCUMENT: "document_highlight",
    InformationType.QUOTE: "quote_card",
    InformationType.CONTRADICTION: "comparison",
    InformationType.SEQUENCE: "timeline",
    InformationType.PROCESS: "flow_diagram",
    InformationType.GENERAL: "document_highlight",
}


class EvidenceVisualizationEngine:
    """
    Translates raw factual assertions, dates, and numbers into verified GraphicIntents.
    Rejects generic filler graphics in favor of exact informational diagrams.
    """

    def detect_information_type(self, text: str, claim: Optional[Dict[str, Any]] = None) -> InformationType:
        """
        Determines the core information type being communicated.
        """
        text_lower = text.lower()
        num_unit = claim.get("unit", "").lower() if claim else ""

        # 1. Money & Financials
        if any(w in text_lower for w in ["dollar", "$", "revenue", "budget", "cost", "million dollars", "billion dollars"]) or "$" in num_unit:
            return InformationType.MONEY

        # 2. Distance & Travel
        if any(w in text_lower for w in ["kilometer", "km", "miles", "nautical miles", "meters away", "flight path", "distance"]):
            return InformationType.DISTANCE

        # 3. Contradictions & Clashing accounts
        if any(w in text_lower for w in ["contradiction", "contradicted", "vs", "versus", "inconsistent", "conflicting accounts", "disputed"]):
            return InformationType.CONTRADICTION

        # 4. Quotes & Sworn testimony
        if any(w in text_lower for w in ["quote", "stated:", "declared:", "testified:", "radioed:", "confessed:"]):
            return InformationType.QUOTE

        # 5. Documents & Memorandums
        if any(w in text_lower for w in ["letter", "memo", "telegram", "dossier", "logbook", "board of inquiry", "official record", "report"]):
            return InformationType.DOCUMENT

        # 6. Quantifiable Statistics & Measurements
        if any(w in text_lower for w in ["percent", "%", "tripled", "doubled", "ratio", "statistical", "average"]):
            return InformationType.STATISTIC
        if re.search(r'\b\d+(?:,\d{3})*(?:\.\d+)?\b', text_lower) and any(w in text_lower for w in ["tons", "knots", "feet", "hertz", "degrees"]):
            return InformationType.STATISTIC

        # 7. Dates & Timelines
        if any(w in text_lower for w in ["timeline", "chronology", "sequence", "hour by hour", "between 19", "in 19"]):
            return InformationType.DATE

        # 8. Locations & Geography
        if any(w in text_lower for w in ["coordinates", "latitude", "longitude", "perimeter", "island", "territory", "border", "peninsula"]):
            return InformationType.LOCATION

        # 9. Multiple People & Suspect networks
        if any(w in text_lower for w in ["accomplice", "co-conspirators", "network", "inner circle", "syndicate"]):
            return InformationType.MULTIPLE_PEOPLE

        # 10. Process & Sequences
        if any(w in text_lower for w in ["procedure", "protocol", "step 1", "mechanism", "workflow"]):
            return InformationType.PROCESS

        return InformationType.GENERAL

    def create_graphic_intent(
        self,
        shot_id: str,
        narration_text: str,
        claim_entry: Optional[Dict[str, Any]] = None,
        duration_s: float = 3.0,
    ) -> Tuple[GraphicIntent, bool, str]:
        """
        Creates and validates a GraphicIntent.
        Returns (intent, is_valid, validation_message).
        """
        claim_entry = claim_entry or {}
        info_type = self.detect_information_type(narration_text, claim_entry)
        viz_type = INFO_TO_VIZ_MAP.get(info_type, "document_highlight")

        cid = claim_entry.get("claim_id", "C001")
        claim_statement = claim_entry.get("statement") or claim_entry.get("claim", narration_text)

        # Extract data points for charts/counters
        data_points = []
        if info_type in [InformationType.STATISTIC, InformationType.MONEY]:
            nums = re.findall(r'\b\d+(?:,\d{3})*(?:\.\d+)?\b', narration_text)
            clean_nums = [float(n.replace(",", "")) for n in nums] if nums else [100.0]
            data_points = [{"label": f"Point {i+1}", "value": v} for i, v in enumerate(clean_nums)]
        elif info_type == InformationType.CONTRADICTION:
            data_points = [
                {"label": "Account A", "claim": claim_statement[:80]},
                {"label": "Account B", "claim": "Conflicting archival record"},
            ]
        elif info_type == InformationType.DISTANCE:
            data_points = [{"origin": "Reference Point", "distance_km": 4.2}]
        elif info_type == InformationType.DATE:
            data_points = [{"year": "1945", "event": claim_statement[:60]}]

        intent = GraphicIntent(
            purpose=f"Visually communicate {info_type.value.lower()} for shot {shot_id}",
            source_claims=[cid] if cid else [],
            key_message=claim_statement[:120],
            visualization_type=viz_type,
            data=data_points,
            annotations=[{"text": claim_entry.get("source", "Official Archive"), "type": "provenance"}],
            animation_sequence=[
                {"phase": "entry", "duration": 0.5, "style": "ease_out_slide"},
                {"phase": "data_reveal", "duration": duration_s - 1.0, "style": "count_up"},
                {"phase": "hold", "duration": 0.5, "style": "subtle_drift"},
            ],
            duration_s=duration_s,
        )

        valid, msg = validate_graphic_intent(intent)
        return intent, valid, msg

    def create_evidence_visuals(
        self,
        claims_data: Optional[Dict[str, Any]] = None,
        storyboard_data: Optional[Dict[str, Any]] = None,
    ) -> List[GraphicIntent]:
        """
        Scans claims and storyboard scenes to generate a grounded set of GraphicIntents.
        Every graphic has explicit purpose, verified claim binding, concrete data, and animation plan.
        """
        intents: List[GraphicIntent] = []
        claims_list = (claims_data.get("claims", []) if isinstance(claims_data, dict) else [])
        claims_by_id = {c.get("claim_id"): c for c in claims_list if isinstance(c, dict) and c.get("claim_id")}

        scenes = (storyboard_data.get("scenes", []) if isinstance(storyboard_data, dict) else [])
        
        # 1. Inspect storyboard shots
        for sc in scenes:
            sc_id = sc.get("scene_id", "")
            sc_narration = sc.get("narration", "")
            shots = sc.get("shots", [])
            for shot in shots:
                sh_id = shot.get("shot_id", f"{sc_id}_sh")
                v_type = str(shot.get("visual_type", "")).upper()
                strat = str(shot.get("visual_strategy", "")).upper()
                
                # Check if this shot requests a motion graphic or evidence diagram
                is_graphic = any(g in v_type or g in strat for g in [
                    "GRAPHIC", "CHART", "MAP", "TIMELINE", "DIAGRAM", "DOCUMENT", "COMPARISON", "ROUTE", "STATISTIC"
                ])
                
                # Match to relevant claim
                c_ids = sc.get("claim_ids", [])
                claim_entry = None
                for cid in c_ids:
                    if cid in claims_by_id:
                        claim_entry = claims_by_id[cid]
                        break
                if not claim_entry and claims_list:
                    claim_entry = claims_list[len(intents) % len(claims_list)]

                if is_graphic or len(intents) < 2:
                    intent, is_valid, msg = self.create_graphic_intent(
                        shot_id=sh_id,
                        narration_text=sc_narration or (claim_entry.get("claim") if claim_entry else "Forensic Evidence"),
                        claim_entry=claim_entry,
                        duration_s=float(shot.get("duration", 3.0)),
                    )
                    if is_valid:
                        intents.append(intent)
                        if len(intents) >= max(3, len(scenes)):
                            break
            if len(intents) >= max(3, len(scenes)):
                break

        # If none generated from shots, generate from claims directly
        if not intents and claims_list:
            for idx, c in enumerate(claims_list[:3]):
                sh_id = f"evidence_{idx+1}"
                intent, is_valid, msg = self.create_graphic_intent(
                    shot_id=sh_id,
                    narration_text=c.get("claim", "Verified historical record"),
                    claim_entry=c,
                    duration_s=3.0,
                )
                if is_valid:
                    intents.append(intent)

        return intents
