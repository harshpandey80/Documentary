import pytest
from pathlib import Path
from docstudio.canva_templates import CanvaTemplateEngine


def test_canva_comparison_render(tmp_path: Path):
    engine = CanvaTemplateEngine(cache_dir=tmp_path / "canva_cache")
    out_video = tmp_path / "compare_test.mp4"

    res = engine.render_comparison_video(
        title_a="ANGLO-SAXON RULE",
        desc_a="Decentralized kingdoms and ancient legal customs before 1066.",
        title_b="NORMAN FEUDALISM",
        desc_b="Centralized royal authority and the Domesday survey.",
        dest_video=out_video,
        duration=1.0,
        width=360,
        height=640,
        fps=15
    )

    assert res.exists()
    assert res.stat().st_size > 1000


def test_canva_curiosity_hook_render(tmp_path: Path):
    engine = CanvaTemplateEngine(cache_dir=tmp_path / "canva_cache")
    out_video = tmp_path / "hook_test.mp4"

    res = engine.render_curiosity_hook_video(
        headline="WILLIAM THE CONQUEROR SPOKE NO ENGLISH",
        subtext="French remained the official language of England's court for over 300 years.",
        dest_video=out_video,
        duration=1.0,
        width=360,
        height=640,
        fps=15
    )

    assert res.exists()
    assert res.stat().st_size > 1000


def test_canva_quote_card_render(tmp_path: Path):
    engine = CanvaTemplateEngine(cache_dir=tmp_path / "canva_cache")
    out_video = tmp_path / "quote_test.mp4"

    res = engine.render_quote_card_video(
        quote_text="I will never retreat from this shore while I draw breath.",
        author="WILLIAM THE CONQUEROR",
        title_context="DUKE OF NORMANDY • 1066",
        dest_video=out_video,
        duration=1.0,
        width=360,
        height=640,
        fps=15
    )

    assert res.exists()
    assert res.stat().st_size > 1000


def test_canva_ranked_step_render(tmp_path: Path):
    engine = CanvaTemplateEngine(cache_dir=tmp_path / "canva_cache")
    out_video = tmp_path / "step_test.mp4"

    res = engine.render_ranked_step_video(
        step_number="01",
        headline="THE BATTLE OF HASTINGS",
        description="The decisive clash on Senlac Hill that altered the English monarchy forever.",
        dest_video=out_video,
        duration=1.0,
        width=360,
        height=640,
        fps=15
    )

    assert res.exists()
    assert res.stat().st_size > 1000


def test_canva_breaking_bulletin_render(tmp_path: Path):
    engine = CanvaTemplateEngine(cache_dir=tmp_path / "canva_cache")
    out_video = tmp_path / "bulletin_test.mp4"

    res = engine.render_breaking_bulletin_video(
        headline="CROWN FORFEITED ON SENLAC HILL",
        ticker_text="KING HAROLD FALLEN IN BATTLE • NORMAN CAVALRY BREAKS SHIELD WALL",
        dest_video=out_video,
        duration=1.0,
        width=360,
        height=640,
        fps=15
    )

    assert res.exists()
    assert res.stat().st_size > 1000
