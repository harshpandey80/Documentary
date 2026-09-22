"""
Unit tests for MetaAIAdapter (Browser Automation & Motion Animation).
"""

from pathlib import Path
from docstudio.visual_providers.browser.meta_ai import MetaAIAdapter, DEFAULT_META_PROFILE_DIR
from docstudio.visual_providers.browser import get_browser_provider, WebCreativeVisualProvider


def test_meta_ai_adapter_initialization():
    adapter = MetaAIAdapter(headless=True)
    assert adapter.profile_dir == DEFAULT_META_PROFILE_DIR
    assert adapter.driver is not None
    assert adapter.timeout_seconds == 60


def test_web_creative_visual_provider_registry():
    provider = get_browser_provider("test_provider")
    assert isinstance(provider, WebCreativeVisualProvider)
    assert provider.is_available() is True
