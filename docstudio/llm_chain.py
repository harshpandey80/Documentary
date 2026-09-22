"""
docstudio/llm_chain.py
======================
Phase 4 — Resilient LLM Provider Chain

Cascade order:
  1. Gemini (gemini-3.8-flash)       — 1st priority: fastest, high context, official API
  2. Groq (openai/gpt-oss-120b)      — 2nd priority: ultra-fast LPU inference, structured JSON
  3. OpenRouter (deepseek/deepseek-v4-flash) — 3rd priority: broad model diversity fallback
  4. Halt with clear error message    — never fake a script

Rules enforced:
  - Failover triggers: 401, 402, 403, 404, 429 (immediate failover without hanging)
  - Exponential backoff on server errors: 500, 502, 503, 504
  - Zero synthetic scripts: if all providers fail, raise LLMChainExhausted
  - No topic-specific knowledge in this module
  - Thread-safe: each call is stateless
"""

from __future__ import annotations

import json
import os
import re
import time
from typing import Any

from dotenv import load_dotenv

load_dotenv()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
OPENROUTER_API_KEY: str = os.getenv("OPENROUTER_API_KEY", "")

GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-3.8-flash")
GROQ_MODEL: str = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
OPENROUTER_MODEL: str = os.getenv("OPENROUTER_MODEL", "deepseek/deepseek-v4-flash")

_MAX_RETRIES: int = 5
_BACKOFF_BASE: float = 2.0  # seconds; doubles each retry


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------
class LLMChainExhausted(RuntimeError):
    """Raised when every provider in the chain has failed."""


class LLMProviderError(RuntimeError):
    """Raised for a single-provider failure (retryable or not)."""


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _strip_code_fence(text: str) -> str:
    """Remove markdown ```json ... ``` fences if present."""
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _parse_json_response(raw: str) -> dict:
    """Parse JSON; raise LLMProviderError with context on failure."""
    try:
        return json.loads(_strip_code_fence(raw))
    except json.JSONDecodeError as exc:
        snippet = raw[:200].replace("\n", " ")
        raise LLMProviderError(
            f"JSON parse failed: {exc}. Response snippet: {snippet!r}"
        ) from exc


def _should_retry(status_code: int) -> bool:
    return status_code in (500, 502, 503, 504)


def _should_failover(status_code: int) -> bool:
    # 429 = Rate limited or quota exhausted -> failover immediately without sleeping
    return status_code in (402, 401, 403, 404, 429)


# ---------------------------------------------------------------------------
# Provider: Gemini
# ---------------------------------------------------------------------------

def _call_gemini(prompt: str, system: str, temperature: float = 0.7) -> dict:
    """
    Call Gemini via google-genai SDK.
    Returns parsed dict or raises LLMProviderError.
    """
    if not GEMINI_API_KEY:
        raise LLMProviderError("GEMINI_API_KEY not set in .env")

    try:
        from google import genai
        from google.genai import types as genai_types
        from google.genai import errors as genai_errors
    except ImportError as exc:
        raise LLMProviderError(
            f"google-genai package not installed: {exc}"
        ) from exc

    client = genai.Client(api_key=GEMINI_API_KEY)

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            # NOTE: Do NOT set response_mime_type="application/json" here —
            # it conflicts with automatic function calling (AFC) on some models
            # and causes 503s. We parse JSON from plain text output instead.
            response = client.models.generate_content(
                model=GEMINI_MODEL,
                contents=prompt,
                config=genai_types.GenerateContentConfig(
                    system_instruction=system,
                    temperature=temperature,
                    max_output_tokens=8192,
                ),
            )
            raw = (response.text or "").strip()
            if not raw:
                raise LLMProviderError("Gemini returned empty response text.")
            return _parse_json_response(raw)

        except genai_errors.ServerError as exc:
            # 503 UNAVAILABLE — retryable
            code = getattr(exc, "status_code", 503)
            wait = _BACKOFF_BASE * (2 ** (attempt - 1))
            print(
                f"[LLMChain][Gemini] Attempt {attempt}/{_MAX_RETRIES} "
                f"ServerError {code} (high demand); waiting {wait:.1f}s ...",
                flush=True,
            )
            if attempt < _MAX_RETRIES:
                time.sleep(wait)
                continue
            raise LLMProviderError(f"Gemini ServerError {code} after {_MAX_RETRIES} retries.") from exc

        except genai_errors.ClientError as exc:
            code = getattr(exc, "code", None) or getattr(exc, "status_code", 0) or 0
            print(
                f"[LLMChain][Gemini] Attempt {attempt}/{_MAX_RETRIES} "
                f"ClientError {code}: {exc}",
                flush=True,
            )
            if _should_failover(code):
                raise LLMProviderError(
                    f"Gemini fatal error {code} -- failover to next provider."
                ) from exc
            if _should_retry(code) and attempt < _MAX_RETRIES:
                wait = _BACKOFF_BASE * (2 ** (attempt - 1))
                print(f"[LLMChain][Gemini] Rate-limited; waiting {wait:.1f}s ...", flush=True)
                time.sleep(wait)
                continue
            raise LLMProviderError(str(exc)) from exc

        except (ConnectionError, TimeoutError, OSError) as exc:
            print(
                f"[LLMChain][Gemini] Attempt {attempt}/{_MAX_RETRIES} "
                f"network error: {exc}",
                flush=True,
            )
            if attempt < _MAX_RETRIES:
                time.sleep(_BACKOFF_BASE * (2 ** (attempt - 1)))
                continue
            raise LLMProviderError(f"Gemini network failure: {exc}") from exc

    raise LLMProviderError("Gemini exhausted all retries.")


# ---------------------------------------------------------------------------
# Provider: Groq (2nd Priority - Ultra-fast LPU Inference)
# ---------------------------------------------------------------------------

def _call_groq(prompt: str, system: str, temperature: float = 0.7) -> dict:
    """
    Call Groq via OpenAI-compatible REST endpoint.
    Returns parsed dict or raises LLMProviderError.
    """
    if not GROQ_API_KEY:
        raise LLMProviderError("GROQ_API_KEY not set in .env")

    try:
        import requests
    except ImportError as exc:
        raise LLMProviderError(f"requests package not installed: {exc}") from exc

    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": temperature,
        "max_tokens": 8192,
    }

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=60,
            )

            if _should_failover(resp.status_code):
                raise LLMProviderError(
                    f"Groq fatal {resp.status_code}: {resp.text[:300]}"
                )
            if _should_retry(resp.status_code):
                print(
                    f"[LLMChain][Groq] Attempt {attempt}/{_MAX_RETRIES} "
                    f"HTTP {resp.status_code}; retrying …",
                    flush=True,
                )
                if attempt < _MAX_RETRIES:
                    time.sleep(_BACKOFF_BASE * (2 ** (attempt - 1)))
                    continue
                raise LLMProviderError(
                    f"Groq HTTP {resp.status_code} after {_MAX_RETRIES} retries."
                )

            resp.raise_for_status()
            data = resp.json()
            raw = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not raw:
                raise LLMProviderError("Groq returned empty content.")
            return _parse_json_response(raw)

        except requests.exceptions.Timeout as exc:
            print(f"[LLMChain][Groq] Attempt {attempt} timeout.", flush=True)
            if attempt < _MAX_RETRIES:
                time.sleep(_BACKOFF_BASE * (2 ** (attempt - 1)))
                continue
            raise LLMProviderError("Groq timed out.") from exc

        except requests.exceptions.ConnectionError as exc:
            print(f"[LLMChain][Groq] Attempt {attempt} connection error.", flush=True)
            if attempt < _MAX_RETRIES:
                time.sleep(_BACKOFF_BASE * (2 ** (attempt - 1)))
                continue
            raise LLMProviderError(f"Groq connection error: {exc}") from exc

    raise LLMProviderError("Groq exhausted all retries.")


# ---------------------------------------------------------------------------
# Provider: OpenRouter (3rd Priority - Broad Model Fallback)
# ---------------------------------------------------------------------------

def _call_openrouter(prompt: str, system: str, temperature: float = 0.7) -> dict:
    """
    Call OpenRouter via REST.
    Returns parsed dict or raises LLMProviderError.
    """
    if not OPENROUTER_API_KEY:
        raise LLMProviderError("OPENROUTER_API_KEY not set in .env")

    try:
        import requests
    except ImportError as exc:
        raise LLMProviderError(f"requests package not installed: {exc}") from exc

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/docstudio",
        "X-Title": "DocStudio Documentary Engine",
    }
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": prompt},
        ],
        "response_format": {"type": "json_object"},
        "temperature": temperature,
        "max_tokens": 4096,
    }

    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            resp = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=180,
            )

            if _should_failover(resp.status_code):
                raise LLMProviderError(
                    f"OpenRouter fatal {resp.status_code}: {resp.text[:300]}"
                )
            if _should_retry(resp.status_code):
                print(
                    f"[LLMChain][OpenRouter] Attempt {attempt}/{_MAX_RETRIES} "
                    f"HTTP {resp.status_code}; retrying …",
                    flush=True,
                )
                if attempt < _MAX_RETRIES:
                    time.sleep(_BACKOFF_BASE * (2 ** (attempt - 1)))
                    continue
                raise LLMProviderError(
                    f"OpenRouter HTTP {resp.status_code} after {_MAX_RETRIES} retries."
                )

            resp.raise_for_status()
            data = resp.json()
            raw = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            if not raw:
                raise LLMProviderError("OpenRouter returned empty content.")
            return _parse_json_response(raw)

        except requests.exceptions.Timeout as exc:
            print(f"[LLMChain][OpenRouter] Attempt {attempt} timeout.", flush=True)
            if attempt < _MAX_RETRIES:
                time.sleep(_BACKOFF_BASE * (2 ** (attempt - 1)))
                continue
            raise LLMProviderError("OpenRouter timed out.") from exc

        except requests.exceptions.ConnectionError as exc:
            print(f"[LLMChain][OpenRouter] Attempt {attempt} connection error.", flush=True)
            if attempt < _MAX_RETRIES:
                time.sleep(_BACKOFF_BASE * (2 ** (attempt - 1)))
                continue
            raise LLMProviderError(f"OpenRouter connection error: {exc}") from exc

    raise LLMProviderError("OpenRouter exhausted all retries.")


# ---------------------------------------------------------------------------
# Public API: complete_json()
# ---------------------------------------------------------------------------

def complete_json(
    prompt: str,
    system: str,
    temperature: float = 0.7,
    provider_override: str | None = None,
) -> dict:
    """
    Request a JSON-structured completion from the best available LLM.

    Cascade:
      1. Gemini (1st priority: if GEMINI_API_KEY set and not overridden)
      2. Groq (2nd priority: if GROQ_API_KEY set and not overridden)
      3. OpenRouter (3rd priority: if OPENROUTER_API_KEY set)
      4. Raises LLMChainExhausted

    Args:
        prompt:            User-facing content prompt.
        system:            System instruction string.
        temperature:       Sampling temperature (0.0–1.0).
        provider_override: Force a specific provider ("gemini" | "groq" | "openrouter").

    Returns:
        Parsed dict from the LLM's JSON response.

    Raises:
        LLMChainExhausted: If every configured provider fails.
    """
    providers_tried: list[str] = []
    errors: list[str] = []

    # --- Determine ordered provider list ---
    # Priority default: 1. Gemini, 2. Groq, 3. OpenRouter
    default_order = ["gemini", "groq", "openrouter"]

    if provider_override:
        p_over = provider_override.strip().lower()
        candidate_order = [p_over] + [p for p in default_order if p != p_over]
    else:
        primary_pref = os.getenv("DOCSTUDIO_LLM_PROVIDER", "gemini").strip().lower()
        if primary_pref in default_order:
            candidate_order = [primary_pref] + [p for p in default_order if p != primary_pref]
        else:
            candidate_order = default_order

    ordered = []
    for p in candidate_order:
        if p == "gemini" and GEMINI_API_KEY:
            ordered.append("gemini")
        elif p == "groq" and GROQ_API_KEY:
            ordered.append("groq")
        elif p == "openrouter" and OPENROUTER_API_KEY:
            ordered.append("openrouter")

    if not ordered:
        raise LLMChainExhausted(
            "No LLM providers configured. "
            "Set GEMINI_API_KEY, GROQ_API_KEY, or OPENROUTER_API_KEY in .env."
        )

    for provider in ordered:
        providers_tried.append(provider)
        try:
            if provider == "gemini":
                print(f"[LLMChain] -> Trying Gemini ({GEMINI_MODEL}) ...", flush=True)
                result = _call_gemini(prompt, system, temperature)
                print("[LLMChain] OK Gemini succeeded.", flush=True)
                return result

            elif provider == "groq":
                print(f"[LLMChain] -> Trying Groq ({GROQ_MODEL}) ...", flush=True)
                result = _call_groq(prompt, system, temperature)
                print("[LLMChain] OK Groq succeeded.", flush=True)
                return result

            elif provider == "openrouter":
                print(f"[LLMChain] -> Trying OpenRouter ({OPENROUTER_MODEL}) ...", flush=True)
                result = _call_openrouter(prompt, system, temperature)
                print("[LLMChain] OK OpenRouter succeeded.", flush=True)
                return result

        except LLMProviderError as exc:
            msg = f"[{provider}] {exc}"
            errors.append(msg)
            print(f"[LLMChain] FAIL {msg}", flush=True)
            # Continue to next provider in the cascade

    # All providers exhausted
    error_summary = "\n  ".join(errors)
    raise LLMChainExhausted(
        f"All LLM providers failed. Tried: {providers_tried}\n\n"
        f"Errors:\n  {error_summary}\n\n"
        "Action required: check API keys in .env, verify network connectivity, "
        "or run with --allow-procedural-fallback to use the structured engine."
    )


# ---------------------------------------------------------------------------
# Smoke-test (run directly: uv run python -m docstudio.llm_chain)
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    SMOKE_SYSTEM = "You output only valid JSON."
    SMOKE_PROMPT = (
        'Return a JSON object with key "status" set to "chain_ok" '
        'and key "provider" set to whichever provider you are.'
    )
    print("[LLMChain] Running smoke test ...")
    try:
        result = complete_json(SMOKE_PROMPT, SMOKE_SYSTEM, temperature=0.0)
        print(f"[LLMChain] Smoke test PASSED: {result}")
    except LLMChainExhausted as exc:
        print(f"[LLMChain] Smoke test FAILED: {exc}")
        raise SystemExit(1)
