import os
import pytest
from pathlib import Path
from docstudio.vox_motion_graphics import VoxMotionGraphicsEngine


@pytest.fixture
def vox_engine(tmp_path):
    return VoxMotionGraphicsEngine(cache_dir=tmp_path / "vox_cache")


def test_render_newspaper_clipping(vox_engine, tmp_path):
    dest = tmp_path / "test_newspaper.mp4"
    result = vox_engine.render_newspaper_clipping(
        headline="OFFICIAL TEST HEADLINE",
        subtext="Naval records corroborate telemetry anomaly at sea.",
        dest_video=dest,
        duration=1.0,
        width=320,
        height=180,
        fps=10,
    )
    assert result is not None
    assert result.exists()
    assert result.stat().st_size > 5000


def test_render_declassified_dossier(vox_engine, tmp_path):
    dest = tmp_path / "test_dossier.mp4"
    result = vox_engine.render_declassified_dossier(
        topic="PROJECT TEST",
        document_body="Declassified operational log regarding unconfirmed vessel movements.",
        dest_video=dest,
        duration=1.0,
        width=320,
        height=180,
        fps=10,
    )
    assert result is not None
    assert result.exists()
    assert result.stat().st_size > 5000


def test_render_polaroid_evidence(vox_engine, tmp_path):
    dest = tmp_path / "test_polaroid.mp4"
    result = vox_engine.render_polaroid_evidence(
        label="RECOVERED ARTIFACT 01",
        dest_video=dest,
        duration=1.0,
        width=320,
        height=180,
        fps=10,
    )
    assert result is not None
    assert result.exists()
    assert result.stat().st_size > 5000


def test_render_kinetic_headline(vox_engine, tmp_path):
    dest = tmp_path / "test_kinetic.mp4"
    result = vox_engine.render_kinetic_headline(
        headline="BREAKING INVESTIGATION FINDINGS",
        category_tag="SPECIAL DISPATCH",
        subtext="Declassified archive corroborated by international analysts.",
        dest_video=dest,
        duration=1.0,
        width=320,
        height=180,
        fps=10,
    )
    assert result is not None
    assert result.exists()
    assert result.stat().st_size > 3000


def test_render_stat_counter_card(vox_engine, tmp_path):
    dest = tmp_path / "test_counter.mp4"
    result = vox_engine.render_stat_counter_card(
        target_number=8848,
        unit=" M",
        label="SURVEYED ALTITUDE",
        subtitle="Geodetic telemetry reference",
        dest_video=dest,
        duration=1.0,
        width=320,
        height=180,
        fps=10,
    )
    assert result is not None
    assert result.exists()
    assert result.stat().st_size > 3000


def test_render_editorial_tagline(vox_engine, tmp_path):
    dest = tmp_path / "test_tagline.mp4"
    result = vox_engine.render_editorial_tagline(
        title="PRIMARY ARCHIVE SUMMARY",
        category="FORENSIC DOSSIER",
        subtitle="Declassified government file index",
        dest_video=dest,
        duration=1.0,
        width=320,
        height=180,
        fps=10,
    )
    assert result is not None
    assert result.exists()
    assert result.stat().st_size > 3000


def test_render_vox_scene_auto_dispatch(vox_engine, tmp_path):
    # Test vertical 9:16 aspect ratio with auto style routing
    dest = tmp_path / "test_vertical.mp4"
    result = vox_engine.render_vox_scene(
        topic="PACIFIC ANOMALY",
        narration="Breaking newspaper reports confirm unsealed log entries.",
        dest_video=dest,
        duration=1.0,
        width=180,
        height=320,
        fps=10,
    )
    assert result is not None
    assert result.exists()
    assert result.stat().st_size > 5000


def test_jitter_curated_templates_catalog():
    # Verify curated templates catalog is loaded and populated
    all_templates = VoxMotionGraphicsEngine.get_available_motion_templates()
    assert len(all_templates) >= 100

    kinetic = VoxMotionGraphicsEngine.get_available_motion_templates("kinetic_typography")
    assert len(kinetic) >= 20
    assert any("text" in t["name"].lower() or "reveal" in t["name"].lower() or "stretch" in t["name"].lower() for t in kinetic)

    stats = VoxMotionGraphicsEngine.get_available_motion_templates("infographics_and_stats")
    assert len(stats) >= 20


def test_no_hardcoded_topic_facts_in_engine():
    # Adhere strictly to Rule 5: engine source code must not contain hardcoded specific documentary facts
    source_path = Path("docstudio/vox_motion_graphics.py")
    text = source_path.read_text(encoding="utf-8")
    assert "Flight 19" not in text
    assert "Challenger Deep" not in text
    assert "Mariana Trench" not in text
