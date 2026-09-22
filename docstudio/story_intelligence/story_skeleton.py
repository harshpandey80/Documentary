"""
docstudio/story_intelligence/story_skeleton.py
==============================================
Generates causal story skeleton (beat sheet), manages Open Loops,
designs emotional architecture with peak at 70-80%, and formats
long-form (10m / 4 chapters) or short-form (45s) structures (Sections 7, 8, 9, 10, 11).
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional, Tuple

from docstudio.llm_chain import complete_json
from docstudio.story_intelligence.models import (
    CausalityTransition,
    ClaimRecord,
    HookCandidate,
    MeaningTest,
    OpenLoop,
    PackagingConcept,
    StoryBeat,
    Thesis,
    TransitionType,
    TruthCategory,
)

SKELETON_SYSTEM = """
You are the Master Story Architect for DocStudio.
Your task is to build a causal beat sheet (the story skeleton) and map all open loops.

STRICT CAUSALITY RULES:
1. Transition types between beats MUST strictly be "BUT", "THEREFORE", or "BECAUSE".
2. BANNED: Meaningless chronological "and then" chains. Every beat must be caused by, complicate, or explain the prior beat.
3. OPEN LOOPS: Every planted question/loop MUST have an explicit payoff beat before the final 10% of runtime. Zero unresolved loops.
4. EMOTIONAL PEAK: Build ONE primary intellectual/emotional climax at approximately 70% to 80% of runtime.
5. CIRCLUAR ECHO: The ending resolution must thematically or visually echo the opening cold hook.

FORMAT RULES:
- If duration <= 90 seconds (Shorts): 4 to 5 beats.
  0-2s Hook, 2-6s Prime+Promise, 6-35s Causal Beats, 35-42s Payoff, 42-45s Loop-back.
- If duration > 90 seconds (Long-Form): 6 to 10 beats organized across cold open, promise/stakes, main forensic chapters, midpoint re-hook, climax (70-80%), and resolution.

Output purely valid JSON matching the schema.
"""


class StorySkeletonEngine:
    """Builds causal beat sheets and open loop tracking."""

    def __init__(self, provider_override: Optional[str] = None):
        self.provider_override = provider_override

    def generate_skeleton(
        self,
        topic: str,
        thesis: Thesis,
        meaning_test: MeaningTest,
        packaging: PackagingConcept,
        hook: HookCandidate,
        claim_records: Dict[str, ClaimRecord],
        target_duration_s: float = 300.0,
    ) -> Tuple[List[StoryBeat], List[OpenLoop], List[CausalityTransition], float, str, str]:
        """
        Builds the beat sheet, open loop map, causality map, peak description, and ending echo.
        Returns: (beats, loops, causality_map, peak_timestamp_s, peak_desc, ending_echo)
        """
        is_short_form = target_duration_s <= 90.0
        cids = list(claim_records.keys())[:15]

        prompt = f"""
Topic: "{topic}"
Target Runtime: {target_duration_s:.0f} seconds
Thesis: "{thesis.formatted_thesis}"
Packaging Title: "{packaging.working_title}"
Selected Hook ({hook.pattern_name}): "{hook.spoken_text}"
Core Question: "{meaning_test.question}"
Payoff Revelation: "{meaning_test.payoff}"
Human Anchor: "{meaning_test.anchor}"
Available Claim IDs: {cids}

Construct the story skeleton:
1. Sequence of beats with beat_id (e.g. B01, B02...), purpose, claim_ids, narration_intent, visual_intent, emotional_state, information_revealed, question_created, loop_ids, transition_type ("BUT", "THEREFORE", "BECAUSE"), target_duration_s, intensity (1-10), truth_category (REAL, RECREATED, ARCHIVAL, MAP, DATA, DOCUMENT, B-ROLL).
2. Open loops list with loop_id (e.g. LOOP_A), plant_beat_id, plant_timestamp_s, payoff_beat_id, payoff_timestamp_s, description.
3. Causality transitions between consecutive beats.
4. peak_timestamp_s (must be between {target_duration_s * 0.70:.1f}s and {target_duration_s * 0.82:.1f}s), peak_description.
5. ending_echo (connecting resolution back to the opening hook motif).

JSON schema:
{{
  "beats": [...],
  "loops": [...],
  "causality_map": [...],
  "peak_timestamp_s": 220.0,
  "peak_description": "...",
  "ending_echo": "..."
}}
"""
        try:
            raw = complete_json(
                prompt=prompt,
                system=SKELETON_SYSTEM,
                temperature=0.4,
                provider_override=self.provider_override,
            )
            return self._parse_skeleton(raw, target_duration_s, cids, hook, meaning_test)
        except Exception as exc:
            print(f"[StorySkeleton] LLM note: {exc}. Using deterministic causal skeleton.")
            return self._generate_fallback_skeleton(target_duration_s, cids, hook, meaning_test, topic, claim_records)

    def _parse_skeleton(
        self,
        raw: Dict[str, Any],
        target_duration_s: float,
        cids: List[str],
        hook: HookCandidate,
        meaning_test: MeaningTest,
    ) -> Tuple[List[StoryBeat], List[OpenLoop], List[CausalityTransition], float, str, str]:
        raw_beats = raw.get("beats", [])
        beats: List[StoryBeat] = []
        accum_time = 0.0

        for i, b in enumerate(raw_beats):
            dur = float(b.get("target_duration_s", target_duration_s / max(1, len(raw_beats))))
            tr_type = str(b.get("transition_type", "BUT")).upper()
            if tr_type not in ("BUT", "THEREFORE", "BECAUSE"):
                tr_type = "THEREFORE" if i % 2 == 0 else "BUT"

            truth_cat = str(b.get("truth_category", "REAL")).upper()
            if truth_cat not in [tc.value for tc in TruthCategory]:
                truth_cat = TruthCategory.ARCHIVAL.value if i % 2 == 0 else TruthCategory.DOCUMENT.value

            b_obj = StoryBeat(
                beat_id=str(b.get("beat_id", f"B{i+1:02d}")),
                purpose=str(b.get("purpose", "Narrative advance")),
                claim_ids=b.get("claim_ids", [cids[min(i, len(cids) - 1)]] if cids else []),
                narration_intent=str(b.get("narration_intent", "")),
                visual_intent=str(b.get("visual_intent", "")),
                emotional_state=str(b.get("emotional_state", "tension")),
                information_revealed=str(b.get("information_revealed", "")),
                question_created=str(b.get("question_created", "")),
                loop_ids=b.get("loop_ids", []),
                transition_type=tr_type,
                target_duration_s=dur,
                intensity=int(b.get("intensity", 7)),
                truth_category=truth_cat,
            )
            beats.append(b_obj)
            accum_time += dur

        if not beats:
            return self._generate_fallback_skeleton(target_duration_s, cids, hook, meaning_test, "Documentary")

        # Parse loops
        raw_loops = raw.get("loops", [])
        loops: List[OpenLoop] = []
        for l in raw_loops:
            loops.append(
                OpenLoop(
                    loop_id=str(l.get("loop_id", "LOOP_A")),
                    plant_beat_id=str(l.get("plant_beat_id", beats[0].beat_id)),
                    plant_timestamp_s=float(l.get("plant_timestamp_s", 0.0)),
                    payoff_beat_id=str(l.get("payoff_beat_id", beats[-2].beat_id if len(beats) > 2 else beats[-1].beat_id)),
                    payoff_timestamp_s=float(l.get("payoff_timestamp_s", target_duration_s * 0.78)),
                    description=str(l.get("description", meaning_test.question)),
                    is_resolved=True,
                )
            )

        # Parse causality map
        causality_map: List[CausalityTransition] = []
        for i in range(len(beats) - 1):
            causality_map.append(
                CausalityTransition(
                    from_beat_id=beats[i].beat_id,
                    to_beat_id=beats[i + 1].beat_id,
                    transition_type=beats[i + 1].transition_type,
                    causal_link=f"Beat {beats[i].beat_id} establishes a premise, {beats[i+1].transition_type} Beat {beats[i+1].beat_id} complicates or resolves it.",
                )
            )

        peak_time = float(raw.get("peak_timestamp_s", target_duration_s * 0.75))
        peak_desc = str(raw.get("peak_description", meaning_test.payoff))
        echo = str(raw.get("ending_echo", "Returns to the opening cold frame, revealing its complete forensic meaning."))

        return beats, loops, causality_map, peak_time, peak_desc, echo

    def _generate_fallback_skeleton(
        self,
        target_duration_s: float,
        cids: List[str],
        hook: HookCandidate,
        meaning_test: MeaningTest,
        topic: str,
        claim_records: Optional[Dict[str, ClaimRecord]] = None,
    ) -> Tuple[List[StoryBeat], List[OpenLoop], List[CausalityTransition], float, str, str]:
        """Deterministic causal structure strictly projecting from verified claim records."""
        is_short = target_duration_s <= 90.0
        num_beats = 4 if is_short else min(6, max(3, len(cids) if cids else 4))
        b_dur = target_duration_s / float(num_beats)

        beats: List[StoryBeat] = []
        for i in range(num_beats):
            cid = cids[min(i, len(cids) - 1)] if cids else f"C{i+1:03d}"
            cr = claim_records.get(cid) if claim_records else None
            claim_text = cr.claim_text if cr else (meaning_test.payoff if i > 0 else hook.first_sentence)

            if i == 0:
                purpose = "Cold Hook & Historical Premise"
                n_intent = hook.first_sentence or f"Establish the core mystery of {topic}."
                v_intent = f"Archival document macro examination and visual scene setting for {topic}."
                tr_type = TransitionType.BUT.value
                intensity = 9
                state = "shock"
                t_cat = TruthCategory.ARCHIVAL.value
            elif i == num_beats - 1:
                purpose = "Historical Consensus & Thematic Conclusion"
                n_intent = f"Present the enduring historical verdict and evidence regarding {topic}."
                v_intent = f"Cinematic historical imagery and closing evidentiary summary of {topic}."
                tr_type = TransitionType.THEREFORE.value
                intensity = 6
                state = "somber_clarity"
                t_cat = TruthCategory.DOCUMENT.value
            elif i % 2 == 1:
                purpose = "Forensic Discrepancy & Primary Evidence"
                n_intent = f"Analyze the primary archival records and documented evidence."
                v_intent = f"Contemporaneous document highlighting and evidence examination of {claim_text[:60]}."
                tr_type = TransitionType.THEREFORE.value
                intensity = 7
                state = "investigation"
                t_cat = TruthCategory.DOCUMENT.value
            else:
                purpose = "Critical Investigation & Analysis"
                n_intent = f"Detail the structural turning point supported by the evidentiary record."
                v_intent = f"Comparative visual analysis contrasting documented claims for {claim_text[:60]}."
                tr_type = TransitionType.BECAUSE.value
                intensity = 8
                state = "revelation"
                t_cat = TruthCategory.REAL.value

            beats.append(
                StoryBeat(
                    beat_id=f"B{i+1:02d}",
                    purpose=purpose,
                    claim_ids=[cid],
                    narration_intent=n_intent,
                    visual_intent=v_intent,
                    emotional_state=state,
                    information_revealed=claim_text,
                    question_created=f"What evidence supports the historical account that {claim_text[:60]}?" if i < num_beats - 1 else "",
                    loop_ids=["LOOP_A"] if i == 0 else (["LOOP_A", "LOOP_B"] if i < num_beats - 1 else []),
                    transition_type=tr_type,
                    target_duration_s=round(b_dur, 1),
                    intensity=intensity,
                    truth_category=t_cat,
                )
            )

        loops = [
            OpenLoop(
                loop_id="LOOP_A",
                plant_beat_id="B01",
                plant_timestamp_s=0.0,
                payoff_beat_id=beats[-1].beat_id,
                payoff_timestamp_s=target_duration_s * 0.75,
                description=meaning_test.question or f"What really transpired during {topic}?",
                is_resolved=True,
            ),
        ]
        if not is_short and len(beats) > 3:
            loops.append(
                OpenLoop(
                    loop_id="LOOP_B",
                    plant_beat_id="B02",
                    plant_timestamp_s=target_duration_s * 0.20,
                    payoff_beat_id=beats[-2].beat_id,
                    payoff_timestamp_s=target_duration_s * 0.77,
                    description=f"What do primary contemporaneous records reveal about {topic}?",
                    is_resolved=True,
                )
            )

        causality_map = [
            CausalityTransition(
                from_beat_id=beats[i].beat_id,
                to_beat_id=beats[i+1].beat_id,
                transition_type=beats[i+1].transition_type,
                causal_link=f"Beat {beats[i].beat_id} establishes historical premise, {beats[i+1].transition_type} Beat {beats[i+1].beat_id} complicates or resolves it.",
            )
            for i in range(len(beats) - 1)
        ]

        peak_time = target_duration_s * 0.75
        peak_desc = meaning_test.payoff
        echo = f"The closing sequence circles back to the primary record of {topic}, resolving the central inquiry with verified evidence."

        return beats, loops, causality_map, peak_time, peak_desc, echo
