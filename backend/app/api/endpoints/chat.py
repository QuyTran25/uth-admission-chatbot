"""
chat.py — POST /api/v1/chat endpoint (Bước 3 — Generation Backend)

Luồng xử lý đầy đủ:
  1. decide_query (SSoT):
     - Lớp 1: year_filter      → phân loại năm (allowed / fallback_warning / refused / clarify)
     - Lớp 2: oos_filter       → phát hiện ý định ngoài phạm vi (Hướng C)
     - Lớp 3: retrieve         → tìm top-K chunks liên quan (hybrid weighted) + Gate
  2. generator        → gọi Gemini (asyncio.to_thread), nhận câu trả lời có [[chunk_id]]
  3. attribution_gate → kiểm chứng chunk_id hợp lệ, kiểm số liệu, tính citation_precision
  4. Trả về ChatResponse

Response behaviors:
  - "answer"            → trả lời + citations
  - "fallback_warning"  → trả lời dữ liệu năm gần nhất + cảnh báo
  - "refused"           → thông báo từ chối rõ ràng, không gọi Gemini
  - "clarify"           → yêu cầu người dùng chỉ rõ năm
"""

import asyncio
import time
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.services.pipeline_decision import decide_query
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
    citation_precision: Optional[float] = None
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
    decide_query (year_filter → oos_filter → retrieval + gate) → generate (Gemini) → attribution_gate
    """
    t_start = time.perf_counter()
    query = request.query.strip()

    # Phân định tiền sinh (Pre-generation 3-layer decision, chạy trong thread pool để non-blocking)
    try:
        decision = await asyncio.to_thread(decide_query, query=query, top_k=request.top_k)
    except Exception:
        logger.exception("[chat] Pipeline decision failed")
        raise HTTPException(
            status_code=500,
            detail="Hệ thống truy xuất dữ liệu gặp lỗi nội bộ. Vui lòng thử lại sau.",
        )

    if decision.behavior == "refused":
        latency = (time.perf_counter() - t_start) * 1000
        return ChatResponse(
            behavior="refused",
            answer=decision.message or "Câu hỏi nằm ngoài phạm vi hỗ trợ của trợ lý tuyển sinh UTH.",
            citations=[],
            citation_precision=None,
            refused_reason=decision.refused_reason,
            oos_categories=decision.oos_categories,
            latency_ms=round(latency, 2),
            year_used=decision.filter_year,
        )

    if decision.behavior == "clarify":
        latency = (time.perf_counter() - t_start) * 1000
        return ChatResponse(
            behavior="clarify",
            answer=decision.message or "Bạn vui lòng nói rõ thêm thông tin nhé.",
            citations=[],
            citation_precision=None,
            refused_reason=None,
            latency_ms=round(latency, 2),
            year_used=decision.filter_year,
        )

    chunks = decision.chunks
    logger.info(f"[chat] Retrieved {len(chunks)} chunks (year={decision.filter_year})")
    is_fallback = decision.is_fallback

    # -------------------------------------------------------------------
    # Generation — Gọi Gemini API (non-blocking thread pool)
    # -------------------------------------------------------------------
    try:
        gen_result = await asyncio.to_thread(
            generate_answer,
            query=query,
            chunks=chunks,
            filter_year=decision.filter_year,
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
            citation_precision=None,
            refused_reason="llm_refused",
            latency_ms=round(latency, 2),
            year_used=decision.filter_year,
        )

    # -------------------------------------------------------------------
    # Attribution Gate — Kiểm chứng trích dẫn & Factual Grounding
    # -------------------------------------------------------------------
    attr_result = check_attribution(
        cited_ids=gen_result.cited_ids,
        retrieved_chunks=chunks,
        response_text=gen_result.answer_text,
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
            citation_precision=None,
            refused_reason="attribution_gate_failed",
            latency_ms=round(latency, 2),
            year_used=decision.filter_year,
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
        year_used=decision.filter_year,
        fallback_warning_text=decision.message if is_fallback else None,
    )
