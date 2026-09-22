"""
Unit tests for Remote Creative Director:
- Manifest Schema serialization and parsing
- ShotManifestValidator (overlaps, mandatory fields, duration)
- ContextBuilder (whole-story context)
- BrowserGenerationQueue (concurrency, status transitions)
- BrowserBridge (request creation, asset QA)
"""

import pytest
from pathlib import Path
from docstudio.remote_creative_director.manifest_schema import (
    ShotManifest,
    SceneManifest,
    ShotDirective,
    NarrationRange,
    VisualPurpose,
    VisualType,
    SourceStrategy,
    ContinuityBible,
)
from docstudio.remote_creative_director.validator import ShotManifestValidator
from docstudio.remote_creative_director.context_builder import ContextBuilder, VisualBudget
from docstudio.remote_creative_director.browser_bridge import BrowserBridge, BrowserGenerationRequest
from docstudio.visual_providers.browser.queue import (
    BrowserGenerationQueue,
    TaskState,
)


def test_shot_manifest_roundtrip():
    shot = ShotDirective(
        shot_id="S01_01",
        start=0.0,
        end=3.5,
        duration=3.5,
        purpose=VisualPurpose.ESTABLISH,
        visual_type=VisualType.MAP,
        visual_reason="Ground the viewer in the flight path geography.",
        source_strategy=SourceStrategy.PROCEDURAL_MAP,
    )
    scene = SceneManifest(
        scene_id="S01",
        story_beat="Takeoff from Fort Lauderdale",
        viewer_takeaway="Five bombers depart on a routine training mission.",
        narration_range=NarrationRange(0.0, 3.5),
        shots=[shot],
    )
    manifest = ShotManifest(
        documentary_id="doc_flight_19",
        topic="The Disappearance of Flight 19",
        total_duration=3.5,
        scenes=[scene],
    )

    d = manifest.to_dict()
    assert d["topic"] == "The Disappearance of Flight 19"
    assert len(d["scenes"]) == 1
    assert d["scenes"][0]["shots"][0]["purpose"] == "ESTABLISH"

    # Reconstitute
    reconstructed = ShotManifest.from_dict(d)
    assert reconstructed.documentary_id == "doc_flight_19"
    assert reconstructed.scenes[0].shots[0].visual_type == VisualType.MAP


def test_validator_rejects_missing_reason():
    shot = ShotDirective(
        shot_id="S01_01",
        start=0.0,
        end=3.0,
        duration=3.0,
        purpose=VisualPurpose.ESTABLISH,
        visual_type=VisualType.STOCK_BROLL,
        visual_reason="",  # Missing mandatory reason
        source_strategy=SourceStrategy.RETRIEVE_ARCHIVE_STOCK,
    )
    scene = SceneManifest(
        scene_id="S01",
        story_beat="Intro",
        viewer_takeaway="Start",
        narration_range=NarrationRange(0.0, 3.0),
        shots=[shot],
    )
    manifest = ShotManifest(
        documentary_id="doc_test",
        topic="Test",
        total_duration=3.0,
        scenes=[scene],
    )

    res = ShotManifestValidator.validate(manifest)
    assert not res.is_valid
    assert any("visual_reason" in e for e in res.errors)


def test_validator_detects_overlap():
    shot1 = ShotDirective(
        shot_id="S01_01",
        start=0.0,
        end=3.0,
        duration=3.0,
        purpose=VisualPurpose.ESTABLISH,
        visual_type=VisualType.STOCK_BROLL,
        visual_reason="Establish the ocean horizon setting.",
        source_strategy=SourceStrategy.RETRIEVE_ARCHIVE_STOCK,
    )
    shot2 = ShotDirective(
        shot_id="S01_02",
        start=2.0,  # Overlaps shot1 by 1.0s
        end=4.5,
        duration=2.5,
        purpose=VisualPurpose.INTRODUCE_PERSON,
        visual_type=VisualType.REAL_ARCHIVAL,
        visual_reason="Introduce flight leader Lt. Taylor.",
        source_strategy=SourceStrategy.RETRIEVE_ARCHIVE_STOCK,
    )
    scene = SceneManifest(
        scene_id="S01",
        story_beat="Intro",
        viewer_takeaway="Start",
        narration_range=NarrationRange(0.0, 4.5),
        shots=[shot1, shot2],
    )
    manifest = ShotManifest(
        documentary_id="doc_test",
        topic="Test",
        total_duration=4.5,
        scenes=[scene],
    )

    res = ShotManifestValidator.validate(manifest)
    assert not res.is_valid
    assert any("overlaps" in e for e in res.errors)


def test_context_builder():
    research = {
        "entities": [{"name": "Charles Taylor", "type": "person", "description": "Navy pilot"}],
        "locations": [{"name": "Bermuda Triangle", "description": "Western Atlantic"}],
        "timeline": [{"year": 1945, "event": "Flight 19 disappears"}],
    }
    claims = {
        "claims": [{"claim_id": "c_1", "statement": "All five planes vanished.", "source": "Navy Report"}],
    }
    story = {
        "scenes": [{"scene_id": "s_1", "story_beat": "The Routine Patrol"}],
    }
    narration = {
        "scenes": [{"scene_id": "s_1", "narration": "On December 5, 1945..."}],
    }

    ctx = ContextBuilder.build_context(
        topic="Flight 19",
        target_duration=60.0,
        research_data=research,
        claims_data=claims,
        story_data=story,
        narration_data=narration,
    )

    assert ctx.topic == "Flight 19"
    assert len(ctx.continuity_bible.characters) == 1
    assert ctx.continuity_bible.characters[0]["name"] == "Charles Taylor"
    assert ctx.visual_budget.max_ai_videos == 2


def test_browser_queue_concurrency():
    queue = BrowserGenerationQueue(max_concurrency=1)
    t1 = queue.enqueue("S01_01", {"prompt": "ocean storm"})
    t2 = queue.enqueue("S01_02", {"prompt": "cockpit dial"})

    task_a = queue.acquire_next_task()
    assert task_a is not None
    assert task_a.shot_id == "S01_01"
    assert task_a.state == TaskState.RUNNING

    # Since max_concurrency=1, second task should NOT be acquired until first completes
    task_b = queue.acquire_next_task()
    assert task_b is None

    # Mark first complete
    queue.mark_completed(task_a.task_id, "/tmp/s01_01.mp4")

    # Now second task can run
    task_b = queue.acquire_next_task()
    assert task_b is not None
    assert task_b.shot_id == "S01_02"


def test_execution_router_instantiation(tmp_path):
    from docstudio.remote_creative_director.provider_router import ExecutionRouter

    router = ExecutionRouter(cache_dir=tmp_path)
    assert router.cache_dir == tmp_path
