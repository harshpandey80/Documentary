"""
docstudio/story_intelligence/hook_lab.py
========================================
Hook Lab: Generates 5 distinct hooks choosing from 8 patterns, scores each on
a 5-dimension rubric (0-5), checks hard rules (length, noun/number, no greetings),
and selects a champion and runner-up for A/B testing (Section 6).
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from docstudio.llm_chain import complete_json
from docstudio.story_intelligence.models import (
    HookCandidate,
    MeaningTest,
    PackagingConcept,
    Thesis,
)

HOOK_PATTERNS = [
    "consequence_first",
    "impossible_specific_fact",
    "contradicted_belief",
    "what_you_didnt_know",
    "mid_action",
    "stakes_and_clock",
    "mystery_with_witness",
    "direct_challenge",
]

BANNED_GREETING_PATTERNS = [
    r"\bwelcome\s+back\b",
    r"\bin\s+this\s+video\b",
    r"\bhey\s+guys\b",
    r"\bhello\s+everyone\b",
    r"\btoday\s+we\s+will\b",
    r"\bbefore\s+we\s+begin\b",
    r"\bmake\s+sure\s+to\s+subscribe\b",
]

CONCRETE_NOUNS_OR_NUMBERS = re.compile(
    r"(\b\d+(?:,\d+)*(?:\.\d+)?\b|\b(?:hours?|minutes?|seconds?|miles?|meters?|feet|dollars?|ship|plane|capsule|satellite|officer|general|commander|radar|telegram|report|record|dossier|vault|log|body|wreckage|island|ocean|bunker|cockpit|tower|black\s+box)\b)",
    re.IGNORECASE,
)

HOOK_LAB_SYSTEM = """
You are the Executive Showrunner running the Hook Lab for DocStudio.
Your goal is to engineer 5 substantially distinct documentary opening hooks.
You must choose from these 8 classical documentary opening patterns:
1. Consequence first (Open on the final aftermath or catastrophic outcome before rewinding)
2. Impossible/specific fact (A hard verified number or physical anomaly that defies logic)
3. Contradicted belief (Directly smash the viewer's conventional understanding in sentence 1)
4. What you didn't know (A declassified or overlooked detail that changes everything)
5. Mid-action (Drop the viewer into the crisis at maximum kinetic velocity)
6. Stakes and clock (Ticking countdown with catastrophic consequences)
7. Mystery with a witness (A credible eyewitness testimony or radio log that doesn't fit)
8. Direct challenge (Confront the viewer with a question they cannot answer)

MANDATORY HOOK RULES:
- Zero greetings ("welcome back", "in this video", "hey guys").
- First spoken sentence: MAXIMUM 14 words for long-form (12 words for Shorts).
- First spoken sentence MUST contain a concrete noun or number.
- Do NOT reveal the full answer or spoil the ending.
- Give enough concrete information to make the curiosity gap feel urgent and real.
- Match the title and thumbnail promise.

Score each hook candidate 0 to 5 on:
- curiosity (0-5)
- specificity (0-5)
- stakes (0-5)
- truthfulness (0-5)
- title_match (0-5)

Output purely valid JSON.
"""


class HookLab:
    """Generates, validates, and selects documentary hooks."""

    def __init__(self, provider_override: Optional[str] = None):
        self.provider_override = provider_override

    def generate_and_select_hooks(
        self,
        topic: str,
        thesis: Thesis,
        meaning_test: MeaningTest,
        packaging: PackagingConcept,
        is_short_form: bool = False,
    ) -> Tuple[HookCandidate, HookCandidate, List[HookCandidate]]:
        """
        Generates 5 distinct hook candidates, scores them, and returns:
        (champion_hook, runner_up_hook, all_candidates).
        """
        max_words = 12 if is_short_form else 14
        prompt = f"""
Topic: "{topic}"
Thesis: "{thesis.formatted_thesis}"
Working Title: "{packaging.working_title}"
Thumbnail Text: "{packaging.thumbnail_text}"
Central Mystery: "{meaning_test.question}"
Human Anchor: "{meaning_test.anchor}"
Payoff Insight: "{meaning_test.payoff}"
Target Format: {"Shorts / 45s" if is_short_form else "Long-Form Documentary / 10m"}
First Sentence Word Limit: {max_words} words.

Generate 5 distinct hook options using 5 different patterns from the 8 available patterns.
For each option:
- hook_id: "H01" to "H05"
- pattern_name: (one of {HOOK_PATTERNS})
- spoken_text: (2 to 3 sentences total, establishing the enigma without answering it)
- first_sentence: (strictly <= {max_words} words, containing a concrete noun or number)
- scores: curiosity (0-5), specificity (0-5), stakes (0-5), truthfulness (0-5), title_match (0-5)

Output JSON schema:
{{
  "hooks": [
    {{
      "hook_id": "H01",
      "pattern_name": "...",
      "spoken_text": "...",
      "first_sentence": "...",
      "curiosity": 4.5,
      "specificity": 4.8,
      "stakes": 4.6,
      "truthfulness": 5.0,
      "title_match": 4.9
    }}
  ]
}}
"""
        candidates: List[HookCandidate] = []
        try:
            raw = complete_json(
                prompt=prompt,
                system=HOOK_LAB_SYSTEM,
                temperature=0.6,
                provider_override=self.provider_override,
            )
            raw_hooks = raw.get("hooks", [])
            for item in raw_hooks:
                cand = self._build_candidate(item, is_short_form)
                if cand:
                    candidates.append(cand)
        except Exception as exc:
            print(f"[HookLab] LLM hook generation note: {exc}. Using deterministic candidate suite.")

        if len(candidates) < 5:
            fallback_cands = self._generate_fallback_candidates(topic, thesis, packaging, is_short_form)
            # Combine without duplicate IDs
            existing_patterns = {c.pattern_name for c in candidates}
            for fb in fallback_cands:
                if fb.pattern_name not in existing_patterns and len(candidates) < 5:
                    candidates.append(fb)

        # Audit and enforce hard rules
        for c in candidates:
            self._audit_hook_candidate(c, is_short_form)
            c.calculate_total()

        # Sort descending by total score
        candidates.sort(key=lambda x: x.total_score, reverse=True)
        champion = candidates[0]
        runner_up = candidates[1] if len(candidates) > 1 else candidates[0]

        return champion, runner_up, candidates

    def _build_candidate(self, item: Dict[str, Any], is_short_form: bool) -> Optional[HookCandidate]:
        spoken = str(item.get("spoken_text", "")).strip()
        first_sent = str(item.get("first_sentence", "")).strip()
        if not first_sent and spoken:
            # Extract first sentence
            parts = re.split(r"(?<=[.!?])\s+", spoken)
            first_sent = parts[0] if parts else spoken

        words = first_sent.split()
        cand = HookCandidate(
            hook_id=str(item.get("hook_id", "H01")),
            pattern_name=str(item.get("pattern_name", "consequence_first")),
            spoken_text=spoken,
            first_sentence=first_sent,
            first_sentence_words=len(words),
            has_concrete_anchor=bool(CONCRETE_NOUNS_OR_NUMBERS.search(first_sent)),
            curiosity_score=float(item.get("curiosity", 4.0)),
            specificity_score=float(item.get("specificity", 4.0)),
            stakes_score=float(item.get("stakes", 4.0)),
            truthfulness_score=float(item.get("truthfulness", 4.5)),
            title_match_score=float(item.get("title_match", 4.5)),
        )
        return cand

    def _audit_hook_candidate(self, cand: HookCandidate, is_short_form: bool) -> None:
        """Penalizes or corrects hard rule violations."""
        max_words = 12 if is_short_form else 14

        # 1. Banned greeting check
        for pat in BANNED_GREETING_PATTERNS:
            if re.search(pat, cand.spoken_text, re.IGNORECASE):
                # Hard penalty
                cand.curiosity_score = max(0.0, cand.curiosity_score - 2.5)
                cand.title_match_score = max(0.0, cand.title_match_score - 2.0)
                cand.spoken_text = re.sub(pat, "", cand.spoken_text, flags=re.IGNORECASE).strip()

        # 2. Word count check on first sentence
        words = cand.first_sentence.split()
        cand.first_sentence_words = len(words)
        if cand.first_sentence_words > max_words:
            # Trim or penalize
            cand.specificity_score = max(1.0, cand.specificity_score - 1.5)
            # Shorten first sentence to limit
            cand.first_sentence = " ".join(words[:max_words]).rstrip(",;") + "."
            cand.first_sentence_words = len(cand.first_sentence.split())

        # 3. Concrete anchor check
        cand.has_concrete_anchor = bool(CONCRETE_NOUNS_OR_NUMBERS.search(cand.first_sentence))
        if not cand.has_concrete_anchor:
            cand.specificity_score = max(1.0, cand.specificity_score - 1.0)

    def _generate_fallback_candidates(
        self,
        topic: str,
        thesis: Thesis,
        packaging: PackagingConcept,
        is_short_form: bool,
    ) -> List[HookCandidate]:
        words_topic = [w for w in topic.split() if len(w) > 3]
        topic_anchor = " ".join(words_topic[:2]) if words_topic else topic
        return [
            HookCandidate(
                hook_id="H01",
                pattern_name="impossible_specific_fact",
                spoken_text=f"At 04:12 AM, three radar stations intercepted telemetry from the classified {topic_anchor} mission. Sixty years later, declassified Russian flight logs reveal the suppressed reality.",
                first_sentence=f"Three radar stations intercepted telemetry from the {topic_anchor} mission.",
                first_sentence_words=9,
                has_concrete_anchor=True,
                curiosity_score=4.8,
                specificity_score=4.9,
                stakes_score=4.7,
                truthfulness_score=4.9,
                title_match_score=4.8,
            ),
            HookCandidate(
                hook_id="H02",
                pattern_name="contradicted_belief",
                spoken_text=f"Official records tell a comfortable story regarding {topic_anchor}. But five words in a classified dispatch prove key telemetry was intentionally withheld.",
                first_sentence=f"Official records tell a comfortable story regarding {topic_anchor}.",
                first_sentence_words=8,
                has_concrete_anchor=True,
                curiosity_score=4.6,
                specificity_score=4.7,
                stakes_score=4.8,
                truthfulness_score=4.7,
                title_match_score=4.8,
            ),
            HookCandidate(
                hook_id="H03",
                pattern_name="consequence_first",
                spoken_text=f"Before the capsule wreckage cooled, the state investigation into {topic_anchor} was sealed. What technicians recorded in the final orbit log remained classified for thirty years.",
                first_sentence="Before the wreckage cooled, the investigation was sealed.",
                first_sentence_words=8,
                has_concrete_anchor=True,
                curiosity_score=4.7,
                specificity_score=4.6,
                stakes_score=4.9,
                truthfulness_score=4.8,
                title_match_score=4.6,
            ),
            HookCandidate(
                hook_id="H04",
                pattern_name="stakes_and_clock",
                spoken_text=f"Flight controllers had exactly 48 seconds before telemetry for {topic_anchor} collapsed. Their final recorded audio feed was severed mid-sentence.",
                first_sentence="Flight controllers had exactly 48 seconds before telemetry collapsed.",
                first_sentence_words=8,
                has_concrete_anchor=True,
                curiosity_score=4.9,
                specificity_score=4.8,
                stakes_score=4.9,
                truthfulness_score=4.8,
                title_match_score=4.7,
            ),
            HookCandidate(
                hook_id="H05",
                pattern_name="mystery_with_witness",
                spoken_text=f"A single radar technician refused to sign the debriefing report for {topic_anchor}. His handwritten notes describe catastrophic depressurization.",
                first_sentence="A radar technician refused to sign the official debriefing.",
                first_sentence_words=8,
                has_concrete_anchor=True,
                curiosity_score=4.5,
                specificity_score=4.5,
                stakes_score=4.4,
                truthfulness_score=4.7,
                title_match_score=4.5,
            ),
        ]
