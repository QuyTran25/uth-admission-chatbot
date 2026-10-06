"""
test_gemini_client.py — Unit test cho Gemini Client (CD3 / B1)

Kiểm tra:
  - Khi gặp 429 quota, client chuyển ngay sang model kế tiếp mà không loop retry delay.
  - Khi tất cả model gặp quota, raise GeminiQuotaExceeded.
"""

import time
from unittest.mock import MagicMock, patch
import pytest

from app.core.gemini_client import (
    GeminiClient,
    GeminiQuotaExceeded,
    GeminiTemporarilyUnavailable,
)


def test_gemini_429_quota_switches_model_immediately():
    """Lỗi 429 quota phải lập tức switch sang model tiếp theo trong thời gian rất ngắn (< 0.2s)."""
    client = GeminiClient()
    client._client = MagicMock()

    calls = []

    def mock_generate_content(model, contents, config):
        calls.append(model)
        if model == "models/gemini-3.6-flash":
            # Ném lỗi 429
            raise Exception("429 Resource Exhausted: Quota exceeded for project")
        # Fallback model thành công
        resp = MagicMock()
        resp.text = "Thành công từ fallback model"
        return resp

    client._client.models.generate_content.side_effect = mock_generate_content

    start_time = time.perf_counter()
    with patch("app.core.gemini_client.settings.GEMINI_MODEL", "models/gemini-3.6-flash"), \
         patch("app.core.gemini_client.settings.GEMINI_FALLBACK_MODELS", "models/gemini-3.5-flash"):
        result = client.generate("Xin chào")
    elapsed = time.perf_counter() - start_time

    # Phải thành công từ fallback
    assert result == "Thành công từ fallback model"
    # Gọi model chính đúng 1 lần (không retry sleep loop) và chuyển sang fallback ngay
    assert calls == ["models/gemini-3.6-flash", "models/gemini-3.5-flash"]
    # Thời gian chạy phải < 0.3s (không bị delay backoff 2s+)
    assert elapsed < 0.3


def test_gemini_all_models_quota_raises_quota_exceeded():
    """Khi mọi model đều trả về quota 429, client ném GeminiQuotaExceeded."""
    client = GeminiClient()
    client._client = MagicMock()

    client._client.models.generate_content.side_effect = Exception("429 Quota Exceeded")

    with patch("app.core.gemini_client.settings.GEMINI_MODEL", "model-1"), \
         patch("app.core.gemini_client.settings.GEMINI_FALLBACK_MODELS", "model-2"):
        with pytest.raises(GeminiQuotaExceeded):
            client.generate("Xin chào")
