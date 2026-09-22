import pytest
import base64
from fastapi.testclient import TestClient
from docstudio.server import app, JOBS_DIR
from docstudio.llm_chain import _should_failover, _should_retry

client = TestClient(app)

def test_llm_chain_fast_failover_on_429():
    """Verify that 429 quota/rate limit errors trigger immediate failover without retry sleeping."""
    assert _should_failover(429) is True
    assert _should_retry(429) is False
    assert _should_failover(402) is True
    assert _should_retry(503) is True

def test_extension_status_endpoint():
    """Verify heartbeat status endpoint for Chrome Extension."""
    resp = client.get("/api/extension/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "connected"
    assert data["version"] == "3.0.0"

def test_extension_active_prompts_endpoint():
    """Verify active prompts endpoint returns valid shot list for the extension."""
    resp = client.get("/api/extension/active_prompts")
    assert resp.status_code == 200
    data = resp.json()
    assert "job_id" in data
    assert "shots" in data
    assert isinstance(data["shots"], list)

def test_extension_upload_visual_endpoint(tmp_path):
    """Verify that extension can upload base64 images directly into a job's visuals directory."""
    # Create mock job folder
    test_job_id = "test_job_ext_123"
    job_dir = JOBS_DIR / test_job_id
    job_dir.mkdir(parents=True, exist_ok=True)
    
    # 1x1 transparent PNG as base64
    tiny_png_b64 = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    
    payload = {
        "job_id": test_job_id,
        "shot_id": "test_shot_1",
        "image_base64": tiny_png_b64
    }
    
    resp = client.post("/api/extension/upload_visual", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert data["shot_id"] == "test_shot_1"
    
    saved_file = job_dir / "visuals" / "synth_test_shot_1.jpg"
    assert saved_file.exists()
    assert saved_file.stat().st_size > 0
    
    # Cleanup mock job
    import shutil
    shutil.rmtree(job_dir, ignore_errors=True)


def test_llm_chain_three_tier_priority_cascade():
    """Verify that complete_json follows 1. Gemini -> 2. Groq -> 3. OpenRouter cascade."""
    from unittest.mock import patch
    from docstudio.llm_chain import complete_json, LLMProviderError, LLMChainExhausted

    # 1. Normal state: Gemini is 1st priority and succeeds
    with patch("docstudio.llm_chain._call_gemini", return_value={"provider": "gemini"}) as mock_gemini, \
         patch("docstudio.llm_chain._call_groq", return_value={"provider": "groq"}) as mock_groq, \
         patch("docstudio.llm_chain._call_openrouter", return_value={"provider": "openrouter"}) as mock_openrouter:
        res = complete_json("prompt", "system")
        assert res["provider"] == "gemini"
        assert mock_gemini.call_count == 1
        assert mock_groq.call_count == 0
        assert mock_openrouter.call_count == 0

    # 2. Gemini fails (e.g. 429 quota exhaustion): Fails over immediately to Groq (2nd priority)
    with patch("docstudio.llm_chain._call_gemini", side_effect=LLMProviderError("429 Quota Exhausted")) as mock_gemini, \
         patch("docstudio.llm_chain._call_groq", return_value={"provider": "groq"}) as mock_groq, \
         patch("docstudio.llm_chain._call_openrouter", return_value={"provider": "openrouter"}) as mock_openrouter:
        res = complete_json("prompt", "system")
        assert res["provider"] == "groq"
        assert mock_gemini.call_count == 1
        assert mock_groq.call_count == 1
        assert mock_openrouter.call_count == 0

    # 3. Gemini & Groq both fail: Fails over to OpenRouter (3rd priority)
    with patch("docstudio.llm_chain._call_gemini", side_effect=LLMProviderError("Gemini error")) as mock_gemini, \
         patch("docstudio.llm_chain._call_groq", side_effect=LLMProviderError("Groq error")) as mock_groq, \
         patch("docstudio.llm_chain._call_openrouter", return_value={"provider": "openrouter"}) as mock_openrouter:
        res = complete_json("prompt", "system")
        assert res["provider"] == "openrouter"
        assert mock_gemini.call_count == 1
        assert mock_groq.call_count == 1
        assert mock_openrouter.call_count == 1

    # 4. All fail: raises LLMChainExhausted
    with patch("docstudio.llm_chain._call_gemini", side_effect=LLMProviderError("Gemini error")), \
         patch("docstudio.llm_chain._call_groq", side_effect=LLMProviderError("Groq error")), \
         patch("docstudio.llm_chain._call_openrouter", side_effect=LLMProviderError("OpenRouter error")):
        with pytest.raises(LLMChainExhausted):
            complete_json("prompt", "system")

