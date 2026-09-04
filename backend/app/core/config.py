"""
config.py — Application settings cho Retrieval API

Sử dụng pydantic-settings để load từ environment variables hoặc .env file.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path

# Thư mục gốc dự án (3 cấp trên config.py: core -> app -> backend -> root)
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_ENV_FILE = _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # --- Embedding model ---
    EMBED_MODEL: str = "bkai-foundation-models/vietnamese-bi-encoder"
    # Bắt buộc True với bkai (PhoBERT-based); False nếu dùng BGE-M3
    WORD_SEGMENTATION: bool = True

    # --- Index paths ---
    INDEX_DIR: str = "backend/data/index"

    # --- Retrieval defaults ---
    TOP_K_DEFAULT: int = 5
    # Năm mặc định theo Mục 2.1 đề cương (nếu user không chỉ rõ)
    DEFAULT_ADMISSION_YEAR: int = 2026

    # --- Hybrid fusion weights (dùng cho Weighted Sum mode) ---
    BM25_WEIGHT: float = 0.4
    DENSE_WEIGHT: float = 0.6
    # k cho RRF: final_score = 1 / (k + rank)
    RRF_K: int = 60

    GEMINI_API_KEY: str = "your_gemini_api_key_here"
    GEMINI_MODEL: str = "models/gemini-3.7-flash"
    GEMINI_TEMPERATURE: float = 0.1
    GEMINI_MAX_TOKENS: int = 2048

    @property
    def index_dir_path(self) -> Path:
        return Path(self.INDEX_DIR)


settings = Settings()
