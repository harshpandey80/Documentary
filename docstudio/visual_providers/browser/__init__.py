"""
DocStudio Browser Visual Provider Module.
Exports BrowserVisualProvider, WebCreativeVisualProvider, and provider factory.
"""

from docstudio.visual_providers.browser.base_provider import (
    BrowserVisualProvider,
    BrowserGenerationResponse,
)
from docstudio.visual_providers.browser.queue import (
    BrowserGenerationQueue,
    QueueTask,
    TaskState,
)
from docstudio.visual_providers.browser.web_generation_provider import (
    WebCreativeVisualProvider,
)


from docstudio.visual_providers.browser.driver import BrowserAutomationDriver
from docstudio.visual_providers.browser.google_flow import GoogleFlowAdapter
from docstudio.visual_providers.browser.meta_ai import MetaAIAdapter


_DEFAULT_PROVIDER: WebCreativeVisualProvider | None = None


def get_browser_provider(name: str = "browser_flow") -> BrowserVisualProvider:
    global _DEFAULT_PROVIDER
    if _DEFAULT_PROVIDER is None:
        _DEFAULT_PROVIDER = WebCreativeVisualProvider(name=name)
    return _DEFAULT_PROVIDER


__all__ = [
    "BrowserVisualProvider",
    "BrowserGenerationResponse",
    "BrowserGenerationQueue",
    "QueueTask",
    "TaskState",
    "WebCreativeVisualProvider",
    "BrowserAutomationDriver",
    "GoogleFlowAdapter",
    "MetaAIAdapter",
    "get_browser_provider",
]
