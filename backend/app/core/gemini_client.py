"""
gemini_client.py — Singleton wrapper cho Google GenAI SDK.

Tách lỗi quota/quá tải tạm thời khỏi lỗi cấu hình để API trả phản hồi an toàn,
không làm lộ raw error payload từ nhà cung cấp.
"""

import logging
import random
import time

from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger("gemini_client")


class GeminiTemporarilyUnavailable(RuntimeError):
    """Gemini provider đang quá tải hoặc có lỗi server tạm thời."""


class GeminiQuotaExceeded(RuntimeError):
    """Quota/rate limit Gemini đã hết; người dùng cần chờ hoặc đổi billing/project."""


_TRANSIENT_MARKERS = ("503", "500", "502", "504", "UNAVAILABLE", "INTERNAL")
_QUOTA_MARKERS = ("429", "RESOURCE_EXHAUSTED", "QUOTA EXCEEDED", "RATE LIMIT")


class GeminiClient:
    """Singleton Gemini client — khởi tạo một lần, dùng nhiều lần."""

    _instance: "GeminiClient | None" = None
    _client: genai.Client | None = None

    def __new__(cls) -> "GeminiClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _ensure_initialized(self) -> None:
        if self._client is not None:
            return

        api_key = settings.GEMINI_API_KEY
        if not api_key or api_key == "your_gemini_api_key_here":
            raise RuntimeError(
                "GEMINI_API_KEY chưa được cấu hình. "
                "Vui lòng thêm vào file .env ở thư mục gốc dự án."
            )

        self._client = genai.Client(api_key=api_key)
        logger.info("Gemini client initialized (model=%s)", settings.GEMINI_MODEL)

    @staticmethod
    def _classify_error(error: Exception) -> str | None:
        message = str(error).upper()
        if any(marker in message for marker in _QUOTA_MARKERS):
            return "quota"
        if any(marker in message for marker in _TRANSIENT_MARKERS):
            return "transient"
        return None

    @staticmethod
    def _models_to_try() -> list[str]:
        fallback_models = [
            model.strip()
            for model in settings.GEMINI_FALLBACK_MODELS.split(",")
            if model.strip()
        ]
        return list(dict.fromkeys([settings.GEMINI_MODEL, *fallback_models]))

    def generate(self, prompt: str) -> str:
        """Sinh nội dung; chuyển model khi quota hoặc provider quá tải."""
        self._ensure_initialized()
        max_retries = settings.GEMINI_MAX_RETRIES
        base_delay = settings.GEMINI_RETRY_BASE_DELAY_SECONDS
        last_category: str | None = None

        for model in self._models_to_try():
            for attempt in range(1, max_retries + 1):
                try:
                    response = self._client.models.generate_content(
                        model=model,
                        contents=prompt,
                        config=types.GenerateContentConfig(
                            temperature=settings.GEMINI_TEMPERATURE,
                            max_output_tokens=settings.GEMINI_MAX_TOKENS,
                        ),
                    )
                    if not response.text:
                        raise GeminiTemporarilyUnavailable("Gemini returned an empty response")
                    return response.text
                except (GeminiTemporarilyUnavailable, GeminiQuotaExceeded):
                    raise
                except Exception as error:
                    category = self._classify_error(error)
                    last_category = category
                    if category in {"quota", "transient"} and attempt < max_retries:
                        delay = base_delay * (2 ** (attempt - 1)) + random.uniform(0, 0.75)
                        logger.warning(
                            "Gemini model %s %s; retry %s/%s in %.1fs",
                            model,
                            category,
                            attempt,
                            max_retries,
                            delay,
                        )
                        time.sleep(delay)
                        continue

                    if category in {"quota", "transient"}:
                        logger.warning(
                            "Gemini model %s unavailable (%s); trying next configured model",
                            model,
                            category,
                        )
                        break

                    logger.exception("Unexpected Gemini API error for model %s", model)
                    raise

        if last_category == "quota":
            raise GeminiQuotaExceeded("All configured Gemini models reached quota or rate limit")
        raise GeminiTemporarilyUnavailable("All configured Gemini models are temporarily unavailable")


# Singleton instance toàn cục
gemini_client = GeminiClient()
