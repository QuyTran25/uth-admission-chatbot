"""
mock_retriever.py — Mock Retrieval API (5 kịch bản)

Hỗ trợ phát triển Generation/Frontend độc lập mà không cần
Retrieval API thật. Sử dụng header X-Mock-Scenario để chọn kịch bản.

Kịch bản:
  success       — HTTP 200 + chunks mẫu 2025/2026
  fallback      — HTTP 200 + warning cảnh báo năm
  clarification — HTTP 200 + options chọn năm
  refused       — HTTP 200 + OUT_OF_SCOPE + message chuẩn
  error         — HTTP 500 (giả lập crash)

Đăng ký vào main.py:
  from app.api.endpoints.mock_retriever import router as mock_router
  app.include_router(mock_router, prefix="/api/v1/mock", tags=["mock-retrieval"])
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("mock_retriever")

router = APIRouter()

# ---------------------------------------------------------------------------
# Shared constants (giữ đồng bộ với API contract README Mục 3.1)
# ---------------------------------------------------------------------------

_OUT_OF_SCOPE_MESSAGE = (
    "Hiện tại mình chưa có thông tin về câu hỏi này. "
    "Để hiểu rõ hơn, bạn vui lòng truy cập trang web "
    "https://tuyensinh.ut.edu.vn/ hoặc liên hệ:\n"
    "☎ 028 3512 8986 – 028 3512 0766\n"
    "📱 0832 488 288\n"
    "✉ Email: tuyensinh@ut.edu.vn\n"
    "Zalo OA: Tuyển Sinh Đại học GTVT TP HCM\n"
    "Fanpage: facebook.com/tuyensinhuth"
)

# ---------------------------------------------------------------------------
# Sample data — chunks mẫu theo API contract (README Mục 4.1)
# ---------------------------------------------------------------------------

_SAMPLE_CHUNKS_2026 = [
    {
        "chunk_id": "2026_diem-chuan_dai-hoc-chinh-quy_t000_r062",
        "score": 0.912,
        "text": (
            "Ngành Công nghệ thông tin – chương trình tiên tiến (mã UTHUIT05A). "
            "Điểm chuẩn năm 2026: 720 điểm."
        ),
        "metadata": {
            "admission_year": 2026,
            "program_type": "dai_hoc_chinh_quy",
            "section_name": "Điểm chuẩn các ngành",
            "source_file": "dai_hoc_chinh_quy_2026_diem-chuan_dai-hoc-chinh-quy_chunks.jsonl",
            "source_urls": ["https://tuyensinh.ut.edu.vn/dai-hoc-chinh-quy/"],
            "extra_urls": [],
            "chunk_type": "table_row",
            "headers": ["Ngành", "Mã", "Điểm chuẩn"],
            "values": ["Công nghệ thông tin", "UTHUIT05A", "720"],
        },
    },
    {
        "chunk_id": "2026_thong-tin-tuyen-sinh_dai-hoc-chinh-quy_txt_s013",
        "score": 0.874,
        "text": (
            "Học phí hệ Đại học chính quy khóa 2026 tính theo tín chỉ: "
            "Chương trình chuẩn: 515.000 VNĐ/tín chỉ. "
            "Chương trình tiên tiến: 1.120.000 VNĐ/tín chỉ."
        ),
        "metadata": {
            "admission_year": 2026,
            "program_type": "dai_hoc_chinh_quy",
            "section_name": "Học phí",
            "source_file": "dai_hoc_chinh_quy_2026_thong-tin-tuyen-sinh_dai-hoc-chinh-quy_chunks.jsonl",
            "source_urls": ["https://tuyensinh.ut.edu.vn/dai-hoc-chinh-quy/"],
            "extra_urls": [],
            "chunk_type": "free_text",
            "headers": [],
            "values": [],
        },
    },
]

_SAMPLE_CHUNKS_2025 = [
    {
        "chunk_id": "2025_diem-chuan_dai-hoc-chinh-quy_t000_r001",
        "score": 0.888,
        "text": (
            "Ngành Khoa học dữ liệu và AI – chương trình tiên tiến. "
            "Điểm chuẩn năm 2025 (xét kết hợp): 999 điểm."
        ),
        "metadata": {
            "admission_year": 2025,
            "program_type": "dai_hoc_chinh_quy",
            "section_name": "Điểm chuẩn các ngành",
            "source_file": "dai_hoc_chinh_quy_2025_diem-chuan_dai-hoc-chinh-quy_chunks.jsonl",
            "source_urls": ["https://tuyensinh.ut.edu.vn/dai-hoc-chinh-quy/"],
            "extra_urls": [],
            "chunk_type": "table_row",
            "headers": ["Ngành", "Điểm chuẩn"],
            "values": ["Khoa học dữ liệu và AI", "999"],
        },
    },
]

# ---------------------------------------------------------------------------
# Request / Response schemas (khớp API contract README Mục 3.1)
# ---------------------------------------------------------------------------

class MockRetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Câu hỏi của người dùng")
    top_k: int = Field(default=5, ge=1, le=20)
    filter_year: Optional[int] = Field(default=None)


class MockRetrieveResponse(BaseModel):
    status: str
    code: Optional[str] = None
    message: Optional[str] = None
    options: List[int] = Field(default_factory=list)
    warning: Optional[str] = None
    chunks: List[dict] = Field(default_factory=list)
    debug: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post(
    "/retrieve",
    response_model=MockRetrieveResponse,
    summary="Mock Retrieval API (5 kịch bản)",
)
async def mock_retrieve(
    request: MockRetrieveRequest,
    x_mock_scenario: str = Header(
        default="success",
        alias="X-Mock-Scenario",
        description="Kịch bản: success | fallback | clarification | refused | error",
    ),
) -> MockRetrieveResponse:
    """
    Mock endpoint trả về dữ liệu giả lập theo kịch bản chỉ định.

    Dùng header **X-Mock-Scenario** để chọn kịch bản:
    - `success` — trả về chunks hợp lệ năm 2026
    - `fallback` — trả về chunks năm 2025 kèm warning
    - `clarification` — yêu cầu người dùng chọn năm
    - `refused` — từ chối với OUT_OF_SCOPE
    - `error` — giả lập lỗi hệ thống HTTP 500
    """
    scenario = x_mock_scenario.lower().strip()
    logger.info(f"mock_retrieve: scenario={scenario}, query='{request.query[:60]}'")

    # ------------------------------------------------------------------
    # Kịch bản 5: error — HTTP 500
    # ------------------------------------------------------------------
    if scenario == "error":
        raise HTTPException(
            status_code=500,
            detail="[MOCK] Giả lập lỗi hệ thống: kết nối index thất bại.",
        )

    # ------------------------------------------------------------------
    # Kịch bản 4: refused — OUT_OF_SCOPE
    # ------------------------------------------------------------------
    if scenario == "refused":
        return MockRetrieveResponse(
            status="refused",
            code="OUT_OF_SCOPE",
            message=_OUT_OF_SCOPE_MESSAGE,
            chunks=[],
            debug={"refusal_source": "year_filter_keyword", "mock": True},
        )

    # ------------------------------------------------------------------
    # Kịch bản 3: clarification — hỏi lại năm (chỉ cutoff_score)
    # ------------------------------------------------------------------
    if scenario == "clarification":
        return MockRetrieveResponse(
            status="clarification_needed",
            code="YEAR_CLARIFICATION_REQUIRED",
            message="Vui lòng chọn năm tuyển sinh bạn muốn tra cứu điểm chuẩn:",
            options=[2026, 2025, 2024, 2023, 2022],
            chunks=[],
            debug={"mock": True},
        )

    # ------------------------------------------------------------------
    # Kịch bản 2: fallback — chunks năm 2025 + warning
    # ------------------------------------------------------------------
    if scenario == "fallback":
        return MockRetrieveResponse(
            status="success",
            warning=(
                "Lưu ý: Điểm chuẩn năm 2026 chưa được công bố. "
                "Thông tin dưới đây là điểm chuẩn năm 2025 để tham khảo. "
                "Từ năm 2025, trường đã thay đổi cách tính điểm chuẩn."
            ),
            chunks=_SAMPLE_CHUNKS_2025,
            debug={
                "filter_year": 2025,
                "retrieval_mode": "hybrid",
                "fusion_method": "weighted",
                "alpha": 0.4,
                "mock": True,
            },
        )

    # ------------------------------------------------------------------
    # Kịch bản 1: success (default) — chunks năm 2026
    # ------------------------------------------------------------------
    chunks = _SAMPLE_CHUNKS_2026[: request.top_k]
    return MockRetrieveResponse(
        status="success",
        chunks=chunks,
        debug={
            "filter_year": request.filter_year or 2026,
            "retrieval_mode": "hybrid",
            "fusion_method": "weighted",
            "alpha": 0.4,
            "top_k": request.top_k,
            "mock": True,
        },
    )


@router.get("/health", summary="Mock health check")
async def mock_health():
    """Kiểm tra mock endpoint đang hoạt động."""
    return {"status": "ok", "mock": True, "scenarios": ["success", "fallback", "clarification", "refused", "error"]}
