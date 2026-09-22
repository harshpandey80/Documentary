import pytest
from pathlib import Path
from PIL import Image
from docstudio.map_animation import MapAnimationEngine, KNOWN_GEO_COORDINATES
from docstudio.motion_array_kit import MotionArrayKit


def test_geo_coordinates_lookup():
    engine = MapAnimationEngine()
    lat, lon = engine._lookup_coords("london")
    assert round(lat, 2) == 51.51
    assert round(lon, 2) == -0.13

    # Unknown coordinate returns deterministic valid lat/lon
    alat, alon = engine._lookup_coords("atlantis_fictional_center")
    assert -90 <= alat <= 90
    assert -180 <= alon <= 180


def test_route_animation_render(tmp_path: Path):
    engine = MapAnimationEngine(cache_dir=tmp_path / "map_cache")
    out_video = tmp_path / "route_normandy_hastings.mp4"

    # Fast 1.0s test render at 360x640 for quick CI verification
    res = engine.render_route_animation(
        origin="normandy",
        destination="hastings",
        dest_video=out_video,
        duration=1.0,
        width=360,
        height=640,
        fps=15,
        theme="parchment",
        vehicle_type="ship"
    )

    assert res.exists()
    assert res.stat().st_size > 1000


def test_region_zoom_render(tmp_path: Path):
    engine = MapAnimationEngine(cache_dir=tmp_path / "map_cache")
    out_video = tmp_path / "zoom_london.mp4"

    res = engine.render_region_zoom(
        target_location="london",
        dest_video=out_video,
        duration=1.0,
        width=360,
        height=640,
        fps=15,
        theme="dark_neon"
    )

    assert res.exists()
    assert res.stat().st_size > 1000


def test_motionarray_viewfinder_hud(tmp_path: Path):
    kit = MotionArrayKit(cache_dir=tmp_path / "hud_cache")
    out_video = tmp_path / "viewfinder_hud.mp4"

    res = kit.render_viewfinder_hud(
        dest_video=out_video,
        duration=1.0,
        width=360,
        height=640,
        fps=15,
        classification="RESTRICTED // HISTORICAL ARCHIVE",
        target_name="TEST SPECIMEN"
    )

    assert res.exists()
    assert res.stat().st_size > 1000


def test_motionarray_forensic_callout(tmp_path: Path):
    kit = MotionArrayKit(cache_dir=tmp_path / "callout_cache")
    out_video = tmp_path / "forensic_callout.mp4"

    res = kit.render_forensic_callout(
        target_point=(180, 320),
        title="DECLASSIFIED SEAL",
        subtitle="AUTHENTICATED ARCHIVAL RECORD",
        dest_video=out_video,
        duration=1.0,
        width=360,
        height=640,
        fps=15
    )

    assert res.exists()
    assert res.stat().st_size > 1000
