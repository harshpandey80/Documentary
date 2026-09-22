import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import shutil

from docstudio.research_engine import ResearchEngine, ResearchFailureError, GroundedResearchValidationError
from docstudio.research_validator import TopicDomainValidator
from docstudio.claims_ledger import ClaimsLedger
from docstudio.story_engine import StoryEngine, StoryGroundingError, InsufficientGroundedMaterialError
from docstudio.job_manager import JobManager
from docstudio.autonomous_pipeline import AutonomousDocumentaryPipeline


# ---------------------------------------------------------------------------
# Test 9a: Gemini 429 cannot produce fabricated historical research
# ---------------------------------------------------------------------------
def test_gemini_429_cannot_produce_fabricated_historical_research():
    """
    Proves that when Gemini encounters a 429 (ResourceExhausted) quota error,
    ResearchEngine fails cleanly with ResearchFailureError and NEVER fabricates
    synthetic historical entities, radar anomalies, or flight logs.
    """
    engine = ResearchEngine()

    # Mock complete_json to raise a 429 Quota Exhaustion exception
    with patch("docstudio.research_engine.complete_json", side_effect=Exception("429 Resource has been exhausted (e.g. check quota)")):
        with pytest.raises(ResearchFailureError) as excinfo:
            engine.conduct_research(topic="The Fall of Alexander the Great")

        # Must explicitly reject fabrication
        assert "strictly prohibited" in str(excinfo.value) or "failed" in str(excinfo.value).lower()


# ---------------------------------------------------------------------------
# Test 9b: Unrelated fallback research is rejected for a historical topic
# ---------------------------------------------------------------------------
def test_unrelated_fallback_research_rejected_for_historical_topic():
    """
    Proves that unrelated fallback research (e.g. telemetry, radar anomalies,
    air traffic controllers, or generic investigative boilerplate) is rejected
    when validated against a historical topic like 'The Fall of Alexander the Great'.
    """
    topic = "The Fall of Alexander the Great"

    # Simulated boilerplate research containing unrelated aviation/radar elements
    fabricated_research = {
        "topic": topic,
        "summary": "Investigative documentary on unexpected loss of signal and radar anomalies.",
        "central_question": "What caused the 48-minute blackout?",
        "entities": [
            {"name": "Federal Aviation Oversight", "role": "Investigative Commission", "type": "organization"},
            {"name": "Flight Controller Log", "role": "Physical Evidence", "type": "artifact"}
        ],
        "timeline": [
            {"time": "04:12 AM", "event": "Radar telemetry contact dropped."}
        ],
        "claims": [
            {
                "claim_id": "CLM-001",
                "statement": "Radar anomalies were detected 48 minutes prior to communications blackout.",
                "source": "Official Archive Depository",
                "verification_status": "verified"
            },
            {
                "claim_id": "CLM-002",
                "statement": "Controllers overwrite tapes within 48 minutes under standard operating procedures.",
                "source": "Investigative Oversight Commission",
                "verification_status": "verified"
            }
        ]
    }

    # Must fail validation
    is_valid, reasons = TopicDomainValidator.validate_research(fabricated_research, topic=topic)
    assert is_valid is False
    assert any("radar" in r.lower() or "telemetry" in r.lower() or "boilerplate" in r.lower() or "entity" in r.lower() for r in reasons)

    # Calling validate_research with raise_on_error=True must raise GroundedResearchValidationError
    with pytest.raises(GroundedResearchValidationError):
        TopicDomainValidator.validate_research(fabricated_research, topic=topic, raise_on_error=True)


# ---------------------------------------------------------------------------
# Test 9c: Every story claim resolves to a claims-ledger ID
# ---------------------------------------------------------------------------
def test_every_story_claim_resolves_to_claims_ledger_id():
    """
    Proves that every factual claim in StoryEngine must resolve to a valid claim ID
    in the ClaimsLedger. Any ungrounded or invented claim ID triggers StoryGroundingError.
    """
    topic = "The Fall of Alexander the Great"

    # Grounded claims ledger
    ledger_data = {
        "topic": topic,
        "claims": [
            {
                "claim_id": "CLM-ALX-001",
                "statement": "Alexander died in Babylon in June 323 BC at age 32.",
                "source": "Arrian, Anabasis of Alexander",
                "verification_status": "verified"
            },
            {
                "claim_id": "CLM-ALX-002",
                "statement": "Following a prolonged banquet, Alexander suffered sudden acute fever and paralysis.",
                "source": "Plutarch, Life of Alexander",
                "verification_status": "verified"
            }
        ]
    }

    # 1. Valid story model where all beats map to registered claims
    valid_story = {
        "topic": topic,
        "central_question": "What caused the sudden demise of Alexander the Great in Babylon?",
        "beats": [
            {
                "beat_id": "BEAT-01",
                "name": "The Babylonian Banquet",
                "dramatic_function": "The Crisis",
                "narrative_action": "Alexander collapses following a sudden onset of fever.",
                "viewer_seeing_intent": "Ancient palace banquet hall in Babylon.",
                "claim_ids": ["CLM-ALX-001", "CLM-ALX-002"]
            }
        ]
    }
    # Should validate successfully
    is_valid, issues = StoryEngine.validate_story_grounding(valid_story, ledger=ledger_data, topic=topic)
    assert is_valid is True
    assert len(issues) == 0

    # 2. Invalid story model where a beat introduces an unregistered/fabricated claim ID
    fabricated_claim_story = {
        "topic": topic,
        "central_question": "What caused the sudden demise of Alexander the Great in Babylon?",
        "beats": [
            {
                "beat_id": "BEAT-01",
                "name": "The Unregistered Radar Event",
                "dramatic_function": "The Anomaly",
                "narrative_action": "An unverified radar report claims foul play.",
                "viewer_seeing_intent": "Secret headquarters communications room.",
                "claim_ids": ["CLM-FABRICATED-999"]
            }
        ]
    }

    with pytest.raises(StoryGroundingError) as excinfo:
        StoryEngine.validate_story_grounding(
            fabricated_claim_story, ledger=ledger_data, topic=topic, raise_on_error=True
        )
    assert "CLM-FABRICATED-999" in str(excinfo.value)

    # 3. Invalid story model where a beat has no claim grounding
    empty_claim_story = {
        "topic": topic,
        "central_question": "What caused the sudden demise of Alexander the Great in Babylon?",
        "beats": [
            {
                "beat_id": "BEAT-01",
                "name": "Ungrounded Dramatization",
                "dramatic_function": "The Hook",
                "narrative_action": "Speculative ungrounded scene.",
                "viewer_seeing_intent": "Dark chamber.",
                "claim_ids": []
            }
        ]
    }

    with pytest.raises(StoryGroundingError):
        StoryEngine.validate_story_grounding(
            empty_claim_story, ledger=ledger_data, topic=topic, raise_on_error=True
        )


# ---------------------------------------------------------------------------
# Test 9d: Ungrounded story causes a clean pipeline failure instead of video generation
# ---------------------------------------------------------------------------
def test_ungrounded_story_causes_clean_pipeline_failure_without_video_generation():
    """
    Proves that when ungrounded research or story data is encountered, DocStudioPipeline
    cleanly fails the job at Stage 1 / Stage 2 / Stage 3, saves status='failed',
    and halts execution BEFORE synthesizing TTS narration or invoking video rendering.
    """
    temp_dir = Path(tempfile.mkdtemp())
    try:
        job_mgr = JobManager(root_dir=temp_dir)
        pipeline = AutonomousDocumentaryPipeline(job_manager=job_mgr)

        topic = "The Fall of Alexander the Great"
        job = job_mgr.create_job(topic=topic)
        job_id = job["job_id"]

        # Mock Researcher to return ungrounded/fabricated research (modern flight logs & radar on Alexander topic)
        unrelated_research = {
            "topic": topic,
            "summary": "Investigative report on radar anomalies and flight logs.",
            "central_question": "What really happened?",
            "entities": [{"name": "Flight Operations", "role": "Dispatch", "type": "agency"}],
            "timeline": [{"time": "04:12 AM", "event": "Radar contact severed"}],
            "claims": [
                {
                    "claim_id": "CLM-001",
                    "statement": "Telemetry logs confirm radar contact ceased at 04:12 AM.",
                    "source": "Official Archive Depository",
                    "verification_status": "verified"
                },
                {
                    "claim_id": "CLM-002",
                    "statement": "Air traffic controllers were ordered to seal communications.",
                    "source": "Investigative Oversight Commission",
                    "verification_status": "verified"
                }
            ]
        }

        # Also mock TTS and rendering to ensure they are NEVER called
        with patch.object(pipeline.researcher, "research_topic", return_value=unrelated_research), \
             patch.object(pipeline.tts, "synthesize_scenes") as mock_tts, \
             patch("docstudio.video_assembler.VideoAssembler.assemble_video") as mock_render:

            result = pipeline.run_job(job_id=job_id)

            # Pipeline must report failure
            assert result["status"] == "failed"
            assert result["stage"] in ("research", "claims", "story")
            assert "error" in result

            # Verify JobManager status
            saved_status = job_mgr.get_job_status(job_id)
            assert saved_status["status"] == "failed"
            assert saved_status["stages"]["research"]["status"] == "failed"

            # Verify downstream execution was HALTED (no TTS narration, no rendering)
            assert mock_tts.call_count == 0
            assert mock_render.call_count == 0

    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
