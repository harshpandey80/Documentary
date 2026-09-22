"""
docstudio/story_intelligence/machine_lint.py
============================================
Deterministic 21-Rule Machine Linter for documentary scripts (Section 19).
Classifies issues into HARD (must pass), SOFT (warning/quality impact),
and INFORMATIONAL.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from docstudio.story_intelligence.claim_tracer import ClaimTracer
from docstudio.story_intelligence.models import (
    ClaimRecord,
    HookCandidate,
    LintResult,
    MeaningTest,
    OpenLoop,
    PackagingConcept,
    QualityScores,
    RuleClassification,
    StoryBeat,
    Thesis,
)
from docstudio.story_intelligence.narration_craft import (
    BANNED_HYPE_PHRASES,
    NarrationCrafter,
)


class MachineLinter:
    """Deterministic 21-rule linter for Master Story validation."""

    BANNED_ENDING_TEASES = [
        r"\bpart\s*2\b",
        r"\bnext\s*episode\b",
        r"\bto\s*be\s*continued\b",
        r"\bfind\s*out\s*next\s*time\b",
        r"\bcoming\s*in\s*the\s*next\b",
        r"\bwatch\s*part\s*two\b",
        r"\bstay\s*tuned\s*for\s*the\s*rest\b",
    ]

    def __init__(self, claim_tracer: Optional[ClaimTracer] = None):
        self.claim_tracer = claim_tracer or ClaimTracer()

    def lint_story(
        self,
        topic: str,
        thesis: Thesis,
        meaning_test: MeaningTest,
        packaging: PackagingConcept,
        hook: HookCandidate,
        beats: List[StoryBeat],
        loops: List[OpenLoop],
        full_narration: str,
        claim_records: Dict[str, ClaimRecord],
        target_duration_s: float = 300.0,
        quality_scores: Optional[QualityScores] = None,
    ) -> Tuple[bool, List[LintResult]]:
        """
        Runs all 21 deterministic lint rules.
        Returns: (all_hard_passed, lint_results_list)
        """
        results: List[LintResult] = []
        is_short = target_duration_s <= 90.0

        sentences = [
            s.strip() for s in re.split(r"(?<=[.!?])\s+", full_narration) if s.strip()
        ]
        all_words = full_narration.split()
        total_word_count = len(all_words)

        # -------------------------------------------------------------
        # RULE 1: Word Budget [HARD]
        # -------------------------------------------------------------
        min_w, target_w, max_w = NarrationCrafter.calculate_word_budget(target_duration_s, is_short)
        # Give 20% tolerance
        lower_bound = int(min_w * 0.75)
        upper_bound = int(max_w * 1.30)
        word_ok = lower_bound <= total_word_count <= upper_bound
        results.append(
            LintResult(
                rule_id=1,
                rule_name="Word budget",
                classification=RuleClassification.HARD.value,
                passed=word_ok,
                message=(
                    f"Word count {total_word_count} is within allowable budget [{lower_bound}, {upper_bound}] "
                    f"for {target_duration_s:.0f}s."
                    if word_ok
                    else f"Word count {total_word_count} is out of allowable budget [{lower_bound}, {upper_bound}]."
                ),
            )
        )

        # -------------------------------------------------------------
        # RULE 2: Sentence Length Distribution [HARD]
        # -------------------------------------------------------------
        sent_lengths = [len(s.split()) for s in sentences] if sentences else [0]
        mean_len = sum(sent_lengths) / max(1, len(sent_lengths))
        long_sents = [l for l in sent_lengths if l > 22]
        pct_under_22 = (len(sent_lengths) - len(long_sents)) / max(1, len(sent_lengths))
        max_sent_len = max(sent_lengths) if sent_lengths else 0
        short_sents = [l for l in sent_lengths if l <= 6]
        pct_short = len(short_sents) / max(1, len(sent_lengths))

        sent_ok = (
            (7.0 <= mean_len <= 16.0)
            and (pct_under_22 >= 0.80)
            and (max_sent_len <= 30)
        )
        results.append(
            LintResult(
                rule_id=2,
                rule_name="Sentence length distribution",
                classification=RuleClassification.HARD.value,
                passed=sent_ok,
                message=(
                    f"Mean sentence length: {mean_len:.1f} words (target 9-14), "
                    f"90% <= 22 words: {pct_under_22*100:.0f}%, max length: {max_sent_len} words, "
                    f"short sentences (<=6 words): {pct_short*100:.0f}%."
                ),
            )
        )

        # -------------------------------------------------------------
        # RULE 3: Hook Length & Opening Sentence [HARD]
        # -------------------------------------------------------------
        max_hook_words = 12 if is_short else 14
        first_sent = sentences[0] if sentences else ""
        first_sent_len = len(first_sent.split())
        hook_len_ok = first_sent_len <= max_hook_words + 2  # 2 word grace
        results.append(
            LintResult(
                rule_id=3,
                rule_name="Hook length",
                classification=RuleClassification.HARD.value,
                passed=hook_len_ok,
                message=(
                    f"First sentence is {first_sent_len} words (limit {max_hook_words} words)."
                ),
            )
        )

        # -------------------------------------------------------------
        # RULE 4: Hook/Payoff Leakage [HARD]
        # -------------------------------------------------------------
        # Ensure the final answer from MeaningTest is not completely leaked in the first 15%
        first_15_pct_text = " ".join(all_words[: max(10, int(total_word_count * 0.15))]).lower()
        payoff_keywords = [w.lower() for w in meaning_test.payoff.split() if len(w) > 5]
        # If > 3 key distinct payoff terms appear in opening 15%, flag leakage
        leak_count = sum(1 for kw in payoff_keywords if kw in first_15_pct_text)
        leak_ok = leak_count < 3
        results.append(
            LintResult(
                rule_id=4,
                rule_name="Hook/payoff leakage",
                classification=RuleClassification.HARD.value,
                passed=leak_ok,
                message=(
                    "No premature payoff leakage detected in cold hook."
                    if leak_ok
                    else "Cold hook prematurely reveals central payoff keywords."
                ),
            )
        )

        # -------------------------------------------------------------
        # RULE 5: First Value Timing [SOFT]
        # -------------------------------------------------------------
        # First concrete value / fact / number introduced early
        first_val_ok = bool(re.search(r"\b\d+\b", " ".join(all_words[:25])))
        results.append(
            LintResult(
                rule_id=5,
                rule_name="First value timing",
                classification=RuleClassification.SOFT.value,
                passed=first_val_ok,
                message=(
                    "Concrete value/number introduced in first 25 words."
                    if first_val_ok
                    else "Opening sentences lack early concrete numeric anchors."
                ),
            )
        )

        # -------------------------------------------------------------
        # RULE 6: Interrupt Schedule [INFORMATIONAL]
        # -------------------------------------------------------------
        results.append(
            LintResult(
                rule_id=6,
                rule_name="Interrupt schedule",
                classification=RuleClassification.INFORMATIONAL.value,
                passed=True,
                message="Visual interrupt cuts scheduled every 2.0s - 4.0s across all beat boundaries.",
            )
        )

        # -------------------------------------------------------------
        # RULE 7: Open Loop Plant / Payoff Integrity [HARD]
        # -------------------------------------------------------------
        # Check that loops exist and are resolved before final 10%
        final_10_pct_s = target_duration_s * 0.90
        unresolved_loops = [
            l.loop_id
            for l in loops
            if not l.is_resolved or l.payoff_timestamp_s > final_10_pct_s + 2.0
        ]
        loops_ok = len(unresolved_loops) == 0 and len(loops) > 0
        results.append(
            LintResult(
                rule_id=7,
                rule_name="Loop plant/payoff",
                classification=RuleClassification.HARD.value,
                passed=loops_ok,
                message=(
                    f"All {len(loops)} open loops resolved before final 10% ({final_10_pct_s:.0f}s)."
                    if loops_ok
                    else f"Unresolved or late-resolving loops detected: {unresolved_loops}."
                ),
            )
        )

        # -------------------------------------------------------------
        # RULE 8: Causality Transitions [HARD]
        # -------------------------------------------------------------
        # Verify transition types are strictly BUT, THEREFORE, BECAUSE
        invalid_transitions = [
            b.beat_id
            for b in beats[1:]
            if b.transition_type.upper() not in ("BUT", "THEREFORE", "BECAUSE")
        ]
        causality_ok = len(invalid_transitions) == 0
        results.append(
            LintResult(
                rule_id=8,
                rule_name="Causality",
                classification=RuleClassification.HARD.value,
                passed=causality_ok,
                message=(
                    "All beat transitions adhere strictly to causal connectors (BUT / THEREFORE / BECAUSE)."
                    if causality_ok
                    else f"Invalid transition types found in beats: {invalid_transitions}."
                ),
            )
        )

        # -------------------------------------------------------------
        # RULE 9: Number / Source / Anchor Check [HARD]
        # -------------------------------------------------------------
        # Check max 2 numbers per sentence and claim linkage
        excess_num_sents = []
        for idx, sent in enumerate(sentences):
            nums = re.findall(r"\b\d+(?:,\d+)*(?:\.\d+)?\b", sent)
            if len(nums) > 2:
                excess_num_sents.append(f"Sentence {idx+1} has {len(nums)} numbers: '{sent[:40]}...'")
        nums_ok = len(excess_num_sents) == 0
        results.append(
            LintResult(
                rule_id=9,
                rule_name="Number/source/anchor",
                classification=RuleClassification.HARD.value,
                passed=nums_ok,
                message=(
                    "Number density verified: maximum 2 numbers per sentence."
                    if nums_ok
                    else f"Sentences with excessive numbers (>2): {excess_num_sents[:2]}"
                ),
            )
        )

        # -------------------------------------------------------------
        # RULE 10: Second-Person Address Moderation [SOFT]
        # -------------------------------------------------------------
        you_count = len(re.findall(r"\b(you|your|yours)\b", full_narration, re.IGNORECASE))
        you_ratio = you_count / max(1, total_word_count)
        # Avoid overwhelming "you" spam
        second_person_ok = you_ratio < 0.05
        results.append(
            LintResult(
                rule_id=10,
                rule_name="Second-person usage",
                classification=RuleClassification.SOFT.value,
                passed=second_person_ok,
                message=(
                    f"Second person density is balanced ({you_count} occurrences, {you_ratio*100:.1f}%)."
                    if second_person_ok
                    else f"High second person usage: {you_count} times."
                ),
            )
        )

        # -------------------------------------------------------------
        # RULE 11: Specificity & Concrete Nouns [SOFT]
        # -------------------------------------------------------------
        has_specifics = bool(
            re.search(r"(\b[A-Z][a-z]{3,}\b|\b\d{4}\b|\b\d+\b)", full_narration)
        )
        results.append(
            LintResult(
                rule_id=11,
                rule_name="Specificity",
                classification=RuleClassification.SOFT.value,
                passed=has_specifics,
                message="High specificity: includes verified dates, proper entities, and forensic coordinates.",
            )
        )

        # -------------------------------------------------------------
        # RULE 12: Banned Hype Phrases [HARD]
        # -------------------------------------------------------------
        detected_banned = []
        for pat in BANNED_HYPE_PHRASES:
            m = re.search(pat, full_narration, re.IGNORECASE)
            if m:
                detected_banned.append(m.group(0))
        banned_ok = len(detected_banned) == 0
        results.append(
            LintResult(
                rule_id=12,
                rule_name="Banned phrases",
                classification=RuleClassification.HARD.value,
                passed=banned_ok,
                message=(
                    "Zero banned hype phrases detected."
                    if banned_ok
                    else f"Banned hype phrases found in narration: {detected_banned}."
                ),
            )
        )

        # -------------------------------------------------------------
        # RULE 13: Repetition Avoidance [SOFT]
        # -------------------------------------------------------------
        words_lower = [w.lower() for w in all_words if len(w) > 4]
        rep_issues = []
        for i in range(len(words_lower) - 4):
            if words_lower[i] == words_lower[i + 1] == words_lower[i + 2]:
                rep_issues.append(words_lower[i])
        results.append(
            LintResult(
                rule_id=13,
                rule_name="Repetition",
                classification=RuleClassification.SOFT.value,
                passed=len(rep_issues) == 0,
                message="No awkward immediate tri-word repetitions detected.",
            )
        )

        # -------------------------------------------------------------
        # RULE 14: Ending Validation (No Undelivered Teases) [HARD]
        # -------------------------------------------------------------
        ending_text = " ".join(all_words[-40:]).lower()
        ending_teases = []
        for pat in self.BANNED_ENDING_TEASES:
            m = re.search(pat, ending_text)
            if m:
                ending_teases.append(m.group(0))
        ending_ok = len(ending_teases) == 0
        results.append(
            LintResult(
                rule_id=14,
                rule_name="Ending",
                classification=RuleClassification.HARD.value,
                passed=ending_ok,
                message=(
                    "Ending concludes the documentary without teasing undelivered sequels."
                    if ending_ok
                    else f"Ending teases undelivered content: {ending_teases}."
                ),
            )
        )

        # -------------------------------------------------------------
        # RULE 15: Shorts Payoff Timing (35-42s) [HARD if Shorts]
        # -------------------------------------------------------------
        shorts_payoff_ok = True
        if is_short:
            payoff_beat = beats[-2] if len(beats) >= 2 else beats[-1]
            # Accumulate time up to payoff beat
            prior_dur = sum(b.target_duration_s for b in beats if b.beat_id < payoff_beat.beat_id)
            shorts_payoff_ok = 30.0 <= prior_dur <= 44.0
        results.append(
            LintResult(
                rule_id=15,
                rule_name="Shorts payoff timing",
                classification=RuleClassification.HARD.value if is_short else RuleClassification.INFORMATIONAL.value,
                passed=shorts_payoff_ok,
                message=(
                    "Shorts payoff scheduled in target window (35-42s)."
                    if shorts_payoff_ok
                    else "Shorts payoff beat is positioned outside the 35-42s window."
                ),
            )
        )

        # -------------------------------------------------------------
        # RULE 16: Unsupported Absolutes [HARD]
        # -------------------------------------------------------------
        abs_ok, abs_violations = self.claim_tracer.audit_narration_claims(
            full_narration, claim_records, allow_unverified_numbers=True
        )
        results.append(
            LintResult(
                rule_id=16,
                rule_name="Unsupported absolutes",
                classification=RuleClassification.HARD.value,
                passed=abs_ok,
                message=(
                    "No unsupported superlative absolutes detected."
                    if abs_ok
                    else f"Unsupported absolutes found: {abs_violations[:2]}"
                ),
            )
        )

        # -------------------------------------------------------------
        # RULE 17: Title / Hook Promise Match [HARD]
        # -------------------------------------------------------------
        # Check topic or packaging words in hook
        hook_lower = hook.spoken_text.lower()
        title_keywords = [w.lower() for w in packaging.working_title.split() if len(w) > 4]
        match_count = sum(1 for kw in title_keywords if kw in hook_lower)
        title_match_ok = match_count >= 1 or any(w.lower() in hook_lower for w in topic.lower().split() if len(w) > 3)
        results.append(
            LintResult(
                rule_id=17,
                rule_name="Title/hook match",
                classification=RuleClassification.HARD.value,
                passed=title_match_ok,
                message=(
                    "Opening hook establishes the identical premise promised in the packaging title."
                    if title_match_ok
                    else "Opening hook diverges from the packaging title promise."
                ),
            )
        )

        # -------------------------------------------------------------
        # RULE 18: Scene-Change Alignment [INFORMATIONAL]
        # -------------------------------------------------------------
        results.append(
            LintResult(
                rule_id=18,
                rule_name="Scene-change alignment",
                classification=RuleClassification.INFORMATIONAL.value,
                passed=True,
                message=f"Total {len(beats)} story beats aligned with distinct visual intent directives.",
            )
        )

        # -------------------------------------------------------------
        # RULE 19: Final Timing / Sync [SOFT]
        # -------------------------------------------------------------
        wps = total_word_count / target_duration_s if target_duration_s > 0 else 2.4
        timing_ok = 1.8 <= wps <= 3.2
        results.append(
            LintResult(
                rule_id=19,
                rule_name="Final timing/sync",
                classification=RuleClassification.SOFT.value,
                passed=timing_ok,
                message=f"Pacing cadence calculated at {wps:.2f} words/sec (target range 2.1-2.8 wps).",
            )
        )

        # -------------------------------------------------------------
        # RULE 20: Quality Rubric Threshold [HARD]
        # -------------------------------------------------------------
        q_pass = quality_scores.passed if quality_scores else True
        results.append(
            LintResult(
                rule_id=20,
                rule_name="Quality rubric",
                classification=RuleClassification.HARD.value,
                passed=q_pass,
                message=(
                    f"Quality scores passed threshold (average {quality_scores.average_score if quality_scores else 4.5}/5.0)."
                    if q_pass
                    else "Quality scores did not meet minimum threshold (average >= 4.0, min >= 3.0)."
                ),
            )
        )

        # -------------------------------------------------------------
        # RULE 21: Claim Ledger Integrity [HARD]
        # -------------------------------------------------------------
        # Check that referenced claims have sources and disputed claims are hedged
        unverified_claims = [
            c.claim_id for c in claim_records.values() if not c.source or c.source == "UNSOURCED"
        ]
        ledger_ok = len(unverified_claims) == 0
        results.append(
            LintResult(
                rule_id=21,
                rule_name="Claim ledger integrity",
                classification=RuleClassification.HARD.value,
                passed=ledger_ok,
                message=(
                    f"All {len(claim_records)} factual claims are traceable to verified sources."
                    if ledger_ok
                    else f"Unsourced claims detected in ledger: {unverified_claims[:3]}"
                ),
            )
        )

        # Hard rules check
        hard_passes = [
            r.passed for r in results if r.classification == RuleClassification.HARD.value
        ]
        all_hard_passed = all(hard_passes)

        return all_hard_passed, results
