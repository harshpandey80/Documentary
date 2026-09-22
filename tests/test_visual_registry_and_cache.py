"""
tests/test_visual_registry_and_cache.py
=======================================
Step 4, 5, 11, 12: Tests for the centralized VisualTypeRegistry, ProviderResolver,
semantic fallback resolution, cost profiles, and deterministic AssetCacheManager.
"""

import tempfile
from pathlib import Path
from docstudio.remote_creative_director.manifest_schema import (
    ShotDirective,
    VisualPurpose,
    SourceStrategy,
)
from docstudio.remote_creative_director.visual_registry import (
    VisualType,
    TruthCategory,
    CostClass,
    ComputeClass,
    VisualTypeRegistry,
    SUPPORTED_NOW,
    PLANNED,
)
from docstudio.remote_creative_director.provider_registry import (
    ProviderResolver,
    ExecutionProvider,
)
from docstudio.remote_creative_director.cache import AssetCacheManager


def test_visual_type_normalization_and_support():
    assert VisualTypeRegistry.normalize_type("map") == VisualType.MAP
    assert VisualTypeRegistry.normalize_type("CHART") == VisualType.DATA_CHART
    assert VisualTypeRegistry.normalize_type("route_map") == VisualType.MAP_ANIMATION
    assert VisualTypeRegistry.normalize_type("ai_clip") == VisualType.AI_IMAGE_TO_VIDEO
    assert VisualTypeRegistry.is_supported(VisualType.MAP)
    assert VisualTypeRegistry.is_supported(VisualType.DATA_CHART)
    assert VisualTypeRegistry.is_planned(VisualType.ARCHIVAL_FOOTAGE)


def test_semantic_fallback_resolution():
    # Map must fall back strictly to spatial/documentary media, never generic footage
    map_fallbacks = VisualTypeRegistry.resolve_fallback_chain(VisualType.MAP)
    assert VisualType.MAP_ANIMATION in map_fallbacks or VisualType.TIMELINE_DIAGRAM in map_fallbacks
    assert VisualType.AI_VIDEO not in map_fallbacks

    # AI Video falls back to Parallax, then high-res still, then stock
    ai_video_fallbacks = VisualTypeRegistry.resolve_fallback_chain(VisualType.AI_VIDEO)
    assert VisualType.AI_IMAGE_TO_VIDEO in ai_video_fallbacks
    assert VisualType.AI_IMAGE in ai_video_fallbacks


def test_cost_profile():
    cost, compute, est = VisualTypeRegistry.get_cost_profile(VisualType.AI_VIDEO)
    assert cost == CostClass.HIGH
    assert compute == ComputeClass.BROWSER
    assert est > 10.0

    cost_map, compute_map, _ = VisualTypeRegistry.get_cost_profile(VisualType.MAP)
    assert cost_map == CostClass.FREE_PROCEDURAL
    assert compute_map == ComputeClass.LOCAL


def test_provider_resolver():
    with tempfile.TemporaryDirectory() as tmp_dir:
        resolver = ProviderResolver(cache_dir=Path(tmp_dir))
        
        map_shot = ShotDirective(
            shot_id="S_MAP",
            start=0.0,
            end=3.0,
            duration=3.0,
            purpose=VisualPurpose.EXPLAIN_GEOGRAPHY,
            visual_type=VisualType.MAP,
            visual_reason="Route explanation.",
            source_strategy=SourceStrategy.PROCEDURAL_MAP,
        )
        primary, fallbacks = resolver.resolve_providers(map_shot)
        assert primary.name == "map_animation"
        assert len(fallbacks) > 0


def test_asset_cache_manager():
    with tempfile.TemporaryDirectory() as tmp_dir:
        cache_dir = Path(tmp_dir)
        cache_mgr = AssetCacheManager(cache_dir=cache_dir)

        shot = ShotDirective(
            shot_id="S_CACHE",
            start=0.0,
            end=4.0,
            duration=4.0,
            purpose=VisualPurpose.SHOW_STATISTICS,
            visual_type=VisualType.DATA_CHART,
            visual_reason="Chart financial metric.",
            source_strategy=SourceStrategy.PROCEDURAL_CHART,
        )

        fp1 = cache_mgr.compute_fingerprint("Bermuda", shot, 1920, 1080, 30)
        fp2 = cache_mgr.compute_fingerprint("Bermuda", shot, 1920, 1080, 30)
        assert fp1 == fp2  # Deterministic

        # Initially cache miss
        assert cache_mgr.get_cached_asset(fp1) is None
        assert cache_mgr.misses == 1

        # Create dummy valid asset
        dummy_file = cache_dir / "dummy_asset.mp4"
        with open(dummy_file, "wb") as f:
            f.write(b"0" * 20000)

        registered = cache_mgr.register_asset(fp1, dummy_file, "S_CACHE", "DATA_CHART")
        assert registered.exists()

        # Now cache hit
        cached = cache_mgr.get_cached_asset(fp1)
        assert cached is not None
        assert cache_mgr.hits == 1
