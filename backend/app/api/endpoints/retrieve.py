"""
retrieve.py — POST /retrieve endpoint

API contract (đã chốt Tuần 1):
  POST /api/v1/retrieve
  GET  /api/v1/health
"""

import time
import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.retrieval_service import (
    search_bm25,
    search_dense,
    search_hybrid,
)

logger = logging.getLogger("retrieve_endpoint")

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class RetrieveFilters(BaseModel):
    admission_year: Optional[int] = Field(
        default=None,
        description="Năm tuyển sinh (2022-2026). Nếu None, mặc định 2026.",
        example=2026,
    )
    program_type: Optional[str] = Field(
        default=None,
        description="Hệ đào tạo: dai_hoc_chinh_quy | dai_hoc_thuong_xuyen | sau_dai_hoc | lien_ket_quoc_te",
        example="dai_hoc_chinh_quy",
    )


class RetrieveRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Câu hỏi của người dùng")
    top_k: int = Field(default=5, ge=1, le=20, description="Số lượng chunk trả về")
    filters: RetrieveFilters = Field(default_factory=RetrieveFilters)
    mode: str = Field(
        default="hybrid",
        description="Chế độ retrieval: bm25 | dense | hybrid",
        pattern="^(bm25|dense|hybrid)$",
    )
    fusion_method: str = Field(
        default="rrf",
        description="Phương pháp fusion khi mode=hybrid: rrf | weighted",
        pattern="^(rrf|weighted)$",
    )
    alpha: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Trọng số dense khi fusion_method=weighted (default: 0.6)",
    )


class ChunkMetadata(BaseModel):
    admission_year: Optional[int]
    program_type: str
    section_name: str
    source_file: str
    source_urls: List[str]
    extra_urls: List[str]


class RetrievedChunk(BaseModel):
    chunk_id: str
    score: float
    text: str
    metadata: ChunkMetadata


class RetrieveResponse(BaseModel):
    query: str
    results: List[RetrievedChunk]
    retrieval_mode: str
    fusion_method: Optional[str]
    total_results: int
    latency_ms: float
    response_meta: dict = Field(
        default_factory=dict,
        description="Metadata thêm: year_defaulted=True nếu năm bị default sang 2026",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/retrieve", response_model=RetrieveResponse, summary="Truy xuất chunks liên quan")
async def retrieve(request: RetrieveRequest) -> RetrieveResponse:
    """
    Truy xuất các chunks liên quan từ Knowledge Base.

    - **query**: câu hỏi tuyển sinh
    - **filters.admission_year**: năm tuyển sinh (mặc định 2026 nếu không chỉ rõ)
    - **filters.program_type**: hệ đào tạo
    - **mode**: bm25 | dense | hybrid (mặc định hybrid)
    - **fusion_method**: rrf | weighted (mặc định rrf)
    """
    t_start = time.perf_counter()

    filters = {
        "admission_year": request.filters.admission_year,
        "program_type": request.filters.program_type,
    }

    try:
        if request.mode == "bm25":
            results, resp_meta = search_bm25(request.query, request.top_k, filters)
            fm = None
        elif request.mode == "dense":
            results, resp_meta = search_dense(request.query, request.top_k, filters)
            fm = None
        else:  # hybrid
            results, resp_meta = search_hybrid(
                request.query,
                request.top_k,
                filters,
                fusion_method=request.fusion_method,
                alpha=request.alpha,
            )
            fm = request.fusion_method
    except Exception as e:
        logger.error(f"Retrieval error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")

    latency_ms = (time.perf_counter() - t_start) * 1000

    chunks = []
    for r in results:
        chunks.append(RetrievedChunk(
            chunk_id=r.chunk_id,
            score=r.score,
            text=r.text,
            metadata=ChunkMetadata(
                admission_year=r.admission_year,
                program_type=r.program_type,
                section_name=r.section_name,
                source_file=r.source_file,
                source_urls=r.source_urls,
                extra_urls=r.extra_urls,
            ),
        ))

    return RetrieveResponse(
        query=request.query,
        results=chunks,
        retrieval_mode=request.mode,
        fusion_method=fm,
        total_results=len(chunks),
        latency_ms=round(latency_ms, 2),
        response_meta=resp_meta,
    )


@router.get("/health", summary="Health check")
async def health():
    """Kiểm tra trạng thái index đã load chưa."""
    from app.core.index_store import index_store
    return {
        "status": "ok",
        "index_loaded": index_store.is_loaded,
    }
