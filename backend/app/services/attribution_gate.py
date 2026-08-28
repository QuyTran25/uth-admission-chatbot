"""
attribution_gate.py — Lớp 2 kiểm chứng sau LLM (Post-generation Gate)

Kiểm tra tính xác thực của câu trả lời bằng 2 phương pháp:

1. Chunk ID check (áp dụng cho tất cả):
   - Mỗi [[chunk_id]] Gemini trích dẫn phải tồn tại trong tập chunks đã truy xuất
   - Không phụ thuộc LLM thêm — đối chiếu trực tiếp

2. Phương pháp phân loại kết quả:
   - passed=True:  Tất cả chunk_id hợp lệ VÀ citation_precision >= ngưỡng
   - passed=False: Có ít nhất 1 chunk_id không tồn tại HOẶC không trích dẫn gì cả
                   → Hệ thống trả về "không tìm thấy thông tin đủ tin cậy"

Ngưỡng Citation Precision: 0.90 (theo đề cương mục (2))
"""

import logging
from dataclasses import dataclass, field

logger = logging.getLogger("attribution_gate")

CITATION_PRECISION_THRESHOLD = 0.90


# ---------------------------------------------------------------------------
# Data class
# ---------------------------------------------------------------------------

@dataclass
class AttributionResult:
    passed: bool
    citation_precision: float     # valid_citations / total_citations (0.0 nếu không có trích dẫn)
    total_citations: int
    valid_citations: int
    failed_citations: list[str]   # chunk_id không tồn tại trong retrieved chunks
    method: str = "chunk_id"      # Hiện tại chỉ dùng chunk_id check


# ---------------------------------------------------------------------------
# Gate logic
# ---------------------------------------------------------------------------

def check_attribution(
    cited_ids: list[str],
    retrieved_chunks: list,       # list[ScoredChunk] từ retrieval_service
    is_refused: bool = False,
) -> AttributionResult:
    """
    Kiểm tra các chunk_id mà Gemini trích dẫn có thực sự tồn tại
    trong danh sách chunks đã được truy xuất hay không.

    Args:
        cited_ids:        Danh sách chunk_id từ GenerationResult.cited_ids
        retrieved_chunks: Các ScoredChunk trả về từ retrieval_service
        is_refused:       Nếu True (Gemini tự từ chối), Gate luôn passed=True

    Returns:
        AttributionResult
    """
    # Nếu Gemini đã từ chối → không cần kiểm tra attribution
    if is_refused:
        return AttributionResult(
            passed=True,
            citation_precision=1.0,
            total_citations=0,
            valid_citations=0,
            failed_citations=[],
            method="skipped_refused",
        )

    # Tập hợp chunk_id đã truy xuất
    retrieved_ids: set[str] = {c.chunk_id for c in retrieved_chunks}

    total = len(cited_ids)

    # Không trích dẫn gì → không thể kiểm chứng → fail
    if total == 0:
        logger.warning("attribution_gate: không có citation nào để kiểm chứng")
        return AttributionResult(
            passed=False,
            citation_precision=0.0,
            total_citations=0,
            valid_citations=0,
            failed_citations=[],
            method="chunk_id",
        )

    # Phân loại valid / invalid citations
    valid = [cid for cid in cited_ids if cid in retrieved_ids]
    failed = [cid for cid in cited_ids if cid not in retrieved_ids]

    precision = len(valid) / total
    passed = precision >= CITATION_PRECISION_THRESHOLD

    if failed:
        logger.warning(
            f"attribution_gate: {len(failed)}/{total} citations không hợp lệ: {failed}"
        )
    else:
        logger.info(
            f"attribution_gate: passed ({len(valid)}/{total} valid, precision={precision:.2f})"
        )

    return AttributionResult(
        passed=passed,
        citation_precision=round(precision, 4),
        total_citations=total,
        valid_citations=len(valid),
        failed_citations=failed,
        method="chunk_id",
    )


def build_citation_list(
    cited_ids: list[str],
    retrieved_chunks: list,
) -> list[dict]:
    """
    Xây dựng danh sách trích dẫn (citations) để trả về cho frontend.
    Chỉ bao gồm các chunk_id hợp lệ (đã được kiểm chứng qua attribution gate).

    Returns:
        list of {chunk_id, source_file, section_name, admission_year, source_urls}
    """
    chunk_map = {c.chunk_id: c for c in retrieved_chunks}
    citations = []
    for cid in cited_ids:
        chunk = chunk_map.get(cid)
        if chunk is None:
            continue  # Bỏ qua chunk không hợp lệ
        citations.append({
            "chunk_id": cid,
            "source_file": chunk.source_file,
            "section_name": chunk.section_name,
            "admission_year": chunk.admission_year,
            "source_urls": chunk.source_urls,
        })
    return citations
