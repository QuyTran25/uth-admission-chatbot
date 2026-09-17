"""
chat.py — POST /api/v1/chat endpoint (Bước 3 — Generation Backend)

Luồng xử lý đầy đủ:
  1. year_filter      → phân loại năm (allowed / fallback_warning / refused)
  2. oos_filter       → phát hiện ý định ngoài phạm vi (Hướng C)
  3. retrieve         → tìm top-K chunks liên quan (hybrid weighted)
  4. Gate disabled    → threshold=0.0, luôn proceed (xem gate_config.json)
  5. generator        → gọi Gemini, nhận câu trả lời có [[chunk_id]]
  6. attribution_gate → kiểm chứng chunk_id hợp lệ, tính citation_precision
  7. Trả về ChatResponse

Response behaviors:
  - "answer"            → trả lời + citations
  - "fallback_warning"  → trả lời dữ liệu năm gần nhất + cảnh báo
  - "refused"           → thông báo từ chối rõ ràng, không gọi Gemini
  - "clarify"           → yêu cầu người dùng chỉ rõ năm
"""

import time
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.year_filter import (
    analyze as year_filter_analyze,
    OUT_OF_SCOPE_MESSAGE,
    YEAR_NOT_SUPPORTED_MESSAGE,
)
from app.services.oos_filter import check_oos
from app.services.retrieval_service import retrieve_with_dynamic_routing
from app.services.generator import generate_answer
from app.services.attribution_gate import check_attribution, build_citation_list
from app.core.gemini_client import GeminiQuotaExceeded, GeminiTemporarilyUnavailable

logger = logging.getLogger("chat_endpoint")

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500, description="Câu hỏi của người dùng")
    top_k: int = Field(default=5, ge=1, le=10, description="Số chunks truy xuất")


class CitationItem(BaseModel):
    chunk_id: str
    source_file: str
    section_name: str
    admission_year: Optional[int]
    source_urls: list[str]


class ChatResponse(BaseModel):
    behavior: str           # "answer" | "fallback_warning" | "refused" | "clarify"
    answer: str             # Câu trả lời văn bản
    citations: list[CitationItem]
    citation_precision: float
    refused_reason: Optional[str] = None   # Lý do từ chối nếu behavior="refused"
    oos_categories: list[str] = []         # Nhóm OOS bị vi phạm (nếu có)
    latency_ms: float
    year_used: Optional[int] = None        # Năm đã dùng để lọc
    fallback_warning_text: Optional[str] = None  # Text cảnh báo năm nếu is_fallback


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.post("/chat", response_model=ChatResponse, summary="Chat tuyển sinh (end-to-end)")
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Endpoint trả lời câu hỏi tuyển sinh end-to-end:
    year_filter → oos_filter → retrieve → generate (Gemini) → attribution_gate
    """
    t_start = time.perf_counter()
    query = request.query.strip()

    # -------------------------------------------------------------------
    # Lớp 1: Year Filter
    # -------------------------------------------------------------------
    yr = year_filter_analyze(query)
    logger.info(f"[chat] year_filter: status={yr.status}, year={yr.filter_year}")

    if yr.status == "refused":
        latency = (time.perf_counter() - t_start) * 1000
        return ChatResponse(
            behavior="refused",
            answer=yr.message or YEAR_NOT_SUPPORTED_MESSAGE,
            citations=[],
            citation_precision=1.0,
            refused_reason="year_not_supported",
            latency_ms=round(latency, 2),
            year_used=yr.filter_year,
        )

    is_fallback = yr.warning is not None

    # -------------------------------------------------------------------
    # Lớp 2: OOS Filter (Hướng C — Regex Intent Filter)
    # -------------------------------------------------------------------
    is_oos, oos_categories = check_oos(
        query,
        year_filter_status=yr.status,
        year_filter_doc_type=yr.document_type,
    )
    logger.info(f"[chat] oos_filter: is_oos={is_oos}, cats={oos_categories}")

    if is_oos:
        latency = (time.perf_counter() - t_start) * 1000
        return ChatResponse(
            behavior="refused",
            answer=OUT_OF_SCOPE_MESSAGE,
            citations=[],
            citation_precision=1.0,
            refused_reason="out_of_scope",
            oos_categories=oos_categories,
            latency_ms=round(latency, 2),
            year_used=yr.filter_year,
        )

    # -------------------------------------------------------------------
    # Retrieval — Hybrid (BM25 + Dense)
    # -------------------------------------------------------------------
    try:
        chunks, _ = retrieve_with_dynamic_routing(
            query=query,
            filter_year=yr.filter_year,
            top_k=request.top_k,
        )
    except Exception as e:
        logger.error(f"[chat] Retrieval failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Retrieval failed: {str(e)}")

    logger.info(f"[chat] Retrieved {len(chunks)} chunks (year={yr.filter_year})")

    # -------------------------------------------------------------------
    # Generation — Gọi Gemini API
    # -------------------------------------------------------------------
    try:
        gen_result = generate_answer(
            query=query,
            chunks=chunks,
            filter_year=yr.filter_year,
            is_fallback=is_fallback,
        )
    except GeminiQuotaExceeded:
        logger.warning("[chat] Gemini quota/rate limit exhausted")
        raise HTTPException(
            status_code=429,
            detail="Hạn mức Gemini API đã hết hoặc đang bị giới hạn. Vui lòng thử lại sau ít phút, kiểm tra quota của đúng Google Cloud project, hoặc bật billing.",
        )
    except GeminiTemporarilyUnavailable:
        logger.warning("[chat] Gemini temporarily unavailable")
        raise HTTPException(
            status_code=503,
            detail="Dịch vụ AI đang quá tải tạm thời. Vui lòng thử lại sau ít phút.",
        )
    except Exception:
        logger.exception("[chat] Generation failed")
        raise HTTPException(
            status_code=500,
            detail="Dịch vụ tạo câu trả lời gặp lỗi nội bộ. Vui lòng thử lại sau.",
        )

    # Nếu Gemini tự phát hiện câu hỏi ngoài phạm vi
    if gen_result.is_refused:
        latency = (time.perf_counter() - t_start) * 1000
        return ChatResponse(
            behavior="refused",
            answer=gen_result.answer_text,
            citations=[],
            citation_precision=1.0,
            refused_reason="llm_refused",
            latency_ms=round(latency, 2),
            year_used=yr.filter_year,
        )

    # -------------------------------------------------------------------
    # Attribution Gate — Kiểm chứng chunk_id
    # -------------------------------------------------------------------
    attr_result = check_attribution(
        cited_ids=gen_result.cited_ids,
        retrieved_chunks=chunks,
        is_refused=gen_result.is_refused,
    )

    logger.info(
        f"[chat] attribution: passed={attr_result.passed}, "
        f"precision={attr_result.citation_precision}, "
        f"failed={attr_result.failed_citations}"
    )

    # Nếu attribution gate fail → câu trả lời không đáng tin cậy
    if not attr_result.passed:
        latency = (time.perf_counter() - t_start) * 1000
        return ChatResponse(
            behavior="refused",
            answer=(
                "Mình không tìm được thông tin đủ tin cậy để trả lời câu hỏi này. "
                "Bạn có thể liên hệ trực tiếp phòng tuyển sinh UTH để được hỗ trợ chính xác hơn."
            ),
            citations=[],
            citation_precision=attr_result.citation_precision,
            refused_reason="attribution_gate_failed",
            latency_ms=round(latency, 2),
            year_used=yr.filter_year,
        )

    # -------------------------------------------------------------------
    # Xây dựng citations và trả về kết quả
    # -------------------------------------------------------------------
    citations_raw = build_citation_list(gen_result.cited_ids, chunks)
    citations = [CitationItem(**c) for c in citations_raw]

    behavior = "fallback_warning" if is_fallback else "answer"
    latency = (time.perf_counter() - t_start) * 1000

    return ChatResponse(
        behavior=behavior,
        answer=gen_result.answer_text,
        citations=citations,
        citation_precision=attr_result.citation_precision,
        latency_ms=round(latency, 2),
        year_used=yr.filter_year,
        fallback_warning_text=yr.warning if is_fallback else None,
    )
