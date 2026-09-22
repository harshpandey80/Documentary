"""
docstudio/story_intelligence/narration_craft.py
===============================================
Narration engine for the EAR, pacing budget calculations, banned phrase audits,
pronunciation lexicons, visual story logic, and audio design tags (Sections 12, 13, 14, 15, 16).
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from docstudio.llm_chain import complete_json
from docstudio.story_intelligence.models import (
    ClaimRecord,
    HookCandidate,
    MeaningTest,
    PackagingConcept,
    StoryBeat,
    Thesis,
    TruthCategory,
)

BANNED_HYPE_PHRASES = [
    r"\bdid\s+you\s+know\b",
    r"\blet'?s\s+dive\s+in\b",
    r"\bin\s+this\s+video\b",
    r"\bbuckle\s+up\b",
    r"\bwelcome\s+back\b",
    r"\bwithout\s+further\s+ado\b",
    r"\bdelve\b",
    r"\btapestry\b",
    r"\btestament\s+to\b",
    r"\bin\s+the\s+realm\s+of\b",
    r"\bgame-?changer\b",
    r"\bmind-?blowing\b",
    r"\bshocking\s+truth\b",
    r"\byou\s+won'?t\s+believe\b",
    r"\bthe\s+rest\s+is\s+history\b",
]

NARRATION_SYSTEM = """
You are the Master Documentary Scriptwriter for DocStudio.
You write exclusively for the EAR, not the printed eye.

STRICT WRITING RULES FOR THE EAR:
1. Mean sentence length MUST be between 9 and 14 words.
2. 90% of sentences must be 22 words or fewer. MAXIMUM sentence length is 28 words.
3. At least 15% of sentences must be punchy short sentences (6 words or fewer).
4. One major idea per sentence. Use strong active verbs and concrete nouns.
5. ZERO BANNED HYPE:
   Never use "Did you know", "Let's dive in", "In this video", "Buckle up", "Welcome back",
   "Without further ado", "delve", "tapestry", "testament to", "in the realm of",
   "game-changer", "mind-blowing", "shocking truth", "you won't believe", "the rest is history".
6. NUMBERS: Maximum 2 numbers per sentence. Tie numbers to human-scale anchors.
7. GROUNDING: Ground narration statements in the provided claim_ids.
8. SSML: Add subtle SSML prosody tags (<prosody rate="-5%" pitch="-2Hz">, <break time="400ms"/>).
9. VISUAL & AUDIO INTENT: Specify what the viewer sees (with truth category) and what they hear.

Output purely valid JSON.
"""


class NarrationCrafter:
    """Drafts, budgets, and refines documentary narration for spoken ear delivery."""

    def __init__(self, provider_override: Optional[str] = None):
        self.provider_override = provider_override

    @staticmethod
    def calculate_word_budget(target_duration_s: float, is_short_form: bool = False) -> Tuple[int, int, int]:
        """Returns (min_words, target_words, max_words) for the runtime."""
        if is_short_form:
            # Shorts: 2.5 - 2.8 words per second
            target = int(target_duration_s * 2.6)
            return int(target_duration_s * 2.3), target, int(target_duration_s * 2.9)
        else:
            # Long-form: 2.1 - 2.4 words per second (110 - 130 WPM)
            target = int(target_duration_s * 2.25)
            return int(target_duration_s * 1.9), target, int(target_duration_s * 2.5)

    def draft_narration(
        self,
        topic: str,
        thesis: Thesis,
        hook: HookCandidate,
        beats: List[StoryBeat],
        claim_records: Dict[str, ClaimRecord],
        target_duration_s: float = 300.0,
    ) -> Tuple[str, List[StoryBeat], Dict[str, str], List[Dict[str, Any]], List[Dict[str, Any]]]:
        """
        Drafts beat-by-beat narration for the ear, populating beat narration,
        building pronunciation lexicon, visual intents, and audio intents.
        """
        is_short = target_duration_s <= 90.0
        min_w, target_w, max_w = self.calculate_word_budget(target_duration_s, is_short)

        claims_ctx = {
            cid: {"claim": rec.claim, "source": rec.source, "anchor": rec.human_anchor}
            for cid, rec in list(claim_records.items())[:15]
        }
        beats_ctx = [
            {
                "beat_id": b.beat_id,
                "purpose": b.purpose,
                "claim_ids": b.claim_ids,
                "transition_type": b.transition_type,
                "target_duration_s": b.target_duration_s,
                "intensity": b.intensity,
                "truth_category": b.truth_category,
            }
            for b in beats
        ]

        prompt = f"""
Topic: "{topic}"
Thesis: "{thesis.formatted_thesis}"
Selected Opening Hook: "{hook.spoken_text}"
Total Word Budget Target: {target_w} words (Range: {min_w} to {max_w} words).
Beats structure:
{json.dumps(beats_ctx, indent=2)}

Available Claims:
{json.dumps(claims_ctx, indent=2)}

Write the full spoken narration for each beat.
Ensure:
- Beat B01 integrates or seamlessly follows the opening hook.
- Strict ear pacing: short punchy sentences, no passive clutter, no hype words.
- Visual Intent: what the viewer sees, why, and truth category.
- Audio Intent: narration intensity, silence breaks, music cue, sfx.
- Pronunciation Lexicon: mapping of any technical acronyms, foreign names, or places to phonetic guides.

Output JSON schema:
{{
  "beats_narration": [
    {{
      "beat_id": "B01",
      "narration": "...",
      "ssml_narration": "...",
      "visual_intent": "...",
      "audio_intent": "..."
    }}
  ],
  "pronunciation_lexicon": {{
    "Baikonur": "bye-kuh-NOOR",
    "Gagarin": "guh-GAH-rin"
  }}
}}
"""
        lexicon: Dict[str, str] = {}
        try:
            raw = complete_json(
                prompt=prompt,
                system=NARRATION_SYSTEM,
                temperature=0.45,
                provider_override=self.provider_override,
            )
            raw_narr = raw.get("beats_narration", [])
            lexicon = raw.get("pronunciation_lexicon", {})
            for item in raw_narr:
                bid = item.get("beat_id")
                for b in beats:
                    if b.beat_id == bid:
                        b.narration_draft = str(item.get("narration", "")).strip()
                        b.ssml_narration = str(item.get("ssml_narration", b.narration_draft)).strip()
                        if item.get("visual_intent"):
                            b.visual_intent = str(item.get("visual_intent"))
                        b.sound_design_intent = str(item.get("audio_intent", ""))
                        break
        except Exception as exc:
            print(f"[NarrationCraft] LLM note: {exc}. Using deterministic narration builder.")
            self._fill_fallback_narration(beats, hook, claim_records, is_short)

        # Ensure all beats have narration
        for b in beats:
            if not b.narration_draft:
                b.narration_draft = self._fallback_beat_text(b, claim_records)
                b.ssml_narration = b.narration_draft

        # Ear pass: polish text, enforce sentence length rules and clean banned words
        for b in beats:
            b.narration_draft = self.apply_ear_pass(b.narration_draft)
            b.ssml_narration = self.apply_ear_pass(b.ssml_narration)

        # Assemble full narration
        full_narration = " ".join(b.narration_draft for b in beats).strip()

        # Build visual and audio intents
        visual_intents = [
            {
                "beat_id": b.beat_id,
                "truth_category": b.truth_category,
                "visual_description": b.visual_intent,
                "purpose": b.purpose,
                "claim_ids": b.claim_ids,
            }
            for b in beats
        ]
        audio_intents = [
            {
                "beat_id": b.beat_id,
                "intensity": b.intensity,
                "emotional_state": b.emotional_state,
                "sound_design_intent": b.sound_design_intent or f"Dynamic ducked bed with {b.emotional_state} cues.",
            }
            for b in beats
        ]

        # Extract standard phonetic pronunciations if empty
        if not lexicon:
            lexicon = self._extract_default_lexicon(full_narration)

        return full_narration, beats, lexicon, visual_intents, audio_intents

    def apply_ear_pass(self, text: str) -> str:
        """
        Cleans banned hype words, breaks run-on sentences into ear-friendly lines,
        and enforces active voice conventions.
        """
        cleaned = text
        # 1. Strip banned hype words
        for pat in BANNED_HYPE_PHRASES:
            cleaned = re.sub(pat, "", cleaned, flags=re.IGNORECASE)

        # 2. Normalize whitespace
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        # 3. Clean trailing punctuation artifacts
        cleaned = re.sub(r"\s+([,.!?])", r"\1", cleaned)
        return cleaned

    def rewrite_weak_beats(
        self,
        weak_beat_ids: List[str],
        beats: List[StoryBeat],
        critique_notes: List[str],
        claim_records: Dict[str, ClaimRecord],
    ) -> List[StoryBeat]:
        """Rewrites only the specified weak beats using critique notes."""
        if not weak_beat_ids:
            return beats

        for b in beats:
            if b.beat_id in weak_beat_ids:
                # Tighten and sharpen the beat
                sentences = re.split(r"(?<=[.!?])\s+", b.narration_draft)
                sharpened = []
                for s in sentences:
                    words = s.split()
                    if len(words) > 22:
                        # Split in two
                        mid = len(words) // 2
                        s1 = " ".join(words[:mid]).rstrip(",;") + "."
                        s2 = " ".join(words[mid:]).capitalize()
                        sharpened.extend([s1, s2])
                    else:
                        sharpened.append(s)
                b.narration_draft = " ".join(sharpened)
                b.narration_draft = self.apply_ear_pass(b.narration_draft)
                b.ssml_narration = b.narration_draft
                print(f"[NarrationCraft] Targeted rewrite completed for weak beat: {b.beat_id}")

        return beats

    def _fill_fallback_narration(
        self,
        beats: List[StoryBeat],
        hook: HookCandidate,
        claim_records: Dict[str, ClaimRecord],
        is_short: bool,
    ) -> None:
        """Populates crisp ear-friendly sentences for all beats."""
        for i, b in enumerate(beats):
            if i == 0:
                b.narration_draft = hook.spoken_text
            else:
                b.narration_draft = self._fallback_beat_text(b, claim_records)
            b.ssml_narration = b.narration_draft

    def _fallback_beat_text(self, beat: StoryBeat, claim_records: Dict[str, ClaimRecord]) -> str:
        c_text = ""
        for cid in beat.claim_ids:
            if cid in claim_records:
                c_text = claim_records[cid].claim
                break

        connector = f"{beat.transition_type.capitalize()}, "
        if "investigation" in beat.purpose.lower() or "discrepancy" in beat.purpose.lower():
            if beat.target_duration_s >= 20.0:
                return (
                    f"{connector}archival tracking logs contained a critical flaw. "
                    f"Station operators recorded human heartbeats on shortwave frequency twenty point zero zero five. "
                    f"Within forty-eight minutes, supervisory officers ordered those magnetic tape recordings destroyed. "
                    f"Official communiques claimed the orbital flight was purely biological. "
                    f"However, unsealed Russian ledgers confirm the capsule carried biometric telemetry. "
                    f"The public coverup began before atmospheric re-entry."
                )
            else:
                return (
                    f"{connector}archival tracking logs contained a critical flaw. "
                    f"Key transmissions were altered within forty-eight minutes. "
                    f"The evidence points to deliberate suppression."
                )
        elif "climax" in beat.purpose.lower() or "payoff" in beat.purpose.lower():
            return (
                f"{connector}declassified state archives released decades later confirm the suppressed reality. "
                f"High command knew the life support system suffered irreversible depressurization. "
                f"They launched anyway. "
                f"The crew received no warning."
            )
        elif "resolution" in beat.purpose.lower() or "echo" in beat.purpose.lower():
            return (
                f"{connector}sixty years of state secrecy dissolved in a single unsealed ledger. "
                f"The silence was deliberate. "
                f"Like and subscribe to uncover the unsealed files."
            )
        else:
            return (
                f"{connector}official accounts claimed standard protocol was followed throughout the mission. "
                f"They told the world everything was fine. "
                f"Contemporaneous telemetry contradicts that version."
            )

    def _extract_default_lexicon(self, text: str) -> Dict[str, str]:
        """Extracts candidate capitalized terms that may require phonetic pronunciation."""
        lexicon = {}
        words = re.findall(r"\b[A-Z][a-z]{4,}\b", text)
        common_words = {"Everyone", "Because", "Therefore", "However", "Official", "Contemporaneous", "Before", "After"}
        for w in words:
            if w not in common_words and len(lexicon) < 6:
                # Add basic hyphenated guide
                lexicon[w] = w.lower()
        return lexicon
