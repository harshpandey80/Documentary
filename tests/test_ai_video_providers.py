import pytest
from pathlib import Path
from docstudio.ai_video import (
    get_video_provider,
    VideoProviderFactory,
    AIVideoProvider,
    VideoGenerationResult,
)
from docstudio.ai_video.base_provider import get_hardware_profile
from docstudio.ai_video.providers import (
    PollinationsVideoProvider,
    ParallaxCameraProvider,
    LTXVideoProvider,
    ComfyUIVideoProvider,
)


def test_hardware_profile_inspection():
    profile = get_hardware_profile()
    assert "has_gpu" in profile
    assert "vram_gb" in profile
    assert "free_disk_gb" in profile
    assert "can_run_local_diffusion" in profile


def test_ltx_hardware_guard():
    ltx = LTXVideoProvider()
    # On machines without 12GB GPU or LTX_API_URL set, is_available must be False
    # and MUST NOT attempt huge model downloads
    if not ltx.endpoint_url and not get_hardware_profile()["can_run_local_diffusion"]:
        assert ltx.is_available() is False
        res = ltx.generate_video(prompt="Test cockpit view")
        assert res.status == "failed"
        assert "LTX provider not configured" in res.metadata.get("reason", "")


def test_parallax_cpu_provider_available():
    parallax = ParallaxCameraProvider()
    assert parallax.is_available() is True
    assert parallax.name == "parallax_camera"


def test_video_provider_factory_selection():
    p_parallax = VideoProviderFactory.get_provider("parallax")
    assert isinstance(p_parallax, ParallaxCameraProvider)

    p_pollinations = VideoProviderFactory.get_provider("pollinations")
    assert isinstance(p_pollinations, PollinationsVideoProvider)

    p_ltx = VideoProviderFactory.get_provider("ltx")
    assert isinstance(p_ltx, LTXVideoProvider)

    p_auto = VideoProviderFactory.get_provider("auto")
    assert isinstance(p_auto, AIVideoProvider)
