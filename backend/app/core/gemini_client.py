"""
gemini_client.py — Singleton wrapper cho Google GenAI SDK (mới)

Dùng package google-genai (thay thế google-generativeai đã deprecated).
Load GEMINI_API_KEY từ .env qua pydantic-settings.
"""

import logging
from google import genai
from google.genai import types

from app.core.config import settings

logger = logging.getLogger("gemini_client")


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
        logger.info(f"Gemini client khởi tạo thành công (model={settings.GEMINI_MODEL})")

    def generate(self, prompt: str) -> str:
        """Gọi Gemini API và trả về text response."""
        self._ensure_initialized()
        try:
            response = self._client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=settings.GEMINI_TEMPERATURE,
                    max_output_tokens=settings.GEMINI_MAX_TOKENS,
                ),
            )
            return response.text
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            raise


# Singleton instance toàn cục
gemini_client = GeminiClient()
