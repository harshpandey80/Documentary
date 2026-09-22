"""
docstudio/story_intelligence/packaging.py
=========================================
Formulates documentary packaging concept before writing the script (Section 5).
Ensures working title, thumbnail concept, 3-6 word thumbnail text, and central promise
are tightly aligned with the thesis and story truth (no bait-and-switch).
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from docstudio.llm_chain import complete_json
from docstudio.story_intelligence.models import (
    MeaningTest,
    PackagingConcept,
    Thesis,
)

PACKAGING_SYSTEM = """
You are an executive documentary packaging strategist (expert in YouTube CTR and honest retention packaging).
Before the script is written, you must establish the documentary's packaging promise.
Rules:
1. Working Title: Punchy, intriguing, honest, maximum 65 characters.
2. Thumbnail Concept: A striking, visual human/evidence moment with strong contrast and narrative tension.
3. Thumbnail Text: Maximum 3 to 6 words. Bold, high-curiosity, readable on mobile screens.
4. Central Promise: What core revelation or understanding the film guarantees to deliver to the viewer.
5. Hook Promise: The specific question planted in the first 10 seconds that fulfills the packaging.
6. NO CLICKBAIT MISMATCH: The packaging must promise ONLY what the thesis and evidence actually substantiate.

Output valid JSON matching the schema.
"""


class PackagingStrategist:
    """Develops pre-script packaging concepts and promises."""

    def __init__(self, provider_override: Optional[str] = None):
        self.provider_override = provider_override

    def create_packaging(
        self,
        topic: str,
        thesis: Thesis,
        meaning_test: MeaningTest,
    ) -> PackagingConcept:
        """Generates title, thumbnail concept, thumbnail text, and promise."""
        prompt = f"""
Topic: "{topic}"
Thesis: "{thesis.formatted_thesis}"
Core Mystery/Question: "{meaning_test.question}"
Human Anchor: "{meaning_test.anchor}"
Payoff/Twist: "{meaning_test.payoff}"

Generate the Packaging Concept:
- working_title: (max 65 chars, compelling, honest)
- thumbnail_concept: (cinematic visual description, dramatic contrast, central subject)
- thumbnail_text: (STRICTLY 3 to 6 words only)
- central_promise: (clear statement of what viewer will understand)
- hook_promise: (opening enigma that hooks into this packaging)

JSON schema:
{{
  "working_title": "...",
  "thumbnail_concept": "...",
  "thumbnail_text": "...",
  "central_promise": "...",
  "hook_promise": "..."
}}
"""
        try:
            raw = complete_json(
                prompt=prompt,
                system=PACKAGING_SYSTEM,
                temperature=0.5,
                provider_override=self.provider_override,
            )
            return self._parse(raw, topic, thesis)
        except Exception as exc:
            print(f"[Packaging] LLM note: {exc}. Using deterministic packaging generator.")
            return self._generate_fallback(topic, thesis)

    def _parse(self, raw: Dict[str, Any], topic: str, thesis: Thesis) -> PackagingConcept:
        thumb_text = str(raw.get("thumbnail_text", "")).strip()
        words = thumb_text.split()
        if len(words) < 2 or len(words) > 6:
            # Enforce 3-6 words
            thumb_text = " ".join(words[:5]) if len(words) > 6 else f"The Truth of {topic}"[:25]
            words = thumb_text.split()
            if len(words) < 3:
                thumb_text = "The Unsealed Files"

        return PackagingConcept(
            working_title=str(raw.get("working_title", f"The Secret Investigation into {topic}")),
            thumbnail_concept=str(raw.get("thumbnail_concept", "Extreme close-up on declassified files with stark forensic lighting")),
            thumbnail_text=thumb_text,
            central_promise=str(raw.get("central_promise", thesis.formatted_thesis)),
            hook_promise=str(raw.get("hook_promise", f"The unsealed records reveal what actually happened to {topic}.")),
        )

    def _generate_fallback(self, topic: str, thesis: Thesis) -> PackagingConcept:
        clean_topic = topic.strip().title()
        return PackagingConcept(
            working_title=f"{clean_topic}: The Unsealed Records",
            thumbnail_concept=f"Dramatic low-angle shot of historical documents with stamped REDACTED warnings and high-contrast spotlight.",
            thumbnail_text="What They Erased",
            central_promise=thesis.formatted_thesis,
            hook_promise=f"Official records told one story about {clean_topic}. Contemporaneous logs told another.",
        )
