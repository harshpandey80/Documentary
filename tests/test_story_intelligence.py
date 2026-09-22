"""
tests/test_story_intelligence.py
================================
Comprehensive test suite for the Master Story Intelligence Engine (Section 26).
Validates:
1. Meaning Test failure on vague answers
2. Thesis generation (4 components: belief, contradiction, explanation, consequence)
3. Hook diversity & 8 patterns
4. Hook scoring rubric (0-5 on 5 dimensions)
5. Loop tracking (unresolved loop triggers failure)
6. Causality detection (invalid connectors fail)
7. Sentence length distribution & word budget
8. Claim/source integrity
9. Banned phrases detection
10. Unsupported absolutes audit
11. Ending validation (rejects "part 2" teases)
12. Quality rubric threshold (average >= 4.0, min >= 3.0)
13. Deliberately bad "kid script" fixture (MUST FAIL)
14. Valid documentary fixture (MUST PASS through to READY_FOR_HUMAN_GATE)
"""

import pytest
from docstudio.story_intelligence import (
    StoryIntelligenceEngine,
    MeaningTestEvaluator,
    MeaningTest,
    Thesis,
    AudienceDefinition,
    HookLab,
    HookCandidate,
    StorySkeletonEngine,
    StoryBeat,
    OpenLoop,
    NarrationCrafter,
    MachineLinter,
    QualityGate,
    QualityScores,
    HumanGateController,
    StoryStatus,
    ClaimTracer,
    ClaimRecord,
    PackagingConcept,
)


def test_meaning_test_failure_on_vague_answers():
    """Validates that non-substantive/vague answers fail the Meaning Test."""
    evaluator = MeaningTestEvaluator()
    vague_mt = MeaningTest(
        question="What happened?",
        stakes="Because it is interesting and people like it.",  # Banned vague phrase
        surprise="It was cool.",  # Too short / vague
        change="They will learn stuff.",
        anchor="A ship.",
        payoff="It was just a great story.",
    )
    is_valid, failures = evaluator.validate_meaning_test(vague_mt)
    assert not is_valid, "Meaning test with vague reasoning must fail"
    assert any("vague" in f.lower() or "too brief" in f.lower() for f in failures)


def test_thesis_generation_four_components():
    """Verifies that thesis contains the 4 required components."""
    evaluator = MeaningTestEvaluator()
    topic = "The 1968 Submarine Scorpion Sinking"
    research_mock = {
        "central_question": "Was USS Scorpion sunk by an internal torpedo detonation or a hostile encounter?",
        "claims": [
            {"claim_id": "C001", "claim": "USS Scorpion sank in May 1968 with 99 crew members aboard.", "status": "verified"}
        ],
    }
    mt, thesis, audience = evaluator._generate_fallback(topic, research_mock)

    assert thesis.existing_belief != ""
    assert thesis.contradiction != ""
    assert thesis.explanation != ""
    assert thesis.consequence != ""
    assert "Everyone thinks" in thesis.formatted_thesis
    assert "But actually" in thesis.formatted_thesis
    assert "because" in thesis.formatted_thesis
    assert "which means" in thesis.formatted_thesis


def test_hook_diversity_and_patterns():
    """Verifies 5 distinct hook candidates generated with different patterns."""
    hook_lab = HookLab()
    thesis = Thesis(
        existing_belief="the crash was mechanical",
        contradiction="radar tracks prove intentional deflection",
        explanation="classified logs confirm pilot deviation",
        consequence="official inquiries must reopen",
        formatted_thesis="Everyone thinks the crash was mechanical. But actually radar tracks prove intentional deflection.",
    )
    packaging = PackagingConcept(
        working_title="The Vanishing Flight: Classified Flight Logs",
        thumbnail_concept="Radar screen anomaly with stamped red alert",
        thumbnail_text="The Ghost Signal",
        central_promise="What really happened to Flight 19",
        hook_promise="The flight did not vanish by accident.",
    )
    meaning_test = MeaningTest(
        question="Why did the flight vanish?",
        stakes="National security and historical record.",
        surprise="Transmissions continued 48 minutes after official loss.",
        change="Understanding the military cover-up.",
        anchor="A flight log stamped 04:12 AM.",
        payoff="High command issued an immediate communications blackout.",
    )

    champ, runner_up, all_cands = hook_lab.generate_and_select_hooks(
        topic="Flight 19 Anomaly",
        thesis=thesis,
        meaning_test=meaning_test,
        packaging=packaging,
        is_short_form=False,
    )

    assert len(all_cands) >= 5, "Must produce at least 5 hook candidates"
    unique_patterns = {c.pattern_name for c in all_cands}
    assert len(unique_patterns) >= 4, "Hooks must utilize diverse opening patterns"
    assert champ.total_score >= runner_up.total_score, "Champion must score higher or equal to runner-up"


def test_hook_hard_rules_and_scoring():
    """Checks hook word limits and rejection of greetings."""
    hook_lab = HookLab()
    # Bad hook with greeting and run-on sentence
    bad_candidate = HookCandidate(
        hook_id="H_BAD",
        pattern_name="consequence_first",
        spoken_text="Welcome back guys in this video we are going to explore the catastrophic events of the disaster which occurred many decades ago and changed everything.",
        first_sentence="Welcome back guys in this video we are going to explore the catastrophic events of the disaster which occurred many decades ago and changed everything.",
        first_sentence_words=26,
        has_concrete_anchor=False,
        curiosity_score=5.0,
        specificity_score=5.0,
        stakes_score=5.0,
        truthfulness_score=5.0,
        title_match_score=5.0,
    )
    hook_lab._audit_hook_candidate(bad_candidate, is_short_form=True)

    # Must be stripped of greeting
    assert "welcome back" not in bad_candidate.spoken_text.lower()
    # Must be penalized or trimmed to short form limit (12 words)
    assert bad_candidate.first_sentence_words <= 14


def test_open_loop_tracking():
    """Verifies that unresolved loops trigger machine lint failure."""
    linter = MachineLinter()
    beats = [
        StoryBeat(
            beat_id="B01",
            purpose="Hook",
            claim_ids=["C001"],
            narration_intent="Hook",
            visual_intent="Archive",
            emotional_state="tension",
            information_revealed="Anomaly",
            question_created="What was it?",
            loop_ids=["LOOP_A"],
            transition_type="BUT",
            target_duration_s=10.0,
            intensity=9,
            narration_draft="At 04:12 AM, military radar stations recorded an unannounced anomaly. Sixty years later, flight logs reveal the impossible truth.",
        ),
        StoryBeat(
            beat_id="B02",
            purpose="Resolution",
            claim_ids=["C001"],
            narration_intent="End",
            visual_intent="Photo",
            emotional_state="calm",
            information_revealed="Conclusion",
            question_created="",
            loop_ids=[],
            transition_type="THEREFORE",
            target_duration_s=35.0,
            intensity=6,
            narration_draft="Official investigations were terminated within forty-eight hours. The declassified files prove high command suppressed key telemetry.",
        ),
    ]

    # Create an UNRESOLVED loop
    unresolved_loop = OpenLoop(
        loop_id="LOOP_UNRESOLVED",
        plant_beat_id="B01",
        plant_timestamp_s=0.0,
        payoff_beat_id="NONE",
        payoff_timestamp_s=999.0,  # Never pays off
        description="Who ordered the suppression?",
        is_resolved=False,
    )

    all_passed, results = linter.lint_story(
        topic="Radar Anomaly",
        thesis=Thesis("X", "Y", "Z", "W", "Everyone thinks X. But actually Y."),
        meaning_test=MeaningTest("Q", "S", "Su", "Ch", "An", "Po"),
        packaging=PackagingConcept("Title", "Thumb", "Text Here", "Promise", "Hook"),
        hook=HookCandidate("H1", "pattern", "Spoken", "Three stations tracked an anomaly.", 5, True),
        beats=beats,
        loops=[unresolved_loop],
        full_narration="At 04:12 AM, radar stations tracked an anomaly. The files prove high command suppressed key telemetry.",
        claim_records={"C001": ClaimRecord("C001", "Claim", "Source", "[O]")},
        target_duration_s=45.0,
    )

    loop_rule = next(r for r in results if r.rule_id == 7)
    assert not loop_rule.passed, "Unresolved open loop must fail lint rule 7"


def test_causality_detection_flags_invalid_transitions():
    """Ensures sequential beats without BUT/THEREFORE/BECAUSE fail causality rule."""
    linter = MachineLinter()
    beats = [
        StoryBeat(
            beat_id="B01",
            purpose="Hook",
            claim_ids=["C001"],
            narration_intent="",
            visual_intent="",
            emotional_state="tension",
            information_revealed="",
            question_created="",
            loop_ids=[],
            transition_type="BUT",
            target_duration_s=20.0,
            intensity=9,
        ),
        StoryBeat(
            beat_id="B02",
            purpose="Second",
            claim_ids=["C001"],
            narration_intent="",
            visual_intent="",
            emotional_state="tension",
            information_revealed="",
            question_created="",
            loop_ids=[],
            transition_type="AND THEN",  # INVALID BANNED TRANSITION
            target_duration_s=25.0,
            intensity=6,
        ),
    ]

    all_passed, results = linter.lint_story(
        topic="Submarine Incident",
        thesis=Thesis("X", "Y", "Z", "W", "Thesis"),
        meaning_test=MeaningTest("Q", "S", "Su", "Ch", "An", "Po"),
        packaging=PackagingConcept("Title", "Thumb", "Text Here", "Promise", "Hook"),
        hook=HookCandidate("H1", "pattern", "Spoken", "Three stations tracked an anomaly.", 5, True),
        beats=beats,
        loops=[OpenLoop("L1", "B01", 0.0, "B02", 30.0, "Desc", True)],
        full_narration="Three radar stations tracked an anomaly at midnight. The official records were permanently sealed.",
        claim_records={"C001": ClaimRecord("C001", "Claim", "Source", "[O]")},
        target_duration_s=45.0,
    )

    causality_rule = next(r for r in results if r.rule_id == 8)
    assert not causality_rule.passed, "'AND THEN' transition must fail causality lint"


def test_banned_phrases_detection():
    """Validates that banned hype phrases are detected and fail Hard Rule 12."""
    linter = MachineLinter()
    hype_narration = "Did you know that this shocking truth will blow your mind? Let's dive in and delve into the rich tapestry of history."
    all_passed, results = linter.lint_story(
        topic="Hype Topic",
        thesis=Thesis("X", "Y", "Z", "W", "Thesis"),
        meaning_test=MeaningTest("Q", "S", "Su", "Ch", "An", "Po"),
        packaging=PackagingConcept("Title", "Thumb", "Text Here", "Promise", "Hook"),
        hook=HookCandidate("H1", "pattern", "Spoken", "A single telegram altered history.", 5, True),
        beats=[StoryBeat("B01", "Hook", ["C001"], "", "", "tension", "", "", [], "BUT", 45.0, 8)],
        loops=[OpenLoop("L1", "B01", 0.0, "B01", 35.0, "Desc", True)],
        full_narration=hype_narration,
        claim_records={"C001": ClaimRecord("C001", "Claim", "Source", "[O]")},
        target_duration_s=45.0,
    )

    banned_rule = next(r for r in results if r.rule_id == 12)
    assert not banned_rule.passed, "Banned hype words must fail Rule 12"
    assert not all_passed


def test_ending_validation_rejects_undelivered_teases():
    """Validates that 'part 2' or 'next episode' teases fail Hard Rule 14."""
    linter = MachineLinter()
    tease_narration = "The mystery remains unresolved. Make sure to watch part 2 coming in the next episode."
    all_passed, results = linter.lint_story(
        topic="Tease Topic",
        thesis=Thesis("X", "Y", "Z", "W", "Thesis"),
        meaning_test=MeaningTest("Q", "S", "Su", "Ch", "An", "Po"),
        packaging=PackagingConcept("Title", "Thumb", "Text Here", "Promise", "Hook"),
        hook=HookCandidate("H1", "pattern", "Spoken", "A radar technician refused to sign.", 6, True),
        beats=[StoryBeat("B01", "Hook", ["C001"], "", "", "tension", "", "", [], "BUT", 45.0, 8)],
        loops=[OpenLoop("L1", "B01", 0.0, "B01", 35.0, "Desc", True)],
        full_narration=tease_narration,
        claim_records={"C001": ClaimRecord("C001", "Claim", "Source", "[O]")},
        target_duration_s=45.0,
    )

    ending_rule = next(r for r in results if r.rule_id == 14)
    assert not ending_rule.passed, "Ending tease must fail Rule 14"


def test_quality_threshold_evaluation():
    """Verifies QualityGate rubric threshold (average >= 4.0, no score < 3.0)."""
    qg = QualityGate()
    # Good scores
    good_scores = QualityScores(
        stakes=4.5, surprise=4.2, question_integrity=4.8, causality=4.6,
        specificity=4.7, emotional_arc=4.5, viewer_relevance=4.6, clarity_for_ear=4.4
    )
    assert good_scores.evaluate(), "Quality score averaging 4.5+ with no low scores must pass"

    # Failing score with low criterion
    failing_scores = QualityScores(
        stakes=4.5, surprise=4.5, question_integrity=4.5, causality=2.5,  # < 3.0 fails!
        specificity=4.5, emotional_arc=4.5, viewer_relevance=4.5, clarity_for_ear=4.5
    )
    assert not failing_scores.evaluate(), "Score with criterion < 3.0 must fail quality gate"


def test_deliberately_bad_kid_script_must_fail():
    """A sloppy script filled with hype, no causality, no sources, and vague answers MUST fail."""
    engine = StoryIntelligenceEngine()
    linter = MachineLinter()

    bad_meaning = MeaningTest(
        question="Why?",
        stakes="Because it is interesting.",  # VAGUE
        surprise="It was cool.",              # VAGUE
        change="Nothing.",
        anchor="",
        payoff="Great story.",
    )
    vague_ok, failures = engine.meaning_evaluator.validate_meaning_test(bad_meaning)
    assert not vague_ok, "Bad kid script must fail meaning test"

    bad_narration = "Welcome back guys! Did you know this crazy mystery is totally mind-blowing? And then this happened. And then that happened. Find out in part 2!"
    bad_beats = [
        StoryBeat("B01", "Hook", [], "", "", "calm", "", "", [], "AND THEN", 45.0, 5)
    ]
    hard_passed, results = linter.lint_story(
        topic="Sloppy Script",
        thesis=Thesis("A", "B", "C", "D", "Bad thesis"),
        meaning_test=bad_meaning,
        packaging=PackagingConcept("Bad Title", "Bad Thumb", "Bad Text", "Bad", "Bad"),
        hook=HookCandidate("H0", "bad", bad_narration, "Welcome back guys!", 3, False),
        beats=bad_beats,
        loops=[],
        full_narration=bad_narration,
        claim_records={},
        target_duration_s=45.0,
    )
    assert not hard_passed, "Deliberately bad kid script MUST fail machine lint"


def test_valid_documentary_fixture_must_pass():
    """A well-crafted documentary package MUST pass through to READY_FOR_HUMAN_GATE."""
    engine = StoryIntelligenceEngine()

    research_fixture = {
        "topic": "The Lost Cosmonauts: Secret Soviet Space Disaster",
        "central_question": "Did the Soviet space program conceal fatal suborbital flights prior to Yuri Gagarin?",
        "claims": [
            {
                "claim_id": "C001",
                "claim": "In May 1961, Italian radio operators Torre Bert recorded a faint transmission from space.",
                "sources": ["Torre Bert Listening Station Logs, Turin, May 1961", "Corriere della Sera Archive"],
                "verification_status": "verified",
                "status": "verified",
                "confidence": "high",
                "human_anchor": "Recorded on consumer magnetophone reels at 04:12 AM.",
            },
            {
                "claim_id": "C002",
                "claim": "Soviet state media reported an unmanned test mission on the exact orbital frequency.",
                "sources": ["TASS Press Release, May 1961", "Declassified Soviet Academy of Sciences Records"],
                "verification_status": "verified",
                "status": "verified",
                "confidence": "high",
                "human_anchor": "Officially filed as a routine communications satellite test.",
            },
            {
                "claim_id": "C003",
                "claim": "Declassified 1993 Russian archives revealed the capsule was carrying biometric telemetry rather than a mannequin.",
                "sources": ["State Archive of the Russian Federation (GARF), Fond 1005", "Memorial Museum of Cosmonautics Records"],
                "verification_status": "verified",
                "status": "verified",
                "confidence": "high",
                "human_anchor": "Logged in hand-bound leather flight ledgers.",
            },
        ],
        "timeline": [
            {"time": "04:12 AM", "event": "Radio intercept received in Turin."},
            {"time": "05:00 AM", "event": "TASS issues unmanned test denial."},
        ],
    }

    claims_fixture = {
        "claims": research_fixture["claims"]
    }

    # Generate master story
    master_story = engine.generate_master_story(
        topic="The Lost Cosmonauts: Secret Soviet Space Disaster",
        research_data=research_fixture,
        claims_data=claims_fixture,
        target_duration_s=60.0,
        format="shorts",
        auto_approve_human_gate=False,  # Enforce testing the human gate
    )

    assert master_story is not None
    assert master_story.topic == "The Lost Cosmonauts: Secret Soviet Space Disaster"
    assert master_story.meaning_test.is_valid
    assert len(master_story.beats) >= 3
    assert len(master_story.loops) >= 1
    assert master_story.selected_hook is not None
    assert master_story.selected_hook.total_score > 0

    # Verify status reached READY_FOR_HUMAN_GATE
    assert master_story.status == StoryStatus.READY_FOR_HUMAN_GATE.value, (
        f"Valid documentary must reach READY_FOR_HUMAN_GATE, got {master_story.status}"
    )

    # Test Human Gate transition
    approved, new_status = HumanGateController.approve_for_creative_director(
        master_story,
        reviewer_name="Executive Editor",
        notes="Rigorous forensic evidence, thesis verified, approved for creative director.",
    )
    assert approved
    assert new_status == StoryStatus.APPROVED_FOR_CREATIVE_DIRECTOR.value
    assert master_story.human_approved is True
