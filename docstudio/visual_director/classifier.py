"""
DocStudio Semantic Visual Classifier.
Classifies narration and story moments into one of 28 semantic visual strategies
and assigns authenticity labels based on evidence and narrative context.
"""

from __future__ import annotations
import re
from typing import Dict, Any, Tuple, Optional, List
from docstudio.visual_director.strategies import (
    VisualStrategy,
    VisualStatus,
)


class SemanticVisualClassifier:
    """
    Evaluates narration text, story beat intent, and claims to select
    the exact visual storytelling strategy and authenticity classification.
    """

    def classify_shot(
        self,
        narration: str,
        story_beat: str = "investigation",
        seeing_intent: str = "",
        keywords: Optional[List[str]] = None,
        referenced_claims: Optional[List[Dict[str, Any]]] = None,
        is_cold_hook: bool = False,
        shot_index: int = 0,
        total_shots_in_scene: int = 1,
    ) -> Tuple[VisualStrategy, VisualStatus, str]:
        """
        Returns (strategy, authenticity_status, reason).
        """
        text = f"{narration} {seeing_intent} {' '.join(keywords or [])}".lower()
        referenced_claims = referenced_claims or []

        # -------------------------------------------------------------
        # 1. COLD HOOK (0-8s): Maximum cinematic immersion or catastrophic anomaly
        # -------------------------------------------------------------
        if is_cold_hook or story_beat == "hook" or "cold hook" in story_beat:
            if any(w in text for w in ["document", "classified", "telegram", "memo", "order", "unsealed"]):
                return VisualStrategy.PRIMARY_DOCUMENT, VisualStatus.AUTHENTIC_SOURCE, "Cold hook centered on declassified primary document reveal."
            elif any(w in text for w in ["radar", "coordinate", "telemetry", "vector", "map", "flight path"]):
                return VisualStrategy.MAP, VisualStatus.PROCEDURAL, "Cold hook centered on tactical tracking or radar anomaly."
            else:
                return VisualStrategy.AI_CINEMATIC_VIDEO, VisualStatus.AI_GENERATED, "Cold hook demanding high-impact cinematic reenactment of anomaly."

        # -------------------------------------------------------------
        # 2. DISTANCE, ROUTE, & GEOSPATIAL MAPS
        # -------------------------------------------------------------
        if any(w in text for w in ["kilometer", "km", "miles", "flight path", "route", "heading", "trajectory", "fled toward", "traveled"]):
            return VisualStrategy.ROUTE_MAP, VisualStatus.PROCEDURAL, "Narrative explicitly tracks movement, distance, or spatial trajectory."

        if any(w in text for w in ["coordinates", "latitude", "longitude", "perimeter", "nautical", "radar", "ocean grid", "territory", "border"]):
            return VisualStrategy.MAP, VisualStatus.PROCEDURAL, "Narrative specifies geographic coordinates or spatial perimeter."

        if any(w in text for w in ["across the world", "global scale", "nationwide", "scale of"]):
            return VisualStrategy.GEOGRAPHICAL_SCALE, VisualStatus.PROCEDURAL, "Narrative communicates expansive geographic scale."

        # -------------------------------------------------------------
        # 3. NUMERICAL DATA, REVENUE, & STATISTICS
        # -------------------------------------------------------------
        if any(w in text for w in ["tripled", "doubled", "revenue", "percent", "growth", "increased from", "decreased from", "statistic", "annual", "budget"]):
            return VisualStrategy.DATA_CHART, VisualStatus.PROCEDURAL, "Narrative presents quantifiable financial or statistical progression."

        if re.search(r'\b\d+(?:,\d{3})*(?:\.\d+)?(?:\s*(?:percent|%|million|billion|thousand|tons|deaths|casualties|hours|passengers|dollars|\$))\b', text):
            return VisualStrategy.STATISTIC, VisualStatus.PROCEDURAL, "Narrative highlights a specific critical numerical measurement or statistic."

        # -------------------------------------------------------------
        # 4. CONTRADICTIONS, COMPARISONS, & EVIDENCE MATRICES
        # -------------------------------------------------------------
        if any(w in text for w in ["contradiction", "contradicted", "versus", "vs", "inconsistent", "two versions", "conflicting accounts", "dispute"]):
            return VisualStrategy.COMPARISON, VisualStatus.PROCEDURAL, "Narrative contrasts conflicting claims or testimony."

        if any(w in text for w in ["timeline", "chronology", "sequence of events", "hour by hour", "minute by minute", "between 19", "in 19"]):
            # If specifically highlighting timeline progression
            if any(w in text for w in ["timeline", "chronology", "sequence", "hour by hour", "minutes later"]):
                return VisualStrategy.TIMELINE, VisualStatus.PROCEDURAL, "Narrative details chronological sequence of timestamped events."

        # -------------------------------------------------------------
        # 5. FORENSIC DOCUMENTS, NEWSPAPERS, & QUOTES
        # -------------------------------------------------------------
        if any(w in text for w in ["newspaper", "headline", "front page", "press reported", "daily gazette"]):
            return VisualStrategy.NEWSPAPER, VisualStatus.ARCHIVAL, "Narrative references historical newspaper coverage."

        if any(w in text for w in ["letter", "memo", "telegram", "board of inquiry", "deposition", "report", "declassified", "logbook", "autopsy", "patent"]):
            has_real_source = any(c.get("source_type") == "primary" for c in referenced_claims)
            status = VisualStatus.AUTHENTIC_SOURCE if has_real_source else VisualStatus.RECONSTRUCTION
            return VisualStrategy.PRIMARY_DOCUMENT, status, "Narrative focuses on primary archival document or official report."

        if any(w in text for w in ["quote", "wrote in", "confessed", "testified", "radioed", "declared", "stated:"]):
            return VisualStrategy.QUOTE_CARD, VisualStatus.PROCEDURAL, "Narrative highlights direct sworn testimony or critical quotation."

        # -------------------------------------------------------------
        # 6. INVESTIGATION & RELATIONAL BOARDS
        # -------------------------------------------------------------
        if any(w in text for w in ["evidence board", "connection", "suspects", "web of", "accomplice", "network of"]):
            return VisualStrategy.EVIDENCE_BOARD, VisualStatus.PROCEDURAL, "Narrative maps intricate relationships or suspect connections."

        # -------------------------------------------------------------
        # 7. DIGITAL, SCREEN, & DATABASE LOOKUPS
        # -------------------------------------------------------------
        if any(w in text for w in ["database", "server", "ip address", "search history", "computer records", "telemetry logs"]):
            return VisualStrategy.DATABASE_LOOKUP, VisualStatus.RECONSTRUCTION, "Narrative analyzes digital records or database queries."

        if any(w in text for w in ["phone", "cell tower", "text message", "voicemail", "call log"]):
            return VisualStrategy.SCREEN_RECREATION, VisualStatus.RECONSTRUCTION, "Narrative references telecommunications or mobile data."

        # -------------------------------------------------------------
        # 8. HUMAN & OBJECT RECONSTRUCTIONS
        # -------------------------------------------------------------
        if any(w in text for w in ["entered the", "boarded", "cockpit", "cabin", "face of", "eyewitness saw", "pilot adjusted"]):
            return VisualStrategy.HUMAN_RECONSTRUCTION, VisualStatus.RECONSTRUCTION, "Narrative depicts human action or firsthand observation."

        if any(w in text for w in ["aircraft", "submersible", "capsule", "device", "weapon", "artifact", "mechanism"]):
            return VisualStrategy.OBJECT_RECONSTRUCTION, VisualStatus.RECONSTRUCTION, "Narrative investigates physical object or vehicle design."

        # -------------------------------------------------------------
        # 9. ARCHIVAL IMAGES VS ESTABLISHING LOCATION
        # -------------------------------------------------------------
        if any(w in text for w in ["photograph", "black and white", "vintage", "archival", "taken in 19", "surviving image"]):
            return VisualStrategy.ARCHIVAL_PHOTO, VisualStatus.ARCHIVAL, "Historical photograph authenticating the era and subjects."

        if any(w in text for w in ["hangar", "building", "airfield", "harbor", "exterior", "facility", "headquarters"]):
            return VisualStrategy.LOCATION_ESTABLISHING, VisualStatus.STOCK, "Establishing environment or historical architectural location."

        # -------------------------------------------------------------
        # 10. MULTI-SHOT PACING VARIETY (Rhythmic fallback based on shot index)
        # -------------------------------------------------------------
        if shot_index == 0:
            return VisualStrategy.LOCATION_ESTABLISHING, VisualStatus.STOCK, "Scene opener establishing narrative setting."
        elif shot_index % 3 == 1:
            return VisualStrategy.ARCHIVAL_PHOTO, VisualStatus.ARCHIVAL, "Archival evidence anchor reinforcing narrative credibility."
        elif shot_index % 3 == 2:
            return VisualStrategy.AI_CINEMATIC_STILL, VisualStatus.AI_GENERATED, "Cinematic recreation visualizing unseen historical moment."

        return VisualStrategy.ATMOSPHERIC_BROLL, VisualStatus.STOCK, "Atmospheric cinema footage providing narrative pacing."
